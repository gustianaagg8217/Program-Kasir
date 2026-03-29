@echo off
REM ============================================================================
REM TELEGRAM_BOT_RUN.BAT - Run Telegram POS System
REM ============================================================================

echo.
echo ====================================================================
echo  🤖 TELEGRAM POS SYSTEM - LAUNCHER
echo ====================================================================
echo.

REM Check if python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python tidak terinstall!
    echo Silakan install Python dari https://www.python.org/
    pause
    exit /b 1
)

REM Check dependencies
echo ⏳ Checking dependencies...
python -c "import telegram; import telegram.ext" >nul 2>&1
if errorlevel 1 (
    echo ❌ python-telegram-bot tidak terinstall!
    echo.
    echo Install dengan command:
    echo.
    echo   pip install python-telegram-bot requests
    echo.
    pause
    exit /b 1
)

REM Run telegram bot
echo.
echo ✅ Semua dependencies tersedia
echo.
echo Memulai Telegram POS System...
echo.

python telegram_main.py

pause
