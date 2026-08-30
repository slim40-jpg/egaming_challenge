@echo off
echo ==========================================
echo   COMPILING GAMING AGENT
echo ==========================================
echo.

g++ -o gaming_agent.exe main.cpp ^
    -lws2_32 -liphlpapi -lsetupapi -lcfgmgr32 -lpdh -ladvapi32 -lpsapi ^
    -lole32 -luuid ^
    -std=c++11 ^
    -Wno-missing-braces ^
    -Wno-write-strings

if %errorlevel% == 0 (
    echo.
    echo ==========================================
    echo ✅ BUILD SUCCESSFUL!
    echo ==========================================
    echo File: gaming_agent.exe
    echo Size: 
    dir gaming_agent.exe
) else (
    echo.
    echo ==========================================
    echo ❌ BUILD FAILED!
    echo ==========================================
)

pause