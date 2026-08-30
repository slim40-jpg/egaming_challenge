// NetworkManager.h
#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <string>

bool DiscoverServer();
bool SendHeartbeat(const std::string &hardwareData);
bool PollForCommands();
bool SendTelemetry();
std::string CollectTelemetry();

#endif // NETWORK_MANAGER_H