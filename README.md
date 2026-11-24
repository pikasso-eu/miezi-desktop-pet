# Miezi – Desktop-Pet

Eine kleine Pixel-Katze, die oben auf dem Browser-Fenster (Windows: Edge, macOS:
Safari/Chrome/Edge) oder auf der Taskleiste eines Monitors herumläuft, sich putzt,
schläft und sich streicheln lässt.
Python + tkinter. Läuft unter **Windows** und **macOS** (macOS braucht zusätzlich
pyobjc für Fenstererkennung und Rendering, siehe [macos/README.md](macos/README.md)).

## Bedienung

| Aktion | Wirkung |
|---|---|
| Linksklick | streicheln (Herz, kleiner Hüpfer) |
| Ziehen | hochheben und absetzen – sie hüpft danach zurück auf ihren Platz |
| Rechtsklick | Menü: Browser-Modus (Windows: Edge; macOS: Safari/Chrome/Edge) oder Monitor, **Figur**, Größe, Schlafen legen, **Autostart**, Beenden |

Im Browser-Modus läuft sie auf der Oberkante des vordersten Browser-Fensters (bei
maximiertem Fenster in der Tab-Leiste, die Fensterknöpfe bleiben frei). Unter Windows
ist das Edge, unter macOS standardmäßig Safari (Menü „Browser“ für Chrome/Edge). Ohne
Browser-Fenster wartet sie auf dem zweiten Monitor. Unter Windows versteckt sie sich bei
Vollbild (Video, F11); unter macOS bleibt sie im echten Vollbild-Space unsichtbar (macOS
lässt normale App-Fenster dort nicht über Safari), in einem maximierten Safari-Fenster
läuft sie oben in der Tab-Leiste.
Einstellungen: `%APPDATA%\Miezi\settings.json` bzw. `~/Library/Application Support/Miezi/settings.json`,
Fehlerprotokoll: jeweils `error.log` daneben.

Unter macOS ist Safari der Standard; das Menü **Browser** stellt auf Chrome/Edge um.
Die Katze zeichnet dort über einen Core-Animation-Layer (Tk 9 kann keine transparenten
Fenster mit Alpha-Bildern). Im echten macOS-Vollbild bleibt sie unsichtbar, weil macOS
ein normales App-Fenster nicht in den Safari-Space lässt; in einem **maximierten**
Safari-Fenster läuft sie sichtbar in der Tab-Leiste. Details und die Technik stehen in
[macos/README.md](macos/README.md#so-funktioniert-es-jetzt).

## Ordner

```
common/              plattformunabhängig (Windows und macOS)
  characters.py      Figuren laden, Einzelbilder zusammensetzen (Spiegeln, Herz, Zzz)
  sprites/           eine Datei pro Figur (erzeugt von tools/), __init__.py = Verzeichnis
windows/
  miezi.py           die App für Windows (Fenster, Edge-Erkennung, Autostart über Win32)
  build.cmd          baut windows\Miezi.exe
macos/
  miezi_mac.py       die App für macOS (Quartz für Fenster, LaunchAgent für Autostart)
  build.sh + Miezi.spec  baut macos/dist/Miezi.app (ohne Dock-Symbol)
tools/               Werkzeuge, die Sprites erzeugen (laufen nur beim Entwickeln)
  convert_sheet.py   Sheet nach Vorlage -> Figur   (für neue Tiere)
  make_template.py   erzeugt die Vorlage aus der schwarzen Katze
  convert_black_cat.py  Sonderfall: KI-Sheet der schwarzen Katze -> Figur
  gen_cat_sprites.py    orange Katze aus Grundformen
  make_icon.py          Programm-Icons aus der Sitzpose der schwarzen Katze
  sheetlib.py        gemeinsame Helfer (PNG lesen/schreiben, Farben, Figuren-Verzeichnis)
art/
  vorlage_katze.png        Beispiel-Sheet – so soll ein Sheet aussehen
  vorlage_katze.json       Beschreibung dazu
  vorlage_katze_raster.png dieselbe Vorlage mit sichtbaren Zellen (nur zum Anschauen)
  schwarze_katze_ki_sheet.png  Original-KI-Bild der schwarzen Katze
  miezi.ico / miezi.icns   Programm-Icons für EXE und App (von tools/make_icon.py erzeugt)
```

So hängt es zusammen:

```
art/<tier>.png + .json ──tools/convert_sheet.py──▶ common/sprites/<tier>.py ──▶ App / EXE
```

Die App braucht zur Laufzeit nur `common/` und ihren Plattformordner – keine PNGs.

## Starten und bauen (Windows)

```
python windows\miezi.py                      # direkt aus dem Quelltext
windows\build.cmd                            # baut windows\Miezi.exe (PyInstaller wird bei Bedarf installiert)
python windows\miezi.py --preview bild.png schwarz mittel   # Vorschaubild einiger Posen
```

Die EXE ist eigenständig, auf dem Ziel-PC wird kein Python gebraucht.

## Starten und bauen (macOS)

```
brew install python-tk@3.13                      # Tkinter für Homebrew-Python (einmalig)
python3 -m venv .venv
.venv/bin/pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa pyinstaller
.venv/bin/python macos/miezi_mac.py              # direkt aus dem Quelltext
PYTHON="$PWD/.venv/bin/python" macos/build.sh    # baut macos/dist/Miezi.app
open macos/dist/Miezi.app                        # oder per Doppelklick
```

Details zu Verhalten, Vollbild-Grenze, Gatekeeper und Autostart:
[macos/README.md](macos/README.md).

## Fertige Programme (Releases)

Fertige Builds gibt es auf der [Releases-Seite](../../releases): `Miezi.exe`
(Windows) und `Miezi-macOS-arm64.zip` / `Miezi-macOS-x86_64.zip` (Apple
Silicon / Intel). Eine neue Version erscheint von allein, sobald ein
Versions-Tag gepusht wird – die GitHub-Runner bauen auf echten Windows- und
Mac-Systemen mit denselben Skripten wie oben:

```
git tag v1.0.0
git push origin v1.0.0        # → Actions bauen EXE + ZIPs und hängen sie an den Release
```

Die Dateien sind **unsigniert**: Windows-SmartScreen und macOS-Gatekeeper
zeigen beim ersten Start einen Warnhinweis (Windows: „Weitere Informationen →
Trotzdem ausführen“, macOS: Rechtsklick → Öffnen). Das ist bei Projekten
ohne Zertifikat normal und im Release-Text dokumentiert.

## Neues Tier einbinden

### 1. Sheet malen (oder generieren und aufräumen)

Am einfachsten `art/vorlage_katze.png` als Ausgangspunkt nehmen
(`art/vorlage_katze_raster.png` zeigt die Zellen). Regeln:

- **PNG mit Transparenz** (RGBA), Hintergrund komplett durchsichtig.
- **Harte Kanten**: jedes Pixel ganz deckend oder ganz durchsichtig – keine weichen Ränder,
  kein Schatten, kein Leuchten (das Fenster kann unter Windows nur „ganz oder gar nicht“).
  Halbtransparentes wird ab Deckkraft 128 (einstellbar: `alpha_min`) als deckend gezählt.
- **Festes Raster**: alle Zellen gleich groß, ohne Abstand (oder mit `gap`), oben links beginnend.
  **Eine Zeile pro Animation**, Bilder von links nach rechts.
- **Gleicher Maßstab** in allen Bildern, Tier **schaut nach rechts** (die App spiegelt selbst),
  **Füße auf der Zellunterkante**, Kopf in allen Laufbildern an derselben Stelle (sonst wackelt es).
- **Größe**: Zelle z.B. 40–64 Sprite-Pixel breit. Darf zum Bearbeiten vergrößert sein
  (`pixel`: 4 heißt, ein Sprite-Pixel ist 4×4 Bildpunkte im Sheet) – aber exakt ganzzahlig.
- Höchstens ca. 80 Farben (mehr wird automatisch reduziert).

Zeilen (Reihenfolge frei, Name steht in der JSON):

| `anim` | Bilder | Pflicht | wofür |
|---|---|---|---|
| `walk` | 4–8 | ja | Laufzyklus (Schleife) |
| `sit` | 1–3 | ja | Sitzen; mehrere = schaut mal hierhin, mal dorthin |
| `blink` | 1 | – | Augen zu (sonst wird nicht geblinzelt) |
| `sleep` | 1–2 | ja | Schlafen (2 Bilder = Atmen) |
| `jump` | 1–3 | – | Hinhüpfen: Absprung, Flug, Landung (sonst Laufbild) |
| `drag` | 1–2 | – | beim Herumziehen (sonst Laufbild) |
| `fx` | `heart`, `z` | ja | Herz beim Streicheln, Zzz beim Schlafen (unten links in die Zelle) |
| `extra` | 1–6 | – | Einlagen beim Sitzen (Putzen, Gähnen …), beliebig viele Zeilen |

Fehlt `jump`/`drag`/`blink`, nimmt die App ein Lauf- bzw. Sitzbild.

### 2. JSON daneben legen (`art/<tier>.json`)

```json
{
  "name": "Graue Katze",
  "cell": [62, 47],
  "pixel": 4,
  "order": 10,
  "walk_ticks": 3,
  "sizes": {"klein": 1, "mittel": 1, "gross": 2},
  "small_from_half": true,
  "rim": null,
  "rows": [
    {"anim": "walk", "frames": 6},
    {"anim": "sit", "frames": 2},
    {"anim": "blink", "frames": 1},
    {"anim": "sleep", "frames": 2},
    {"anim": "jump", "frames": 3},
    {"anim": "drag", "frames": 2},
    {"anim": "fx", "frames": ["heart", "z"]},
    {"anim": "extra", "name": "putzen", "frames": 2, "seq": [[1, 10], [2, 6], [1, 10]]}
  ]
}
```

| Feld | Bedeutung |
|---|---|
| `name` | Anzeigename im Menü „Figur“ |
| `cell` | Zellgröße in Sprite-Pixeln [Breite, Höhe] |
| `pixel` | Sheet-Bildpunkte pro Sprite-Pixel (1 = Sheet ist schon in Originalgröße) |
| `gap` | optional: Abstand zwischen Zellen in Sheet-Bildpunkten (Standard 0) |
| `order` | Reihenfolge im Menü (kleiner = weiter oben) |
| `walk_ticks` | Tempo des Laufzyklus: Bildwechsel alle n × 50 ms |
| `sizes` | Vergrößerung für Klein/Mittel/Groß (bei 100 % Windows-Skalierung) |
| `small_from_half` | `true`: „Klein“ bekommt eine eigene halbe Auflösung statt Vergrößerung 1 |
| `rim` | optional: Farbe wie `"#5a5363"` für den äußersten Rand – hilft dunklen Tieren auf dunklem Grund |
| `hop` | optional: Bild für den Hüpfer beim Streicheln (Standard: erstes Sitzbild) |
| `rows[].seq` | nur bei `extra`: Ablauf als [Bildnummer, Dauer in 50-ms-Takten] |

Die Laufgeschwindigkeit ergibt sich aus der Körperbreite (1/40 pro Takt), muss also nicht
eingestellt werden.

### 3. Umwandeln, prüfen, bauen

```
python tools\convert_sheet.py art\graue_katze.png graue_katze
python windows\miezi.py --preview vorschau.png graue_katze
windows\build.cmd
```

(Auf dem Mac entsprechend `python3 tools/convert_sheet.py …`,
`macos/miezi_mac.py --preview …` und `macos/build.sh`.)

Der Konverter schreibt `common/sprites/graue_katze.py` und trägt die Figur automatisch in
`common/sprites/__init__.py` ein. Danach steht sie im Menü „Figur“. Code muss nicht angepasst
werden. Zum Entfernen die Datei löschen und `python tools\sheetlib.py` aufrufen.

### Tipps für KI-generierte Sheets

KI-Bilder sehen wie Pixel-Art aus, haben aber fast nie ein exaktes Raster, die Bilder liegen
frei verteilt, oft mit Schein-Effekten, Beschriftung und leicht unterschiedlichen Größen.
Zwei Wege:

1. **Aufräumen** in einem Pixel-Editor (Aseprite, LibreSprite, Piskel): auf die echte
   Pixelgröße verkleinern (nächster Nachbar), Bilder ins Raster der Vorlage schieben,
   Ränder hart machen, Effekte und Text entfernen. Danach `convert_sheet.py`.
2. **Eigener Konverter** nach dem Muster von `tools/convert_black_cat.py`: der schätzt das
   Pixelraster, schneidet feste Bereiche aus, richtet am Kopf aus und gleicht Größen an.
   Lohnt sich, wenn man das Sheet nicht von Hand bearbeiten will.

Im Prompt hilft: „transparenter Hintergrund, keine Beschriftung, kein Leuchten, festes Raster
mit gleich großen Zellen, Katze schaut nach rechts, Füße auf der Zellunterkante“.

## Mitwirken

Fehlerberichte und neue Tiere sind willkommen. **Bitte vorher
[CONTRIBUTING.md](CONTRIBUTING.md) lesen.** Die wichtigste Regel in Kurzform:

> **Kein Pull Request ohne vorher freigegebenes Issue.** PRs ohne Issue
> können ohne Kommentar geschlossen werden. Auf Issues und PRs wird nach
> Möglichkeit geantwortet – eine Antwort ist nicht zugesagt, und Schweigen
> ist keine Einladung zum Pingen. Inaktive Beiträge werden nach einer Frist
> automatisch geschlossen.

## Lizenz

[MIT](LICENSE) © 2026 Dirk Varnholt. Sicherheitslücken bitte vertraulich
melden, siehe [SECURITY.md](SECURITY.md).
