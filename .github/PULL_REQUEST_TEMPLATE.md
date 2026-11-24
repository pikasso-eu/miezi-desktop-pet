<!--
Danke für deine Arbeit! Ein Hinweis vorab, damit keine Zeit verloren geht:

PRs ohne vorheriges, vom Maintainer freigegebenes Issue können ohne
Kommentar geschlossen werden. Siehe CONTRIBUTING.md – die Regel ist dort
begründet und wird hier nicht diskutiert.
-->

## Issue (Pflicht)

Closes #

## Was ändert dieser PR – und warum?

_1–3 Sätze. Das „was“ und das „warum“, nicht jede Zeile des „wie“._

## Wie wurde getestet?

| Betriebssystem    | Wie gestartet                       | Getestet |
|-------------------|-------------------------------------|----------|
| Windows           | `python windows\miezi.py`           | ☐ ja / ☐ nein |
| macOS             | `python3 macos/miezi_mac.py`        | ☐ ja / ☐ nein |

## Checkliste

- [ ] Es gibt ein Issue, und sein Inhalt wurde vom Maintainer freigegeben.
- [ ] Der PR behandelt genau **ein** Thema und bleibt klein.
- [ ] Auf mindestens einem unterstützten Betriebssystem getestet (Tabelle oben).
- [ ] Bei neuen Tieren: Sheet mit `tools/convert_sheet.py` umgewandelt,
      `common/sprites/` nicht von Hand editiert.
- [ ] Keine Build-Artefakte im PR (EXE, `dist/`, `build/`, `.venv/`).
- [ ] README und/oder CHANGELOG ergänzt, falls sich Verhalten oder Bedienung ändern.
