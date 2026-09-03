// ============================================================
// GAME_DISCOVERY.CPP - Game Discovery Implementation
// ============================================================

#include "game_discovery.h"
#include <sstream>
#include <fstream>
#include <cstdio>
#include <set>

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
    size_t lastSlash = shortcutPath.find_last_of("\\");
    std::string name = (lastSlash != std::string::npos) ? shortcutPath.substr(lastSlash + 1) : shortcutPath;

    size_t extPos = name.find(".lnk");
    if (extPos != std::string::npos)
    {
        name = name.substr(0, extPos);
    }

    extPos = name.find(".url");
    if (extPos != std::string::npos)
    {
        name = name.substr(0, extPos);
    }

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

    while (!name.empty() && name.back() == ' ')
        name.pop_back();

    return name;
}

std::string ResolveShortcutTarget(const std::string &shortcutPath)
{
    IShellLinkA *psl = NULL;
    IPersistFile *ppf = NULL;
    char targetPath[MAX_PATH] = {0};

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
                hr = psl->Resolve(NULL, SLR_NO_UI | SLR_NOSEARCH);
                if (SUCCEEDED(hr))
                {
                    psl->GetPath(targetPath, MAX_PATH, &wfd, SLGP_RAWPATH);
                }
            }
            ppf->Release();
        }
        psl->Release();
    }

    CoUninitialize();

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

// ============================================================
// GAME DETECTION FILTER - UPDATED
// ============================================================

bool IsGameExecutable(const std::string &exeName, const std::string &shortcutName)
{
    std::string exeLower = exeName;
    std::string nameLower = shortcutName;
    std::transform(exeLower.begin(), exeLower.end(), exeLower.begin(), ::tolower);
    std::transform(nameLower.begin(), nameLower.end(), nameLower.begin(), ::tolower);

    // ============================================================
    // 1. BLOCK LIST - Applications that are definitely NOT games
    // ============================================================
    std::vector<std::string> blockList = {
        // Browsers
        "chrome", "firefox", "edge", "opera", "brave", "safari", "browser", "iexplore",

        // Development Tools
        "visual studio", "vscode", "code.exe", "clion", "pycharm", "intellij",
        "eclipse", "netbeans", "android studio", "xcode", "sublime", "notepad++",
        "postman", "docker", "virtualbox", "vmware", "git", "github", "gitbash",
        "powershell", "cmd", "terminal", "putty", "winscp", "filezilla",
        "cmake", "mingw", "cygwin", "msys2", "conemu", "kitty",

        // Adobe & Design
        "adobe", "photoshop", "premiere", "after effects", "illustrator", "indesign",
        "lightroom", "dreamweaver", "flash", "animate", "audition", "character animator",
        "acrobat", "reader", "creative cloud", "xd", "figma", "sketch",

        // Office & Productivity
        "microsoft office", "word", "excel", "powerpoint", "outlook", "access", "publisher",
        "onenote", "project", "visio", "teams", "skype", "slack", "zoom",
        "google", "spotify", "vlc", "media player", "winamp", "foobar",

        // Utilities
        "notepad", "calculator", "paint", "snipping", "snip", "magnifier",
        "winrar", "7-zip", "winzip", "ccleaner", "malwarebytes", "avast", "norton",
        "tailscale", "anydesk", "teamviewer", "remote desktop", "rdp",
        "vpn", "openvpn", "wireguard", "protonvpn", "nordvpn",

        // Audio/Video
        "audacity", "obs", "open broadcaster", "capcut", "deepsound", "waves",
        "fl studio", "ableton", "logic pro", "cubase", "protools",
        "davinci", "resolve", "final cut", "after effects",

        // Educational
        "cisco packet tracer", "wireshark", "nmap", "burp", "metasploit", "kali",
        "unity hub", "unreal engine", "godot", "musehub", "projectlibre",
        "matlab", "simulink", "autocad", "solidworks", "blender",

        // System
        "explorer", "svchost", "winlogon", "services", "taskmgr", "msconfig", "regedit",
        "control panel", "settings", "start menu", "shell", "command prompt",
        "one drive", "onedrive", "backup", "restore", "recovery",
        "windows defender", "security", "firewall", "update", "installer",

        // Game Launchers (not games themselves)
        "steam", "epic games", "origin", "battle.net", "gog", "ubisoft",
        "riot client", "nvidia", "amd", "intel", "graphics", "driver",
        "updater", "launcher", "patcher", "downloader", "updater",
        "gamebar", "game mode", "xbox", "game pass",

        // Cheat/Mod tools
        "cheat engine", "artmoney", "wemod", "we mod", "trainer",

        // Random system tools
        "msbuild", "dotnet", "nodejs", "python", "java", "jdk", "jre",
        "php", "mysql", "postgres", "mongodb", "redis", "elasticsearch",
        "docker desktop", "kubernetes", "kubectl", "minikube", "helm",

        // Social/Communication
        "discord", "telegram", "whatsapp", "signal", "messenger", "wechat",
        "line", "kakao", "viber", "snapchat", "tiktok", "instagram",

        // Download managers
        "utorrent", "qbittorrent", "transmission", "deluge", "aria2",

        // Other common apps
        "everything", "search", "launchy", "keypirinha", "wox"};

    // Check block list
    for (const auto &app : blockList)
    {
        if (exeLower.find(app) != std::string::npos ||
            nameLower.find(app) != std::string::npos)
        {
            return false;
        }
    }

    // ============================================================
    // 2. GAME INDICATORS - Keywords that suggest a game
    // ============================================================
    std::vector<std::string> gameIndicators = {
        // Game categories
        "game", "player", "play", "match", "tournament", "esports",
        "fps", "rpg", "mmo", "rts", "moba", "battle", "royale",

        // Sports games
        "fifa", "pes", "nba", "nfl", "mlb", "nhl", "f1", "moto", "wrc",
        "nfs", "need for speed", "forza", "gran turismo", "dirt",

        // FPS games
        "counter-strike", "csgo", "cs2", "valorant", "fortnite", "apex",
        "call of duty", "cod", "battlefield", "destiny", "halo", "gears",
        "doom", "quake", "wolfenstein", "titanfall", "medal of honor",
        "overwatch", "rainbow six", "siege", "pubg", "battle royale",

        // MOBA/RPG
        "league of legends", "lol", "dota", "smite", "heroes", "storm",
        "world of warcraft", "wow", "final fantasy", "xiv", "xiv",
        "elder scrolls", "skyrim", "oblivion", "morrowind",

        // Action/Adventure
        "grand theft auto", "gta", "red dead", "mafia", "saints row",
        "assassin's creed", "far cry", "watch dogs", "cyberpunk", "witcher",
        "dark souls", "elden ring", "sekiro", "bloodborne", "demon souls",
        "resident evil", "silent hill", "dead space", "outlast", "amnesia",
        "tomb raider", "uncharted", "last of us", "god of war",

        // Fighting games
        "mortal kombat", "street fighter", "tekken", "dead or alive",
        "guilty gear", "king of fighters", "soul calibur", "dragon ball",
        "naruto", "one piece", "demon slayer", "jump force", "dbz",
        "mugen", "blazblue", "skullgirls", "injustice",

        // Racing games
        "need for speed", "forza", "gran turismo", "project cars",
        "assetto corsa", "iracing", "r factor", "dirt", "wrc",
        "nascar", "f1", "moto gp", "ride", "mx vs atv",

        // Strategy games
        "starcraft", "warcraft", "age of empires", "civilization",
        "total war", "command & conquer", "red alert", "xcom",
        "crusader kings", "europa universalis", "hearts of iron",
        "stellaris", "rimworld", "factorio", "satisfactory",

        // Indie games
        "minecraft", "terraria", "stardew", "undertale", "cuphead",
        "hollow knight", "dead cells", "celeste", "hades", "risk of rain",
        "slay the spire", "darkest dungeon", "baba is you", "outer wilds",
        "disco elysium", "hades", "hades 2", "cult of the lamb",

        // Horror games
        "dead by daylight", "friday the 13th", "evil dead", "phasmophobia",
        "outlast", "amnesia", "fnaf", "five nights at freddy's",

        // Platform/Party games
        "mario", "sonic", "crash bandicoot", "spyro", "ratchet", "clank",
        "jackbox", "among us", "fall guys", "gang beasts", "ultimate chicken",

        // Game executables
        "game.exe", "client.exe", "launcher.exe", "play.exe", "start.exe"};

    // Check game indicators
    for (const auto &indicator : gameIndicators)
    {
        if (exeLower.find(indicator) != std::string::npos ||
            nameLower.find(indicator) != std::string::npos)
        {
            return true;
        }
    }

    // ============================================================
    // 3. PATH-BASED DETECTION - Check if in a game folder
    // ============================================================
    // We don't have full path here, but we can check common patterns
    // This is handled in ScanInstalledGames with the full path

    return false;
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
// GET GAME ICON
// ============================================================

std::string GetGameIcon(const std::string &gameName)
{
    std::string nameLower = gameName;
    std::transform(nameLower.begin(), nameLower.end(), nameLower.begin(), ::tolower);

    // FPS Games
    if (nameLower.find("counter-strike") != std::string::npos ||
        nameLower.find("csgo") != std::string::npos ||
        nameLower.find("cs2") != std::string::npos)
        return "🎯";
    if (nameLower.find("valorant") != std::string::npos)
        return "🔫";
    if (nameLower.find("fortnite") != std::string::npos)
        return "🎮";
    if (nameLower.find("call of duty") != std::string::npos ||
        nameLower.find("cod") != std::string::npos)
        return "🔫";
    if (nameLower.find("battlefield") != std::string::npos)
        return "⚔️";
    if (nameLower.find("overwatch") != std::string::npos)
        return "🎯";
    if (nameLower.find("apex") != std::string::npos)
        return "🔫";
    if (nameLower.find("destiny") != std::string::npos)
        return "🌟";
    if (nameLower.find("halo") != std::string::npos)
        return "🪖";
    if (nameLower.find("doom") != std::string::npos)
        return "😈";
    if (nameLower.find("quake") != std::string::npos)
        return "⚡";
    if (nameLower.find("rainbow six") != std::string::npos)
        return "🌈";
    if (nameLower.find("pubg") != std::string::npos)
        return "🪂";

    // MOBA Games
    if (nameLower.find("league of legends") != std::string::npos ||
        nameLower.find("lol") != std::string::npos)
        return "🏆";
    if (nameLower.find("dota") != std::string::npos)
        return "⚔️";
    if (nameLower.find("smite") != std::string::npos)
        return "⚡";

    // Sports Games
    if (nameLower.find("fifa") != std::string::npos)
        return "⚽";
    if (nameLower.find("pes") != std::string::npos)
        return "⚽";
    if (nameLower.find("nba") != std::string::npos)
        return "🏀";
    if (nameLower.find("nfl") != std::string::npos)
        return "🏈";
    if (nameLower.find("f1") != std::string::npos ||
        nameLower.find("formula") != std::string::npos)
        return "🏎️";
    if (nameLower.find("forza") != std::string::npos)
        return "🚗";
    if (nameLower.find("need for speed") != std::string::npos ||
        nameLower.find("nfs") != std::string::npos)
        return "🏎️";
    if (nameLower.find("rocket league") != std::string::npos)
        return "🚗";

    // Action/Adventure
    if (nameLower.find("gta") != std::string::npos ||
        nameLower.find("grand theft auto") != std::string::npos)
        return "🚗";
    if (nameLower.find("assassin") != std::string::npos)
        return "🗡️";
    if (nameLower.find("far cry") != std::string::npos)
        return "🏹";
    if (nameLower.find("cyberpunk") != std::string::npos)
        return "🤖";
    if (nameLower.find("witcher") != std::string::npos)
        return "🐺";
    if (nameLower.find("elden ring") != std::string::npos ||
        nameLower.find("dark souls") != std::string::npos)
        return "⚔️";
    if (nameLower.find("resident evil") != std::string::npos)
        return "🧟";

    // Fighting Games
    if (nameLower.find("mortal kombat") != std::string::npos)
        return "💀";
    if (nameLower.find("street fighter") != std::string::npos)
        return "👊";
    if (nameLower.find("tekken") != std::string::npos)
        return "👊";
    if (nameLower.find("dragon ball") != std::string::npos ||
        nameLower.find("dbz") != std::string::npos)
        return "🐉";
    if (nameLower.find("naruto") != std::string::npos)
        return "🍥";
    if (nameLower.find("mugen") != std::string::npos)
        return "👊";

    // RPG Games
    if (nameLower.find("world of warcraft") != std::string::npos ||
        nameLower.find("wow") != std::string::npos)
        return "🗡️";
    if (nameLower.find("final fantasy") != std::string::npos)
        return "⚔️";
    if (nameLower.find("skyrim") != std::string::npos ||
        nameLower.find("elder scrolls") != std::string::npos)
        return "🐉";
    if (nameLower.find("witcher") != std::string::npos)
        return "🐺";
    if (nameLower.find("diablo") != std::string::npos)
        return "😈";

    // Strategy Games
    if (nameLower.find("starcraft") != std::string::npos)
        return "🚀";
    if (nameLower.find("warcraft") != std::string::npos)
        return "⚔️";
    if (nameLower.find("age of empires") != std::string::npos)
        return "🏰";
    if (nameLower.find("civilization") != std::string::npos)
        return "🌍";
    if (nameLower.find("total war") != std::string::npos)
        return "⚔️";
    if (nameLower.find("xcom") != std::string::npos)
        return "👾";

    // Indie Games
    if (nameLower.find("minecraft") != std::string::npos)
        return "⛏️";
    if (nameLower.find("terraria") != std::string::npos)
        return "🌿";
    if (nameLower.find("stardew") != std::string::npos)
        return "🌾";
    if (nameLower.find("undertale") != std::string::npos)
        return "💛";
    if (nameLower.find("cuphead") != std::string::npos)
        return "☕";
    if (nameLower.find("hollow knight") != std::string::npos)
        return "🪲";
    if (nameLower.find("hades") != std::string::npos)
        return "🔥";

    // Platform/Party
    if (nameLower.find("among us") != std::string::npos)
        return "👾";
    if (nameLower.find("fall guys") != std::string::npos)
        return "🎮";
    if (nameLower.find("jackbox") != std::string::npos)
        return "📦";

    // Default
    return "🎮";
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
// SCAN INSTALLED GAMES - UPDATED
// ============================================================

std::vector<InstalledGame> ScanInstalledGames()
{
    std::vector<InstalledGame> games;
    std::vector<std::string> searchPaths;

    // Only scan desktop shortcuts (not all program files)
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

    // Also scan game launcher directories (but only for games, not launchers)
    std::vector<std::string> additionalPaths = {
        "C:\\Program Files\\Steam\\steamapps\\common\\",
        "C:\\Program Files (x86)\\Steam\\steamapps\\common\\",
        "C:\\Program Files\\Epic Games\\",
        "C:\\Program Files (x86)\\Epic Games\\",
        "C:\\Program Files\\Riot Games\\",
        "C:\\Program Files (x86)\\Riot Games\\",
        "C:\\Program Files\\Battle.net\\",
        "C:\\Program Files (x86)\\Battle.net\\",
        "C:\\Program Files\\Ubisoft\\Ubisoft Game Launcher\\games\\",
        "C:\\Program Files (x86)\\Ubisoft\\Ubisoft Game Launcher\\games\\",
        "C:\\Program Files\\Origin Games\\",
        "C:\\Program Files (x86)\\Origin Games\\",
        "C:\\Program Files\\GOG Galaxy\\Games\\",
        "C:\\Program Files (x86)\\GOG Galaxy\\Games\\"};

    for (const auto &path : additionalPaths)
    {
        searchPaths.push_back(path);
    }

    printf("[GAME SCAN] Scanning for games...\n");

    std::set<std::string> foundGames; // To avoid duplicates

    for (const auto &searchPath : searchPaths)
    {
        if (searchPath.empty())
            continue;

        // Scan for .lnk files
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
                    std::string targetPath = ResolveShortcutTarget(shortcutPath);

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

                            // Check if it's a game
                            if (IsGameExecutable(exeName, shortcutName))
                            {
                                // Check if we already have this game
                                std::string key = shortcutName;
                                if (foundGames.find(key) == foundGames.end())
                                {
                                    foundGames.insert(key);

                                    bool isRunning = IsProcessRunning(exeName);
                                    std::string platform = DetectGamePlatform(targetPath);
                                    std::string icon = GetGameIcon(shortcutName);

                                    InstalledGame game;
                                    game.name = shortcutName;
                                    game.executable_path = targetPath;
                                    game.shortcut_path = shortcutPath;
                                    game.icon_path = shortcutPath;
                                    game.is_running = isRunning;
                                    game.platform = platform;
                                    game.game_id = "";

                                    games.push_back(game);
                                    printf("[GAME SCAN] Found game: %s -> %s (%s)\n",
                                           game.name.c_str(),
                                           game.executable_path.c_str(),
                                           platform.c_str());
                                }
                            }
                        }
                    }
                }
            } while (FindNextFileA(hFind, &findData));
            FindClose(hFind);
        }

        // Also scan for direct .exe files in game directories
        // Only if the directory name suggests it's a game
        std::string dirName = searchPath;
        size_t lastSlash = dirName.find_last_of("\\");
        if (lastSlash != std::string::npos)
        {
            dirName = dirName.substr(0, lastSlash);
            lastSlash = dirName.find_last_of("\\");
            if (lastSlash != std::string::npos)
            {
                dirName = dirName.substr(lastSlash + 1);
            }
        }

        // Only scan if the directory name looks like it contains games
        std::string dirLower = dirName;
        std::transform(dirLower.begin(), dirLower.end(), dirLower.begin(), ::tolower);
        std::vector<std::string> gameDirKeywords = {
            "steamapps", "common", "epic", "riot", "battle", "ubisoft",
            "origin", "gog", "games", "game"};

        bool isGameDir = false;
        for (const auto &keyword : gameDirKeywords)
        {
            if (dirLower.find(keyword) != std::string::npos)
            {
                isGameDir = true;
                break;
            }
        }

        if (isGameDir)
        {
            std::string exeSearch = searchPath + "*.exe";
            hFind = FindFirstFileA(exeSearch.c_str(), &findData);

            if (hFind != INVALID_HANDLE_VALUE)
            {
                do
                {
                    if (!(findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
                    {
                        std::string exePath = searchPath + findData.cFileName;
                        std::string exeName = findData.cFileName;

                        // Check if it's a game
                        if (IsGameExecutable(exeName, exeName) &&
                            exeName.find("launcher") == std::string::npos &&
                            exeName.find("updater") == std::string::npos &&
                            exeName.find("installer") == std::string::npos)
                        {

                            std::string gameName = exeName.substr(0, exeName.find_last_of("."));
                            std::string key = gameName;

                            if (foundGames.find(key) == foundGames.end())
                            {
                                foundGames.insert(key);

                                bool isRunning = IsProcessRunning(exeName);
                                std::string platform = DetectGamePlatform(exePath);
                                std::string icon = GetGameIcon(gameName);

                                InstalledGame game;
                                game.name = gameName;
                                game.executable_path = exePath;
                                game.shortcut_path = "";
                                game.icon_path = exePath;
                                game.is_running = isRunning;
                                game.platform = platform;
                                game.game_id = "";

                                games.push_back(game);
                                printf("[GAME SCAN] Found game: %s -> %s (%s)\n",
                                       game.name.c_str(),
                                       game.executable_path.c_str(),
                                       platform.c_str());
                            }
                        }
                    }
                } while (FindNextFileA(hFind, &findData));
                FindClose(hFind);
            }
        }
    }

    // Remove duplicates (same game from different locations)
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