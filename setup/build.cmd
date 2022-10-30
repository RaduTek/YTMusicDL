@echo off

title Build YTMusicDL for Windows

echo Build YTMusicDL for Windows
echo Requires pyinstaller
echo.
: Checking for pyinstaller
pyinstaller > nul
if %errorlevel%==9009 (
    echo pyinstaller is not installed!
    echo To install use: pip install pyinstaller
    echo And ensure pyinstaller is available to PATH.
    echo Press any key to exit...
    pause > nul
    exit /b
)
cls

echo Building YTMusicDL for Windows...
echo.
pyinstaller --clean --icon "..\other\YTMusicDL_icon.ico" --onefile "..\ytmusicdl.py"

echo Press any key to exit...
pause > nul
exit /b