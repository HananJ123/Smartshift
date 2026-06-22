#!/usr/bin/env bash
# Smartshift - Startskript fuer Mac und Linux

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "  Smartshift - Schichtplanung"
echo "========================================"
echo

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "FEHLER: Python wurde nicht gefunden."
    exit 1
fi

if [ ! -f ".venv/bin/python" ]; then
    echo "[1/2] Erstelle virtuelle Umgebung..."
    "$PY" -m venv .venv
else
    echo "[1/2] Virtuelle Umgebung vorhanden."
fi

if [ ! -f ".venv/.deps_installed" ]; then
    echo "[2/2] Installiere Abhaengigkeiten einmalig..."
    ./.venv/bin/python -m pip install --upgrade pip --timeout 30
    ./.venv/bin/python -m pip install -r requirements.txt --timeout 30
    touch .venv/.deps_installed
else
    echo "[2/2] Abhaengigkeiten bereits installiert. Ueberspringe..."
fi

echo
echo "Server startet..."
echo "Oeffne im Browser:  http://localhost:8000"
echo "Zum Beenden: Strg + C druecken"
echo

cd backend
exec ../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload