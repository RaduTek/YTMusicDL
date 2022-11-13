@echo off

title Build YTMusicDL for Windows

echo Building YTMusicDL for Windows...
echo.
if not exist "..\venv\Scripts\pyinstaller.exe" (
    echo Pyinstaller does not exist in virtual environment directory.
    pause > nul
    echo Press any key to exit...
    exit /b
)

..\venv\Scripts\pyinstaller.exe --collect-all "ytmusicapi" --icon "..\other\YTMusicDL_icon.ico" --onefile "..\ytmusicdl.py"

echo Press any key to exit...
pause > nul
exit /b