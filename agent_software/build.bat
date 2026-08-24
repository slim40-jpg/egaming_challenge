@echo off
echo Compiling Gaming Agent...

g++ -o agent.exe main.cpp -lws2_32 -liphlpapi -lsetupapi -lcfgmgr32 -luuid -lpdh -static

if %errorlevel% == 0 (
    echo Done! Running agent.exe...
    agent.exe
) else (
    echo Compilation failed!
)

pause