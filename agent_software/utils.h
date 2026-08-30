// Utils.h
#ifndef UTILS_H
#define UTILS_H

#include <string>
#include <vector>
#include <windows.h>

// String utilities
std::string ToLower(const std::string &str);
bool ContainsKeyword(const std::string &text, const std::vector<std::string> &keywords);

// System utilities
std::string GetHostname();
std::string GetMACAddress();
std::string GetLocalIP();
std::string GetTimestamp();
void LogMessage(const std::string &message);

// Window utilities
std::string GetActiveWindowTitle();
bool IsWindowFullscreen();
void GetWindowSize(int &width, int &height);

// Process utilities
DWORD GetProcessID(const std::string &processName);
std::string GetProcessName(DWORD pid);
bool IsProcessRunning(const std::string &processName);

#endif