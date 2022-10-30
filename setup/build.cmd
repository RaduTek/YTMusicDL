@echo off

title Build YTMusicDL for Windows

echo Build YTMusicDL for Windows
echo Requires pyinstaller
echo.
: Checking for pyinstaller
pyinstaller > nul
if %errorlevel%==9009 (
    echo pyinstaller is not installed!
    pause
    exit /b
)
cls

echo Building YTMusicDL for Windows...
echo.
pyinstaller --clean --icon "..\other\YTMusicDL_icon.ico" --onefile "..\ytmusicdl.py"

pause
exit /b