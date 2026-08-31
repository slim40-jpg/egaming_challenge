// ============================================================
// GAME_DISCOVERY.CPP - Game Discovery Implementation
// ============================================================

#include "game_discovery.h"
#include <sstream>
#include <fstream>
#include <cstdio>

// ============================================================
// DESKTOP PATH FUNCTIONS
// ============================================================

std::string GetDesktopPath()
{
    char desktopPath[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathA(NULL, CSIDL_DESKTOP, NULL, 0, desktopPath)))
    {
        std::string path(desktopPath);
        if (!path.empty() && path.back() != '\\')
        {
            path += '\\';
        }
        return path;
    }
    return "";
}

std::string GetPublicDesktopPath()
{
    char desktopPath[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathA(NULL, CSIDL_COMMON_DESKTOPDIRECTORY, NULL, 0, desktopPath)))
    {
        std::string path(desktopPath);
        if (!path.empty() && path.back() != '\\')
        {
            path += '\\';
        }
        return path;
    }
    return "";
}

// ============================================================
// SHORTCUT UTILITIES
// ============================================================

std::string GetGameNameFromShortcut(const std::string &shortcutPath)
{
    // Extract name without extension
    size_t lastSlash = shortcutPath.find_last_of("\\");
    std::string name = (lastSlash != std::string::npos) ? shortcutPath.substr(lastSlash + 1) : shortcutPath;

    // Remove .lnk extension
    size_t extPos = name.find(".lnk");
    if (extPos != std::string::npos)
    {
        name = name.substr(0, extPos);
    }

    // Remove .url extension
    extPos = name.find(".url");
    if (extPos != std::string::npos)
    {
        name = name.substr(0, extPos);
    }

    // Clean up common suffixes
    std::vector<std::string> suffixes = {
        " - Shortcut", " - Raccourci", " - Copy", " - Copie",
        " - shortcut", " - raccourci"};
    for (const auto &suffix : suffixes)
    {
        size_t pos = name.find(suffix);
        if (pos != std::string::npos)
        {
            name = name.substr(0, pos);
        }
    }

    // Trim spaces
    while (!name.empty() && name.back() == ' ')
        name.pop_back();

    return name;
}

std::string ResolveShortcutTarget(const std::string &shortcutPath)
{
    IShellLinkA *psl = NULL;
    IPersistFile *ppf = NULL;
    char targetPath[MAX_PATH] = {0};
    char workingDir[MAX_PATH] = {0};

    CoInitialize(NULL);

    HRESULT hr = CoCreateInstance(CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER,
                                  IID_IShellLinkA, (LPVOID *)&psl);
    if (SUCCEEDED(hr))
    {
        hr = psl->QueryInterface(IID_IPersistFile, (LPVOID *)&ppf);
        if (SUCCEEDED(hr))
        {
            WCHAR wsz[MAX_PATH];
            MultiByteToWideChar(CP_ACP, 0, shortcutPath.c_str(), -1, wsz, MAX_PATH);
            hr = ppf->Load(wsz, STGM_READ);
            if (SUCCEEDED(hr))
            {
                WIN32_FIND_DATAA wfd;
                // Try to resolve the shortcut
                hr = psl->Resolve(NULL, SLR_NO_UI | SLR_NOSEARCH);
                if (SUCCEEDED(hr))
                {
                    // Get the target path
                    if (psl->GetPath(targetPath, MAX_PATH, &wfd, SLGP_RAWPATH) == S_OK)
                    {
                        printf("[SHORTCUT] Resolved: %s -> %s\n", shortcutPath.c_str(), targetPath);
                    }
                }
                else
                {
                    // If resolve fails, try to get the path directly
                    if (psl->GetPath(targetPath, MAX_PATH, &wfd, SLGP_RAWPATH) == S_OK)
                    {
                        printf("[SHORTCUT] Direct path: %s -> %s\n", shortcutPath.c_str(), targetPath);
                    }
                }

                // If target is empty, try to get it from the working directory
                if (strlen(targetPath) == 0)
                {
                    // Try to get the target from the shortcut's arguments or working directory
                    // Some shortcuts might point to a URL or special location
                    if (psl->GetWorkingDirectory(workingDir, MAX_PATH) == S_OK)
                    {
                        printf("[SHORTCUT] Working directory: %s\n", workingDir);
                    }
                }
            }
            else
            {
                printf("[SHORTCUT] Failed to load: %s\n", shortcutPath.c_str());
            }
            ppf->Release();
        }
        else
        {
            printf("[SHORTCUT] Failed to get IPersistFile for: %s\n", shortcutPath.c_str());
        }
        psl->Release();
    }
    else
    {
        printf("[SHORTCUT] Failed to create IShellLink for: %s\n", shortcutPath.c_str());
    }

    CoUninitialize();

    // If target is empty, try to find it by searching the shortcut's directory
    if (strlen(targetPath) == 0)
    {
        // Try to find an .exe with the same name as the shortcut in the same directory
        std::string shortcutDir = shortcutPath.substr(0, shortcutPath.find_last_of("\\"));
        std::string shortcutName = shortcutPath.substr(shortcutPath.find_last_of("\\") + 1);
        size_t extPos = shortcutName.find(".lnk");
        if (extPos != std::string::npos)
        {
            shortcutName = shortcutName.substr(0, extPos);
        }

        // Search for .exe with the same name
        std::string exeSearch = shortcutDir + "\\" + shortcutName + ".exe";
        if (GetFileAttributesA(exeSearch.c_str()) != INVALID_FILE_ATTRIBUTES)
        {
            strcpy_s(targetPath, exeSearch.c_str());
            printf("[SHORTCUT] Found matching EXE: %s\n", targetPath);
        }
        else
        {
            printf("[SHORTCUT] No matching EXE found for: %s\n", shortcutPath.c_str());
        }
    }

    return std::string(targetPath);
}
// ============================================================
// PROCESS CHECKING
// ============================================================

bool IsProcessRunning(const std::string &exeName)
{
    if (exeName.empty())
        return false;

    std::string exeLower = exeName;
    std::transform(exeLower.begin(), exeLower.end(), exeLower.begin(), ::tolower);

    // Extract just the filename without path
    size_t lastSlash = exeLower.find_last_of("\\");
    if (lastSlash != std::string::npos)
    {
        exeLower = exeLower.substr(lastSlash + 1);
    }

    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE)
    {
        return false;
    }

    PROCESSENTRY32 pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32);

    bool found = false;
    if (Process32First(hSnapshot, &pe32))
    {
        do
        {
            std::string processName = pe32.szExeFile;
            std::transform(processName.begin(), processName.end(), processName.begin(), ::tolower);

            // Check if the process name matches the game executable
            if (processName == exeLower ||
                processName.find(exeLower) != std::string::npos ||
                exeLower.find(processName) != std::string::npos)
            {
                found = true;
                break;
            }
        } while (Process32Next(hSnapshot, &pe32));
    }

    CloseHandle(hSnapshot);
    return found;
}

bool IsGameExecutable(const std::string &exeName, const std::string &shortcutName)
{
    std::string exeLower = exeName;
    std::string nameLower = shortcutName;
    std::transform(exeLower.begin(), exeLower.end(), exeLower.begin(), ::tolower);
    std::transform(nameLower.begin(), nameLower.end(), nameLower.begin(), ::tolower);

    // Non-game keywords
    std::vector<std::string> nonGameKeywords = {
        "uninstall", "setup", "install", "config", "help",
        "readme", "license", "updater", "launcher", "helper",
        "visual studio", "code", "chrome", "firefox", "edge",
        "explorer", "cmd", "powershell", "terminal", "git",
        "notepad", "word", "excel", "powerpoint", "outlook",
        "calculator", "paint", "snipping", "media player"};

    // Check if it contains non-game keywords
    for (const auto &keyword : nonGameKeywords)
    {
        if (exeLower.find(keyword) != std::string::npos ||
            nameLower.find(keyword) != std::string::npos)
        {
            return false;
        }
    }

    // Check if it's a known game by extension (exe only)
    std::string ext = exeName.substr(exeName.find_last_of(".") + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (ext != "exe" && ext != "com")
    {
        return false;
    }

    return true;
}

// ============================================================
// DETECT GAME PLATFORM
// ============================================================

std::string DetectGamePlatform(const std::string &path)
{
    std::string pathLower = path;
    std::transform(pathLower.begin(), pathLower.end(), pathLower.begin(), ::tolower);

    if (pathLower.find("steam") != std::string::npos)
    {
        return "steam";
    }
    else if (pathLower.find("epic games") != std::string::npos ||
             pathLower.find("epicgames") != std::string::npos)
    {
        return "epic";
    }
    else if (pathLower.find("riot games") != std::string::npos ||
             pathLower.find("riotgames") != std::string::npos)
    {
        return "riot";
    }
    else if (pathLower.find("battle.net") != std::string::npos ||
             pathLower.find("battlenet") != std::string::npos)
    {
        return "battle.net";
    }
    else if (pathLower.find("ubisoft") != std::string::npos)
    {
        return "ubisoft";
    }
    else if (pathLower.find("origin") != std::string::npos ||
             pathLower.find("ea games") != std::string::npos)
    {
        return "ea";
    }
    else if (pathLower.find("gog") != std::string::npos)
    {
        return "gog";
    }
    else
    {
        return "standalone";
    }
}

// ============================================================
// UPDATE GAME RUNNING STATUS
// ============================================================

void UpdateGameRunningStatus(std::vector<InstalledGame> &games)
{
    for (auto &game : games)
    {
        std::string exeName = game.executable_path;
        size_t lastSlash = exeName.find_last_of("\\");
        if (lastSlash != std::string::npos)
        {
            exeName = exeName.substr(lastSlash + 1);
        }
        game.is_running = IsProcessRunning(exeName);
    }
}

// ============================================================
// SCAN INSTALLED GAMES
// ============================================================

std::vector<InstalledGame> ScanInstalledGames()
{
    std::vector<InstalledGame> games;
    std::vector<std::string> searchPaths;

    std::string userDesktop = GetDesktopPath();
    if (!userDesktop.empty())
    {
        searchPaths.push_back(userDesktop);
    }

    std::string publicDesktop = GetPublicDesktopPath();
    if (!publicDesktop.empty() && publicDesktop != userDesktop)
    {
        searchPaths.push_back(publicDesktop);
    }

    printf("[GAME SCAN] Scanning desktop for games...\n");

    for (const auto &searchPath : searchPaths)
    {
        if (searchPath.empty())
            continue;

        printf("[GAME SCAN] Searching in: %s\n", searchPath.c_str());

        std::string lnkSearch = searchPath + "*.lnk";
        WIN32_FIND_DATAA findData;
        HANDLE hFind = FindFirstFileA(lnkSearch.c_str(), &findData);

        if (hFind != INVALID_HANDLE_VALUE)
        {
            do
            {
                if (!(findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
                {
                    std::string shortcutPath = searchPath + findData.cFileName;
                    printf("[GAME SCAN] Found shortcut: %s\n", shortcutPath.c_str());

                    std::string targetPath = ResolveShortcutTarget(shortcutPath);
                    printf("[GAME SCAN] Resolved target: %s\n", targetPath.c_str());

                    if (!targetPath.empty())
                    {
                        std::string ext = targetPath.substr(targetPath.find_last_of(".") + 1);
                        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

                        if (ext == "exe" || ext == "com")
                        {
                            size_t lastSlash = targetPath.find_last_of("\\");
                            std::string exeName = (lastSlash != std::string::npos) ? targetPath.substr(lastSlash + 1) : targetPath;

                            std::string shortcutName = findData.cFileName;
                            size_t extPos = shortcutName.find(".lnk");
                            if (extPos != std::string::npos)
                            {
                                shortcutName = shortcutName.substr(0, extPos);
                            }

                            printf("[GAME SCAN] EXE: %s, Name: %s\n", exeName.c_str(), shortcutName.c_str());

                            if (IsGameExecutable(exeName, shortcutName))
                            {
                                bool isRunning = IsProcessRunning(exeName);
                                std::string platform = DetectGamePlatform(targetPath);

                                InstalledGame game;
                                game.name = shortcutName;
                                game.executable_path = targetPath;
                                game.shortcut_path = shortcutPath;
                                game.icon_path = shortcutPath;
                                game.is_running = isRunning;
                                game.platform = platform;
                                game.game_id = "";

                                games.push_back(game);
                                printf("[GAME SCAN] ✅ ADDED: %s -> %s\n",
                                       game.name.c_str(),
                                       game.executable_path.c_str());
                            }
                            else
                            {
                                printf("[GAME SCAN] ❌ SKIPPED: %s (not a game)\n", shortcutName.c_str());
                            }
                        }
                    }
                    else
                    {
                        printf("[GAME SCAN] ❌ Could not resolve target for: %s\n", shortcutPath.c_str());
                    }
                }
            } while (FindNextFileA(hFind, &findData));
            FindClose(hFind);
        }
    }

    // Remove duplicates
    std::map<std::string, InstalledGame> uniqueGames;
    for (const auto &game : games)
    {
        std::string key = game.name;
        if (uniqueGames.find(key) == uniqueGames.end() || game.is_running)
        {
            uniqueGames[key] = game;
        }
    }

    std::vector<InstalledGame> result;
    for (const auto &pair : uniqueGames)
    {
        result.push_back(pair.second);
    }

    std::sort(result.begin(), result.end(), [](const InstalledGame &a, const InstalledGame &b)
              { return a.name < b.name; });

    printf("[GAME SCAN] Total games found: %zu\n", result.size());

    return result;
}