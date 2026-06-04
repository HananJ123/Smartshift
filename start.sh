#!/usr/bin/env bash
# Smartshift - Startskript fuer Mac und Linux
# Verwendung:  ./start.sh    (oder im Terminal: bash start.sh)

set -e

# In den Ordner wechseln, in dem dieses Skript liegt
cd "$(dirname "$0")"

echo "========================================"
echo "  Smartshift - Schichtplanung"
echo "========================================"
echo

# Python-Befehl ermitteln (python3 bevorzugt)
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "FEHLER: Python wurde nicht gefunden."
    echo "Bitte Python 3.10+ installieren: https://www.python.org/downloads/"
    echo "(Mac-Tipp: 'brew install python' falls Homebrew installiert ist)"
    exit 1
fi

# Virtuelle Umgebung erstellen, falls noch nicht vorhanden
if [ ! -f ".venv/bin/python" ]; then
    echo "[1/2] Erstelle virtuelle Umgebung..."
    "$PY" -m venv .venv
fi

# Abhaengigkeiten immer pruefen/installieren (schnell, wenn bereits vorhanden)
echo "[2/2] Installiere/pruefe Abhaengigkeiten..."
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo
echo "Server startet..."
echo "Oeffne im Browser:  http://localhost:8000"
echo "Zum Beenden: Strg + C druecken"
echo

cd backend
exec ../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
