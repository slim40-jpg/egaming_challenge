// Utils.cpp
#include "Utils.h"
#include <iphlpapi.h>
#include <psapi.h>
#include <sstream>
#include <algorithm>

#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "psapi.lib")

std::string ToLower(const std::string &str)
{
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

bool ContainsKeyword(const std::string &text, const std::vector<std::string> &keywords)
{
    std::string lowerText = ToLower(text);
    for (const auto &keyword : keywords)
    {
        if (lowerText.find(ToLower(keyword)) != std::string::npos)
        {
            return true;
        }
    }
    return false;
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

std::string GetMACAddress()
{
    // ... existing implementation ...
    return "00-00-00-00-00-00";
}

std::string GetLocalIP()
{
    // ... existing implementation ...
    return "127.0.0.1";
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
    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);
    int width = rect.right - rect.left;
    int height = rect.bottom - rect.top;
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

bool IsProcessRunning(const std::string &processName)
{
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE)
        return false;
    PROCESSENTRY32 pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32);
    bool found = false;
    if (Process32First(hSnapshot, &pe32))
    {
        do
        {
            if (processName == pe32.szExeFile)
            {
                found = true;
                break;
            }
        } while (Process32Next(hSnapshot, &pe32));
    }
    CloseHandle(hSnapshot);
    return found;
}