@echo off
rem Baut Miezi.exe (eine Datei, ohne Konsolenfenster) aus miezi.py.
rem Aufruf: Doppelklick oder  windows\build.cmd  - die EXE landet in diesem Ordner (windows\).
rem (.cmd statt .ps1, weil PowerShell-Skripte per Gruppenrichtlinie gesperrt sein koennen.)
setlocal
cd /d "%~dp0"
 
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller fehlt - installiere es fuer den aktuellen Benutzer ...
    python -m pip install --user pyinstaller || exit /b 1
)
 
rem Zwischendateien nach %TEMP%, die fertige EXE direkt in diesen Ordner.
rem --paths: gemeinsamer Code in ..\common (Figuren stehen in common\sprites\__init__.py)
set "WORK=%TEMP%\miezi-build"
python -m PyInstaller --onefile --noconsole --name Miezi --clean ^
    --paths "%~dp0..\common" ^
    --workpath "%WORK%\build" --specpath "%WORK%" --distpath "%~dp0." "%~dp0miezi.py" || exit /b 1
 
echo.
echo Fertig: %~dp0Miezi.exe