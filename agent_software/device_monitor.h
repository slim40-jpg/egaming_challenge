#pragma once

#include <string>
#include <vector>

struct InputDevice
{
    std::string name;        // "Logitech USB Keyboard"
    std::string deviceClass; // "Keyboard" or "Mouse"
    std::string instanceId;  // unique per device (SPDRP_HARDWAREID)
};

// Returns all currently connected keyboards + mice
std::vector<InputDevice> GetInputDevices();

// Returns devices in `previous` that are NOT in `current` (removed devices)
std::vector<InputDevice> DiffInputDevices(
    const std::vector<InputDevice> &previous,
    const std::vector<InputDevice> &current);