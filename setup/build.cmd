@echo off

title Build YTMusicDL for Windows

echo Building YTMusicDL for Windows...
echo.
pyinstaller --collect-all "ytmusicapi" --icon "..\other\YTMusicDL_icon.ico" --onefile "..\ytmusicdl.py"

echo Press any key to exit...
pause > nul
exit /b