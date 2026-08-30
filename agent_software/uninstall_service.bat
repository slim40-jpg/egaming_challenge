@echo off
echo ============================================
echo   Gaming Agent - Windows Service Uninstaller
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

echo [1] Stopping service...
agent.exe --stop

echo [2] Uninstalling service...
agent.exe --uninstall

echo.
echo ============================================
echo   Done!
echo ============================================
pause