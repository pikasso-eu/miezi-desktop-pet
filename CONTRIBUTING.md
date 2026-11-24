# Mitwirken an Miezi

Schön, dass die kleine Katze Interesse weckt! Miezi lebt von Freizeit und
Freude an Pixel-Tieren – deshalb gibt es hier ein paar klare Regeln. Sie sind
keine Bürokratie, sondern Projektbetrieb: Sie sparen beiden Seiten Zeit und
Diskussionen.

## Die wichtigste Regel zuerst

**Kein Pull Request ohne vorheriges, angenommenes Issue.**
Beschreibt bitte zuerst das Problem oder die Idee in einem Issue. Erst wenn der
Maintainer dort grünes Licht gegeben hat, lohnt sich Arbeit an einem PR.
**PRs ohne freigegebenes Issue können ohne Kommentar geschlossen werden.**
Das ist keine persönliche Ablehnung und keine Höflichkeitsfrage – es ist die
Arbeitsweise dieses Projekts, und sie wird nicht im PR selbst ausgehandelt.

## Wofür ich dankbar bin

- **Fehlerberichte** mit Nachbauanleitung: Betriebssystem, Version, was
  passiert ist, was passieren sollte. Auch gern das `error.log` (Pfade stehen
  im README).
- **Neue Tiere** als Sprite-Sheet nach den Regeln im README
  („Neues Tier einbinden“) – das ist die willkommenste Beitragsart.
- **Kleine, gezielte Fixes**: Tippfehler, Abstürze, offensichtliche
  Logikfehler. Bei reinen Tippfehler-/Doku-PRs darf das Issue entfallen.

## Was ich voraussichtlich nicht übernehme

- Große Refactorings, Technologie- oder Framework-Wechsel
  (Python + tkinter bleibt die Basis).
- Neue externe Abhängigkeiten in der Laufzeit-App.
- Reine Stil- oder „Modernisierungs“-PRs ohne zugrundeliegendes Problem.
- Funktionen, die nicht zum Ziel passen: eine kleine, eigenständige,
  leichtgewichtige Desktop-Katze – ohne Netzwerk, Telemetrie, Updater oder
  Konten.
- Automatisch oder maschinell erstellte Massen-PRs.

## Keine Antwortpflicht – bitte ernst genommen

Issues und PRs werden gelesen, wenn Zeit ist. Manchmal bleibt eine Antwort
aus, und das ist in Ordnung: **Schweigen ist keine Einladung zum Pingen oder
Nachsetzen.** Inaktive Issues und PRs werden nach einer Frist automatisch
geschlossen (siehe Workflow „Zurück ohne Rückmeldung“). Auch ein geschlossener
PR ist keine Bewertung der Arbeit – wer weitermachen möchte, eröffnet zuerst
ein Issue und diskutiert das Anliegen dort.

## So läuft’s, wenn es grünes Licht gibt

1. Forken, Zweig von `main` für genau das eine Thema anlegen.
2. Klein halten: ein PR = ein Thema. Lieber zwei kleine als ein großer.
3. Testen und im PR angeben, **wo** getestet wurde:
   `python windows\miezi.py` bzw. `python3 macos/miezi_mac.py`.
   Neue Tiere mit `tools/convert_sheet.py` umwandeln und mit
   `--preview` prüfen.
4. PR beschreiben: **was** und **warum** (nicht jede Zeile „wie“),
   Issue verlinken (`Closes #123`), Checkliste im PR-Template ausfüllen.

## Spielregeln für Grafiken (Kurzfassung)

PNG mit Transparenz, harte Kanten (Pixel ganz deckend oder ganz
durchsichtig), festes Raster, eine Zeile pro Animation, Tier schaut nach
rechts, Füße auf der Zellunterkante. Details im
[README](README.md#neues-tier-einbinden).
Die Dateien unter `common/sprites/` werden von den Werkzeugen erzeugt und
nicht von Hand editiert.

## Ton

Freundlich und direkt. Kritik richtet sich an Code und Grafiken, nicht an
Menschen. Details im [Code of Conduct](CODE_OF_CONDUCT.md).
