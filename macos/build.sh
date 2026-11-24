#!/bin/bash
# Baut macos/dist/Miezi.app aus macos/miezi_mac.py.
# Aufruf:  macos/build.sh          (oder mit eigenem Python: PYTHON=/pfad/python macos/build.sh)
# Ergebnis: macos/dist/Miezi.app  - auf dem Ziel-Mac wird kein Python gebraucht.
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter fehlt. Bei Homebrew-Python:  brew install python-tk@3.13"
  exit 1
fi
if ! "$PY" -c "import Quartz, AppKit" >/dev/null 2>&1; then
  echo "pyobjc fehlt:  $PY -m pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa"
  exit 1
fi
if ! "$PY" -m PyInstaller --version >/dev/null 2>&1; then
  echo "PyInstaller fehlt - installiere es ..."
  "$PY" -m pip install pyinstaller
fi

WORK="${TMPDIR:-/tmp}/miezi-build"
"$PY" -m PyInstaller --clean --noconfirm --workpath "$WORK/build" --distpath ./dist Miezi.spec

echo
echo "Fertig: $(pwd)/dist/Miezi.app"
