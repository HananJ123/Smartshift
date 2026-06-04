@echo off
title Smartshift Server
cd /d "%~dp0"

echo ========================================
echo   Smartshift - Schichtplanung
echo ========================================
echo.

REM Virtuelle Umgebung pruefen / erstellen
if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Erstelle virtuelle Umgebung...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo FEHLER: Python wurde nicht gefunden.
        echo Bitte Python 3.10+ installieren: https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
)

echo Installiere/pruefe Abhaengigkeiten...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Server startet...
echo Oeffne im Browser:  http://localhost:8000
echo Zum Beenden: dieses Fenster schliessen oder Strg+C
echo.

cd backend
"..\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

REM Falls der Server abstuerzt, Fenster offen halten zur Fehleranzeige
echo.
echo ========================================
echo  Server wurde beendet.
echo ========================================
pause
