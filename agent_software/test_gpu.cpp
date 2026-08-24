#include <windows.h>
#include <pdh.h>
#include <pdhmsg.h>
#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>

#pragma comment(lib, "pdh.lib")

std::vector<std::string> GetGPUCounterPaths()
{
    std::vector<std::string> paths;

    PDH_HQUERY query = nullptr;

    std::cout << "[TEST] Opening PDH query..." << std::endl;

    if (PdhOpenQueryA(nullptr, 0, &query) != ERROR_SUCCESS)
    {
        std::cout << "[TEST] Failed to open query!" << std::endl;
        return paths;
    }

    std::cout << "[TEST] Query opened successfully!" << std::endl;

    DWORD bufferSize = 0;
    DWORD itemCount = 0;

    // Add wildcard counter temporarily
    PDH_HCOUNTER wildcardCounter = nullptr;

    std::cout << "[TEST] Adding wildcard counter: \\GPU Engine(*)\\Utilization Percentage" << std::endl;

    PDH_STATUS status = PdhAddCounterA(
        query,
        "\\GPU Engine(*)\\Utilization Percentage",
        0,
        &wildcardCounter);

    if (status != ERROR_SUCCESS)
    {
        std::cout << "[TEST] Failed to add wildcard counter! Error: " << status << std::endl;
        PdhCloseQuery(query);
        return paths;
    }

    std::cout << "[TEST] Wildcard counter added successfully!" << std::endl;

    // ============================================
    // FIX: Collect data MULTIPLE times with delays
    // ============================================

    std::cout << "[TEST] Collecting query data (waiting for valid values)..." << std::endl;

    // First collection
    PdhCollectQueryData(query);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // Second collection
    PdhCollectQueryData(query);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // Third collection (sometimes needed)
    PdhCollectQueryData(query);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    std::cout << "[TEST] Getting formatted counter array..." << std::endl;
    status = PdhGetFormattedCounterArrayA(
        wildcardCounter,
        PDH_FMT_DOUBLE,
        &bufferSize,
        &itemCount,
        nullptr);

    std::cout << "[TEST] Status: " << status << ", BufferSize: " << bufferSize << ", ItemCount: " << itemCount << std::endl;

    if (status == PDH_MORE_DATA && bufferSize > 0)
    {
        std::cout << "[TEST] Allocating buffer of size: " << bufferSize << std::endl;

        auto items = (PPDH_FMT_COUNTERVALUE_ITEM_A)
            HeapAlloc(
                GetProcessHeap(),
                HEAP_ZERO_MEMORY,
                bufferSize);

        if (items)
        {
            status = PdhGetFormattedCounterArrayA(
                wildcardCounter,
                PDH_FMT_DOUBLE,
                &bufferSize,
                &itemCount,
                items);

            std::cout << "[TEST] Second call status: " << status << std::endl;

            if (status == ERROR_SUCCESS)
            {
                std::cout << "[TEST] Found " << itemCount << " GPU engine instances:" << std::endl;

                // Filter out negative values
                int validCount = 0;
                for (DWORD i = 0; i < itemCount; i++)
                {
                    std::string instanceName = items[i].szName;
                    double value = items[i].FmtValue.doubleValue;

                    // Only add if the value is positive (valid)
                    if (value > 0)
                    {
                        std::cout << "  [" << i << "] " << instanceName << " = " << value << "%" << std::endl;

                        std::string fullPath =
                            "\\GPU Engine(" +
                            instanceName +
                            ")\\Utilization Percentage";

                        paths.push_back(fullPath);
                        validCount++;
                    }
                }

                if (validCount == 0)
                {
                    std::cout << "[TEST] All values were 0 or negative. GPU might be idle." << std::endl;
                    std::cout << "[TEST] Try running a game or GPU-intensive task!" << std::endl;
                }
                else
                {
                    std::cout << "[TEST] Valid counters found: " << validCount << std::endl;
                }
            }
            else
            {
                std::cout << "[TEST] Failed to get formatted counter array! Error: " << status << std::endl;
                std::cout << "[TEST] Error: " << std::hex << status << std::dec << std::endl;
            }

            HeapFree(GetProcessHeap(), 0, items);
        }
        else
        {
            std::cout << "[TEST] Failed to allocate buffer!" << std::endl;
        }
    }
    else if (status == ERROR_SUCCESS)
    {
        // This shouldn't happen with a wildcard counter
        std::cout << "[TEST] No data available!" << std::endl;
    }
    else
    {
        std::cout << "[TEST] No GPU counter instances found!" << std::endl;
    }

    PdhCloseQuery(query);
    return paths;
}

int main()
{
    std::cout << "========================================" << std::endl;
    std::cout << "   GPU COUNTER DISCOVERY TEST" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "IMPORTANT: If values show 0%, try running" << std::endl;
    std::cout << "a game or GPU-intensive task in the background." << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;

    std::vector<std::string> paths = GetGPUCounterPaths();

    std::cout << "\n========================================" << std::endl;
    std::cout << "RESULTS:" << std::endl;
    std::cout << "========================================" << std::endl;

    if (paths.empty())
    {
        std::cout << "No GPU counters with valid values found on this system." << std::endl;
        std::cout << "Your GPU might be idle or doesn't support utilization counters." << std::endl;
        std::cout << "Try running a game or GPU-intensive task and test again." << std::endl;
    }
    else
    {
        std::cout << "Found " << paths.size() << " valid GPU counter(s):" << std::endl;
        for (const auto &path : paths)
        {
            std::cout << "  " << path << std::endl;
        }
    }

    std::cout << "\nPress Enter to exit..." << std::endl;
    std::cin.get();
    return 0;
}