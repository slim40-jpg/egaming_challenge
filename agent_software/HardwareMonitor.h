// HardwareMonitor.h
#ifndef HARDWARE_MONITOR_H
#define HARDWARE_MONITOR_H

#include <string>

int GetCPUUsage();
int GetRAMUsage();
int GetGPUUsage();
int GetCPUTemperature();

std::string GetCPUName();
std::string GetGPUName();
std::string GetRAMSize();

// ML Features structure
struct MLFeatures
{
    float cpu_usage;
    float gpu_usage;
    float ram_usage;
    float cpu_gpu_ratio;
    std::string process_name;
    int is_game_process;
    float process_cpu;
    float process_memory;
    std::string window_title;
    int title_has_match;
    int title_has_menu;
    int is_fullscreen;
    int window_width;
    int window_height;
    int hour_of_day;
    int day_of_week;
    int session_duration;
    int is_fifa;
    int is_lol;
    int is_csgo;
    int is_mugen;
};

MLFeatures CollectMLFeatures();

#endif // HARDWARE_MONITOR_H