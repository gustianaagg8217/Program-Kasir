@echo off
REM ============================================================================
REM CREATE DESKTOP SHORTCUT FOR GUI
REM ============================================================================

echo.
echo Membuat shortcut di Desktop...
echo.

REM Get current directory
setlocal enabledelayedexpansion
set "CURRENT_DIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"

REM Create VBS script to create shortcut
call :create_shortcut

echo.
echo ✅ Shortcut berhasil dibuat di Desktop!
echo Sekarang Anda bisa double-click icon "🛒 POS GUI System" untuk menjalankan aplikasi.
echo.
pause
goto :eof

:create_shortcut
@echo off
setlocal enabledelayedexpansion
set "CURRENT_DIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"

(
echo Set objWS = WScript.CreateObject("WScript.Shell"^)
echo strDesktop = objWS.SpecialFolders("Desktop"^)
echo set objLink = objWS.CreateShortcut(strDesktop ^& "\🛒 POS GUI System.lnk"^)
echo objLink.TargetPath = "!CURRENT_DIR!run_gui.bat"
echo objLink.WorkingDirectory = "!CURRENT_DIR!"
echo objLink.Description = "Sistem POS - GUI Version"
echo objLink.IconLocation = "C:\Windows\System32\cmd.exe, 0"
echo objLink.Save
) > "%TEMP%\create_shortcut.vbs"

REM Run VBS script to create shortcut
cscript "%TEMP%\create_shortcut.vbs"

REM Clean up
del "%TEMP%\create_shortcut.vbs"

goto :eof
