@echo off
echo ==================================================
echo    BUILDING MEMORY SCANNER
echo ==================================================
echo.

g++ -o memory_scanner.exe memory_scanner.cpp -lws2_32 -liphlpapi -lsetupapi -lcfgmgr32 -lpdh -ladvapi32 -lpsapi -std=c++11

if %errorlevel% == 0 (
    echo.
    echo ✅ BUILD SUCCESSFUL!
    echo    File: memory_scanner.exe
    echo.
    echo To run: memory_scanner.exe
) else (
    echo.
    echo ❌ BUILD FAILED!
)

pause