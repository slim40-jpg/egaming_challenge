// ============================================================
// GAMING PC AGENT - CLEAN VERSION (NO ML)
// ============================================================

#define _WIN32_WINNT 0x0A00
#define _CRT_SECURE_NO_WARNINGS

// ============================================================
// HEADER FILES
// ============================================================
#include "device_monitor.h"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <winsvc.h>
#include <map>
#include <iostream>
#include <algorithm>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <atomic>
#include <sstream>
#include <fstream>
#include <iphlpapi.h>
#include <setupapi.h>
#include <devguid.h>
#include <cfgmgr32.h>
#include <pdh.h>
#include <pdhmsg.h>
#include <tlhelp32.h>
#include <psapi.h>
#include <comdef.h>
#include <Wbemidl.h>
#include <d3d11.h>
#include <dxgi.h>
#include "game_discovery.h"

#pragma comment(lib, "wbemuuid.lib")
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "setupapi.lib")
#pragma comment(lib, "cfgmgr32.lib")
#pragma comment(lib, "pdh.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")

void LogMessage(const std::string &message);
bool ContainsKeyword(const std::string &text, const std::vector<std::string> &keywords);

// ============================================================
// STRING CONVERSION HELPERS
// ============================================================

std::string WCharToString(const WCHAR *wstr)
{
    if (!wstr)
        return "";
    int len = WideCharToMultiByte(CP_ACP, 0, wstr, -1, NULL, 0, NULL, NULL);
    if (len <= 0)
        return "";
    std::vector<char> buffer(len);
    WideCharToMultiByte(CP_ACP, 0, wstr, -1, buffer.data(), len, NULL, NULL);
    return std::string(buffer.data());
}

std::string GetProcessExeName(const PROCESSENTRY32 &pe32)
{
#ifdef UNICODE
    return WCharToString(pe32.szExeFile);
#else
    return std::string(pe32.szExeFile);
#endif
}

std::string GetModuleName(const MODULEENTRY32 &me32)
{
#ifdef UNICODE
    return WCharToString(me32.szModule);
#else
    return std::string(me32.szModule);
#endif
}

// ============================================================
// GAME DETECTOR CLASS  (unchanged)
// ============================================================

class GameDetector
{
private:
    std::vector<std::string> m_graphicsDlls;
    std::vector<std::string> m_nonGameKeywords;
    std::map<std::string, std::string> m_gameFriendlyNames;

public:
    GameDetector()
    {
        m_graphicsDlls = {
            "d3d9.dll", "d3d10.dll", "d3d11.dll", "d3d12.dll",
            "dxgi.dll", "vulkan-1.dll", "opengl32.dll",
            "libcef.dll", "nvcuda.dll", "amd_ags_x64.dll"};

        m_nonGameKeywords = {
            "explorer", "chrome", "firefox", "edge", "opera",
            "photoshop", "premiere", "after_effects", "blender",
            "unity", "unreal", "visual_studio", "code",
            "slack", "discord", "spotify", "vlc", "media_player",
            "excel", "word", "powerpoint", "outlook",
            "cmd", "powershell", "terminal", "git"};

        m_gameFriendlyNames = {
            {"cs2.exe", "Counter-Strike 2"},
            {"csgo.exe", "Counter-Strike 2"},
            {"fifa23.exe", "EA FC 24"},
            {"fifa24.exe", "EA FC 24"},
            {"valorant.exe", "Valorant"},
            {"fortnite.exe", "Fortnite"},
            {"mugen.exe", "MUGEN"},
            {"dbz.exe", "Dragon Ball Z"},
            {"NSUNSR.exe", "Naruto Storm Revolution"},
            {"dota2.exe", "Dota 2"},
            {"rocketleague.exe", "Rocket League"},
            {"League of Legends.exe", "League of Legends"},
            {"lol.exe", "League of Legends"},
            {"gta5.exe", "GTA V"}};
    }

    std::string ToLower(const std::string &str)
    {
        std::string result = str;
        std::transform(result.begin(), result.end(), result.begin(), ::tolower);
        return result;
    }

    std::string GetFriendlyGameName(const std::string &exeName)
    {
        auto it = m_gameFriendlyNames.find(exeName);
        if (it != m_gameFriendlyNames.end())
        {
            return it->second;
        }
        return CleanGameName(exeName);
    }

    bool IsExeRegisteredAsGame(const std::string &exeName)
    {
        HKEY hKey;
        const char *subkey = "Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR\\AppCaptureX";

        if (RegOpenKeyExA(HKEY_CURRENT_USER, subkey, 0, KEY_READ, &hKey) != ERROR_SUCCESS)
        {
            subkey = "Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR";
            if (RegOpenKeyExA(HKEY_CURRENT_USER, subkey, 0, KEY_READ, &hKey) != ERROR_SUCCESS)
            {
                return false;
            }
        }

        DWORD index = 0;
        char valueName[256];
        DWORD valueNameSize = 256;
        bool found = false;

        while (RegEnumValueA(hKey, index, valueName, &valueNameSize, NULL, NULL, NULL, NULL) == ERROR_SUCCESS)
        {
            std::string registeredExe = valueName;
            if (ToLower(registeredExe).find(ToLower(exeName)) != std::string::npos)
            {
                found = true;
                break;
            }
            index++;
            valueNameSize = 256;
        }

        RegCloseKey(hKey);
        return found;
    }

    bool IsProcessAGame(DWORD processID)
    {
        HANDLE hModuleSnap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, processID);
        if (hModuleSnap == INVALID_HANDLE_VALUE)
            return false;

        MODULEENTRY32 me32;
        me32.dwSize = sizeof(MODULEENTRY32);

        bool isGame = false;
        if (Module32First(hModuleSnap, &me32))
        {
            do
            {
                std::string moduleName = GetModuleName(me32);
                std::string moduleLower = ToLower(moduleName);

                for (const auto &dll : m_graphicsDlls)
                {
                    if (moduleLower == dll)
                    {
                        isGame = true;
                        break;
                    }
                }
            } while (Module32Next(hModuleSnap, &me32) && !isGame);
        }

        CloseHandle(hModuleSnap);
        return isGame;
    }

    bool IsProcessProbablyGame(const std::string &processName)
    {
        std::string lowerName = ToLower(processName);

        for (const auto &keyword : m_nonGameKeywords)
        {
            if (lowerName.find(keyword) != std::string::npos)
            {
                return false;
            }
        }

        std::vector<std::string> gamePatterns = {
            "game", "player", "play", "client", "server",
            "win64", "win32", "x64", "x86", "release"};

        for (const auto &pattern : gamePatterns)
        {
            if (lowerName.find(pattern) != std::string::npos)
            {
                return true;
            }
        }

        if (lowerName.length() < 20 && lowerName.find(".exe") != std::string::npos)
        {
            std::string nameWithoutExt = lowerName.substr(0, lowerName.find(".exe"));
            std::vector<std::string> commonWords = {"setup", "install", "config", "help", "readme"};
            for (const auto &word : commonWords)
            {
                if (nameWithoutExt == word)
                    return false;
            }
            return true;
        }

        return false;
    }

    bool IsProcessDefinitelyGame(DWORD processID)
    {
        HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, processID);
        if (!hProcess)
            return false;

        char processName[MAX_PATH];
        DWORD size = MAX_PATH;
        if (!QueryFullProcessImageNameA(hProcess, 0, processName, &size))
        {
            CloseHandle(hProcess);
            return false;
        }

        CloseHandle(hProcess);

        std::string fullPath(processName);
        size_t lastSlash = fullPath.find_last_of("\\");
        std::string exeName = (lastSlash != std::string::npos) ? fullPath.substr(lastSlash + 1) : fullPath;

        if (IsExeRegisteredAsGame(exeName))
            return true;
        if (IsProcessAGame(processID))
            return true;
        if (IsProcessProbablyGame(exeName))
            return true;

        return false;
    }

    std::string CleanGameName(const std::string &exeName)
    {
        std::string game = exeName;

        size_t extPos = game.find(".exe");
        if (extPos != std::string::npos)
        {
            game = game.substr(0, extPos);
        }

        std::vector<std::string> suffixes = {
            "-Shipping", "-Client", "-Server", "_Win64", "_x64",
            "Win64", "Win32", "x64", "x86", "Release", "Debug"};
        for (const auto &suffix : suffixes)
        {
            size_t pos = game.find(suffix);
            if (pos != std::string::npos)
            {
                game = game.substr(0, pos);
            }
        }

        size_t lastSlash = game.find_last_of("\\");
        if (lastSlash != std::string::npos)
        {
            game = game.substr(lastSlash + 1);
        }

        return game;
    }

    std::string GetCurrentGameName()
    {
        HWND hwnd = GetForegroundWindow();
        if (hwnd)
        {
            DWORD pid;
            GetWindowThreadProcessId(hwnd, &pid);
            if (IsProcessDefinitelyGame(pid))
            {
                HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid);
                if (hProcess)
                {
                    char processName[MAX_PATH];
                    DWORD size = MAX_PATH;
                    if (QueryFullProcessImageNameA(hProcess, 0, processName, &size))
                    {
                        CloseHandle(hProcess);
                        std::string fullPath(processName);
                        size_t lastSlash = fullPath.find_last_of("\\");
                        std::string exeName = (lastSlash != std::string::npos) ? fullPath.substr(lastSlash + 1) : fullPath;
                        return GetFriendlyGameName(exeName);
                    }
                    CloseHandle(hProcess);
                }
            }
        }

        HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (hSnapshot == INVALID_HANDLE_VALUE)
        {
            return "none";
        }

        PROCESSENTRY32 pe32;
        pe32.dwSize = sizeof(PROCESSENTRY32);

        if (Process32First(hSnapshot, &pe32))
        {
            do
            {
                if (pe32.th32ProcessID == 0 || pe32.th32ProcessID == 4)
                    continue;

                if (IsProcessDefinitelyGame(pe32.th32ProcessID))
                {
                    std::string exeName = GetProcessExeName(pe32);
                    CloseHandle(hSnapshot);
                    return GetFriendlyGameName(exeName);
                }
            } while (Process32Next(hSnapshot, &pe32));
        }

        CloseHandle(hSnapshot);
        return "none";
    }
};

GameDetector g_GameDetector;

// ============================================================
// CONTAINS KEYWORD
// ============================================================

bool ContainsKeyword(const std::string &text, const std::vector<std::string> &keywords)
{
    std::string lowerText = g_GameDetector.ToLower(text);
    for (const auto &keyword : keywords)
    {
        if (lowerText.find(g_GameDetector.ToLower(keyword)) != std::string::npos)
        {
            return true;
        }
    }
    return false;
}

// ============================================================
// CONFIGURATION
// ============================================================

std::string SERVER_URL;
const int DISCOVERY_PORT = 9000;
const int HEARTBEAT_INTERVAL_MS = 10000;
const int COMMAND_POLL_INTERVAL_MS = 2000;
const int TELEMETRY_INTERVAL_MS = 2000;

std::string g_Hostname;
std::string g_Status = "online";
std::atomic<bool> g_Running{true};
std::string g_SessionUser = "";

SERVICE_STATUS_HANDLE g_hServiceStatus = NULL;
SERVICE_STATUS g_ServiceStatus;
std::thread g_ServiceThread;

// ============================================================
// HELPER FUNCTIONS
// ============================================================

std::string GetMACAddress()
{
    PIP_ADAPTER_INFO pAdapterInfo = NULL;
    ULONG ulOutBufLen = sizeof(IP_ADAPTER_INFO);

    pAdapterInfo = (IP_ADAPTER_INFO *)malloc(sizeof(IP_ADAPTER_INFO));
    if (pAdapterInfo == NULL)
        return "00-00-00-00-00-00";

    DWORD dwRetVal = GetAdaptersInfo(pAdapterInfo, &ulOutBufLen);
    if (dwRetVal == ERROR_BUFFER_OVERFLOW)
    {
        free(pAdapterInfo);
        pAdapterInfo = (IP_ADAPTER_INFO *)malloc(ulOutBufLen);
        if (pAdapterInfo == NULL)
            return "00-00-00-00-00-00";
        dwRetVal = GetAdaptersInfo(pAdapterInfo, &ulOutBufLen);
    }

    if (dwRetVal != NO_ERROR)
    {
        free(pAdapterInfo);
        return "00-00-00-00-00-00";
    }

    PIP_ADAPTER_INFO pAdapter = pAdapterInfo;
    std::string macAddress = "00-00-00-00-00-00";

    while (pAdapter)
    {
        std::string description = pAdapter->Description;
        if (description.find("Virtual") == std::string::npos &&
            description.find("Loopback") == std::string::npos &&
            description.find("VPN") == std::string::npos &&
            description.find("TAP") == std::string::npos &&
            description.find("Tailscale") == std::string::npos &&
            description.find("VMware") == std::string::npos &&
            description.find("VirtualBox") == std::string::npos &&
            pAdapter->AddressLength == 6)
        {
            char mac[18];
            sprintf_s(mac, sizeof(mac), "%02X-%02X-%02X-%02X-%02X-%02X",
                      pAdapter->Address[0], pAdapter->Address[1],
                      pAdapter->Address[2], pAdapter->Address[3],
                      pAdapter->Address[4], pAdapter->Address[5]);
            macAddress = std::string(mac);
            break;
        }
        pAdapter = pAdapter->Next;
    }

    free(pAdapterInfo);
    return macAddress;
}

std::string GetCPUName()
{
    HKEY hKey;
    char cpuName[256] = "Unknown CPU";
    DWORD size = sizeof(cpuName);

    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE,
                      "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0",
                      0, KEY_READ, &hKey) == ERROR_SUCCESS)
    {
        if (RegQueryValueExA(hKey, "ProcessorNameString", NULL, NULL, (LPBYTE)cpuName, &size) == ERROR_SUCCESS)
        {
            RegCloseKey(hKey);
            std::string result(cpuName);
            while (!result.empty() && result.back() == ' ')
                result.pop_back();
            return result;
        }
        RegCloseKey(hKey);
    }
    return "Unknown CPU";
}

std::string GetGPUName()
{
    HKEY hKey;
    char gpuName[256] = "Unknown GPU";
    DWORD size = sizeof(gpuName);

    for (int i = 0; i < 10; i++)
    {
        char subkey[256];
        sprintf_s(subkey, "SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\%04d", i);
        if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, subkey, 0, KEY_READ, &hKey) == ERROR_SUCCESS)
        {
            if (RegQueryValueExA(hKey, "DriverDesc", NULL, NULL, (LPBYTE)gpuName, &size) == ERROR_SUCCESS)
            {
                RegCloseKey(hKey);
                std::string result(gpuName);
                while (!result.empty() && result.back() == ' ')
                    result.pop_back();
                return result;
            }
            RegCloseKey(hKey);
        }
    }
    return "Unknown GPU";
}

std::string GetRAMSize()
{
    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(MEMORYSTATUSEX);
    if (GlobalMemoryStatusEx(&memStatus))
    {
        unsigned long long totalRamGB = memStatus.ullTotalPhys / (1024 * 1024 * 1024);
        return std::to_string(totalRamGB) + " GB";
    }
    return "Unknown RAM";
}

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

std::string GetLocalIP()
{
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
        return "127.0.0.1";

    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) != 0)
    {
        WSACleanup();
        return "127.0.0.1";
    }

    struct addrinfo *result = nullptr;
    struct addrinfo hints = {};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    hints.ai_flags = AI_PASSIVE;

    if (getaddrinfo(hostname, nullptr, &hints, &result) != 0)
    {
        WSACleanup();
        return "127.0.0.1";
    }

    std::string bestIP = "127.0.0.1";

    for (struct addrinfo *ptr = result; ptr != nullptr; ptr = ptr->ai_next)
    {
        struct sockaddr_in *sockaddr_ipv4 = (struct sockaddr_in *)ptr->ai_addr;
        char ipBuffer[16];
        inet_ntop(AF_INET, &(sockaddr_ipv4->sin_addr), ipBuffer, sizeof(ipBuffer));
        std::string currentIP = std::string(ipBuffer);

        if (currentIP.substr(0, 4) == "127.")
            continue;
        if (currentIP.substr(0, 7) == "169.254")
            continue;
        if (currentIP.substr(0, 11) == "192.168.56.")
            continue;

        if (currentIP.substr(0, 7) == "192.168" || currentIP.substr(0, 3) == "10.")
        {
            bestIP = currentIP;
            break;
        }
        if (bestIP == "127.0.0.1")
            bestIP = currentIP;
    }

    freeaddrinfo(result);
    WSACleanup();
    return bestIP;
}

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

void LogMessage(const std::string &message)
{
    std::cout << "[" << GetTimestamp() << "] " << message << std::endl;
}

// ============================================================
// CPU TEMPERATURE
// ============================================================

int GetCPUTemperature()
{
    HKEY hKey;
    DWORD temp = 0;
    DWORD size = sizeof(temp);

    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE,
                      "HARDWARE\\ACPI\\ThermalZone\\TZ0\\_TMP",
                      0, KEY_READ, &hKey) == ERROR_SUCCESS)
    {
        if (RegQueryValueExA(hKey, "Temperature", NULL, NULL, (LPBYTE)&temp, &size) == ERROR_SUCCESS)
        {
            RegCloseKey(hKey);
            return (int)((temp / 10.0) - 273.15);
        }
        RegCloseKey(hKey);
    }

    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE,
                      "HARDWARE\\ACPI\\ThermalZone\\TZ00\\_TMP",
                      0, KEY_READ, &hKey) == ERROR_SUCCESS)
    {
        if (RegQueryValueExA(hKey, "Temperature", NULL, NULL, (LPBYTE)&temp, &size) == ERROR_SUCCESS)
        {
            RegCloseKey(hKey);
            return (int)((temp / 10.0) - 273.15);
        }
        RegCloseKey(hKey);
    }

    return 0;
}

// ============================================================
// HARDWARE MONITORING
// ============================================================

int GetCPUUsage()
{
    static FILETIME prevIdle = {0, 0};
    static FILETIME prevKernel = {0, 0};
    static FILETIME prevUser = {0, 0};
    static bool firstCall = true;

    FILETIME idleTime, kernelTime, userTime;
    if (!GetSystemTimes(&idleTime, &kernelTime, &userTime))
        return 0;

    auto FileTimeToULongLong = [](const FILETIME &ft) -> unsigned long long
    {
        return ((unsigned long long)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
    };

    if (firstCall)
    {
        prevIdle = idleTime;
        prevKernel = kernelTime;
        prevUser = userTime;
        firstCall = false;
        return 0;
    }

    unsigned long long idleDiff = FileTimeToULongLong(idleTime) - FileTimeToULongLong(prevIdle);
    unsigned long long kernelDiff = FileTimeToULongLong(kernelTime) - FileTimeToULongLong(prevKernel);
    unsigned long long userDiff = FileTimeToULongLong(userTime) - FileTimeToULongLong(prevUser);
    unsigned long long totalDiff = kernelDiff + userDiff;

    prevIdle = idleTime;
    prevKernel = kernelTime;
    prevUser = userTime;

    if (totalDiff == 0)
        return 0;
    return 100 - (int)((idleDiff * 100) / totalDiff);
}

int GetRAMUsage()
{
    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(MEMORYSTATUSEX);
    if (!GlobalMemoryStatusEx(&memStatus))
        return 0;
    return (int)memStatus.dwMemoryLoad;
}

// ============================================================
// GPU USAGE DETECTION
// ============================================================

int GetGPUUsageViaDXGI()
{
    IDXGIFactory1 *pFactory = nullptr;
    IDXGIAdapter1 *pAdapter = nullptr;

    HRESULT hr = CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void **)&pFactory);
    if (FAILED(hr) || pFactory == nullptr)
        return 0;

    hr = pFactory->EnumAdapters1(0, &pAdapter);
    if (FAILED(hr) || pAdapter == nullptr)
    {
        pFactory->Release();
        return 0;
    }

    DXGI_ADAPTER_DESC1 desc;
    pAdapter->GetDesc1(&desc);

    std::string gpuName = WCharToString(desc.Description);
    bool isRealGPU = (gpuName.find("Microsoft") == std::string::npos &&
                      gpuName.find("Basic") == std::string::npos &&
                      gpuName.find("Software") == std::string::npos &&
                      gpuName.find("Render") == std::string::npos);

    pAdapter->Release();
    pFactory->Release();

    if (!isRealGPU)
        return 0;

    std::string currentGame = g_GameDetector.GetCurrentGameName();
    int cpuUsage = GetCPUUsage();

    if (currentGame != "none")
    {
        if (cpuUsage > 70)
            return 85 + (cpuUsage - 70) / 6;
        else if (cpuUsage > 50)
            return 60 + (cpuUsage - 50) / 2;
        else
            return 40 + cpuUsage / 5;
    }
    else
    {
        if (cpuUsage > 60)
            return 20 + (cpuUsage - 60) / 4;
        else
            return cpuUsage / 5;
    }
}

int GetGPUUsageViaPDH()
{
    static PDH_HQUERY query = NULL;
    static PDH_HCOUNTER counter = NULL;
    static bool firstRun = true;

    if (firstRun)
    {
        firstRun = false;
        if (PdhOpenQueryA(NULL, 0, &query) == ERROR_SUCCESS)
        {
            const char *counterPaths[] = {
                "\\GPU Process Memory\\Usage",
                "\\GPU Engine\\Utilization Percentage",
                "\\GPU 0\\Utilization Percentage",
                "\\GPU 0\\Engine Utilization",
                "\\GPU 1\\Utilization Percentage"};
            for (int i = 0; i < 5 && counter == NULL; i++)
            {
                PdhAddCounterA(query, counterPaths[i], 0, &counter);
                if (counter != NULL)
                    break;
            }
            if (counter != NULL)
            {
                PdhCollectQueryData(query);
                Sleep(200);
                PdhCollectQueryData(query);
            }
        }
    }

    if (query == NULL || counter == NULL)
        return 0;

    PdhCollectQueryData(query);
    PDH_FMT_COUNTERVALUE counterVal;
    if (PdhGetFormattedCounterValue(counter, PDH_FMT_LONG, NULL, &counterVal) == ERROR_SUCCESS)
    {
        if (counterVal.CStatus == PDH_CSTATUS_VALID_DATA)
            return (int)counterVal.longValue;
    }
    return 0;
}

int GetGPUUsageViaNVIDIA()
{
    HKEY hKey;
    DWORD usage = 0;
    DWORD size = sizeof(usage);

    for (int i = 0; i < 10; i++)
    {
        char subkey[256];
        sprintf_s(subkey, "SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\%04d", i);
        if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, subkey, 0, KEY_READ, &hKey) == ERROR_SUCCESS)
        {
            char driverDesc[256];
            DWORD descSize = sizeof(driverDesc);
            if (RegQueryValueExA(hKey, "DriverDesc", NULL, NULL, (LPBYTE)driverDesc, &descSize) == ERROR_SUCCESS)
            {
                std::string desc = driverDesc;
                if (desc.find("NVIDIA") != std::string::npos ||
                    desc.find("AMD") != std::string::npos ||
                    desc.find("Radeon") != std::string::npos ||
                    desc.find("Intel") != std::string::npos)
                {
                    if (RegQueryValueExA(hKey, "Performance", NULL, NULL, (LPBYTE)&usage, &size) == ERROR_SUCCESS)
                    {
                        RegCloseKey(hKey);
                        if (usage > 0 && usage <= 100)
                            return (int)usage;
                    }
                }
            }
            RegCloseKey(hKey);
        }
    }
    return 0;
}

int GetGPUUsage()
{
    int usage = 0;

    usage = GetGPUUsageViaPDH();
    if (usage > 0 && usage <= 100)
        return usage;

    usage = GetGPUUsageViaNVIDIA();
    if (usage > 0 && usage <= 100)
        return usage;

    usage = GetGPUUsageViaDXGI();
    if (usage > 0 && usage <= 100)
        return usage;

    std::string currentGame = g_GameDetector.GetCurrentGameName();
    int cpuUsage = GetCPUUsage();

    if (currentGame != "none")
    {
        if (cpuUsage > 80)
            return 90;
        else if (cpuUsage > 60)
            return 75;
        else if (cpuUsage > 40)
            return 60;
        else
            return 45;
    }
    else
    {
        if (cpuUsage > 50)
            return 25;
        else
            return 10;
    }
}

// ============================================================
// TELEMETRY FUNCTIONS
// ============================================================

std::string GetActiveWindowTitle()
{
    HWND hwnd = GetForegroundWindow();
    if (!hwnd)
        return "";
    char title[256];
    GetWindowTextA(hwnd, title, sizeof(title));
    return std::string(title);
}

bool IsWindowFullscreen()
{
    HWND hwnd = GetForegroundWindow();
    if (!hwnd)
        return false;
    RECT rect;
    GetWindowRect(hwnd, &rect);
    int width = rect.right - rect.left;
    int height = rect.bottom - rect.top;
    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);
    return (width >= screenWidth * 0.85 && height >= screenHeight * 0.85);
}

void GetWindowSize(int &width, int &height)
{
    HWND hwnd = GetForegroundWindow();
    if (!hwnd)
    {
        width = 0;
        height = 0;
        return;
    }
    RECT rect;
    GetWindowRect(hwnd, &rect);
    width = rect.right - rect.left;
    height = rect.bottom - rect.top;
}

std::string CollectTelemetry()
{
    std::string currentGame = g_GameDetector.GetCurrentGameName();
    int cpuUsage = GetCPUUsage();
    int gpuUsage = GetGPUUsage();
    int ramUsage = GetRAMUsage();
    int cpuTemp = GetCPUTemperature();
    std::string windowTitle = GetActiveWindowTitle();
    bool isFullscreen = IsWindowFullscreen();
    int windowWidth = 0, windowHeight = 0;
    GetWindowSize(windowWidth, windowHeight);

    std::stringstream json;
    json << "{"
         << "\"process_name\":\"" << currentGame << "\","
         << "\"cpu_usage\":" << cpuUsage << ","
         << "\"gpu_usage\":" << gpuUsage << ","
         << "\"ram_usage\":" << ramUsage << ","
         << "\"cpu_temperature\":" << cpuTemp << ","
         << "\"window_title\":\"" << windowTitle << "\","
         << "\"is_fullscreen\":" << (isFullscreen ? 1 : 0) << ","
         << "\"window_width\":" << windowWidth << ","
         << "\"window_height\":" << windowHeight
         << "}";

    return json.str();
}

// ============================================================
// NETWORK FUNCTIONS
// ============================================================

std::string DiscoverServer(int timeout_seconds = 10)
{
    LogMessage("[DISCOVERY] Searching for server on the network...");
    LogMessage("[DISCOVERY] Listening on port " + std::to_string(DISCOVERY_PORT));

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        LogMessage("[DISCOVERY] WSAStartup failed");
        return "";
    }

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET)
    {
        LogMessage("[DISCOVERY] Socket creation failed");
        WSACleanup();
        return "";
    }

    BOOL broadcast = TRUE;
    setsockopt(sock, SOL_SOCKET, SO_BROADCAST, (char *)&broadcast, sizeof(broadcast));

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(DISCOVERY_PORT);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR)
    {
        LogMessage("[DISCOVERY] Failed to bind to port " + std::to_string(DISCOVERY_PORT));
        closesocket(sock);
        WSACleanup();
        return "";
    }

    DWORD timeout = timeout_seconds * 1000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char *)&timeout, sizeof(timeout));

    char buffer[256];
    struct sockaddr_in senderAddr;
    int senderAddrSize = sizeof(senderAddr);

    auto startTime = std::chrono::steady_clock::now();

    while (std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - startTime).count() < timeout_seconds)
    {
        int bytesReceived = recvfrom(sock, buffer, sizeof(buffer) - 1, 0,
                                     (struct sockaddr *)&senderAddr, &senderAddrSize);

        if (bytesReceived > 0)
        {
            buffer[bytesReceived] = '\0';
            std::string message(buffer);

            if (message.find("SERVER:") == 0)
            {
                std::string ip = message.substr(7);
                size_t colonPos = ip.find(':');
                if (colonPos != std::string::npos)
                    ip = ip.substr(0, colonPos);
                LogMessage("[DISCOVERY] ✅ Server found at: " + ip);
                closesocket(sock);
                WSACleanup();
                return ip;
            }
        }
    }

    LogMessage("[DISCOVERY] ❌ Server not found (timeout)");
    closesocket(sock);
    WSACleanup();
    return "";
}

// ============================================================
// SEND FUNCTIONS
// ============================================================

bool SendTelemetryToEndpoint(const std::string &data, const std::string &endpoint)
{
    if (SERVER_URL.empty())
        return false;

    std::string serverUrl = SERVER_URL;
    std::string host = serverUrl;
    std::string path = endpoint;

    size_t httpPos = host.find("://");
    if (httpPos != std::string::npos)
        host = host.substr(httpPos + 3);

    std::string hostname = host;
    int port = 8003;
    size_t colonPos = host.find(":");
    if (colonPos != std::string::npos)
    {
        hostname = host.substr(0, colonPos);
        port = std::stoi(host.substr(colonPos + 1));
    }

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        LogMessage("[TELEMETRY] WSAStartup failed");
        return false;
    }

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
    {
        LogMessage("[TELEMETRY] Socket creation failed");
        WSACleanup();
        return false;
    }

    struct sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    serverAddr.sin_addr.s_addr = inet_addr(hostname.c_str());

    if (connect(sock, (struct sockaddr *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        LogMessage("[TELEMETRY] Connection failed: " + std::to_string(WSAGetLastError()));
        closesocket(sock);
        WSACleanup();
        return false;
    }

    std::string request =
        "POST " + path + " HTTP/1.1\r\n"
                         "Host: " +
        hostname + "\r\n"
                   "Content-Type: application/json\r\n"
                   "Content-Length: " +
        std::to_string(data.length()) + "\r\n"
                                        "Connection: close\r\n"
                                        "\r\n" +
        data;

    int sent = send(sock, request.c_str(), request.length(), 0);
    if (sent == SOCKET_ERROR)
    {
        LogMessage("[TELEMETRY] Send failed: " + std::to_string(WSAGetLastError()));
        closesocket(sock);
        WSACleanup();
        return false;
    }

    char buffer[1024];
    recv(sock, buffer, sizeof(buffer) - 1, 0);
    closesocket(sock);
    WSACleanup();
    return true;
}

bool SendTelemetry()
{
    if (SERVER_URL.empty())
        return false;

    std::string telemetryData = CollectTelemetry();
    std::string macAddress = GetMACAddress();
    std::string cpuName = GetCPUName();
    std::string gpuName = GetGPUName();
    std::string ramSize = GetRAMSize();
    std::string ipAddress = GetLocalIP();

    std::stringstream json;
    json << "{"
         << "\"pc_id\":\"" << macAddress << "\","
         << "\"hostname\":\"" << g_Hostname << "\","
         << "\"ip_address\":\"" << ipAddress << "\","
         << "\"features\":" << telemetryData << ","
         << "\"hardware\":{"
         << "\"cpu\":\"" << cpuName << "\","
         << "\"gpu\":\"" << gpuName << "\","
         << "\"ram\":\"" << ramSize << "\""
         << "}"
         << "}";

    std::string data = json.str();
    LogMessage("[DEBUG] ===== SENDING TELEMETRY =====");
    LogMessage("[DEBUG] Data: " + data);
    LogMessage("[DEBUG] ==============================");
    return SendTelemetryToEndpoint(data, "/api/heartbeat");
}

// ============================================================
// SEND INSTALLED GAMES
// ============================================================

std::string EscapeJsonString(const std::string &input)
{
    std::string output;
    output.reserve(input.length() * 2);

    for (char c : input)
    {
        switch (c)
        {
        case '"':
            output += "\\\"";
            break;
        case '\\':
            output += "\\\\";
            break;
        case '\b':
            output += "\\b";
            break;
        case '\f':
            output += "\\f";
            break;
        case '\n':
            output += "\\n";
            break;
        case '\r':
            output += "\\r";
            break;
        case '\t':
            output += "\\t";
            break;
        default:
            if (c < 0x20)
            {
                char buf[7];
                sprintf_s(buf, "\\u%04x", c);
                output += buf;
            }
            else
                output += c;
            break;
        }
    }
    return output;
}

bool SendInstalledGames()
{
    if (SERVER_URL.empty())
        return false;

    std::vector<InstalledGame> games = ScanInstalledGames();
    std::string macAddress = GetMACAddress();

    printf("[GAME SEND] Sending %zu games to server\n", games.size());
    for (const auto &game : games)
    {
        printf("[GAME SEND] Game: %s\n", game.name.c_str());
        printf("[GAME SEND]   Executable: %s\n", game.executable_path.c_str());
        printf("[GAME SEND]   Shortcut: %s\n", game.shortcut_path.c_str());
        printf("[GAME SEND]   Running: %s\n", game.is_running ? "true" : "false");
    }

    std::stringstream json;
    json << "{"
         << "\"pc_id\":\"" << macAddress << "\","
         << "\"hostname\":\"" << g_Hostname << "\","
         << "\"games\":[";

    for (size_t i = 0; i < games.size(); i++)
    {
        const auto &game = games[i];
        json << "{"
             << "\"name\":\"" << EscapeJsonString(game.name) << "\","
             << "\"executable_path\":\"" << EscapeJsonString(game.executable_path) << "\","
             << "\"shortcut_path\":\"" << EscapeJsonString(game.shortcut_path) << "\","
             << "\"platform\":\"" << game.platform << "\","
             << "\"is_running\":" << (game.is_running ? "true" : "false")
             << "}";
        if (i < games.size() - 1)
            json << ",";
    }

    json << "]}";

    std::string data = json.str();
    printf("[GAME SEND] Full JSON: %s\n", data.c_str());
    return SendTelemetryToEndpoint(data, "/api/games/installed");
}

// ============================================================
// COMMAND EXECUTION
// ============================================================

void ExecuteCommand(const std::string &command, const std::string &parameter)
{
    LogMessage("[EXEC] Command received: " + command + " with param: " + parameter);

    if (command == "LOCK")
    {
        LogMessage("[EXEC] Attempting to lock workstation...");
        if (LockWorkStation())
        {
            g_Status = "locked";
            LogMessage("[EXEC] ✅ Screen locked successfully");
        }
        else
        {
            LogMessage("[EXEC] ❌ Failed to lock screen. Error: " + std::to_string(GetLastError()));
            LogMessage("[EXEC] 🔄 Trying alternative lock method...");
            system("rundll32.exe user32.dll,LockWorkStation");
            Sleep(500);
            g_Status = "locked";
        }
    }
    else if (command == "SHUTDOWN")
    {
        LogMessage("[EXEC] Attempting to shutdown system...");
        HANDLE hToken;
        TOKEN_PRIVILEGES tkp;

        if (OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
        {
            if (LookupPrivilegeValue(NULL, SE_SHUTDOWN_NAME, &tkp.Privileges[0].Luid))
            {
                tkp.PrivilegeCount = 1;
                tkp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

                if (AdjustTokenPrivileges(hToken, FALSE, &tkp, 0, (PTOKEN_PRIVILEGES)NULL, 0))
                {
                    if (GetLastError() == ERROR_SUCCESS)
                    {
                        if (ExitWindowsEx(EWX_SHUTDOWN | EWX_FORCE, SHTDN_REASON_MAJOR_OTHER))
                        {
                            LogMessage("[EXEC] ✅ Shutdown initiated successfully");
                            CloseHandle(hToken);
                            return;
                        }
                    }
                }
            }
            CloseHandle(hToken);
        }

        int result = system("shutdown /s /f /t 10 /c \"Gaming Agent: System shutdown initiated by admin\"");
        if (result == 0)
            LogMessage("[EXEC] ✅ Shutdown command sent successfully");
        else
        {
            system("powershell -Command \"Stop-Computer -Force\"");
            LogMessage("[EXEC] PowerShell shutdown attempted");
        }
    }
    else if (command == "RESTART")
    {
        LogMessage("[EXEC] Attempting to restart system...");
        HANDLE hToken;
        TOKEN_PRIVILEGES tkp;

        if (OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
        {
            if (LookupPrivilegeValue(NULL, SE_SHUTDOWN_NAME, &tkp.Privileges[0].Luid))
            {
                tkp.PrivilegeCount = 1;
                tkp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

                if (AdjustTokenPrivileges(hToken, FALSE, &tkp, 0, (PTOKEN_PRIVILEGES)NULL, 0))
                {
                    if (GetLastError() == ERROR_SUCCESS)
                    {
                        if (ExitWindowsEx(EWX_REBOOT | EWX_FORCE, SHTDN_REASON_MAJOR_OTHER))
                        {
                            LogMessage("[EXEC] ✅ Restart initiated successfully");
                            CloseHandle(hToken);
                            return;
                        }
                    }
                }
            }
            CloseHandle(hToken);
        }

        int result = system("shutdown /r /f /t 10 /c \"Gaming Agent: System restart initiated by admin\"");
        if (result == 0)
            LogMessage("[EXEC] ✅ Restart command sent successfully");
        else
        {
            system("powershell -Command \"Restart-Computer -Force\"");
            LogMessage("[EXEC] PowerShell restart attempted");
        }
    }
    else if (command == "START_SESSION")
    {
        g_SessionUser = parameter.empty() ? "Player" : parameter;
        g_Status = "in_session";
        LogMessage("[EXEC] ✅ Session started for: " + g_SessionUser);
    }
    else if (command == "END_SESSION")
    {
        LogMessage("[EXEC] Ending session...");
        g_SessionUser = "";
        g_Status = "online";
        LogMessage("[EXEC] ✅ Session ended");
    }
    else if (command == "LAUNCH_GAME")
    {
        LogMessage("🎮 Launching game: " + parameter);
        std::string gamePath = parameter;

        if (GetFileAttributesA(gamePath.c_str()) == INVALID_FILE_ATTRIBUTES)
        {
            LogMessage("❌ File not found: " + gamePath);

            std::string fileName = gamePath;
            size_t lastSlash = fileName.find_last_of("\\");
            if (lastSlash != std::string::npos)
                fileName = fileName.substr(lastSlash + 1);

            LogMessage("🔍 Searching for: " + fileName);

            std::vector<std::string> searchPaths = {
                "C:\\Program Files\\",
                "C:\\Program Files (x86)\\",
                "C:\\Users\\slims\\Downloads\\",
                "C:\\Users\\slims\\OneDrive\\Bureau\\",
                "C:\\Program Files\\Steam\\steamapps\\common\\",
                "C:\\Program Files (x86)\\Steam\\steamapps\\common\\"};

            bool found = false;
            for (const auto &path : searchPaths)
            {
                std::string fullPath = path + fileName;
                if (GetFileAttributesA(fullPath.c_str()) != INVALID_FILE_ATTRIBUTES)
                {
                    gamePath = fullPath;
                    found = true;
                    LogMessage("✅ Found at: " + gamePath);
                    break;
                }
            }

            if (!found)
            {
                std::string downloadPath = "C:\\Users\\slims\\Downloads\\";
                WIN32_FIND_DATAA findData;
                std::string searchPattern = downloadPath + "*.exe";
                HANDLE hFind = FindFirstFileA(searchPattern.c_str(), &findData);
                if (hFind != INVALID_HANDLE_VALUE)
                {
                    do
                    {
                        if (!(findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
                        {
                            std::string foundPath = downloadPath + findData.cFileName;
                            if (foundPath.find(fileName) != std::string::npos)
                            {
                                gamePath = foundPath;
                                found = true;
                                LogMessage("✅ Found in Downloads: " + gamePath);
                                break;
                            }
                        }
                    } while (FindNextFileA(hFind, &findData) && !found);
                    FindClose(hFind);
                }
            }

            if (!found)
            {
                LogMessage("❌ Could not find game: " + fileName);
                return;
            }
        }

        LogMessage("🚀 Attempting to launch: " + gamePath);
        HINSTANCE result = ShellExecuteA(NULL, "open", gamePath.c_str(), NULL, NULL, SW_SHOW);

        if ((intptr_t)result > 32)
        {
            LogMessage("✅ Game launched successfully: " + gamePath);
            SendTelemetry();
        }
        else
        {
            LogMessage("❌ Failed to launch game: " + gamePath);
            LogMessage("Error code: " + std::to_string((int)(intptr_t)result));
            std::string cmd = "start \"\" \"" + gamePath + "\"";
            int systemResult = system(cmd.c_str());
            if (systemResult == 0)
                LogMessage("✅ Alternative launch successful");
            else
                LogMessage("❌ Alternative launch failed with code: " + std::to_string(systemResult));
        }
    }
    else
    {
        LogMessage("[EXEC] ❌ Unknown command: " + command);
    }
}

bool PollForCommands()
{
    if (SERVER_URL.empty())
        return false;

    std::string serverUrl = SERVER_URL;
    std::string host = serverUrl;

    size_t httpPos = host.find("://");
    if (httpPos != std::string::npos)
        host = host.substr(httpPos + 3);

    std::string hostname = host;
    int port = 8003;
    size_t colonPos = host.find(":");
    if (colonPos != std::string::npos)
    {
        hostname = host.substr(0, colonPos);
        port = std::stoi(host.substr(colonPos + 1));
    }

    std::string macAddress = GetMACAddress();
    std::string path = "/api/commands/" + macAddress;

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
        return false;

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
    {
        WSACleanup();
        return false;
    }

    struct sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    serverAddr.sin_addr.s_addr = inet_addr(hostname.c_str());

    if (connect(sock, (struct sockaddr *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        closesocket(sock);
        WSACleanup();
        return false;
    }

    std::string request =
        "GET " + path + " HTTP/1.1\r\n"
                        "Host: " +
        hostname + "\r\n"
                   "Connection: close\r\n"
                   "\r\n";

    send(sock, request.c_str(), request.length(), 0);

    std::string fullResponse;
    char buffer[4096];
    int bytesReceived;

    while ((bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0)
    {
        buffer[bytesReceived] = '\0';
        fullResponse += buffer;
    }

    closesocket(sock);
    WSACleanup();

    bool hasCommands = false;
    if (!fullResponse.empty())
    {
        size_t jsonStart = fullResponse.find('[');
        if (jsonStart == std::string::npos)
            jsonStart = fullResponse.find('{');

        if (jsonStart != std::string::npos)
        {
            std::string jsonBody = fullResponse.substr(jsonStart);
            while (!jsonBody.empty() && (jsonBody.back() == '\r' || jsonBody.back() == '\n' || jsonBody.back() == ' ' || jsonBody.back() == '\0'))
                jsonBody.pop_back();

            LogMessage("[POLL] Response: " + jsonBody);

            if (!jsonBody.empty() && jsonBody != "[]" && jsonBody != "null")
            {
                size_t pos = 0;
                while (pos < jsonBody.length())
                {
                    size_t objStart = jsonBody.find("{", pos);
                    if (objStart == std::string::npos)
                        break;
                    size_t objEnd = jsonBody.find("}", objStart);
                    if (objEnd == std::string::npos)
                        break;

                    std::string cmdObj = jsonBody.substr(objStart, objEnd - objStart + 1);
                    pos = objEnd + 1;

                    std::string action = "";
                    size_t actionPos = cmdObj.find("\"action\"");
                    if (actionPos != std::string::npos)
                    {
                        size_t colonPos = cmdObj.find(":", actionPos);
                        if (colonPos != std::string::npos)
                        {
                            size_t quoteStart = cmdObj.find("\"", colonPos + 1);
                            if (quoteStart != std::string::npos)
                            {
                                size_t quoteEnd = cmdObj.find("\"", quoteStart + 1);
                                if (quoteEnd != std::string::npos)
                                    action = cmdObj.substr(quoteStart + 1, quoteEnd - quoteStart - 1);
                            }
                        }
                    }

                    std::string parameter = "";
                    size_t paramPos = cmdObj.find("\"parameter\"");
                    if (paramPos != std::string::npos)
                    {
                        size_t colonPos = cmdObj.find(":", paramPos);
                        if (colonPos != std::string::npos)
                        {
                            size_t quoteStart = cmdObj.find("\"", colonPos + 1);
                            if (quoteStart != std::string::npos)
                            {
                                size_t quoteEnd = cmdObj.find("\"", quoteStart + 1);
                                if (quoteEnd != std::string::npos)
                                {
                                    parameter = cmdObj.substr(quoteStart + 1, quoteEnd - quoteStart - 1);
                                    std::string unescaped;
                                    for (size_t i = 0; i < parameter.length(); i++)
                                    {
                                        if (parameter[i] == '\\' && i + 1 < parameter.length() && parameter[i + 1] == '\\')
                                        {
                                            unescaped += '\\';
                                            i++;
                                        }
                                        else
                                            unescaped += parameter[i];
                                    }
                                    parameter = unescaped;
                                }
                            }
                        }
                    }

                    LogMessage("[POLL] Command: '" + action + "', Param: '" + parameter + "'");

                    if (!action.empty())
                    {
                        if (action == "LAUNCH_GAME")
                        {
                            ExecuteCommand(action, parameter);
                            hasCommands = true;
                        }
                        else if (action == "LOCK")
                        {
                            ExecuteCommand(action, "");
                            hasCommands = true;
                        }
                        else if (action == "SHUTDOWN")
                        {
                            ExecuteCommand(action, "");
                            hasCommands = true;
                        }
                        else if (action == "RESTART")
                        {
                            ExecuteCommand(action, "");
                            hasCommands = true;
                        }
                        else if (action == "START_SESSION")
                        {
                            ExecuteCommand(action, parameter.empty() ? "Player" : parameter);
                            hasCommands = true;
                        }
                        else if (action == "END_SESSION")
                        {
                            ExecuteCommand(action, "");
                            hasCommands = true;
                        }
                    }
                }
            }
        }
    }

    return hasCommands;
}

// ============================================================
// DEVICE MONITORING THREAD (NEW - uses device_monitor.h)
// ============================================================

void DeviceMonitoringThread()
{
    // Initial snapshot of input devices (keyboards + mice)
    std::vector<InputDevice> previousDevices = GetInputDevices();

    LogMessage("[DEVICE] Monitoring input devices (keyboard + mouse)...");
    LogMessage("[DEVICE] Initial snapshot: " + std::to_string(previousDevices.size()) + " device(s)");
    for (const auto &dev : previousDevices)
    {
        LogMessage("[DEVICE]   " + dev.deviceClass + ": " + dev.name);
    }

    while (g_Running)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(5000));
        if (!g_Running)
            break;

        std::vector<InputDevice> currentDevices = GetInputDevices();

        // Detect removals
        std::vector<InputDevice> removed = DiffInputDevices(previousDevices, currentDevices);

        if (!removed.empty())
        {
            for (const auto &dev : removed)
            {
                LogMessage("[DEVICE] ⚠️ REMOVED: " + dev.deviceClass + " — " + dev.name);
            }

            // Send alert to server
            if (!SERVER_URL.empty())
            {
                std::string cpuName = GetCPUName();
                std::string gpuName = GetGPUName();
                std::string ramSize = GetRAMSize();

                std::stringstream json;
                json << "{"
                     << "\"pc_id\":\"" << GetMACAddress() << "\","
                     << "\"hostname\":\"" << g_Hostname << "\","
                     << "\"device_removed\":true,"
                     << "\"removed_devices\":[";

                for (size_t i = 0; i < removed.size(); i++)
                {
                    json << "{"
                         << "\"class\":\"" << removed[i].deviceClass << "\","
                         << "\"name\":\"" << EscapeJsonString(removed[i].name) << "\","
                         << "\"instance_id\":\"" << EscapeJsonString(removed[i].instanceId) << "\""
                         << "}";
                    if (i < removed.size() - 1)
                        json << ",";
                }

                json << "],"
                     << "\"hardware\":{"
                     << "\"cpu\":\"" << cpuName << "\","
                     << "\"gpu\":\"" << gpuName << "\","
                     << "\"ram\":\"" << ramSize << "\""
                     << "},"
                     << "\"timestamp\":\"" << GetTimestamp() << "\""
                     << "}";

                SendTelemetryToEndpoint(json.str(), "/api/heartbeat");
            }

            // Log newly connected devices too
            std::vector<InputDevice> added = DiffInputDevices(currentDevices, previousDevices);
            for (const auto &dev : added)
            {
                LogMessage("[DEVICE] ➕ CONNECTED: " + dev.deviceClass + " — " + dev.name);
            }
        }

        previousDevices = currentDevices;
    }

    LogMessage("[DEVICE] Monitoring stopped.");
}

// ============================================================
// AGENT MAIN LOOP
// ============================================================

void AgentMainLoop()
{
    LogMessage("Agent main loop started");

    // Start device monitoring thread
    std::thread deviceThread(DeviceMonitoringThread);

    auto lastCommandPoll = std::chrono::steady_clock::now();
    auto lastTelemetry = std::chrono::steady_clock::now();
    auto lastGameScan = std::chrono::steady_clock::now();

    while (g_Running)
    {
        auto now = std::chrono::steady_clock::now();

        // Send telemetry - every 2 seconds
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastTelemetry).count() >= TELEMETRY_INTERVAL_MS)
        {
            SendTelemetry();
            lastTelemetry = now;
        }

        // Scan for installed games - every 30 seconds
        if (std::chrono::duration_cast<std::chrono::seconds>(now - lastGameScan).count() >= 30)
        {
            SendInstalledGames();
            lastGameScan = now;
        }

        // Poll commands - every 2 seconds
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastCommandPoll).count() >= COMMAND_POLL_INTERVAL_MS)
        {
            PollForCommands();
            lastCommandPoll = now;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    if (deviceThread.joinable())
        deviceThread.join();

    LogMessage("Agent main loop stopped");
}

// ============================================================
// SERVICE FUNCTIONS
// ============================================================

void WINAPI ServiceCtrlHandler(DWORD dwCtrl)
{
    switch (dwCtrl)
    {
    case SERVICE_CONTROL_STOP:
    case SERVICE_CONTROL_SHUTDOWN:
        g_ServiceStatus.dwCurrentState = SERVICE_STOP_PENDING;
        SetServiceStatus(g_hServiceStatus, &g_ServiceStatus);
        g_Running = false;
        if (g_ServiceThread.joinable())
            g_ServiceThread.join();
        g_ServiceStatus.dwCurrentState = SERVICE_STOPPED;
        SetServiceStatus(g_hServiceStatus, &g_ServiceStatus);
        break;
    default:
        break;
    }
}

void WINAPI ServiceMain(DWORD argc, LPSTR *argv)
{
    g_ServiceStatus.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
    g_ServiceStatus.dwCurrentState = SERVICE_START_PENDING;
    g_ServiceStatus.dwControlsAccepted = SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN;
    g_ServiceStatus.dwWin32ExitCode = 0;
    g_ServiceStatus.dwServiceSpecificExitCode = 0;
    g_ServiceStatus.dwCheckPoint = 0;
    g_ServiceStatus.dwWaitHint = 30000;

    g_hServiceStatus = RegisterServiceCtrlHandlerA("GamingAgent", (LPHANDLER_FUNCTION)ServiceCtrlHandler);
    if (g_hServiceStatus == NULL)
        return;

    g_ServiceStatus.dwCurrentState = SERVICE_RUNNING;
    SetServiceStatus(g_hServiceStatus, &g_ServiceStatus);

    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);

    g_Hostname = GetHostname();
    g_Running = true;

    LogMessage("[SERVICE] Discovering server...");
    std::string serverIP = DiscoverServer(15);
    if (serverIP.empty())
    {
        LogMessage("[SERVICE] ⚠️ Server discovery failed, will retry in main loop");
        SERVER_URL = "";
    }
    else
    {
        SERVER_URL = "http://" + serverIP + ":8003";
        LogMessage("[SERVICE] ✅ Server discovered at: " + SERVER_URL);
    }

    g_ServiceThread = std::thread(AgentMainLoop);

    while (g_Running)
    {
        if (SERVER_URL.empty())
        {
            Sleep(30000);
            LogMessage("[SERVICE] Retrying server discovery...");
            serverIP = DiscoverServer(10);
            if (!serverIP.empty())
            {
                SERVER_URL = "http://" + serverIP + ":8003";
                LogMessage("[SERVICE] ✅ Server rediscovered at: " + SERVER_URL);
            }
        }
        else
        {
            Sleep(1000);
        }
    }

    if (g_ServiceThread.joinable())
        g_ServiceThread.join();

    WSACleanup();

    g_ServiceStatus.dwCurrentState = SERVICE_STOPPED;
    SetServiceStatus(g_hServiceStatus, &g_ServiceStatus);
}

// ============================================================
// SERVICE INSTALLATION FUNCTIONS
// ============================================================

void InstallService()
{
    SC_HANDLE hSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_CREATE_SERVICE);
    if (hSCManager)
    {
        char szPath[MAX_PATH];
        GetModuleFileNameA(NULL, szPath, MAX_PATH);

        SC_HANDLE hService = CreateServiceA(
            hSCManager, "GamingAgent", "Gaming Agent Service",
            SERVICE_ALL_ACCESS, SERVICE_WIN32_OWN_PROCESS,
            SERVICE_AUTO_START, SERVICE_ERROR_NORMAL,
            szPath, NULL, NULL, NULL, NULL, NULL);

        if (hService)
        {
            printf("[SUCCESS] Service 'GamingAgent' installed successfully!\n");
            CloseServiceHandle(hService);
        }
        else
        {
            printf("[ERROR] Failed to install service. Error: %d\n", GetLastError());
        }
        CloseServiceHandle(hSCManager);
    }
    else
    {
        printf("[ERROR] Failed to open Service Control Manager. Run as Administrator!\n");
    }
}

void UninstallService()
{
    SC_HANDLE hSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    if (hSCManager)
    {
        SC_HANDLE hService = OpenServiceA(hSCManager, "GamingAgent", SERVICE_ALL_ACCESS);
        if (hService)
        {
            SERVICE_STATUS status;
            if (QueryServiceStatus(hService, &status))
            {
                if (status.dwCurrentState != SERVICE_STOPPED)
                {
                    printf("Stopping service...\n");
                    ControlService(hService, SERVICE_CONTROL_STOP, &status);
                    Sleep(2000);
                }
            }

            if (DeleteService(hService))
                printf("[SUCCESS] Service 'GamingAgent' uninstalled!\n");
            else
                printf("[ERROR] Failed to uninstall service. Error: %d\n", GetLastError());
            CloseServiceHandle(hService);
        }
        else
        {
            printf("[ERROR] Service 'GamingAgent' not found.\n");
        }
        CloseServiceHandle(hSCManager);
    }
    else
    {
        printf("[ERROR] Failed to open Service Control Manager. Run as Administrator!\n");
    }
}

void StartService()
{
    SC_HANDLE hSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    if (hSCManager)
    {
        SC_HANDLE hService = OpenServiceA(hSCManager, "GamingAgent", SERVICE_ALL_ACCESS);
        if (hService)
        {
            if (StartServiceA(hService, 0, NULL))
                printf("[SUCCESS] Service 'GamingAgent' started!\n");
            else
                printf("[ERROR] Failed to start service. Error: %d\n", GetLastError());
            CloseServiceHandle(hService);
        }
        else
        {
            printf("[ERROR] Service 'GamingAgent' not found.\n");
        }
        CloseServiceHandle(hSCManager);
    }
    else
    {
        printf("[ERROR] Failed to open Service Control Manager. Run as Administrator!\n");
    }
}

void StopService()
{
    SC_HANDLE hSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    if (hSCManager)
    {
        SC_HANDLE hService = OpenServiceA(hSCManager, "GamingAgent", SERVICE_ALL_ACCESS);
        if (hService)
        {
            SERVICE_STATUS status;
            if (ControlService(hService, SERVICE_CONTROL_STOP, &status))
                printf("[SUCCESS] Service 'GamingAgent' stopped!\n");
            else
                printf("[ERROR] Failed to stop service. Error: %d\n", GetLastError());
            CloseServiceHandle(hService);
        }
        else
        {
            printf("[ERROR] Service 'GamingAgent' not found.\n");
        }
        CloseServiceHandle(hSCManager);
    }
    else
    {
        printf("[ERROR] Failed to open Service Control Manager. Run as Administrator!\n");
    }
}

void ShowServiceStatus()
{
    SC_HANDLE hSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    if (hSCManager)
    {
        SC_HANDLE hService = OpenServiceA(hSCManager, "GamingAgent", SERVICE_ALL_ACCESS);
        if (hService)
        {
            SERVICE_STATUS status;
            if (QueryServiceStatus(hService, &status))
            {
                const char *stateStr;
                switch (status.dwCurrentState)
                {
                case SERVICE_STOPPED:
                    stateStr = "STOPPED";
                    break;
                case SERVICE_RUNNING:
                    stateStr = "RUNNING";
                    break;
                default:
                    stateStr = "OTHER";
                    break;
                }
                printf("[STATUS] GamingAgent: %s\n", stateStr);
            }
            CloseServiceHandle(hService);
        }
        else
        {
            printf("[ERROR] Service 'GamingAgent' not found.\n");
        }
        CloseServiceHandle(hSCManager);
    }
    else
    {
        printf("[ERROR] Failed to open Service Control Manager. Run as Administrator!\n");
    }
}

// ============================================================
// MAIN ENTRY POINT
// ============================================================

int main()
{
    if (strstr(GetCommandLineA(), "--install"))
    {
        InstallService();
        return 0;
    }
    if (strstr(GetCommandLineA(), "--uninstall"))
    {
        UninstallService();
        return 0;
    }
    if (strstr(GetCommandLineA(), "--start"))
    {
        StartService();
        return 0;
    }
    if (strstr(GetCommandLineA(), "--stop"))
    {
        StopService();
        return 0;
    }
    if (strstr(GetCommandLineA(), "--status"))
    {
        ShowServiceStatus();
        return 0;
    }

    if (GetStdHandle(STD_OUTPUT_HANDLE) == NULL)
    {
        SERVICE_TABLE_ENTRYA ServiceTable[] = {
            {(LPSTR) "GamingAgent", (LPSERVICE_MAIN_FUNCTIONA)ServiceMain},
            {NULL, NULL}};
        StartServiceCtrlDispatcherA(ServiceTable);
        return 0;
    }

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cout << "Winsock initialization failed!" << std::endl;
        return 1;
    }

    g_Hostname = GetHostname();

    // ─── Show input devices at startup ───
    auto devices = GetInputDevices();
    std::cout << "===========================================" << std::endl;
    std::cout << "   INPUT DEVICES DETECTED" << std::endl;
    std::cout << "===========================================" << std::endl;
    for (const auto &device : devices)
    {
        std::cout << device.deviceClass << ": " << device.name << " [OK]" << std::endl;
    }
    std::cout << "===========================================" << std::endl;
    std::cout << "   GAMING PC AGENT (C++)" << std::endl;
    std::cout << "===========================================" << std::endl;
    std::cout << "Hostname: " << g_Hostname << std::endl;
    std::cout << "MAC: " << GetMACAddress() << std::endl;
    std::cout << "IP: " << GetLocalIP() << std::endl;
    std::cout << "CPU: " << GetCPUName() << std::endl;
    std::cout << "GPU: " << GetGPUName() << std::endl;
    std::cout << "RAM: " << GetRAMSize() << std::endl;
    std::cout << "Status: " << g_Status << std::endl;
    std::cout << "===========================================" << std::endl;

    std::cout << "Discovering server on the network..." << std::endl;
    std::string serverIP = DiscoverServer(10);

    if (serverIP.empty())
    {
        std::cout << "[ERROR] Could not find server!" << std::endl;
        std::cout << "Make sure the server is running." << std::endl;
        std::cout << "Press Enter to exit..." << std::endl;
        std::cin.get();
        WSACleanup();
        return 1;
    }

    SERVER_URL = "http://" + serverIP + ":8003";
    std::cout << "✅ Server found at: " << SERVER_URL << std::endl;
    std::cout << "===========================================" << std::endl;
    std::cout << "Agent is running. Press Enter to stop..." << std::endl;

    std::thread agentThread(AgentMainLoop);

    std::cin.get();

    g_Running = false;

    if (agentThread.joinable())
        agentThread.join();

    WSACleanup();

    std::cout << "Agent stopped." << std::endl;
    return 0;
}