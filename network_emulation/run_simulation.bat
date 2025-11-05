@echo off
echo H-UDP Network Emulation Test
echo ============================
echo.
echo Step 1: Start Clumsy as Administrator
echo   - Configure your desired scenario
echo   - DO NOT click Start yet
echo.
pause
echo.
echo Step 2: Starting Receiver...
start "H-UDP Receiver" cmd /k python demo\app.py
echo.
timeout /t 3
echo Step 3: Starting Sender...
start "H-UDP Sender" cmd /k python demo\app.py
echo.
echo Step 4: Now click START in Clumsy window
echo.
pause
echo.
echo Test complete. Click STOP in Clumsy.
pause