// ============================================================
// device_monitor.cpp
// Detects keyboards and mice via Windows Setup API
// ============================================================

#include "device_monitor.h"

#include <windows.h>
#include <setupapi.h>
#include <devguid.h>
#include <initguid.h>
#include <algorithm>
#include <iostream>

#pragma comment(lib, "setupapi.lib")

// ============================================================
// GUIDs for device classes we care about
// ============================================================
// GUID_DEVCLASS_KEYBOARD = {4D36E96B-E325-11CE-BFC1-08002BE10318}
// GUID_DEVCLASS_MOUSE    = {4D36E96F-E325-11CE-BFC1-08002BE10318}
// Both are already defined in <devguid.h>

// ============================================================
// Helper: get a string property from a device
// ============================================================

static std::string GetDevicePropertyString(
    HDEVINFO deviceInfoSet,
    PSP_DEVINFO_DATA deviceInfoData,
    DWORD property)
{
    DWORD requiredSize = 0;
    DWORD propertyType = 0;

    // First call: get the required buffer size
    SetupDiGetDeviceRegistryPropertyA(
        deviceInfoSet,
        deviceInfoData,
        property,
        &propertyType,
        nullptr,
        0,
        &requiredSize);

    if (requiredSize == 0)
        return "";

    std::vector<char> buffer(requiredSize, 0);

    if (!SetupDiGetDeviceRegistryPropertyA(
            deviceInfoSet,
            deviceInfoData,
            property,
            &propertyType,
            reinterpret_cast<PBYTE>(buffer.data()),
            requiredSize,
            nullptr))
    {
        return "";
    }

    return std::string(buffer.data());
}

// ============================================================
// Helper: enumerate one device class (Keyboard or Mouse)
// ============================================================

static void EnumerateDeviceClass(
    const GUID *classGuid,
    const std::string &className,
    std::vector<InputDevice> &out)
{
    HDEVINFO deviceInfoSet = SetupDiGetClassDevsA(
        classGuid,
        nullptr,
        nullptr,
        DIGCF_PRESENT);

    if (deviceInfoSet == INVALID_HANDLE_VALUE)
        return;

    SP_DEVINFO_DATA deviceInfoData;
    deviceInfoData.cbSize = sizeof(SP_DEVINFO_DATA);

    DWORD index = 0;
    while (SetupDiEnumDeviceInfo(deviceInfoSet, index, &deviceInfoData))
    {
        index++;

        // Friendly name (what the user sees in Device Manager)
        std::string friendlyName = GetDevicePropertyString(
            deviceInfoSet, &deviceInfoData, SPDRP_FRIENDLYNAME);

        // Fallback: device description
        if (friendlyName.empty())
        {
            friendlyName = GetDevicePropertyString(
                deviceInfoSet, &deviceInfoData, SPDRP_DEVICEDESC);
        }

        // Fallback: hardware ID
        if (friendlyName.empty())
        {
            friendlyName = GetDevicePropertyString(
                deviceInfoSet, &deviceInfoData, SPDRP_HARDWAREID);
        }

        // Skip entries with no name at all
        if (friendlyName.empty())
            continue;

        // Stable unique identifier — use the hardware ID (e.g.
        // "HID\VID_046D&PID_C31C&REV_6400")
        std::string hardwareId = GetDevicePropertyString(
            deviceInfoSet, &deviceInfoData, SPDRP_HARDWAREID);

        InputDevice dev;
        dev.name = friendlyName;
        dev.deviceClass = className;
        dev.instanceId = hardwareId.empty() ? friendlyName : hardwareId;

        out.push_back(dev);
    }

    SetupDiDestroyDeviceInfoList(deviceInfoSet);
}

// ============================================================
// Public: GetInputDevices
// ============================================================

std::vector<InputDevice> GetInputDevices()
{
    std::vector<InputDevice> devices;

    // Keyboards
    EnumerateDeviceClass(
        &GUID_DEVCLASS_KEYBOARD,
        "Keyboard",
        devices);

    // Mice
    EnumerateDeviceClass(
        &GUID_DEVCLASS_MOUSE,
        "Mouse",
        devices);

    return devices;
}

// ============================================================
// Public: DiffInputDevices
// ============================================================
// Returns devices present in `previous` but missing from `current`.
// Matching is done on `instanceId` (fallback to `name` if empty).

std::vector<InputDevice> DiffInputDevices(
    const std::vector<InputDevice> &previous,
    const std::vector<InputDevice> &current)
{
    std::vector<InputDevice> removed;

    auto findInCurrent = [&](const InputDevice &dev) -> bool
    {
        for (const auto &c : current)
        {
            // Primary match: instanceId
            if (!dev.instanceId.empty() && !c.instanceId.empty())
            {
                if (dev.instanceId == c.instanceId)
                    return true;
            }
            // Fallback match: name + class
            else if (dev.name == c.name && dev.deviceClass == c.deviceClass)
            {
                return true;
            }
        }
        return false;
    };

    for (const auto &dev : previous)
    {
        if (!findInCurrent(dev))
            removed.push_back(dev);
    }

    return removed;
}