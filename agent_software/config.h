// Config.h
#ifndef CONFIG_H
#define CONFIG_H

#include <string>

// Network Configuration
const int DISCOVERY_PORT = 9000;
const int SERVER_PORT = 8003;
const int HEARTBEAT_INTERVAL_MS = 10000;
const int USB_CHECK_INTERVAL_MS = 5000;
const int COMMAND_POLL_INTERVAL_MS = 2000;
const int TELEMETRY_INTERVAL_MS = 2000;

// Global variables (declared extern, defined in main.cpp)
extern std::string SERVER_URL;
extern std::string g_Hostname;
extern std::string g_Status;
extern std::atomic<bool> g_Running;
extern std::string g_SessionUser;

#endif // CONFIG_H