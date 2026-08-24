// ============================================================
// FIXES FOR COMMON ERRORS
// ============================================================

#define _WIN32_WINNT 0x0600     // Enables LockWorkStation
#define _CRT_SECURE_NO_WARNINGS // Disables warnings about sprintf_s

// ============================================================
// HEADER FILES - IMPORTANT: winsock2.h MUST come BEFORE windows.h!
// ============================================================

#include <winsock2.h> // MUST BE FIRST! (before windows.h)
#include <ws2tcpip.h> // For modern networking functions
#include <windows.h>  // Now windows.h is safe to include

#include <iostream>   // For console output
#include <string>     // For std::string
#include <vector>     // For std::vector
#include <thread>     // For std::thread
#include <chrono>     // For std::chrono
#include <atomic>     // For std::atomic
#include <sstream>    // For std::stringstream
#include <fstream>    // For std::ifstream
#include <iphlpapi.h> // For IP Helper API
#include <setupapi.h> // For SetupAPI (USB detection)
#include <devguid.h>  // For device GUIDs
#include <cfgmgr32.h>
#include <pdh.h>
#include <pdhmsg.h>

#pragma comment(lib, "ws2_32.lib")   // Winsock library - for networking
#pragma comment(lib, "iphlpapi.lib") // IP Helper API - for network info
#pragma comment(lib, "setupapi.lib") // Setup API - for USB detection
#pragma comment(lib, "cfgmgr32.lib") // Configuration Manager - hardware info
#pragma comment(lib, "pdh.lib")

// ============================================================
// CONFIGURATION - Settings you can change
// ============================================================

// The server URL (change this to your server's IP)
const std::string SERVER_URL = "http://192.168.100.41:8000";

// How often to send heartbeats (in milliseconds)
const int HEARTBEAT_INTERVAL_MS = 10000; // 10 seconds

// How often to check for USB changes (in milliseconds)
const int USB_CHECK_INTERVAL_MS = 5000; // 5 seconds

// How often to poll for commands (in milliseconds)
const int COMMAND_POLL_INTERVAL_MS = 2000; // 2 seconds

// ============================================================
// GLOBAL STATE - The agent's current status
// ============================================================

std::string g_Hostname;            // This PC's name (e.g., "PC-GAMING-01")
std::string g_Status = "online";   // "online", "in_session", "locked"
std::atomic<bool> g_Running{true}; // Atomic = thread-safe flag to stop the agent
std::string g_SessionUser = "";    // Who's currently using the PC

// ============================================================
// HELPER FUNCTIONS - Small utilities used everywhere
// ============================================================

/**
 * Gets the computer's hostname.
 * Why: We need a unique identifier for this PC so the server knows which one we are.
 * Example: "PC-GAMING-01" or "DESKTOP-ABC123"
 */
std::string GetHostname()
{
    char buffer[256];
    DWORD size = sizeof(buffer);
    if (GetComputerNameA(buffer, &size))
    {
        return std::string(buffer);
    }
    return "UNKNOWN-PC";
}

/**
 * Gets the local IP address of this PC.
 * Why: The server needs to know where to send commands.
 * Example: "192.168.1.50"
 */
std::string GetLocalIP()
{
    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        return "127.0.0.1";
    }

    // Get the hostname
    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) != 0)
    {
        WSACleanup();
        return "127.0.0.1";
    }

    // Get all IP addresses for this host
    struct addrinfo *result = nullptr;
    struct addrinfo hints = {};
    hints.ai_family = AF_INET; // IPv4 only
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    hints.ai_flags = AI_PASSIVE;

    if (getaddrinfo(hostname, nullptr, &hints, &result) != 0)
    {
        WSACleanup();
        return "127.0.0.1";
    }

    // List to store all good IPs
    std::vector<std::string> goodIPs;
    std::string bestIP = "127.0.0.1";

    // Loop through all IPs
    for (struct addrinfo *ptr = result; ptr != nullptr; ptr = ptr->ai_next)
    {
        struct sockaddr_in *sockaddr_ipv4 = (struct sockaddr_in *)ptr->ai_addr;
        char ipBuffer[16];
        inet_ntop(AF_INET, &(sockaddr_ipv4->sin_addr), ipBuffer, sizeof(ipBuffer));
        std::string currentIP = std::string(ipBuffer);

        // ============================================
        // STEP 1: Skip obvious fake IPs
        // ============================================

        // Skip loopback (127.0.0.1)
        if (currentIP.substr(0, 4) == "127.")
            continue;

        // Skip link-local (169.254.x.x) - Tailscale, VPNs
        if (currentIP.substr(0, 7) == "169.254")
            continue;

        // Skip virtual adapters (192.168.56.x - VirtualBox/Hyper-V)
        if (currentIP.substr(0, 11) == "192.168.56.")
            continue;

        // Skip other common virtual adapter ranges
        if (currentIP.substr(0, 10) == "192.168.57." ||
            currentIP.substr(0, 10) == "192.168.58." ||
            currentIP.substr(0, 10) == "192.168.59." ||
            currentIP.substr(0, 10) == "192.168.60.")
            continue;

        // ============================================
        // STEP 2: Check if it's a REAL network IP
        // ============================================

        bool isPrivateIP = false;

        // Check for private IP ranges
        // 192.168.x.x
        if (currentIP.substr(0, 7) == "192.168")
            isPrivateIP = true;

        // 10.x.x.x
        if (currentIP.substr(0, 3) == "10.")
            isPrivateIP = true;

        // 172.16.x.x to 172.31.x.x
        if (currentIP.substr(0, 4) == "172.")
        {
            // Check if it's in the 16-31 range
            int secondOctet = 0;
            try
            {
                secondOctet = std::stoi(currentIP.substr(4, 2));
                if (secondOctet >= 16 && secondOctet <= 31)
                    isPrivateIP = true;
            }
            catch (...)
            {
                // Not a valid number
            }
        }

        // ============================================
        // STEP 3: Store the IP if it's good
        // ============================================

        if (isPrivateIP)
        {
            goodIPs.push_back(currentIP);

            // Prefer 192.168.x.x (most common for home/office networks)
            if (currentIP.substr(0, 7) == "192.168")
            {
                bestIP = currentIP;
                break; // Found a 192.168.x.x IP - use it immediately!
            }

            // If we haven't found a 192.168 IP yet, use this one
            if (bestIP == "127.0.0.1")
                bestIP = currentIP;
        }
    }

    freeaddrinfo(result);
    WSACleanup();

    // If we found good IPs but none were 192.168, use the first one
    if (!goodIPs.empty() && bestIP == "127.0.0.1")
    {
        bestIP = goodIPs[0];
    }

    // DEBUG: Print all found IPs (remove this later)
    std::cout << "[DEBUG] Found IPs: ";
    for (const auto &ip : goodIPs)
        std::cout << ip << " ";
    std::cout << std::endl;

    return bestIP;
}
/**
 * Creates a timestamp string for logging.
 * Why: So we know when events happened.
 * Example: "2026-08-24 14:30:25"
 */
std::string GetTimestamp()
{
    SYSTEMTIME st;
    GetSystemTime(&st);
    char buffer[64];
    sprintf_s(buffer, "%04d-%02d-%02d %02d:%02d:%02d",
              st.wYear, st.wMonth, st.wDay,
              st.wHour, st.wMinute, st.wSecond);
    return std::string(buffer);
}

/**
 * Logs a message to console and optionally to a file.
 * Why: Debugging - you can see what the agent is doing.
 */
void LogMessage(const std::string &message)
{
    std::cout << "[" << GetTimestamp() << "] " << message << std::endl;
}

// ============================================================
// HARDWARE MONITORING - Reading PC health
// ============================================================

/**
 * Gets CPU usage percentage.
 * Why: We need to monitor PC health (MVP requirement).
 *
 * HOW IT WORKS:
 * 1. We use GetSystemTimes() to get the amount of time the CPU has been:
 *    - Idle (doing nothing)
 *    - Kernel (doing system tasks)
 *    - User (running programs)
 * 2. We compare these values over a 1-second interval
 * 3. The difference tells us how busy the CPU was
 *
 * This is the Windows API way - no external libraries needed!
 */
int GetCPUUsage()
{
    // Static variables keep their value between function calls
    static FILETIME prevIdle = {0, 0};
    static FILETIME prevKernel = {0, 0};
    static FILETIME prevUser = {0, 0};
    static bool firstCall = true;

    FILETIME idleTime, kernelTime, userTime;

    // Get the current CPU times
    if (!GetSystemTimes(&idleTime, &kernelTime, &userTime))
    {
        return 0; // Error - return 0%
    }

    // Convert FILETIME to 64-bit integers for easier math
    auto FileTimeToULongLong = [](const FILETIME &ft) -> unsigned long long
    {
        return ((unsigned long long)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
    };

    if (firstCall)
    {
        // First call - just store the values and return 0
        prevIdle = idleTime;
        prevKernel = kernelTime;
        prevUser = userTime;
        firstCall = false;
        return 0;
    }

    // Calculate the differences
    unsigned long long idleDiff = FileTimeToULongLong(idleTime) - FileTimeToULongLong(prevIdle);
    unsigned long long kernelDiff = FileTimeToULongLong(kernelTime) - FileTimeToULongLong(prevKernel);
    unsigned long long userDiff = FileTimeToULongLong(userTime) - FileTimeToULongLong(prevUser);

    // Total time = kernel + user (idle is part of kernel)
    unsigned long long totalDiff = kernelDiff + userDiff;

    // Store current values for next call
    prevIdle = idleTime;
    prevKernel = kernelTime;
    prevUser = userTime;

    // Calculate usage percentage
    // If totalDiff is 0, avoid division by zero
    if (totalDiff == 0)
        return 0;

    // Idle percentage = (idleDiff / totalDiff) * 100
    // Usage percentage = 100 - idle percentage
    int cpuUsage = 100 - (int)((idleDiff * 100) / totalDiff);

    return cpuUsage;
}

/**
 * Gets RAM usage percentage.
 * Why: Monitor memory usage - important for gaming PCs.
 *
 * HOW IT WORKS:
 * 1. Get the total amount of RAM
 * 2. Get the amount of free RAM
 * 3. Calculate: (Total - Free) / Total * 100
 *
 * Uses GlobalMemoryStatusEx - the modern Windows API for memory info.
 */
int GetRAMUsage()
{
    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(MEMORYSTATUSEX);

    if (!GlobalMemoryStatusEx(&memStatus))
    {
        return 0; // Error
    }

    // dwMemoryLoad is the percentage of memory in use
    // Windows calculates this for us! So we just return it.
    return (int)memStatus.dwMemoryLoad;
}

/**
 * Gets CPU temperature (if available).
 * Why: This is a bonus feature - overheating is a big problem in gaming.
 *
 * NOTE: This is simplified. Getting CPU temp on Windows is complex.
 * You usually need to use WMI (Windows Management Instrumentation) or a library.
 *
 * For the MVP, we'll return a simulated value or 0 if not available.
 * In a real implementation, you'd use:
 * - WMI: Win32_TemperatureProbe
 * - OpenHardwareMonitor library
 * - Or read from CPU registers directly
 */
int GetCPUTemperature()
{
    // TODO: Implement actual CPU temperature reading
    // For now, return 0 (meaning "not available")
    //
    // In production, you'd use:
    // 1. WMI with COM calls
    // 2. Or a library like hwinfo (C++ library)
    return 0;
}

/**
 * Gets GPU usage percentage (if available).
 * Why: Monitor GPU performance - critical for gaming.
 *
 * Similar to CPU temp, this is complex on Windows.
 * For MVP, return 0 (not available).
 */
// ============================================================
// GPU MONITORING - Auto-Discovery Version
// ============================================================

/**
 * Discovers all available GPU Engine counter instances.
 * Returns a vector of full counter paths.
 */
std::vector<std::string> GetGPUCounterPaths()
{
    std::vector<std::string> paths;

    PDH_HQUERY query = nullptr;

    if (PdhOpenQueryA(nullptr, 0, &query) != ERROR_SUCCESS)
    {
        return paths;
    }

    DWORD bufferSize = 0;
    DWORD itemCount = 0;

    // Add wildcard counter temporarily
    PDH_HCOUNTER wildcardCounter = nullptr;

    PDH_STATUS status = PdhAddCounterA(
        query,
        "\\GPU Engine(*)\\Utilization Percentage",
        0,
        &wildcardCounter);

    if (status != ERROR_SUCCESS)
    {
        PdhCloseQuery(query);
        return paths;
    }

    PdhCollectQueryData(query);

    status = PdhGetFormattedCounterArrayA(
        wildcardCounter,
        PDH_FMT_DOUBLE,
        &bufferSize,
        &itemCount,
        nullptr);

    if (status == PDH_MORE_DATA && bufferSize > 0)
    {
        auto items = (PPDH_FMT_COUNTERVALUE_ITEM_A)
            HeapAlloc(
                GetProcessHeap(),
                HEAP_ZERO_MEMORY,
                bufferSize);

        if (items)
        {
            status = PdhGetFormattedCounterArrayA(
                wildcardCounter,
                PDH_FMT_DOUBLE,
                &bufferSize,
                &itemCount,
                items);

            if (status == ERROR_SUCCESS)
            {
                for (DWORD i = 0; i < itemCount; i++)
                {
                    std::string instanceName = items[i].szName;

                    // Build full counter path for this instance
                    std::string fullPath =
                        "\\GPU Engine(" +
                        instanceName +
                        ")\\Utilization Percentage";

                    paths.push_back(fullPath);
                }
            }

            HeapFree(GetProcessHeap(), 0, items);
        }
    }

    PdhCloseQuery(query);
    return paths;
}

/**
 * Gets total GPU usage by discovering all GPU engine instances
 * and summing their utilization.
 */
int GetGPUUsage()
{
    static PDH_HQUERY query = nullptr;
    static std::vector<PDH_HCOUNTER> counters;
    static bool initialized = false;
    static bool firstCall = true;
    static bool gpuAvailable = true;

    if (!initialized)
    {
        LogMessage("Initializing GPU monitoring...");

        // Open a query
        if (PdhOpenQueryA(nullptr, 0, &query) != ERROR_SUCCESS)
        {
            LogMessage("Failed to open PDH query");
            gpuAvailable = false;
            initialized = true;
            return 0;
        }

        // Add the wildcard counter - this gets ALL GPU engines
        PDH_HCOUNTER wildcardCounter = nullptr;
        PDH_STATUS status = PdhAddCounterA(
            query,
            "\\GPU Engine(*)\\Utilization Percentage",
            0,
            &wildcardCounter);

        if (status != ERROR_SUCCESS)
        {
            LogMessage("Failed to add GPU counter");
            PdhCloseQuery(query);
            query = nullptr;
            gpuAvailable = false;
            initialized = true;
            return 0;
        }

        // Collect data multiple times to get valid values
        LogMessage("Collecting GPU data...");
        PdhCollectQueryData(query);
        Sleep(500);
        PdhCollectQueryData(query);
        Sleep(500);
        PdhCollectQueryData(query);
        Sleep(500);

        // Get the counter array
        DWORD bufferSize = 0;
        DWORD itemCount = 0;

        status = PdhGetFormattedCounterArrayA(
            wildcardCounter,
            PDH_FMT_DOUBLE,
            &bufferSize,
            &itemCount,
            nullptr);

        if (status == PDH_MORE_DATA && bufferSize > 0)
        {
            auto items = (PPDH_FMT_COUNTERVALUE_ITEM_A)
                HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, bufferSize);

            if (items)
            {
                status = PdhGetFormattedCounterArrayA(
                    wildcardCounter,
                    PDH_FMT_DOUBLE,
                    &bufferSize,
                    &itemCount,
                    items);

                if (status == ERROR_SUCCESS)
                {
                    LogMessage("Found " + std::to_string(itemCount) + " GPU engine instances");

                    int addedCount = 0;
                    for (DWORD i = 0; i < itemCount; i++)
                    {
                        double value = items[i].FmtValue.doubleValue;

                        // ============================================
                        // KEY FIX: Only add if value is > 0
                        // ============================================
                        if (value > 0.0 && value <= 100.0)
                        {
                            std::string instanceName = items[i].szName;

                            // Build the full counter path
                            std::string fullPath =
                                "\\GPU Engine(" + instanceName + ")\\Utilization Percentage";

                            // Add this specific counter to our query
                            PDH_HCOUNTER specificCounter = nullptr;
                            PDH_STATUS addStatus = PdhAddCounterA(
                                query,
                                fullPath.c_str(),
                                0,
                                &specificCounter);

                            if (addStatus == ERROR_SUCCESS)
                            {
                                counters.push_back(specificCounter);
                                addedCount++;

                                // Log first few for debugging
                                if (addedCount <= 5)
                                {
                                    LogMessage("  Added: " + instanceName + " = " + std::to_string(value) + "%");
                                }
                            }
                        }
                    }

                    LogMessage("Added " + std::to_string(addedCount) + " GPU counters with positive values");
                }

                HeapFree(GetProcessHeap(), 0, items);
            }
        }

        if (counters.empty())
        {
            LogMessage("No GPU counters with positive values found");
            LogMessage("Try running a game or GPU-intensive task");
            PdhCloseQuery(query);
            query = nullptr;
            gpuAvailable = false;
            initialized = true;
            return 0;
        }

        initialized = true;
        firstCall = true;

        // First data collection
        PdhCollectQueryData(query);
        LogMessage("GPU monitoring initialized successfully! (" + std::to_string(counters.size()) + " active counters)");
        return 0;
    }

    // ============================================
    // Handle first call (returns 0 as baseline)
    // ============================================
    if (firstCall)
    {
        firstCall = false;
        PdhCollectQueryData(query);
        Sleep(100);
        return 0;
    }

    // ============================================
    // Check if GPU is available
    // ============================================
    if (!gpuAvailable || query == nullptr || counters.empty())
    {
        return 0;
    }

    // ============================================
    // Collect data (requires two ticks)
    // ============================================
    PdhCollectQueryData(query);
    Sleep(100);
    PdhCollectQueryData(query);

    // ============================================
    // Sum all GPU engine usages
    // ============================================
    double totalGpuUsage = 0.0;

    for (PDH_HCOUNTER counter : counters)
    {
        PDH_FMT_COUNTERVALUE counterValue;
        PDH_STATUS status = PdhGetFormattedCounterValue(
            counter,
            PDH_FMT_DOUBLE,
            nullptr,
            &counterValue);

        if (status == ERROR_SUCCESS)
        {
            double usage = counterValue.doubleValue;
            if (usage > 0.0 && usage <= 100.0)
            {
                totalGpuUsage += usage;
            }
        }
    }

    // ============================================
    // Return the total (capped at 100%)
    // ============================================
    if (totalGpuUsage > 100.0)
        totalGpuUsage = 100.0;
    if (totalGpuUsage < 0.0)
        totalGpuUsage = 0.0;

    return (int)totalGpuUsage;
}
/**
 * Collects ALL hardware information into a JSON-like string.
 * Why: This is the data we send to the server in the heartbeat.
 */
std::string GetHardwareTelemetry()
{
    int cpuUsage = GetCPUUsage();
    int ramUsage = GetRAMUsage();
    int cpuTemp = GetCPUTemperature();
    int gpuUsage = GetGPUUsage();

    // Build a JSON string manually (simpler than using a library for MVP)
    std::stringstream json;
    json << "{"
         << "\"hostname\":\"" << g_Hostname << "\","
         << "\"cpu_usage\":" << cpuUsage << ","
         << "\"ram_usage\":" << ramUsage << ","
         << "\"cpu_temperature\":" << cpuTemp << ","
         << "\"gpu_usage\":" << gpuUsage << ","
         << "\"status\":\"" << g_Status << "\","
         << "\"ip_address\":\"" << GetLocalIP() << "\","
         << "\"timestamp\":\"" << GetTimestamp() << "\""
         << "}";

    return json.str();
}

// ============================================================
// USB DETECTION - Anti-theft alert
// ============================================================

/**
 * Gets a list of all connected USB devices.
 * Why: We monitor USB devices so we can detect if someone unplugs a keyboard/mouse.
 *
 * HOW IT WORKS:
 * 1. We use SetupAPI (Windows hardware detection API)
 * 2. We ask for all devices in the "USB" device class
 * 3. We loop through them and collect their names
 * 4. We return a vector (list) of device names
 *
 * This is the standard Windows way to enumerate hardware.
 */
std::vector<std::string> GetUSBDevices()
{
    std::vector<std::string> devices;

    // Get a list of all devices in the "USB" class
    // GUID_DEVCLASS_USB is a special identifier for USB devices
    HDEVINFO deviceInfoSet = SetupDiGetClassDevs(
        &GUID_DEVCLASS_USB, // The USB device class GUID
        nullptr,            // No specific device
        nullptr,            // No window handle
        DIGCF_PRESENT       // Only devices that are currently plugged in
    );

    if (deviceInfoSet == INVALID_HANDLE_VALUE)
    {
        LogMessage("Failed to get USB device list");
        return devices;
    }

    // Loop through each device
    SP_DEVINFO_DATA deviceInfoData;
    deviceInfoData.cbSize = sizeof(SP_DEVINFO_DATA);

    DWORD deviceIndex = 0;
    while (SetupDiEnumDeviceInfo(deviceInfoSet, deviceIndex, &deviceInfoData))
    {
        deviceIndex++;

        // Get the device's friendly name (e.g., "Logitech G502 Mouse")
        char deviceName[256] = {0};
        if (SetupDiGetDeviceRegistryPropertyA(
                deviceInfoSet,
                &deviceInfoData,
                SPDRP_FRIENDLYNAME, // The friendly name property
                nullptr,
                (PBYTE)deviceName,
                sizeof(deviceName),
                nullptr))
        {
            // Only add if the name isn't empty
            if (strlen(deviceName) > 0)
            {
                devices.push_back(std::string(deviceName));
            }
        }
    }

    SetupDiDestroyDeviceInfoList(deviceInfoSet);
    return devices;
}

/**
 * Checks if any USB devices have been removed since the last check.
 * Why: This triggers the anti-theft alert.
 *
 * HOW IT WORKS:
 * 1. We store a list of USB devices from the previous check
 * 2. We get the current list
 * 3. We compare them
 * 4. If a device was in the old list but not the new list, it was unplugged
 */
bool CheckUSBRemoval(std::vector<std::string> &previousDevices)
{
    std::vector<std::string> currentDevices = GetUSBDevices();

    // Check if any device from the previous list is missing
    for (const std::string &oldDevice : previousDevices)
    {
        bool stillConnected = false;
        for (const std::string &newDevice : currentDevices)
        {
            if (oldDevice == newDevice)
            {
                stillConnected = true;
                break;
            }
        }
        if (!stillConnected)
        {
            // A device was removed!
            LogMessage("ALERT: USB device removed: " + oldDevice);
            previousDevices = currentDevices; // Update the list
            return true;                      // Yes, a device was removed
        }
    }

    // Update the list for next time
    previousDevices = currentDevices;
    return false; // No removal detected
}

// ============================================================
// NETWORK COMMUNICATION - Talking to the server
// ============================================================

/**
 * Sends an HTTP POST request to the server.
 * Why: This is how the agent communicates with the server.
 *
 * This is a simple HTTP client implementation using Windows sockets.
 *
 * FOR THE MVP: You could use a library like libcurl or cpprestsdk.
 * But this pure Windows implementation works without extra dependencies.
 */
bool SendHeartbeat(const std::string &hardwareData)
{
    LogMessage("Sending heartbeat to server...");

    // Parse the server URL
    std::string serverUrl = SERVER_URL;
    std::string host = serverUrl;
    std::string path = "/api/heartbeat";

    // Remove http:// from host
    size_t httpPos = host.find("://");
    if (httpPos != std::string::npos)
    {
        host = host.substr(httpPos + 3);
    }

    // Extract host and port
    std::string hostname = host;
    int port = 8000;
    size_t colonPos = host.find(":");
    if (colonPos != std::string::npos)
    {
        hostname = host.substr(0, colonPos);
        port = std::stoi(host.substr(colonPos + 1));
    }

    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        LogMessage("WSAStartup failed");
        return false;
    }

    // Create socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
    {
        LogMessage("Socket creation failed");
        WSACleanup();
        return false;
    }

    // Set up server address
    struct sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    serverAddr.sin_addr.s_addr = inet_addr(hostname.c_str());

    // Connect to server
    if (connect(sock, (struct sockaddr *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        LogMessage("Connection to server failed! Is the server running?");
        closesocket(sock);
        WSACleanup();
        return false;
    }

    // Build HTTP POST request
    std::string request =
        "POST " + path + " HTTP/1.1\r\n"
                         "Host: " +
        hostname + "\r\n"
                   "Content-Type: application/json\r\n"
                   "Content-Length: " +
        std::to_string(hardwareData.length()) + "\r\n"
                                                "Connection: close\r\n"
                                                "\r\n" +
        hardwareData;

    // Send request
    int bytesSent = send(sock, request.c_str(), request.length(), 0);
    if (bytesSent == SOCKET_ERROR)
    {
        LogMessage("Send failed");
        closesocket(sock);
        WSACleanup();
        return false;
    }

    // Receive response
    char buffer[1024];
    int bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0);
    if (bytesReceived > 0)
    {
        buffer[bytesReceived] = '\0';
        if (strstr(buffer, "200 OK") != nullptr)
        {
            LogMessage("Heartbeat sent successfully!");
        }
        else
        {
            LogMessage("Server responded but not with 200 OK");
        }
    }

    closesocket(sock);
    WSACleanup();
    return true;
}
/**
 * Polls the server for commands.
 * Why: The server needs to be able to send commands (lock, shutdown, etc.).
 *
 * HOW IT WORKS:
 * 1. We send a GET request to the server
 * 2. The server responds with a list of commands for this PC
 * 3. We execute each command
 */
void ExecuteCommand(const std::string &command, const std::string &parameter);

bool PollForCommands()
{
    LogMessage("Polling for commands...");

    // Create a simple HTTP GET request to the server
    std::string request =
        "GET /api/commands/" + g_Hostname + " HTTP/1.1\r\n"
                                            "Host: 192.168.100.41:8000\r\n"
                                            "Connection: close\r\n"
                                            "\r\n";

    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        LogMessage("WSAStartup failed");
        return false;
    }

    // Create socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
    {
        LogMessage("Socket creation failed");
        WSACleanup();
        return false;
    }

    // Set up server address
    struct sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8000);
    serverAddr.sin_addr.s_addr = inet_addr("192.168.100.41");

    // Connect to server
    if (connect(sock, (struct sockaddr *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        LogMessage("Connection failed - is the server running?");
        closesocket(sock);
        WSACleanup();
        return false;
    }

    LogMessage("Connected to server");

    // Send request
    send(sock, request.c_str(), request.length(), 0);
    LogMessage("Request sent");

    // Read ALL data until the connection closes
    std::string fullResponse;
    char buffer[4096];
    int bytesReceived;

    while ((bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0)
    {
        buffer[bytesReceived] = '\0';
        fullResponse += buffer;
        LogMessage("Received chunk: " + std::to_string(bytesReceived) + " bytes");
    }

    if (fullResponse.empty())
    {
        LogMessage("No response from server");
        closesocket(sock);
        WSACleanup();
        return false;
    }

    LogMessage("Total bytes received: " + std::to_string(fullResponse.length()));
    LogMessage("Full response: " + fullResponse);

    // Find the JSON body - look for the first '[' character
    size_t jsonStart = fullResponse.find('[');
    if (jsonStart == std::string::npos)
    {
        LogMessage("No JSON array found (no '[' character)");
        closesocket(sock);
        WSACleanup();
        return false;
    }

    // Extract from '[' to the end
    std::string jsonBody = fullResponse.substr(jsonStart);

    // Trim trailing whitespace
    while (!jsonBody.empty() && (jsonBody.back() == '\r' || jsonBody.back() == '\n' || jsonBody.back() == ' ' || jsonBody.back() == '\0'))
    {
        jsonBody.pop_back();
    }

    LogMessage("JSON Body: [" + jsonBody + "]");

    // Check for commands
    if (jsonBody.find("LOCK") != std::string::npos)
    {
        LogMessage(">>> EXECUTING LOCK");
        ExecuteCommand("LOCK", "");
        closesocket(sock);
        WSACleanup();
        return true;
    }
    else if (jsonBody.find("SHUTDOWN") != std::string::npos)
    {
        LogMessage(">>> EXECUTING SHUTDOWN");
        ExecuteCommand("SHUTDOWN", "");
        closesocket(sock);
        WSACleanup();
        return true;
    }
    else if (jsonBody.find("RESTART") != std::string::npos)
    {
        LogMessage(">>> EXECUTING RESTART");
        ExecuteCommand("RESTART", "");
        closesocket(sock);
        WSACleanup();
        return true;
    }
    else if (jsonBody.find("START_SESSION") != std::string::npos)
    {
        LogMessage(">>> EXECUTING START_SESSION");
        ExecuteCommand("START_SESSION", "Player");
        closesocket(sock);
        WSACleanup();
        return true;
    }
    else if (jsonBody.find("END_SESSION") != std::string::npos)
    {
        LogMessage(">>> EXECUTING END_SESSION");
        ExecuteCommand("END_SESSION", "");
        closesocket(sock);
        WSACleanup();
        return true;
    }
    else
    {
        LogMessage("No commands found in JSON");
    }

    closesocket(sock);
    WSACleanup();
    return false;
}

/**
 * Executes a command received from the server.
 * Why: This is how the admin controls the PC remotely.
 */
void ExecuteCommand(const std::string &command, const std::string &parameter = "")
{
    LogMessage("Executing command: " + command + " (param: " + parameter + ")");

    if (command == "LOCK")
    {
        // Lock the workstation (like pressing Win+L)
        // LockWorkStation() is a Windows API function
        if (LockWorkStation())
        {
            g_Status = "locked";
            LogMessage("Screen locked successfully");
        }
        else
        {
            LogMessage("Failed to lock screen");
        }
    }
    else if (command == "RESTART")
    {
        LogMessage("Restarting PC...");
        system("shutdown /r /t 10 /c \"Restarting by remote command\"");
    }
    else if (command == "SHUTDOWN")
    {
        LogMessage("Shutting down PC...");
        system("shutdown /s /t 10 /c \"Shutting down by remote command\"");
    }
    else if (command == "START_SESSION")
    {
        // Start a gaming session
        g_SessionUser = parameter.empty() ? "Player" : parameter;
        g_Status = "in_session";
        LogMessage("Session started for: " + g_SessionUser);
    }
    else if (command == "END_SESSION")
    {
        // End the gaming session
        LogMessage("Session ended for: " + g_SessionUser);
        g_SessionUser = "";
        g_Status = "online";
    }
    else
    {
        LogMessage("Unknown command: " + command);
    }
}

/**
 * Processes a list of commands from the server.
 */
void ProcessCommands(const std::vector<std::pair<std::string, std::string>> &commands)
{
    for (const auto &cmd : commands)
    {
        ExecuteCommand(cmd.first, cmd.second);
    }
}

// ============================================================
// MAIN AGENT THREAD - This is where the magic happens
// ============================================================

/**
 * The main agent loop.
 * Why: This runs continuously, doing all the work.
 *
 * This is the "heart" of the agent. It runs in its own thread
 * and performs all the tasks in a loop with small sleeps.
 *
 * The sleep is CRITICAL - it prevents the CPU from being overloaded.
 * With a 100ms sleep, the agent uses almost 0% CPU when idle.
 */
void AgentMainLoop()
{
    LogMessage("Agent main loop started");

    // Initialize USB monitoring
    std::vector<std::string> usbDevices = GetUSBDevices();

    // Main loop - runs until g_Running is set to false
    while (g_Running)
    {
        // === TASK 1: Check for USB removal (anti-theft) ===
        // We check every USB_CHECK_INTERVAL_MS milliseconds
        static auto lastUsbCheck = std::chrono::steady_clock::now();
        auto now = std::chrono::steady_clock::now();

        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastUsbCheck).count() >= USB_CHECK_INTERVAL_MS)
        {

            if (CheckUSBRemoval(usbDevices))
            {
                // A USB device was removed - send alert to server
                LogMessage("USB removal detected - sending alert");
                // TODO: Send alert to server
            }
            lastUsbCheck = now;
        }

        // === TASK 2: Send heartbeat to server ===
        // We send every HEARTBEAT_INTERVAL_MS milliseconds
        static auto lastHeartbeat = std::chrono::steady_clock::now();

        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastHeartbeat).count() >= HEARTBEAT_INTERVAL_MS)
        {

            // Get hardware data
            std::string hardwareData = GetHardwareTelemetry();

            // Send to server
            SendHeartbeat(hardwareData);
            lastHeartbeat = now;
        }

        // === TASK 3: Poll for commands ===
        // We poll every COMMAND_POLL_INTERVAL_MS milliseconds
        static auto lastCommandPoll = std::chrono::steady_clock::now();

        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastCommandPoll).count() >= COMMAND_POLL_INTERVAL_MS)
        {

            PollForCommands();
            lastCommandPoll = now;
        }

        // === CRITICAL: Sleep to prevent CPU hogging ===
        // This is why the agent uses almost 0% CPU!
        // We sleep for a short time, then loop again.
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    LogMessage("Agent main loop stopped");
}

// ============================================================
// MAIN ENTRY POINT - Where the program starts
// ============================================================

int main()
{
    // Initialize Winsock (for networking)
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cout << "Winsock initialization failed!" << std::endl;
        return 1;
    }

    // Get the hostname
    g_Hostname = GetHostname();

    // Print startup banner
    std::cout << "===========================================" << std::endl;
    std::cout << "   GAMING PC AGENT (C++)" << std::endl;
    std::cout << "===========================================" << std::endl;
    std::cout << "Hostname: " << g_Hostname << std::endl;
    std::cout << "IP: " << GetLocalIP() << std::endl;
    std::cout << "Status: " << g_Status << std::endl;
    std::cout << "===========================================" << std::endl;
    std::cout << "Server: " << SERVER_URL << std::endl;
    std::cout << "Heartbeat interval: " << HEARTBEAT_INTERVAL_MS / 1000 << "s" << std::endl;
    std::cout << "Press Ctrl+C to exit" << std::endl;
    std::cout << "===========================================" << std::endl;

    // Create the agent thread
    std::thread agentThread(AgentMainLoop);

    // Wait for user to press Enter to stop
    std::cout << "\nAgent is running. Press Enter to stop..." << std::endl;
    std::cin.get();

    // Signal the agent to stop
    g_Running = false;

    // Wait for the agent thread to finish
    if (agentThread.joinable())
    {
        agentThread.join();
    }

    // Cleanup Winsock
    WSACleanup();

    std::cout << "Agent stopped." << std::endl;
    return 0;
}