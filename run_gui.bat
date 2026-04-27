@echo off
REM ============================================================================
REM GUI POS SYSTEM LAUNCHER
REM ============================================================================

echo.
echo ======================================================================
echo   🛒 SISTEM POS - GUI VERSION
echo   Copyright (c) 2026. All rights reserved. By Aventa Intelligent Power
echo ======================================================================
echo.

REM Set UTF-8 encoding untuk Windows terminal
chcp 65001 >nul 2>&1

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python tidak terinstall atau tidak terdaftar di PATH!
    echo Silakan install Python terlebih dahulu.
    pause
    exit /b 1
)

REM Install required packages if needed
echo ⏳ Memastikan dependencies terinstall...
pip install tkcalendar pillow python-telegram-bot requests -q

REM Run the GUI application
echo.
echo ✅ Menjalankan aplikasi...
echo.

python gui_main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Error saat menjalankan aplikasi!
    pause
    exit /b 1
)

pause
