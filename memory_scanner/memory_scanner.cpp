// ============================================================
// STANDALONE MEMORY SCANNER - DETECTS MATCH END VIA RAM
// COMPLETE VERSION WITH YOUR GAME DETECTOR INTEGRATED
// ============================================================

#define _WIN32_WINNT 0x0600
#define _CRT_SECURE_NO_WARNINGS

#include <windows.h>
#include <tlhelp32.h>
#include <psapi.h>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <chrono>
#include <thread>
#include <sstream>
#include <fstream>
#include <regex>
#include <map>

#pragma comment(lib, "psapi.lib")

// ============================================================
// LOGGING
// ============================================================

void LogMessage(const std::string &message)
{
    SYSTEMTIME st;
    GetSystemTime(&st);
    char buffer[64];
    sprintf_s(buffer, "%02d:%02d:%02d", st.wHour, st.wMinute, st.wSecond);
    std::cout << "[" << buffer << "] " << message << std::endl;
}

// ============================================================
// STRING HELPERS
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

std::string ToLower(const std::string &str)
{
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

std::string CleanString(const std::string &str)
{
    std::string result;
    for (char c : str)
    {
        if (c >= 32 && c <= 126)
            result += c;
    }
    result.erase(std::remove(result.begin(), result.end(), '\0'), result.end());
    return result;
}

std::string ToHexString(uintptr_t addr)
{
    char buffer[32];
    sprintf_s(buffer, "%llX", (unsigned long long)addr);
    return std::string(buffer);
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

// ============================================================
// FILTER FALSE POSITIVES
// ============================================================

bool IsFalsePositive(const std::string &value)
{
    // Skip Windows system paths
    if (value.find("Windows") != std::string::npos)
        return true;
    if (value.find("System32") != std::string::npos)
        return true;
    if (value.find("SysWOW64") != std::string::npos)
        return true;
    if (value.find("dxilconv") != std::string::npos)
        return true;
    if (value.find(".dll") != std::string::npos)
        return true;
    if (value.find(".exe") != std::string::npos)
        return true;
    if (value.find("C:") != std::string::npos)
        return true;
    if (value.find(":\\") != std::string::npos)
        return true;

    // Skip if the value is too short or just common words
    if (value.length() < 3)
        return true;
    if (value == "Win" || value == "win" || value == "WIN")
        return true;
    if (value == "Lose" || value == "lose" || value == "LOSE")
        return true;
    if (value == "Menu" || value == "menu" || value == "MENU")
        return true;

    return false;
}

// ============================================================
// GAME PATTERNS DATABASE
// ============================================================

struct GamePatterns
{
    std::string game_name;
    std::vector<std::string> process_names;
    std::vector<std::string> match_end_patterns;
    std::vector<std::string> win_patterns;
    std::vector<std::string> lose_patterns;
    std::vector<std::string> match_start_patterns;
    std::vector<std::string> menu_patterns;
};

// ============================================================
// UPDATED GAME PATTERNS - MORE SPECIFIC!
// ============================================================

std::vector<GamePatterns> GetGamePatterns()
{
    std::vector<GamePatterns> patterns;

    // ============================================================
    // NARUTO / DBZ / MUGEN - SPECIFIC PATTERNS
    // ============================================================
    GamePatterns naruto;
    naruto.game_name = "Naruto / DBZ";
    naruto.process_names = {"NSUNSR.exe", "Dbz-me-2.exe", "MUGEN.exe", "Naruto.exe", "Dbz.exe"};

    // USE MORE SPECIFIC PATTERNS WITH CONTEXT
    naruto.match_end_patterns = {
        "You Win!",     // Exact match with exclamation
        "You Lose!",    // Exact match with exclamation
        "Perfect Win!", // Exact match
        "Game Over",    // Exact match
        "Continue?",    // Exact match with question mark
        "Naruto Wins!", // Exact match
        "Sasuke Wins!", // Exact match
        "Goku Wins!",   // Exact match
        "KO!"           // WITH exclamation, not just "K.O."
    };

    naruto.win_patterns = {
        "You Win!",     // Exact match
        "Perfect Win!", // Exact match
        "Naruto Wins!", // Exact match
        "Sasuke Wins!", // Exact match
        "Goku Wins!",   // Exact match
        "Victory!"      // Exact match
    };

    naruto.lose_patterns = {
        "You Lose!", // Exact match
        "Defeat!",   // Exact match
        "KO!"        // WITH exclamation
    };

    naruto.match_start_patterns = {
        "Fight!",  // Exact match
        "Round 1", // Exact match
        "Round 2", // Exact match
        "VS"       // Exact match
    };

    naruto.menu_patterns = {
        "Main Menu",        // Exact match
        "Character Select", // Exact match
        "Battle Mode",      // Exact match
        "Options"           // Exact match
    };
    patterns.push_back(naruto);

    // ============================================================
    // FIFA / EA FC - SPECIFIC PATTERNS
    // ============================================================
    GamePatterns fifa;
    fifa.game_name = "FIFA";
    fifa.process_names = {"FIFA24.exe", "FIFA23.exe", "FIFA22.exe", "FIFA.exe", "EAFC.exe"};
    fifa.match_end_patterns = {
        "Full Time",      // Exact match
        "Match Finished", // Exact match
        "Final Whistle",  // Exact match
        "FT"              // Exact match
    };
    fifa.win_patterns = {
        "Winner!",  // Exact match
        "Victory!", // Exact match
        "You Win!", // Exact match
        "Champion!" // Exact match
    };
    fifa.lose_patterns = {
        "Defeat!",    // Exact match
        "You Lose!",  // Exact match
        "Eliminated!" // Exact match
    };
    fifa.match_start_patterns = {
        "Kick Off!",     // Exact match
        "Match Started", // Exact match
        "Goal!"          // Exact match
    };
    fifa.menu_patterns = {
        "Main Menu",     // Exact match
        "Ultimate Team", // Exact match
        "Career Mode"    // Exact match
    };
    patterns.push_back(fifa);

    // ============================================================
    // LEAGUE OF LEGENDS - SPECIFIC PATTERNS
    // ============================================================
    GamePatterns lol;
    lol.game_name = "League of Legends";
    lol.process_names = {"League of Legends.exe", "LoL.exe"};
    lol.match_end_patterns = {
        "Victory!",   // Exact match
        "Defeat!",    // Exact match
        "Game Over",  // Exact match
        "Match Ended" // Exact match
    };
    lol.win_patterns = {"Victory!", "Win!", "MVP"};
    lol.lose_patterns = {"Defeat!", "Lose!", "Lost"};
    lol.match_start_patterns = {
        "Summoner's Rift", // Exact match
        "Match Started",   // Exact match
        "Champion Select"  // Exact match
    };
    lol.menu_patterns = {
        "Main Menu",       // Exact match
        "Champion Select", // Exact match
        "Queue",           // Exact match
        "Lobby"            // Exact match
    };
    patterns.push_back(lol);

    // ============================================================
    // COUNTER-STRIKE 2 - SPECIFIC PATTERNS
    // ============================================================
    GamePatterns cs2;
    cs2.game_name = "Counter-Strike";
    cs2.process_names = {"cs2.exe", "csgo.exe"};
    cs2.match_end_patterns = {
        "Terrorist Win",         // Exact match
        "Counter-Terrorist Win", // Exact match
        "Match Ended",           // Exact match
        "Game Over"              // Exact match
    };
    cs2.win_patterns = {"Win", "Victory"};
    cs2.lose_patterns = {"Loss", "Defeat", "Lost"};
    cs2.match_start_patterns = {
        "Match Started",     // Exact match
        "Round",             // Exact match
        "Counter-Terrorist", // Exact match
        "Terrorist"          // Exact match
    };
    cs2.menu_patterns = {
        "Main Menu",   // Exact match
        "Competitive", // Exact match
        "Casual"       // Exact match
    };
    patterns.push_back(cs2);

    return patterns;
}

// ============================================================
// MEMORY SCANNER CLASS
// ============================================================

class MemoryScanner
{
private:
    HANDLE m_hProcess = NULL;
    DWORD m_processId = 0;
    std::string m_gameName;
    std::vector<GamePatterns> m_patterns;
    int m_matchCount = 0;
    bool m_inMatch = false;

public:
    MemoryScanner()
    {
        m_patterns = GetGamePatterns();
        LogMessage("🔍 Memory Scanner initialized");
        LogMessage("📊 Loaded " + std::to_string(m_patterns.size()) + " game pattern sets");
    }

    ~MemoryScanner()
    {
        if (m_hProcess)
        {
            CloseHandle(m_hProcess);
        }
    }

    // ============================================================
    // FIND AND ATTACH TO GAME (Using your game detection logic)
    // ============================================================

    bool FindAndAttachToGame()
    {
        // If already attached, check if process still running
        if (m_hProcess != NULL)
        {
            DWORD exitCode;
            if (GetExitCodeProcess(m_hProcess, &exitCode) && exitCode == STILL_ACTIVE)
            {
                return true;
            }
            CloseHandle(m_hProcess);
            m_hProcess = NULL;
        }

        HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (hSnapshot == INVALID_HANDLE_VALUE)
            return false;

        PROCESSENTRY32 pe32;
        pe32.dwSize = sizeof(PROCESSENTRY32);

        if (Process32First(hSnapshot, &pe32))
        {
            do
            {
                if (pe32.th32ProcessID == 0 || pe32.th32ProcessID == 4)
                    continue;

                std::string processName = GetProcessExeName(pe32);
                std::string lowerName = ToLower(processName);

                // Check against all known game process names
                for (const auto &patterns : m_patterns)
                {
                    for (const auto &procName : patterns.process_names)
                    {
                        if (lowerName.find(ToLower(procName)) != std::string::npos)
                        {
                            DWORD pid = pe32.th32ProcessID;
                            HANDLE hProcess = OpenProcess(
                                PROCESS_VM_READ | PROCESS_QUERY_INFORMATION |
                                    PROCESS_VM_OPERATION,
                                FALSE, pid);

                            if (hProcess)
                            {
                                m_hProcess = hProcess;
                                m_processId = pid;
                                m_gameName = patterns.game_name;
                                CloseHandle(hSnapshot);
                                LogMessage("✅ Attached to: " + m_gameName +
                                           " (PID: " + std::to_string(pid) + ")");
                                return true;
                            }
                        }
                    }
                }
            } while (Process32Next(hSnapshot, &pe32));
        }

        CloseHandle(hSnapshot);
        return false;
    }

    // ============================================================
    // SCAN MEMORY FOR PATTERN
    // ============================================================

    struct ScanResult
    {
        bool found;
        std::string pattern;
        uintptr_t address;
        std::string value;
        float confidence;
    };

    ScanResult ScanMemoryForString(const std::string &searchPattern)
    {
        ScanResult result;
        result.found = false;
        result.confidence = 0;

        if (m_hProcess == NULL)
            return result;

        MEMORY_BASIC_INFORMATION mbi;
        uintptr_t address = 0;
        int scanned = 0;
        int maxScan = 100 * 1024 * 1024; // 100MB limit

        while (VirtualQueryEx(m_hProcess, (LPCVOID)address, &mbi, sizeof(mbi)) && scanned < maxScan)
        {
            if (mbi.State == MEM_COMMIT &&
                (mbi.Protect & PAGE_READWRITE || mbi.Protect & PAGE_READONLY) &&
                !(mbi.Protect & PAGE_GUARD))
            {

                size_t regionSize = mbi.RegionSize;
                if (regionSize > 10 * 1024 * 1024)
                {
                    address += regionSize;
                    continue;
                }

                std::vector<char> buffer(regionSize);
                SIZE_T bytesRead;

                if (ReadProcessMemory(m_hProcess, mbi.BaseAddress, buffer.data(),
                                      regionSize, &bytesRead))
                {
                    std::string memoryString(buffer.data(), bytesRead);
                    memoryString = CleanString(memoryString);

                    // Get context around the match
                    size_t pos = memoryString.find(searchPattern);
                    if (pos != std::string::npos)
                    {
                        int start = std::max(0, (int)pos - 20);
                        int length = std::min((int)searchPattern.length() + 60,
                                              (int)memoryString.length() - start);
                        std::string context = memoryString.substr(start, length);

                        // Filter out false positives
                        if (!IsFalsePositive(context))
                        {
                            result.found = true;
                            result.pattern = searchPattern;
                            result.address = (uintptr_t)mbi.BaseAddress + pos;
                            result.value = context;
                            result.confidence = 100;
                            return result;
                        }
                    }
                }
                scanned += regionSize;
            }
            address += mbi.RegionSize;
        }

        return result;
    }

    // ============================================================
    // DETECT MATCH END (Complete Detection)
    // ============================================================

    struct DetectionResult
    {
        bool match_active;
        bool match_just_ended;
        bool is_win;
        bool is_loss;
        std::string result_text;
        std::string detected_pattern;
        std::string game_name;
        int match_number;
        float confidence;
        std::vector<std::string> evidence;
        std::string timestamp;
        bool detection_confirmed;
    };

    DetectionResult Detect()
    {
        DetectionResult result;
        result.match_active = false;
        result.match_just_ended = false;
        result.is_win = false;
        result.is_loss = false;
        result.confidence = 0;
        result.match_number = m_matchCount;
        result.game_name = m_gameName;
        result.timestamp = GetTimestamp();
        result.detection_confirmed = false;

        // Try to find and attach to a game
        if (!FindAndAttachToGame())
        {
            return result;
        }

        // Get patterns for this game
        GamePatterns *gamePatterns = nullptr;
        for (auto &p : m_patterns)
        {
            if (p.game_name == m_gameName)
            {
                gamePatterns = &p;
                break;
            }
        }
        if (gamePatterns == nullptr)
            return result;

        // ============================================================
        // COLLECT ALL EVIDENCE
        // ============================================================

        struct Evidence
        {
            std::string pattern;
            std::string value;
            std::string type;
        };
        std::vector<Evidence> foundEvidence;

        // Check win patterns
        for (const auto &pattern : gamePatterns->win_patterns)
        {
            auto scanResult = ScanMemoryForString(pattern);
            if (scanResult.found)
            {
                foundEvidence.push_back({pattern, scanResult.value, "win"});
                LogMessage("   Found win pattern: '" + pattern + "'");
            }
        }

        // Check lose patterns
        for (const auto &pattern : gamePatterns->lose_patterns)
        {
            auto scanResult = ScanMemoryForString(pattern);
            if (scanResult.found)
            {
                foundEvidence.push_back({pattern, scanResult.value, "lose"});
                LogMessage("   Found lose pattern: '" + pattern + "'");
            }
        }

        // Check match end patterns
        for (const auto &pattern : gamePatterns->match_end_patterns)
        {
            auto scanResult = ScanMemoryForString(pattern);
            if (scanResult.found)
            {
                foundEvidence.push_back({pattern, scanResult.value, "end"});
                LogMessage("   Found end pattern: '" + pattern + "'");
            }
        }

        // Check match start patterns
        bool matchStartFound = false;
        for (const auto &pattern : gamePatterns->match_start_patterns)
        {
            auto scanResult = ScanMemoryForString(pattern);
            if (scanResult.found)
            {
                matchStartFound = true;
                result.evidence.push_back("Match start: '" + pattern + "'");
                break;
            }
        }

        // Check menu patterns
        bool menuFound = false;
        for (const auto &pattern : gamePatterns->menu_patterns)
        {
            auto scanResult = ScanMemoryForString(pattern);
            if (scanResult.found)
            {
                menuFound = true;
                result.evidence.push_back("Menu: '" + pattern + "'");
                break;
            }
        }

        // ============================================================
        // ANALYZE EVIDENCE
        // ============================================================

        int winCount = 0, loseCount = 0, endCount = 0;
        for (const auto &ev : foundEvidence)
        {
            if (ev.type == "win")
                winCount++;
            else if (ev.type == "lose")
                loseCount++;
            else if (ev.type == "end")
                endCount++;
        }

        // ============================================================
        // MAKE DECISION
        // ============================================================

        // 1. Check for match end (win or lose)
        if (winCount > 0 || loseCount > 0 || endCount > 0)
        {
            result.match_just_ended = true;
            result.is_win = winCount > loseCount;
            result.is_loss = loseCount > winCount;

            // Calculate confidence
            int total = winCount + loseCount + endCount;
            result.confidence = std::min(100.0f, (total * 25.0f) + 20.0f);

            // Use first evidence
            if (!foundEvidence.empty())
            {
                result.result_text = foundEvidence[0].value;
                result.detected_pattern = foundEvidence[0].pattern;
            }

            // Build evidence
            for (const auto &ev : foundEvidence)
            {
                result.evidence.push_back(ev.type + ": '" + ev.pattern + "'");
            }

            // Increment match count
            if (!m_inMatch)
            {
                m_matchCount++;
                result.match_number = m_matchCount;
            }
            m_inMatch = false;
            result.detection_confirmed = true;

            LogMessage("🎉 MATCH END DETECTED! #" + std::to_string(result.match_number));
            LogMessage("   Result: " + std::string(result.is_win ? "WIN" : "LOSE"));
            LogMessage("   Confidence: " + std::to_string((int)result.confidence) + "%");
            LogMessage("   Evidence: " + std::to_string(foundEvidence.size()) + " matches");

            return result;
        }

        // 2. Check if in match
        if (matchStartFound && !menuFound)
        {
            result.match_active = true;
            result.confidence = 70;
            result.evidence.push_back("In match");

            if (!m_inMatch)
            {
                m_matchCount++;
                result.match_number = m_matchCount;
                LogMessage("🎮 MATCH STARTED! #" + std::to_string(m_matchCount));
            }
            m_inMatch = true;
            return result;
        }

        // 3. Check if in menu
        if (menuFound)
        {
            result.match_active = false;
            result.confidence = 80;
            result.evidence.push_back("In menu");

            if (m_inMatch)
            {
                m_inMatch = false;
                LogMessage("📋 Returned to menu");
            }
            return result;
        }

        // 4. Unknown state
        result.confidence = 30;
        result.evidence.push_back("Unknown state");

        return result;
    }

    // ============================================================
    // GET STATUS
    // ============================================================

    bool IsGameRunning() const { return m_hProcess != NULL; }
    std::string GetGameName() const { return m_gameName; }
    int GetMatchCount() const { return m_matchCount; }
    bool IsInMatch() const { return m_inMatch; }
};

// ============================================================
// MAIN PROGRAM
// ============================================================

int main()
{
    std::cout << "==================================================" << std::endl;
    std::cout << "   🔍 MEMORY SCANNER - MATCH END DETECTOR" << std::endl;
    std::cout << "   NO ML, NO PREDICTION, JUST FACTS!" << std::endl;
    std::cout << "==================================================" << std::endl;
    std::cout << std::endl;

    MemoryScanner scanner;

    std::cout << "🔄 Scanning for games..." << std::endl;
    std::cout << std::endl;

    bool firstRun = true;
    int lastMatchCount = 0;

    while (true)
    {
        auto detection = scanner.Detect();

        // Print status every few seconds
        if (firstRun || detection.timestamp.substr(11, 5) != GetTimestamp().substr(11, 5))
        {
            if (!firstRun)
            {
                std::cout << std::endl;
                std::cout << "==================================================" << std::endl;
            }
            firstRun = false;

            std::cout << "🔍 SCANNING: " << detection.timestamp << std::endl;
            if (scanner.IsGameRunning())
            {
                std::cout << "   Game: " << scanner.GetGameName() << std::endl;
                std::cout << "   Matches: " << scanner.GetMatchCount() << std::endl;
                std::cout << "   In Match: " << (scanner.IsInMatch() ? "YES" : "NO") << std::endl;
            }
            else
            {
                std::cout << "   Status: Waiting for game..." << std::endl;
            }
            std::cout << "--------------------------------------------------" << std::endl;
        }

        // Show detection results
        if (detection.detection_confirmed)
        {
            std::cout << std::endl;
            std::cout << "🎉 MATCH DETECTED!" << std::endl;
            std::cout << "   Result: " << (detection.is_win ? "🏆 WIN" : detection.is_loss ? "💀 LOSS"
                                                                                           : "UNKNOWN")
                      << std::endl;
            std::cout << "   Match #: " << detection.match_number << std::endl;
            std::cout << "   Pattern: '" << detection.detected_pattern << "'" << std::endl;
            std::cout << "   Confidence: " << detection.confidence << "%" << std::endl;
            if (!detection.result_text.empty())
            {
                std::cout << "   Text: " << detection.result_text << std::endl;
            }
            std::cout << "--------------------------------------------------" << std::endl;

            // ============================================================
            // 🔥 AUTO-END SESSION - CALL YOUR EXISTING FUNCTION HERE
            // ============================================================
            // If you want to call your existing session end function:
            //
            // if (g_Status == "in_session") {
            //     LogMessage("💲 Auto-ending session after match!");
            //     // Call your existing function:
            //     // auto_end_round_session(pc_id);
            //     // OR
            //     // ExecuteCommand("END_SESSION", "");
            // }
            //
            // For standalone testing, just log:
            LogMessage("💲 MATCH ENDED - SESSION WOULD END HERE");
        }

        // If match count changed, log it
        if (detection.match_number != lastMatchCount)
        {
            lastMatchCount = detection.match_number;
        }

        // Wait before next scan
        Sleep(2000);
    }

    return 0;
}