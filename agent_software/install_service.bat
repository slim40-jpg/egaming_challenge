@echo off
echo ============================================
echo   Gaming Agent - Windows Service Installer
echo ============================================
echo.

REM Run as Administrator check
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [1] Installing service...
gaming_agent.exe --install

if %errorlevel% equ 0 (
    echo.
    echo [2] Starting service...
    gaming_agent.exe --start
    echo.
    echo [3] Checking status...
    gaming_agent.exe --status
) else (
    echo [!] Installation failed!
)

echo.
echo ============================================
echo   Done!
echo ============================================
pause