// GameDetector.h
#ifndef GAME_DETECTOR_H
#define GAME_DETECTOR_H

#include <Windows.h>
#include <string>
#include <vector>

class GameDetector
{
private:
    std::vector<std::string> m_graphicsDlls;
    std::vector<std::string> m_nonGameKeywords;
    std::vector<std::string> m_launcherKeywords;

    std::string ToLower(const std::string &str);
    bool IsExeRegisteredAsGame(const std::string &exeName);
    bool IsProcessAGame(DWORD processID);
    bool IsProcessProbablyGame(const std::string &processName);
    bool IsProcessDefinitelyGame(DWORD processID);
    std::string CleanGameName(const std::string &exeName);

public:
    GameDetector();
    std::string GetCurrentActiveGame();
    std::string GetCurrentGameName();
};

extern GameDetector g_GameDetector;

#endif // GAME_DETECTOR_H