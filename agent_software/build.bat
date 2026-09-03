@echo off
echo ==========================================
echo   COMPILING GAMING AGENT (Static)
echo ==========================================
echo.

set CXX=g++
set CXXFLAGS=-std=c++17 -O2 -Wall -Wno-unknown-pragmas -Wno-unused-parameter -Wno-misleading-indentation -static
set LDFLAGS=-static -lws2_32 -liphlpapi -lsetupapi -lcfgmgr32 -lpdh -ladvapi32 -lpsapi -lwbemuuid -ldxgi -ld3d11 -luuid -lole32 -loleaut32 -lshell32 -lshlwapi -lole32 -loleaut32 -lcomctl32 -lgdi32 -luser32

echo Compiling main.cpp and game_discovery.cpp...
%CXX% %CXXFLAGS% -o gaming_agent.exe main.cpp game_discovery.cpp %LDFLAGS%

if %errorlevel% == 0 (
    echo.
    echo ==========================================
    echo   BUILD SUCCESSFUL!
    echo ==========================================
    echo.
    echo Executable: gaming_agent.exe (Static)
    echo Size: 
    dir gaming_agent.exe | find "gaming_agent.exe"
    echo.
    echo This executable can run on any Windows PC
    echo without requiring additional DLLs.
) else (
    echo.
    echo ==========================================
    echo   BUILD FAILED!
    echo ==========================================
)

pause