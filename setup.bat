@echo off
REM ===============================================
REM POS System Automatic Setup Script for Windows
REM ===============================================
REM
REM This script will:
REM 1. Check Python installation
REM 2. Install required packages
REM 3. Initialize database
REM 4. Verify setup
REM
REM Run this script by double-clicking or:
REM   cmd.exe → cd d:\Program_Kasir → setup.bat
REM
REM ===============================================

setlocal enabledelayedexpansion

echo.
echo ===============================================
echo   POS SYSTEM - AUTOMATIC INSTALLATION
echo ===============================================
echo.

REM Colors and formatting
color 0A
title POS System Setup

REM ===============================================
REM Step 1: Check Python
REM ===============================================
echo [1/5] Checking Python installation...
python --version >nul 2>&1

if errorlevel 1 (
    echo.
    echo ❌ ERROR: Python not found!
    echo.
    echo Please install Python first:
    echo   1. Go to: https://www.python.org/downloads/
    echo   2. Download Python 3.8 or higher
    echo   3. During installation, CHECK: "Add python.exe to PATH"
    echo   4. Run this script again
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo ✅ Found: %PYTHON_VER%
echo.

REM ===============================================
REM Step 2: Create Virtual Environment (Optional)
REM ===============================================
set USE_VENV=0

echo [2/5] Virtual Environment Setup (Optional)
if exist "venv" (
    echo ℹ️  Virtual environment already exists
    set USE_VENV=1
) else (
    echo ℹ️  No virtual environment detected
    set /p CREATE_VENV="Create virtual environment? (y/n): "
    
    if /i "%CREATE_VENV%"=="y" (
        echo Creating virtual environment...
        python -m venv venv
        if errorlevel 1 (
            echo ❌ Failed to create virtual environment
        ) else (
            echo ✅ Virtual environment created
            set USE_VENV=1
        )
    )
)
echo.

REM ===============================================
REM Step 3: Install Dependencies
REM ===============================================
echo [3/5] Installing Python packages...
echo.

if %USE_VENV% equ 1 (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    if errorlevel 1 (
        echo ⚠️  Warning: Could not activate venv
    )
)

echo Installing required packages...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

echo Installing python-telegram-bot and requests...
python -m pip install python-telegram-bot requests >nul 2>&1

if errorlevel 1 (
    echo ⚠️  Warning: Some packages could not be installed
    echo    (This is OK if using core features only)
) else (
    echo ✅ Packages installed successfully
)
echo.

REM ===============================================
REM Step 4: Initialize Database
REM ===============================================
echo [4/5] Initializing database...
echo.

python setup_database.py

if errorlevel 1 (
    echo.
    echo ❌ Database initialization failed
    echo.
    pause
    exit /b 1
)
echo.

REM ===============================================
REM Step 5: Verify Installation
REM ===============================================
echo [5/5] Verifying installation...
echo.

echo Testing Python modules...
python setup_verify.py
echo.

REM ===============================================
REM Setup Complete
REM ===============================================
echo.
echo ===============================================
echo    ✅ SETUP COMPLETE!
echo ===============================================
echo.
echo Next steps:
echo   1. Read: GETTING_STARTED.md (5-minute quickstart)
echo   2. Read: README.md (features overview)
echo   3. Run:  python main.py
echo.
echo Documentation:
echo   - INSTALL.md ...................... Detailed installation
echo   - GETTING_STARTED.md .............. Quick start guide
echo   - TROUBLESHOOTING.md .............. Common issues
echo   - README.md ....................... Full documentation
echo   - TELEGRAM_BOT_QUICKSTART.md ...... 5-min Telegram setup
echo.
echo To start the application:
echo   - Double-click: main.py
echo   - Or type:     python main.py
echo.
echo ===============================================
echo.

REM ===============================================
REM Optional: Offer to run program
REM ===============================================
set /p RUN_PROGRAM="Do you want to start the program now? (y/n): "

if /i "%RUN_PROGRAM%"=="y" (
    echo.
    echo Starting POS System...
    echo.
    python main.py
) else (
    echo.
    echo Setup finished. Run 'python main.py' when ready.
    echo.
    pause
)

endlocal
