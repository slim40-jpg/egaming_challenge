// ============================================================
// MAIN.H - Shared declarations
// ============================================================

#ifndef MAIN_H
#define MAIN_H

#include <string>
#include <atomic>

// Global variables
extern std::string SERVER_URL;
extern std::string g_Hostname;
extern std::string g_Status;
extern std::atomic<bool> g_Running;

// Global game detector
class GameDetector;
extern GameDetector g_GameDetector;

// Function declarations
void LogMessage(const std::string &message);
bool SendTelemetryToEndpoint(const std::string &data, const std::string &endpoint);

#endif // MAIN_H