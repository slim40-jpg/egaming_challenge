// ============================================================
// GAME_DISCOVERY.H - Game Discovery and Management
// ============================================================

#ifndef GAME_DISCOVERY_H
#define GAME_DISCOVERY_H

#include <windows.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <objbase.h>
#include <comdef.h>
#include <shellapi.h>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <tlhelp32.h>

#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "ole32.lib")

// ============================================================
// DATA STRUCTURES
// ============================================================

struct InstalledGame
{
    std::string name;
    std::string executable_path;
    std::string shortcut_path;
    std::string icon_path;
    bool is_running;
    std::string platform; // steam, epic, riot, standalone, etc.
    std::string game_id;  // Steam ID, etc.
};

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

// Desktop paths
std::string GetDesktopPath();
std::string GetPublicDesktopPath();

// Shortcut utilities
std::string GetGameNameFromShortcut(const std::string &shortcutPath);
std::string ResolveShortcutTarget(const std::string &shortcutPath);

// Process checking
bool IsProcessRunning(const std::string &exeName);
bool IsGameExecutable(const std::string &exeName, const std::string &shortcutName);

// Game discovery
std::vector<InstalledGame> ScanInstalledGames();
std::vector<InstalledGame> ScanGameLaunchers();

// Platform detection
std::string DetectGamePlatform(const std::string &path);

// Game status
void UpdateGameRunningStatus(std::vector<InstalledGame> &games);

#endif // GAME_DISCOVERY_H