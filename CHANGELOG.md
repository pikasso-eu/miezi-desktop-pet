# Changelog

## 2026-11-24 (10)
- Release-Workflow `.github/workflows/release.yml`: ein Tag (`v1.0.0`) genügt –
  GitHub-Runner bauen `windows/build.cmd` (EXE) und `macos/build.sh`
  (App, als ZIP via `ditto`) auf `windows-latest`, `macos-14` (arm64) und
  `macos-13` (x86_64) und hängen die drei Dateien an den GitHub-Release.
  Hinweis auf SmartScreen/Gatekeeper im Release-Text.
- README um Abschnitt „Fertige Programme (Releases)“ ergänzt.

## 2026-11-24 (9)
- Neue Programm-Icons: `tools/make_icon.py` rendert die Sitzpose der schwarzen
  Katze aus `common/sprites/schwarz.py` und schreibt `art/miezi.ico`
  (Windows: 16/24/32/48 als BMP + 256 px PNG) und `art/miezi.icns`
  (macOS: 16–1024 px, PNG-Einträge) – nur Standardbibliothek.
- `windows/build.cmd` und `macos/build.sh` erzeugen die Icons vor jedem Build
  neu; `Miezi.spec` bindet die `.icns` in die App ein, PyInstaller die `.ico`
  in die EXE. (Die laufenden Fenster sind `overrideredirect`, deshalb gibt es
  kein laufzeitabhängiges Taskleisten-Icon – das Icon gehört zur Datei.)

## 2026-11-24 (8)
- Für GitHub vorbereitet: Git-Historie neu aufgebaut (frisches Repository
  ohne die alte Historie), MIT-Lizenz ergänzt.
- Doku für Mitarbeit: `CONTRIBUTING.md` (Regeln inkl. „kein PR ohne
  freigegebenes Issue“, keine Antwortpflicht), PR- und Issue-Vorlagen unter
  `.github/`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.
- Workflow `stale.yml`: inaktive Issues (30 + 14 Tage) und PRs (21 + 14
  Tage) werden automatisch mit Standardtext geschlossen – der Maintainer muss
  dafür nicht antworten.
- README um „Mitwirken“ und „Lizenz“ ergänzt; `.gitignore` um
  System-/Editor-Reste (`.DS_Store`, `Thumbs.db`, …) erweitert.

## 2026-11-23 (7)
- macOS: Safari ist der Standard-Browser; der Menüpunkt „Browser“ stellt auf Safari,
  Chrome oder Edge um, `MIEZI_BROWSER` ergänzt andere. Im echten macOS-Vollbild bleibt
  die Katze unsichtbar (macOS lässt ein normales App-Fenster nicht in den Safari-Space);
  in einem maximierten Safari-Fenster läuft sie oben in der Tab-Leiste.
- macOS: Die Frames gehen über einen Core-Animation-Layer (CGImage, straight Alpha)
  statt über das Tk-Label – kein schwarzer Kasten und keine überlagerten Einzelbilder
  mehr. Bei Fehlern fällt sie sichtbar aufs Label zurück.
- macOS: Layer-Rahmen wird pro Frame gesetzt, Bilddaten liegen in CFData (sichere
  Lebensdauer), `CGImageCreate`-Fehler werden geloggt statt still ein leeres Bild zu setzen.

## 2026-11-23 (6)
- macOS-Version umgesetzt: `macos/miezi_mac.py` läuft wie die Windows-Version (Edge-Kante,
  Monitor-Modus, Streicheln, Ziehen, Menü) – Quartz für Fenster-/Bildschirm-Erkennung,
  echte Alpha-Bilder statt KEY-Farbe, Rechtsklick = Button 2, Autostart über LaunchAgent,
  Einzel-Instanz über flock-Sperrdatei. `windows/miezi.py` bleibt unberührt.
- `macos/build.sh` + `macos/Miezi.spec` bauen `macos/dist/Miezi.app` (LSUIElement, kein
  Dock-Symbol; beim Quelltext-Start erledigt setActivationPolicy das).
- `common/characters.py`: `grid_to_photo(..., transparent=None)` jetzt ein einziger
  put-Aufruf statt Schleife pro Pixel (leere Felder lässt Tk unverändert = durchsichtig).
- `MIEZI_BROWSER=<App-Name>` stellt die Kanten-Erkennung auf einen anderen Browser um
  (Test ohne installiertes Edge).
- READMEs und CHANGELOG angepasst.

## 2026-11-23 (5)
- Neuer Ordneraufbau: `common/` (plattformunabhängig: Figuren, Bild-Zusammenbau),
  `windows/` (App + build.cmd, die EXE liegt jetzt in `windows\Miezi.exe`), `macos/` (Plan für
  die Mac-Version), `art/` (Sheets), `tools/`.
- Figuren sind eigene Module in `common/sprites/` und werden über `__init__.py` (von den
  Werkzeugen gepflegt) automatisch ins Menü übernommen – kein Code-Eingriff für neue Tiere.
- Vorlage `art/vorlage_katze.png` (+ `.json`, + Ansicht mit Raster) und allgemeiner Konverter
  `tools/convert_sheet.py`; Probe: Vorlage → Konverter ergibt bitgenau die schwarze Katze.
- README.md mit Anleitung „Neues Tier einbinden“, macos/README.md mit Portierungsplan.
- Schwarze Katze: Kopf aller Lauf- und Sitzbilder jetzt exakt in derselben Spalte (vorher
  wackelte er durch Rundung bei einigen Bildern um 1 Pixel).
- Autostart-Eintrag zieht beim ersten Start der verschobenen EXE automatisch mit um.

## 2026-11-23 (4)
- Schwarze Katze ist jetzt die Standardfigur.
- Menüpunkt „Mit Windows starten“: Eintrag unter HKCU\…\Run (nur eigener Benutzer,
  keine Adminrechte). Wird die EXE verschoben, zieht der Eintrag beim nächsten Start mit.

## 2026-11-23 (3)
- Zweite Figur „Schwarze Katze“ (Rechtsklick → Figur), aus einem KI-generierten Spritesheet:
  6 Laufbilder, Sitzen mit Umherschauen und Blinzeln, atmendes Schlafen, Sprung (3 Bilder)
  beim Hinhüpfen, 2 Bilder beim Herumziehen.
- Beim Sitzen gelegentliche Einlagen: Putzen, Strecken, Gähnen, Umdrehen.
- Größen der schwarzen Katze: Klein 31 px (eigene halbe Auflösung), Mittel 62 px, Groß 124 px.
- Aufgehellte Kontur, damit sie auf dunklem Edge-Design sichtbar bleibt.
- tools/convert_black_cat.py rechnet das Sheet auf sein Pixelraster herunter, richtet die
  Bilder am Kopf aus und erzeugt black_cat_sprites.py (nur Standardbibliothek).
- Orange Katze unverändert.

## 2026-11-23 (2)
- Katze in doppelter Auflösung (40x26-Raster statt 20x13): Schattierung, Glanzkanten,
  grüne Augen mit Lichtpunkt, Wangen, weißer Brustlatz und Pfoten.
- Laufzyklus mit 4 statt 2 Bildern, atmende Schlafanimation, größere Herz-/Zzz-Effekte.
- Sprites werden von tools/gen_cat_sprites.py aus Grundformen erzeugt (cat_sprites.py).
- Größen jetzt Klein/Mittel/Groß = 40/80/120 px Breite (bei 100 % Skalierung).
- Claude-Krabbe und Figurenmenü entfernt.
- build.ps1 durch build.cmd ersetzt (PowerShell-Skripte sind per Richtlinie gesperrt);
  die EXE landet jetzt direkt im Projektordner.

## 2026-11-23
- Erste Version: Desktop-Pet „Miezi“ (Python/tkinter, Pixel-Katze 20 px Raster).
- Modi: läuft oben auf dem Edge-Fenster oder auf der Taskleiste eines gewählten Monitors;
  ohne Edge-Fenster wartet sie auf dem zweiten Monitor.
- Zweite Figur „Claude-Krabbe“ wählbar.
- build.ps1 baut eine eigenständige Miezi.exe (PyInstaller, kein Python nötig).
