"""Figuren-Verzeichnis - automatisch gepflegt von tools/sheetlib.py (update_registry).

Jede Datei <id>.py hier ist eine Figur mit CHARACTER und SETS. Die Werkzeuge in tools/
tragen neue Figuren hier selbst ein; von Hand: python tools/sheetlib.py"""

from . import orange
from . import schwarz

MODULES = {'orange': orange, 'schwarz': schwarz}
