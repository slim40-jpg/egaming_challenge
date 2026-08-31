@echo off
echo ==========================================
echo   COMPILING GAMING AGENT
echo ==========================================
echo.

set CXX=g++
set CXXFLAGS=-std=c++17 -O2 -Wall -Wno-unknown-pragmas -Wno-unused-parameter -Wno-misleading-indentation
set LDFLAGS=-lws2_32 -liphlpapi -lsetupapi -lcfgmgr32 -lpdh -ladvapi32 -lpsapi -lwbemuuid -ldxgi -ld3d11 -luuid -lole32 -loleaut32 -lshell32 -lshlwapi
echo Compiling main.cpp and game_discovery.cpp...
%CXX% %CXXFLAGS% -o gaming_agent.exe main.cpp game_discovery.cpp %LDFLAGS%

if %errorlevel% == 0 (
    echo.
    echo ==========================================
    echo   BUILD SUCCESSFUL!
    echo ==========================================
    echo.
    echo Executable: gaming_agent.exe
    echo.
    echo Usage:
    echo   gaming_agent.exe            - Run as console
    echo   gaming_agent.exe --install  - Install as Windows service
    echo   gaming_agent.exe --uninstall- Uninstall service
    echo   gaming_agent.exe --start    - Start service
    echo   gaming_agent.exe --stop     - Stop service
    echo   gaming_agent.exe --status   - Check service status
) else (
    echo.
    echo ==========================================
    echo   BUILD FAILED!
    echo ==========================================
)

pause