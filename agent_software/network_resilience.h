// network_resilience.h
// ============================================================
// OFFLINE STATE + PENDING EVENT QUEUE
// ============================================================
// Handles network drops by:
//   1. Persisting session state to disk
//   2. Queueing events when the server is unreachable
//   3. Flushing the queue when the server comes back
// ============================================================

#ifndef NETWORK_RESILIENCE_H
#define NETWORK_RESILIENCE_H

#include <string>
#include <vector>
#include <mutex>
#include <chrono>

// ────────────────────────────────────────────────────────────
// Offline session state (persisted to disk)
// ────────────────────────────────────────────────────────────

struct OfflineState
{
    std::string current_user;
    std::chrono::steady_clock::time_point session_start;
    bool in_session = false;
    bool is_locked  = false;
};

// Global accessor
extern OfflineState g_OfflineState;

// ────────────────────────────────────────────────────────────
// Public API
// ────────────────────────────────────────────────────────────

// Call once at startup (in main(), after WSAStartup)
void InitNetworkResilience();

// Call whenever session/lock state changes
void SaveOfflineState();

// Called automatically on init — reloads previous session from disk
void LoadOfflineState();

// Queue an event when the server is unreachable
void QueueEvent(const std::string &endpoint, const std::string &json);

// Attempt to flush all queued events to the server
// Returns true if all were flushed, false if some remain
bool FlushPendingEvents();

// How many events are currently waiting
size_t PendingEventCount();

// Convenience helper: send-or-queue
// Attempts to POST to the endpoint. If it fails, queues it.
// Returns true on success, false if queued.
bool SendOrQueue(const std::string &endpoint, const std::string &json);

#endif // NETWORK_RESILIENCE_H