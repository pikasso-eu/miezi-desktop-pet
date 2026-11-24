# Miezi für macOS

Die Mac-Version läuft (`macos/miezi_mac.py`) und lässt sich mit `macos/build.sh` zu
`macos/dist/Miezi.app` bauen. Die Katze verhält sich wie unter Windows: sie läuft oben
auf dem Fenster des Browsers – Standard ist **Safari**, im Menü „Browser“ auch Chrome
oder Edge –, sitzt ohne Browser auf dem Ausweich-Bildschirm, putzt sich, schläft,
läuft auf der Taskleisten-Kante des gewählten Monitors und lässt sich streicheln.
Im Browser-Vollbild (eigener macOS-Space) bleibt sie unsichtbar; macOS lässt ein
normales App-Fenster dort nicht über Safari legen. In einem **maximierten** Safari-Fenster
(Titelleiste doppelklicken oder Fenster → Zoomen) läuft sie oben in der Tab-Leiste.

## So funktioniert es jetzt

### Wo die Katze läuft

| Situation | Verhalten |
|---|---|
| Browserfenster normal, Platz über dem Fenster | Katze steht auf der Oberkante des Fensters, der Körper ragt darüber |
| Browserfenster maximiert (füllt die Arbeitsfläche, Menüleiste bleibt) | Katze läuft in der Tab-Leiste; links bleiben 150 pt für die Ampel frei, rechts 8 pt Rand |
| Browser im echten macOS-Vollbild (eigener Space) | Katze wird an die Oberkante des Vollbildfensters gesetzt, ist dort aber **nicht sichtbar** (macOS-Space-Sperre, siehe unten) |
| Kein Browser offen | Katze wartet auf dem Ausweichmonitor (zweiter Bildschirm, sonst Hauptbildschirm) |
| Monitor-Modus (Menü) | Katze läuft auf der Arbeitsfläche des gewählten Monitors, immer im Vordergrund |

Standardbrowser ist **Safari**. Rechtsklick → **Browser** stellt auf Safari, Chrome oder
Edge um; `MIEZI_BROWSER="Google Chrome"` ergänzt beim Start aus dem Terminal einen
anderen App-Namen. Die Auswahl wird in `settings.json` gespeichert.

### Der Ablauf pro Tick

1. **Fenster finden:** `CGWindowListCopyWindowInfo` liefert die Fenster des gewählten
   Browsers (`kCGWindowOwnerName`, `layer == 0`, mindestens 300×150), von vorne nach
   hinten. Das braucht **keine** Bildschirmaufnahme-Freigabe.
2. **Platz berechnen:** `surface()` entscheidet, ob die Katze auf der Oberkante, in der
   Tab-Leiste oder auf dem Monitor läuft und ob sie im Vordergrund bleiben muss. Topmost
   ist sie nur, wenn der Browser die vorderste App ist.
3. **Zeichnen:** Tk hält nur das leere, transparente Fenster; die Pixel kommen aus einem
   `CALayer` auf der Frame-View (Details unter „Rendering“). Jedes Einzelbild ist ein
   `CGImage` mit echtem Alpha und ersetzt das vorherige vollständig.
4. **Bewegen:** Die Verhaltenslogik (Laufen, Sitzen, Schlafen, Hüpfen, Putzen) ist
   dieselbe wie unter Windows; der Tick läuft alle 50 ms.

### Die Vollbild-Grenze

Ein echtes macOS-Vollbild liegt in einem eigenen Space. Das Fenster einer normalen App
bleibt in seinem eigenen Space; `CanJoinAllSpaces`, `FullScreenAuxiliary`,
`CanJoinAllApplications` und ein hoher Fensterpegel ändern daran nichts. Auch die
privaten Space-APIs (`CGSSetWindowListWorkspace`, `CGSAddWindowsToSpaces`) verweigern
das Umsetzen eines normalen App-Fensters. Deshalb ist die Katze im echten Vollbild
unsichtbar – das ist eine macOS-Einschränkung, kein Fehler der App.

**Workaround:** Safari maximieren (Titelleiste doppelklicken oder Fenster → Zoomen)
statt `Ctrl+Cmd+F`. Dann bleibt die Katze im selben Space und läuft sichtbar in der
Tab-Leiste.

### Menü und Einstellungen

- **Im Browser (oben)** / **Monitor 1, 2, …** – Untergrund wählen
- **Browser** – Safari, Chrome, Edge
- **Figur**, **Größe** – schwarze/orange Katze, klein/mittel/groß
- **Schlafen legen**, **Bei Anmeldung starten**, **Beenden**

Einstellungen: `~/Library/Application Support/Miezi/settings.json` (wird beim Ändern
über das Menü geschrieben). Fehlerprotokoll: `error.log` daneben; die App startet nur
einmal (Sperrdatei `miezi.lock`).

## Entwicklungsumgebung

```
brew install python-tk@3.13                    # Tkinter für Homebrew-Python (einmalig)
python3.13 -m venv .venv                       # Projekt-venv im Repo-Stamm
.venv/bin/pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa pyinstaller
.venv/bin/python macos/miezi_mac.py            # starten
.venv/bin/python macos/miezi_mac.py --preview vorschau.png schwarz mittel
MIEZI_BROWSER="Google Chrome" .venv/bin/python macos/miezi_mac.py   # Katze auf anderem Browser testen
```

Tk und Quartz rechnen beide in Punkten – die DPI-Rechnung der Windows-Version entfällt.

## Bauen

```
PYTHON="$PWD/.venv/bin/python" macos/build.sh   # aus dem Repo-Stamm
# oder aus macos/:  PYTHON=../.venv/bin/python ./build.sh
open macos/dist/Miezi.app
```

`macos/Miezi.spec` setzt `LSUIElement` in die Info.plist (kein Dock-Symbol, kein Cmd-Tab).
Beim Start aus dem Quelltext erledigt `setActivationPolicy_(Accessory)` das.

**Gatekeeper:** Ohne Apple-Entwicklerzertifikat warnt macOS beim ersten Start einer
heruntergeladenen App. Öffnen per Rechtsklick → Öffnen, oder einmal
`xattr -dr com.apple.quarantine Miezi.app`. PyInstaller signiert auf Apple Silicon
automatisch ad hoc; das reicht für den eigenen Mac.

## Wie die Portierung die Windows-Stellen ersetzt

| Windows (`windows/miezi.py`) | macOS (`macos/miezi_mac.py`) |
|---|---|
| `-transparentcolor` + KEY-Farbe | Core-Animation-Layer mit CGImage (straight Alpha) – siehe „Rendering“ unten; `-transparent` + `bg="systemTransparent"` bleibt als Unterbau |
| `fix_exstyle` (Toolwindow, NoActivate) | `overrideredirect` reicht in Tk 9 nicht – die NSWindow wird per `setStyleMask_(0)` randlos gemacht; `LSUIElement`/Accessory gegen das Dock-Symbol |
| `EnumDisplayMonitors` | `NSScreen.screens()`: `frame()`/`visibleFrame()`, Ursprung unten links → y umrechnen; Hauptbildschirm liegt in Cocoa bei (0, 0) |
| `EnumWindows` + Klassenname + Prozessname | Quartz `CGWindowListCopyWindowInfo(OnScreenOnly \| ExcludeDesktopElements)`: `kCGWindowOwnerName == BROWSER_APP` (Safari/Chrome/Edge), `kCGWindowLayer == 0`, ≥ 300×150; Liste ist schon von vorne nach hinten sortiert. Braucht **keine** Bildschirmaufnahme-Freigabe. |
| Vollbild = Fenster == Monitor → verstecken | Browser-Vollbild: `surface()` setzt die Katze an die Oberkante des Vollbildfensters; macOS lässt ein normales App-Fenster aber nicht in den fremden Space – dort bleibt sie unsichtbar. In einem maximierten Fenster läuft sie in der Tab-Leiste. |
| `stack_above` (über das Edge-Fenster einsortieren) | geht mit fremden Fenstern nicht → `-topmost` nur, solange der Browser die vorderste App ist (`NSWorkspace.frontmostApplication`), sonst normale Ebene |
| `GetCursorPos` | `root.winfo_pointerxy()` |
| Rechtsklick `<Button-3>` | `<Button-2>` (zusätzlich `<Control-Button-1>`) |
| Autostart über Registry `Run` | LaunchAgent `~/Library/LaunchAgents/de.miezi.desktoppet.plist` (`RunAtLoad`), wirkt ab der nächsten Anmeldung |
| Mutex `Local\MieziDesktopPet` | `fcntl.flock` auf `…/Miezi/miezi.lock` (Datei muss offen bleiben, sonst entfällt die Sperre) |
| `%APPDATA%\Miezi` | `~/Library/Application Support/Miezi/` |

Die Verhaltenslogik (Laufen, Sitzen, Schlafen, Hüpfen, Einlagen) ist aus der
Windows-Version übernommen; eine gemeinsame `common/pet.py` (Schritt 1 des alten Plans)
wurde bewusst **nicht** gebaut, damit die Windows-EXE unberührt bleibt. Wenn sich die
Verhaltenslogik künftig ändert, beide Dateien pflegen – oder jetzt zusammenführen.

## Rendering: Core-Animation-Layer statt Tk-Label

Der klassische Trick (`-transparent` + `bg="systemTransparent"` + Alpha-Bilder aufs Label)
funktioniert mit **Tk 9.1 auf dem Mac nicht**: Aqua-Tk zeichnet den Fensterinhalt in ein
Bitmap ohne Alphakanal (`kCGImageAlphaNoneSkipLast`). Durchsichtige Bildpixel werden dort
schwarz, und jedes neue Frame wird per Source-over auf das alte gemalt – die Katze sitzt in
einem schwarzen Rechteck aus übereinanderkopierten Pose-Fragmenten. (Denselben Bug hat
Dodaios/Dodaios#1642.) Tk 8.6 (python.org-Python) kann es noch; ein Downgrade ist aber keine
Option, solange Homebrew nur Tk 9 liefert.

Die Mac-Version zeichnet die Frames deshalb an Tk vorbei (`setup_layer`, `layer_image`,
`layer_refresh` in `miezi_mac.py`):

- Ein `CALayer` hängt auf der **Frame-View** (SuperView der Tk-ContentsView – an der
  ContentsView selbst würde das schwarze Tk-Bitmap dahinter durchscheinen), die ContentsView
  steht auf `alphaValue 0`, bleibt aber Klick-Ziel.
- Jedes Einzelbild wird aus dem Sprite-Raster direkt als RGBA-Bytes aufgebaut (nächster
  Nachbar, `scale × backingScaleFactor`), als `CGImage` mit `kCGImageAlphaLast`
  (straight alpha) erzeugt und per `CATransaction` (ohne implizite Animationen) als
  `contents` gesetzt – das ersetzt das vorherige Bild komplett.
- Pixeldaten in `CFData` (der DataProvider hält sonst nur einen Zeiger auf einen
  Python-Puffer), `CGImageCreate`-Ergebnis wird geprüft, Layer-Rahmen und Backing-Scale
  alle 40 Ticks nachgezogen (Größen-/Monitorwechsel, Re-Attach falls umgebaut).
- Klappt das Anlegen des Layers nicht, fällt `_draw` sichtbar auf das Tk-Label zurück
  (der Weg funktioniert mit Tk 8.6).

## Bekannte Unterschiede zur Windows-Version

- Die Fensterknöpfe (Ampel) sitzen auf dem Mac **links**, die Tab-Leiste bleibt dort also
  rechts frei (Windows: Knöpfe rechts).
- Der Browser-Modus erkennt Safari (Standard), Chrome und Edge; im Menü „Browser“ lässt
  sich das umstellen. `MIEZI_BROWSER=<App-Name>` ergänzt einen anderen Browser.
- Im echten macOS-Vollbild (eigener Space) bleibt die Katze unsichtbar: macOS lässt ein
  Fenster einer normalen App dort nicht über Safari legen – auch nicht mit
  `CanJoinAllSpaces`/`FullScreenAuxiliary`/`CanJoinAllApplications`. In einem maximierten
  Safari-Fenster läuft sie oben in der Tab-Leiste.
- Autostart aus dem Quelltext zeigt auf den Python-Interpreter, der beim Setzen aktiv war
  (venv nicht verschieben). Aus der .app heraus zeigt er auf `Miezi.app/Contents/MacOS/Miezi`.
