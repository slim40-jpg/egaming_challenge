// network_resilience.cpp
// ============================================================
// Implementation of offline state + pending queue
// ============================================================

#include "network_resilience.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <windows.h>

// ─── EXTERNAL: defined in main.cpp ───
// The function used to actually POST to the local server.
// Declared here so we can call it from this file.
extern bool SendTelemetryToEndpoint(const std::string &data,
                                    const std::string &endpoint);

// External logging function from main.cpp
extern void LogMessage(const std::string &message);

// External lock state (from main.cpp)
extern bool g_IsLocked(); // wrapper (see main.cpp)

// Actually we can just access the global — but atomic<bool> can't be
// forward-declared easily, so we use a small function below.
// Simpler: pass a callback. For now, we just call a helper.

// ────────────────────────────────────────────────────────────
// Globals
// ────────────────────────────────────────────────────────────

OfflineState g_OfflineState;

// Pending event queue
static std::mutex g_QueueMutex;
static std::vector<std::pair<std::string, std::string>> g_PendingEvents;

// Path where we persist offline state
static const std::string OFFLINE_STATE_FILE =
    "C:\\ProgramData\\GamingAgent\\offline_state.json";

// ────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────

static void EnsureDirectoryExists(const std::string &filepath)
{
    size_t pos = filepath.find_last_of("\\/");
    if (pos == std::string::npos)
        return;
    std::string dir = filepath.substr(0, pos);

    // Create each segment
    std::string current;
    for (size_t i = 0; i < dir.size(); ++i)
    {
        current += dir[i];
        if (dir[i] == '\\' || dir[i] == '/')
        {
            if (current.size() > 3) // skip "C:\"
            {
                CreateDirectoryA(current.c_str(), NULL);
            }
        }
    }
    CreateDirectoryA(dir.c_str(), NULL);
}

// ────────────────────────────────────────────────────────────
// Init
// ────────────────────────────────────────────────────────────

void InitNetworkResilience()
{
    LogMessage("[RESILIENCE] Initializing...");
    LoadOfflineState();
    LogMessage("[RESILIENCE] Ready");
}

// ────────────────────────────────────────────────────────────
// Save / Load offline state
// ────────────────────────────────────────────────────────────

void SaveOfflineState()
{
    EnsureDirectoryExists(OFFLINE_STATE_FILE);

    std::ofstream f(OFFLINE_STATE_FILE);
    if (!f.is_open())
    {
        LogMessage("[RESILIENCE] ⚠️ Cannot write " + OFFLINE_STATE_FILE);
        return;
    }

    auto epoch = std::chrono::duration_cast<std::chrono::seconds>(
                     g_OfflineState.session_start.time_since_epoch())
                     .count();

    f << "{"
      << "\"user\":\"" << g_OfflineState.current_user << "\","
      << "\"in_session\":" << (g_OfflineState.in_session ? "true" : "false") << ","
      << "\"is_locked\":" << (g_OfflineState.is_locked ? "true" : "false") << ","
      << "\"session_start_epoch\":" << epoch
      << "}";
    f.close();

    LogMessage("[RESILIENCE] State saved to disk");
}

void LoadOfflineState()
{
    std::ifstream f(OFFLINE_STATE_FILE);
    if (!f.is_open())
    {
        LogMessage("[RESILIENCE] No previous state found (fresh start)");
        return;
    }

    std::string content((std::istreambuf_iterator<char>(f)),
                        std::istreambuf_iterator<char>());
    f.close();

    // Very simple JSON extraction (key-by-key)
    auto extract_str = [&](const std::string &key, const std::string &def) -> std::string
    {
        std::string needle = "\"" + key + "\":\"";
        size_t pos = content.find(needle);
        if (pos == std::string::npos)
            return def;
        pos += needle.length();
        size_t end = content.find("\"", pos);
        if (end == std::string::npos)
            return def;
        return content.substr(pos, end - pos);
    };

    auto extract_bool = [&](const std::string &key, bool def) -> bool
    {
        std::string needle = "\"" + key + "\":";
        size_t pos = content.find(needle);
        if (pos == std::string::npos)
            return def;
        pos += needle.length();
        return content.compare(pos, 4, "true") == 0;
    };

    auto extract_long = [&](const std::string &key, long def) -> long
    {
        std::string needle = "\"" + key + "\":";
        size_t pos = content.find(needle);
        if (pos == std::string::npos)
            return def;
        pos += needle.length();
        size_t end = content.find_first_of(",}", pos);
        if (end == std::string::npos)
            return def;
        try
        {
            return std::stol(content.substr(pos, end - pos));
        }
        catch (...)
        {
            return def;
        }
    };

    g_OfflineState.current_user = extract_str("user", "");
    g_OfflineState.in_session = extract_bool("in_session", false);
    g_OfflineState.is_locked = extract_bool("is_locked", false);

    long start_epoch = extract_long("session_start_epoch", 0);
    if (start_epoch > 0)
    {
        g_OfflineState.session_start =
            std::chrono::steady_clock::time_point(std::chrono::seconds(start_epoch));
    }

    if (g_OfflineState.in_session)
    {
        LogMessage("[RESILIENCE] 🛟 Restored previous session: user=" +
                   g_OfflineState.current_user +
                   " locked=" + (g_OfflineState.is_locked ? "yes" : "no"));
    }
    else
    {
        LogMessage("[RESILIENCE] Previous state was not in session");
    }
}

// ────────────────────────────────────────────────────────────
// Queue
// ────────────────────────────────────────────────────────────

void QueueEvent(const std::string &endpoint, const std::string &json)
{
    std::lock_guard<std::mutex> lock(g_QueueMutex);
    g_PendingEvents.push_back({endpoint, json});
    LogMessage("[RESILIENCE] 📥 Event queued (" +
               std::to_string(g_PendingEvents.size()) + " pending)");
}

size_t PendingEventCount()
{
    std::lock_guard<std::mutex> lock(g_QueueMutex);
    return g_PendingEvents.size();
}

bool FlushPendingEvents()
{
    std::lock_guard<std::mutex> lock(g_QueueMutex);
    if (g_PendingEvents.empty())
        return true;

    LogMessage("[RESILIENCE] 🔄 Flushing " +
               std::to_string(g_PendingEvents.size()) + " pending events...");

    auto it = g_PendingEvents.begin();
    size_t flushed = 0;
    while (it != g_PendingEvents.end())
    {
        if (SendTelemetryToEndpoint(it->second, it->first))
        {
            it = g_PendingEvents.erase(it);
            ++flushed;
        }
        else
        {
            ++it; // Keep in queue for next attempt
        }
    }

    LogMessage("[RESILIENCE] Flushed " + std::to_string(flushed) + " / " +
               std::to_string(flushed + g_PendingEvents.size()) + " events");

    return g_PendingEvents.empty();
}

// ────────────────────────────────────────────────────────────
// SendOrQueue — try to send, fall back to queue
// ────────────────────────────────────────────────────────────

bool SendOrQueue(const std::string &endpoint, const std::string &json)
{
    if (SendTelemetryToEndpoint(json, endpoint))
    {
        // Success — flush any pending events now that we know the network works
        FlushPendingEvents();
        return true;
    }

    // Failed — queue it
    QueueEvent(endpoint, json);
    return false;
}