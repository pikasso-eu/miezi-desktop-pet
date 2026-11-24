"""Miezi - ein kleines Desktop-Pet fuer macOS (Python + tkinter + pyobjc).

Wie unter Windows laeuft die Katze oben auf dem Fenster des Browsers (Standard: Safari,
per Menue auch Chrome/Edge) bzw. in der Tab-Leiste, wenn das Fenster den ganzen
Bildschirm fuellt. Ist kein Browser offen, wartet sie auf dem zweiten Bildschirm. Im
echten macOS-Vollbild (eigener Space) laesst macOS ein Fenster einer normalen App nicht
ueber Safari legen; in einem maximierten Safari-Fenster laeuft sie oben in der Tab-Leiste.

Linksklick = streicheln, Ziehen = hochheben und woanders hinsetzen, Rechtsklick = Menue.
Start: Sie erscheint am Mauszeiger und huepft von dort zu ihrem Platz.

Noetig sind pyobjc-framework-Quartz und pyobjc-framework-Cocoa (siehe README hier).
Tk und Quartz rechnen beide in Punkten, deshalb entfaellt die DPI-Rechnung der
Windows-Version.
"""
import fcntl
import json
import math
import os
import plistlib
import random
import sys
import time
import tkinter as tk

# Figuren und Bild-Zusammenbau sind plattformunabhaengig und liegen in ../common
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from characters import CHARACTERS, compose, grid_to_photo  # noqa: E402

try:
    import AppKit
    import CoreFoundation
    import Foundation
    import Quartz
except ImportError:
    sys.exit("pyobjc fehlt:  python3 -m pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa")

BROWSER_DEFAULT = os.environ.get("MIEZI_BROWSER", "Safari")  # Safari ist der Standard
BROWSER_CHOICES = ("Safari", "Google Chrome", "Microsoft Edge")
if BROWSER_DEFAULT not in BROWSER_CHOICES:  # MIEZI_BROWSER darf auch ein anderer Browser sein
    BROWSER_CHOICES = (BROWSER_DEFAULT,) + BROWSER_CHOICES
BROWSER_LABELS = {"Safari": "Safari", "Google Chrome": "Chrome", "Microsoft Edge": "Edge"}
LAUNCH_AGENT = "de.miezi.desktoppet"  # Name der plist unter ~/Library/LaunchAgents


# --------------------------------------------------------------------------- Bild auf Layer
# Aqua-Tk 9 zeichnet den Fensterinhalt in ein Bitmap ohne Alphakanal
# (kCGImageAlphaNoneSkipLast): durchsichtige Bildpixel werden schwarz, und ein neues
# Bild löscht das alte nicht (Source-over) - die Katze säße in einem schwarzen Kasten
# aus übereinanderkopierten Einzelbildern. Deshalb liegt die Grafik als Core-Animation-
# Layer auf der Frame-View über derTk-Inhaltsblick, die auf Alpha 0 gedreht wird;
# Klicks bleiben trotzdem bei ihr. Wie bei Dodaios/Dodaios#1642.


# --------------------------------------------------------------------------- Bildschirme und Fenster
def _to_top_left(rect, primary_h):
    """NSScreen-Rechteck (Ursprung unten links) -> (l, t, r, b), Ursprung oben links."""
    return (rect.origin.x, primary_h - (rect.origin.y + rect.size.height),
            rect.origin.x + rect.size.width, primary_h - rect.origin.y)


def get_monitors():
    """Alle Bildschirme, von links nach rechts sortiert. full = ganz, work = ohne Menueleiste/Dock."""
    screens = AppKit.NSScreen.screens()
    primary_h = screens[0].frame().size.height
    for s in screens:  # der Hauptbildschirm liegt in Cocoa bei (0, 0)
        if s.frame().origin.x == 0 and s.frame().origin.y == 0:
            primary_h = s.frame().size.height
            break
    mons = []
    for s in screens:
        f, v = s.frame(), s.visibleFrame()
        mons.append({"full": _to_top_left(f, primary_h), "work": _to_top_left(v, primary_h),
                     "primary": f.origin.x == 0 and f.origin.y == 0})
    mons.sort(key=lambda m: (m["full"][0], m["full"][1]))
    return mons


def browser_windows(app):
    """Sichtbare Hauptfenster von `app` als (l, t, r, b) - die Liste von Quartz ist schon
    von vorne nach hinten sortiert. Besitzername und Rahmen gibt es ohne jede Freigabe;
    nur der Fenstertitel (den wir nicht brauchen) waere freigabepflichtig."""
    opts = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    out = []
    for w in Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID):
        if w.get("kCGWindowOwnerName") != app or w.get("kCGWindowLayer") != 0:
            continue
        b = w["kCGWindowBounds"]
        if b["Width"] < 300 or b["Height"] < 150:
            continue
        out.append((b["X"], b["Y"], b["X"] + b["Width"], b["Y"] + b["Height"]))
    return out


def browser_frontmost(app):
    try:
        return AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() == app
    except Exception:
        return False



# --------------------------------------------------------------------------- Einstellungen
SETTINGS_DIR = os.path.expanduser("~/Library/Application Support/Miezi")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
DEFAULTS = {"mode": "edge", "monitor": 1, "size": "mittel", "char": "schwarz", "browser": BROWSER_DEFAULT}


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s.update(json.load(f))
    except Exception:
        pass
    return s


def save_settings(s):
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except Exception:
        pass


def log_error(exc):
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(os.path.join(SETTINGS_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {exc!r}\n")
    except Exception:
        pass


# --------------------------------------------------------------------------- Autostart
# LaunchAgent im Benutzerordner: laeuft ohne Adminrechte, wirkt ab der naechsten Anmeldung.
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCH_AGENT}.plist")


def autostart_command():
    if getattr(sys, "frozen", False):  # als Miezi.app
        return [sys.executable]
    return [sys.executable, os.path.abspath(__file__)]


def autostart_get():
    try:
        with open(PLIST_PATH, "rb") as f:
            return plistlib.load(f).get("ProgramArguments")
    except Exception:
        return None


def autostart_set(on):
    try:
        if on:
            os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
            with open(PLIST_PATH, "wb") as f:
                plistlib.dump({"Label": LAUNCH_AGENT, "ProgramArguments": autostart_command(),
                               "RunAtLoad": True}, f)
        else:
            try:
                os.remove(PLIST_PATH)
            except FileNotFoundError:
                pass
    except OSError as exc:
        log_error(exc)


# --------------------------------------------------------------------------- nur eine Instanz
_lock_fh = None

def single_instance():
    """Sperrdatei mit flock. Die Datei muss die ganze Laufzeit offen bleiben - wird das
    Objekt nicht referenziert, schliesst Python es und die Sperre verschwindet."""
    global _lock_fh
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        _lock_fh = open(os.path.join(SETTINGS_DIR, "miezi.lock"), "w")
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit(0)


# --------------------------------------------------------------------------- Pet
TICK_MS = 50


class Pet:
    def __init__(self):
        self.settings = load_settings()
        if self.settings.get("browser") not in BROWSER_CHOICES:
            self.settings["browser"] = BROWSER_DEFAULT
        self.browser = self.settings["browser"]
        self.root = tk.Tk()
        self.root.title("Miezi")
        self.root.overrideredirect(True)
        self.root.attributes("-transparent", True)  # Fenstergrund durchsichtig (systemTransparent)
        self.root.config(bg="systemTransparent")
        self.lbl = tk.Label(self.root, bg="systemTransparent", bd=0, highlightthickness=0, cursor="hand2")
        self.lbl.pack()

        self.frames = {}
        self.apply_size()

        self.root.update()
        self.make_borderless()
        self.setup_layer()  # klappt das nicht (kein Layer), zeichnet _draw aufs Label
        try:  # kein Dock-Symbol, auch beim Start direkt aus dem Quelltext
            AppKit.NSApplication.sharedApplication().setActivationPolicy_(1)  # Accessory
        except Exception:
            pass

        self.monitors = get_monitors()
        self.topmost = None
        self.visible = True

        # Start am Mauszeiger
        self.x, self.y = self.root.winfo_pointerxy()
        self.x -= self.w // 2
        self.y -= self.h // 2
        self.facing_left = random.random() < 0.5
        self.t = 0
        self.surf_key = None
        self.relx = 0
        self.state = None
        self.start_travel()
        self.fx, self.fx_until = None, 0
        self.hop_t = -1
        self.extra = None  # laufende Einlage (Liste von Bildnamen) + Position
        self.extra_i = 0
        self.press = None

        for widget in (self.root, self.lbl):
            widget.bind("<ButtonPress-1>", self.on_press)
            widget.bind("<B1-Motion>", self.on_motion)
            widget.bind("<ButtonRelease-1>", self.on_release)
            widget.bind("<Button-2>", self.on_menu)  # Rechtsklick ist auf dem Mac Button 2
            widget.bind("<Control-Button-1>", self.on_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.mode_var = tk.StringVar()
        self.browser_var = tk.StringVar(value=self.browser)
        self.size_var = tk.StringVar(value=self.settings["size"])
        self.char_var = tk.StringVar(value=self.settings["char"])
        self.autostart_var = tk.BooleanVar()
        cmd = autostart_get()
        if cmd and getattr(sys, "frozen", False) and cmd != autostart_command():
            autostart_set(True)  # App wurde verschoben -> Eintrag auf neuen Pfad
        self.root.after(TICK_MS, self.tick)

    # ---------------------------------------------------------------- Fenster
    def make_borderless(self):
        """Tk 9 auf dem Mac laesst die Titelleiste trotz overrideredirect stehen - die
        NSWindow direkt auf randlos (styleMask 0) und ohne Schatten setzen."""
        self.ns_win = None
        for w in AppKit.NSApplication.sharedApplication().windows():
            if w.title() == "Miezi":
                w.setStyleMask_(0)
                w.setHasShadow_(False)
                w.setExcludedFromWindowsMenu_(True)
                # Guertel und Hosentraeger: -transparent macht das Fenster schon klar,
                # aber styleMask 0 kommt erst danach - background sicher auf durchsichtig.
                w.setOpaque_(False)
                w.setBackgroundColor_(AppKit.NSColor.clearColor())
                self.ns_win = w
                self.overlay_flags()

    def overlay_flags(self):
        """CollectionBehavior, damit das Fenster im Vollbild-Space *anderer* Apps
        erscheint. CanJoinAllSpaces allein genuegt dafuer nicht; entscheidend ist
        CanJoinAllApplications (flacher Fensterpegel, siehe set_topmost)."""
        try:
            behavior = (AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
                        AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)
            behavior |= getattr(AppKit, "NSWindowCollectionBehaviorCanJoinAllApplications", 0)
            self.ns_win.setCollectionBehavior_(behavior)
        except Exception as exc:
            log_error(exc)

    def setup_layer(self):
        """Frame-Layer auf der Frame-View (SuperView der Tk-Inhaltsblick) anlegen.

        Haengt der Layer an der Inhaltsblick selbst, sieht man das schwarze Tk-Bitmap
        dahinter; deshalb liegt er eine Ebene hoeher. Die Inhaltsblick wird erst
        ausgeblendet, wenn das erste Bild wirklich im Layer liegt - so bleibt das
        Fenster sichtbar, falls der Layer-Weg scheitert (siehe disable_layer)."""
        self.layer, self.backing = None, 1
        self.layer_shown = False
        self.host_layer = None
        try:
            cv = self.ns_win.contentView()
            host_view = cv.superview()
            host_view.setWantsLayer_(True)
            host = host_view.layer()
            if host is None:
                return
            cv.setWantsLayer_(True)
            self.host_layer = host
            layer = Quartz.CALayer.layer()
            layer.setContentsGravity_(Quartz.kCAGravityResize)
            layer.setMinificationFilter_(Quartz.kCAFilterNearest)
            layer.setMagnificationFilter_(Quartz.kCAFilterNearest)
            layer.setZPosition_(1000)
            # NSNull als Aktion = keine impliziten Animationen (Fade/Move) beim Bildwechsel.
            null = Foundation.NSNull.null()
            layer.setActions_({k: null for k in
                               ("contents", "bounds", "position", "hidden", "onOrderIn", "onOrderOut")})
            self.backing = int(self.ns_win.backingScaleFactor() or 1)  # Retina: scharf bauen
            layer.setContentsScale_(self.backing)
            layer.setFrame_(self.layer_frame())  # Punkte, relativ zur Frame-View
            host.addSublayer_(layer)
            self.layer = layer
        except Exception as exc:
            log_error(exc)
            self.layer = None

    def layer_frame(self):
        """Layer-Rahmen in Punkten, relativ zur Frame-View (Ursprung unten links)."""
        f = self.ns_win.contentView().frame()
        return ((f.origin.x, f.origin.y), (self.w, self.h))

    def layer_refresh(self):
        """Layer-Rahmen, Backing-Scale und Attach nachziehen (Groessen-/Monitorwechsel)."""
        try:
            self.overlay_flags()
            cv = self.ns_win.contentView()
            self.layer.setFrame_(self.layer_frame())
            scale = int(self.ns_win.backingScaleFactor() or 1)
            if scale != self.backing:
                self.backing = scale
                self.frames = {k: v for k, v in self.frames.items() if k[0] != "L"}
                self.layer.setContentsScale_(scale)
            host = cv.superview().layer()
            if host is None:  # Tk hat die Ansicht umgebaut -> wieder aufs Label
                self.disable_layer()
                return
            if host is not self.host_layer or self.layer.superlayer() is not host:
                self.host_layer = host
                host.addSublayer_(self.layer)
            if self.layer_shown:
                cv.setAlphaValue_(0.0)
            if self.topmost:
                # Nach einem Space-Wechsel (Safari -> Vollbild) wieder nach vorn holen.
                self.ns_win.orderFrontRegardless()
        except Exception as exc:
            log_error(exc)

    def disable_layer(self):
        """Layer abschalten und das Tk-Bitmap wieder sichtbar machen (Fallback)."""
        try:
            self.ns_win.contentView().setAlphaValue_(1.0)
        except Exception as exc:
            log_error(exc)
        self.layer = None
        self.layer_shown = False

    def layer_image(self, name, fx, phase):
        """Einzelbild als CGImage (straight RGBA, naechster Nachbar) - im frames-Cache."""
        key = ("L", name, self.facing_left, fx, phase)
        img = self.frames.get(key)
        if img is None:
            grid = compose(self.look, name, self.facing_left, fx, phase)
            z = self.scale * self.backing
            colors = {c: bytes.fromhex(v[1:]) + b"\xff" for c, v in self.look["PALETTE"].items()}
            clear = b"\x00\x00\x00\x00" * z  # auch transparente Pixel auf z vergroessern
            rows = []
            for row in grid:
                line = b"".join(clear if c == "." else colors[c] * z for c in row)
                rows.extend([line] * z)  # Pixel-Art: hart hochskalieren, keine Weichzeichnung
            data = b"".join(rows)
            w2, h2 = len(grid[0]) * z, len(grid) * z
            if len(data) != w2 * h2 * 4:  # faengt Skalierungsfehler wie den clear-Pixel-Bug
                raise ValueError(f"Bildpuffer falsch: {len(data)} statt {w2 * h2 * 4} Bytes")
            # CFData kopiert die Bytes und wird vom Provider gehalten; mit
            # CGDataProviderCreateWithData(None, data, ...) haette der Provider nur
            # einen Zeiger auf den Python-Puffer, der nach dem Rueckweg frei wird.
            cfdata = CoreFoundation.CFDataCreate(None, data, len(data))
            prov = Quartz.CGDataProviderCreateWithCFData(cfdata)
            img = Quartz.CGImageCreate(w2, h2, 8, 32, w2 * 4,
                                       Quartz.CGColorSpaceCreateDeviceRGB(),
                                       Quartz.kCGImageAlphaLast, prov, None, False,
                                       Quartz.kCGRenderingIntentDefault)
            if img is None:
                raise ValueError(f"CGImageCreate lieferte None ({w2}x{h2}, {len(data)} Bytes)")
            self.frames[key] = img
        return img

    def apply_size(self):
        if self.settings.get("char") not in CHARACTERS:
            self.settings["char"] = DEFAULTS["char"] if DEFAULTS["char"] in CHARACTERS else next(iter(CHARACTERS))
        self.char = CHARACTERS[self.settings["char"]]
        look_name, zoom = self.char["sizes"].get(self.settings["size"], self.char["sizes"]["mittel"])
        self.look = self.char["looks"][look_name]
        self.scale = max(1, round(zoom))  # Punkte = Tk-Pixel, kein DPI-Faktor wie unter Windows
        self.frames.clear()
        self.w = self.look["W"] * self.scale
        self.h = (self.look["BODY_H"] + self.look["FX_H"]) * self.scale
        self.body_h = self.look["BODY_H"] * self.scale
        self.unit = self.w / 40  # Bewegungseinheit = 1/40 Koerperbreite

    def frame(self, name, fx=None, phase=0):
        key = (name, self.facing_left, fx, phase)
        img = self.frames.get(key)
        if img is None:
            grid = compose(self.look, name, self.facing_left, fx, phase)
            img = grid_to_photo(grid, self.scale, self.look["PALETTE"], transparent=None)
            self.frames[key] = img
        return img

    def drag_frame(self):
        frames = self.char["drag"]
        return frames[(self.t // 6) % len(frames)]

    def jump_frame(self, p):
        frames = self.char["jump"]
        k = 0 if p < 0.15 else (2 if p > 0.85 else 1)
        return frames[min(k, len(frames) - 1)]

    def set_topmost(self, on):
        if self.topmost != on:
            self.root.attributes("-topmost", on)
            try:
                # StatusWindowLevel (25) + CanJoinAllApplications: damit erscheint das
                # Fenster auch ueber dem Vollbild-Space von Safari. Ein hoeherer Pegel
                # (screenSaver) wird vom Window-Server dort nicht mitgezeichnet.
                self.ns_win.setLevel_(AppKit.NSStatusWindowLevel if on else AppKit.NSNormalWindowLevel)
                self.overlay_flags()  # Tk setzt die CollectionBehavior bei -topmost zurueck
                if on:
                    self.ns_win.orderFrontRegardless()
            except Exception as exc:
                log_error(exc)
            self.topmost = on

    def show(self, on):
        if self.visible != on:
            self.root.attributes("-alpha", 1.0 if on else 0.0)
            self.visible = on
            self.overlay_flags()  # auch -alpha setzt die CollectionBehavior zurueck

    # ---------------------------------------------------------------- Untergrund
    def pick_monitor(self, index):
        if not self.monitors:
            self.monitors = get_monitors()
        index = max(0, min(index, len(self.monitors) - 1))
        return self.monitors[index]

    def fallback_monitor(self):
        """Ohne Browser: auf den zweiten Bildschirm (falls vorhanden), sonst Hauptbildschirm."""
        for m in self.monitors:
            if not m["primary"]:
                return m
        return self.monitors[0]

    def monitor_of_rect(self, rect):
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        for m in self.monitors:
            l, t, r, b = m["full"]
            if l <= cx <= r and t <= cy <= b:
                return m
        return self.monitors[0]

    def browser_fullscreen(self):
        """Browser-Fenster, das einen ganzen Monitor bedeckt - auch in einem anderen
        Space. `OnScreenOnly` sieht das Safari-Vollbild dort nicht immer, `All` schon."""
        opts = Quartz.kCGWindowListOptionAll
        for w in Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID):
            if w.get("kCGWindowOwnerName") != self.browser or w.get("kCGWindowLayer") != 0:
                continue
            b = w["kCGWindowBounds"]
            if b["Width"] < 300 or b["Height"] < 150:
                continue
            l, t = b["X"], b["Y"]
            r, bb = l + b["Width"], t + b["Height"]
            for mon in self.monitors:
                fl, ft, fr, fb = mon["full"]
                if l <= fl and t <= ft and r >= fr and bb >= fb:
                    return (l, t, r, bb)
        return None

    def surface(self):
        """Liefert (key, left, right, floor_y, topmost) fuer den aktuellen Untergrund."""
        if self.t % 40 == 0:
            self.monitors = get_monitors()
        if self.settings["mode"] == "edge":
            full = self.browser_fullscreen()
            if full is not None:
                # Browser im Vollbild (auch im eigenen Space): oben im Fenster laufen.
                l, t, r, _b = full
                return (("edge", self.browser, "full"), l, r,
                        t + self.body_h + 2, browser_frontmost(self.browser))
            wins = browser_windows(self.browser)
            if wins:
                l, t, r, b = wins[0]
                mon = self.monitor_of_rect((l, t, r, b))
                fl, ft, fr, fb = mon["full"]
                front = browser_frontmost(self.browser)
                if l <= fl and t <= ft and r >= fr and b >= fb:
                    # Browser im Vollbild: oben im Fenster laufen statt zu verschwinden.
                    # Das Fenster joint per CollectionBehavior den Vollbild-Space.
                    return (("edge", self.browser, "full"), l, r,
                            t + self.body_h + 2, front)
                if t - mon["work"][1] >= self.body_h:
                    # Platz ueber dem Fenster: auf der Oberkante laufen
                    return (("edge", self.browser, "top"), l, r, t + self.scale, front)
                # Randlos/Fuellhoehe: in der Tab-Leiste laufen, Ampel-Knoepfe links frei lassen
                margin = 150
                return (("edge", self.browser, "tabs"), l + margin, r - 8,
                        t + self.body_h + 2, front)
            mon = self.fallback_monitor()
        else:
            mon = self.pick_monitor(self.settings["monitor"])
        l, t, r, b = mon["work"]
        return (("mon", mon["full"]), l, r, b, True)

    # ---------------------------------------------------------------- Verhalten
    def set_state(self, state, ticks_min=0, ticks_max=0):
        self.state = state
        self.state_until = self.t + random.randint(ticks_min, ticks_max)

    def start_travel(self):
        self.state = "travel"
        self.travel_from = (self.x, self.y)
        self.travel_p = 0.0
        self.travel_steps = None

    def next_behavior(self, sleepy=False):
        roll = random.random()
        if self.state == "walk":
            if roll < (0.35 if sleepy else 0.08):
                self.set_state("sleep", 200, 600)
            elif roll < 0.7:
                self.set_state("sit", 30, 120)
            else:
                self.facing_left = not self.facing_left
                self.set_state("walk", 40, 160)
        elif self.state == "sleep":
            self.set_state("sit", 40, 80)
        else:
            if roll < (0.3 if sleepy else 0.12):
                self.set_state("sleep", 200, 600)
            else:
                if random.random() < 0.4:
                    self.facing_left = not self.facing_left
                self.set_state("walk", 40, 200)

    # ---------------------------------------------------------------- Tick
    def tick(self):
        try:
            self._tick()
        except Exception as exc:  # nie die Schleife sterben lassen
            log_error(exc)
        self.root.after(TICK_MS, self.tick)

    def _tick(self):
        self.t += 1
        surf = self.surface()
        if surf is None:
            self.show(False)
            return
        self.show(True)
        key, left, right, floor, topmost = surf
        self.set_topmost(topmost or self.state == "drag")

        max_rel = max(0, right - self.w - left)
        ch = self.char
        name, fx, phase, yoff = ch["sit"][0], None, 0, 0
        if self.state != "sit":
            self.extra = None

        if self.state == "drag":
            name = self.drag_frame()
        elif self.state == "travel":
            tx = min(max(self.travel_from[0], left), left + max_rel)
            ty = floor - self.h
            if self.travel_steps is None:
                dist = math.hypot(tx - self.travel_from[0], ty - self.travel_from[1])
                self.travel_steps = max(6, min(36, dist / (6 * self.unit)))
                self.travel_arc = min(30 * self.unit, dist * 0.35)
                self.facing_left = tx < self.travel_from[0]
            self.travel_p = min(1.0, self.travel_p + 1 / self.travel_steps)
            p = self.travel_p
            e = p * p * (3 - 2 * p)
            fx0, fy0 = self.travel_from
            self.x = round(fx0 + (tx - fx0) * e)
            self.y = round(fy0 + (ty - fy0) * e - math.sin(p * math.pi) * self.travel_arc)
            name = self.jump_frame(p)
            if p >= 1.0:
                self.surf_key = key
                self.relx = tx - left
                self.set_state("sit", 10, 30)
        else:
            if key != self.surf_key:
                self.start_travel()
                return self._draw(self.jump_frame(0))
            sleepy = key[0] == "mon" and self.settings["mode"] == "edge"
            if self.t >= self.state_until and self.hop_t < 0 and not self.extra:
                self.next_behavior(sleepy)
            if self.state == "walk":
                self.relx += (-1 if self.facing_left else 1) * self.unit
                if self.relx <= 0:
                    self.relx, self.facing_left = 0, False
                elif self.relx >= max_rel:
                    self.relx, self.facing_left = max_rel, True
                walk = ch["walk"]
                name = walk[(self.t // ch["walk_ticks"]) % len(walk)]
                if random.random() < 0.004:
                    self.facing_left = not self.facing_left
            elif self.state == "sleep":
                name = ch["sleep"][(self.t // 24) % 2]  # Atmen
                fx, phase = "zzz", (self.t // 12) % 3
            else:
                if not self.extra and ch["extras"] and self.hop_t < 0 and random.random() < 0.006:
                    seq = random.choice(list(ch["extras"].values()))
                    self.extra = [n for n, ticks in seq for _ in range(ticks)]
                    self.extra_i = 0
                if self.extra:
                    name = self.extra[self.extra_i]
                    self.extra_i += 1
                    if self.extra_i >= len(self.extra):
                        self.extra = None
                elif (self.t % 70) < 3:
                    name = ch["blink"]
                else:
                    name = ch["sit"][(self.t // 80) % len(ch["sit"])]  # mal hierhin, mal dorthin schauen
            if max_rel == 0:
                self.relx = 0
            self.relx = min(max(self.relx, 0), max_rel)
            if self.hop_t >= 0:  # Freudenhuepfer nach dem Streicheln
                k = self.hop_t / 10
                yoff = -round(math.sin(k * math.pi) * 5 * self.unit)
                self.hop_t = self.hop_t + 1 if self.hop_t < 10 else -1
                name = ch["hop"] if self.hop_t > 0 else ch["sit"][0]
            self.x = left + round(self.relx)
            self.y = floor - self.h + yoff

        if self.t < self.fx_until and fx is None:
            fx, phase = self.fx, (self.t // 6) % 2
        self._draw(name, fx, phase)

    def _draw(self, name, fx=None, phase=0):
        self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")
        if self.layer is not None and self.t % 40 == 0:
            self.layer_refresh()
        if self.layer is not None:
            try:
                img = self.layer_image(name, fx, phase)
                self.layer.setFrame_(self.layer_frame())
                began = False
                try:
                    Quartz.CATransaction.begin()
                    Quartz.CATransaction.setDisableActions_(True)  # kein Fade/Move beim Bildwechsel
                    began = True
                except Exception as exc:  # Aktionen sind schon per NSNull abgeschaltet
                    log_error(exc)
                try:
                    self.layer.setContents_(img)  # ersetzt das alte Bild komplett, mit Alphakanal
                finally:
                    if began:
                        try:
                            Quartz.CATransaction.commit()
                        except Exception as exc:
                            log_error(exc)
                if not self.layer_shown:  # Tk-Bitmap erst ausblenden, wenn das Bild steht
                    self.ns_win.contentView().setAlphaValue_(0.0)
                    self.layer_shown = True
                return
            except Exception as exc:  # Layer-Weg scheitert -> sichtbar aufs Label zurueck
                log_error(exc)
                self.disable_layer()
        self.lbl.config(image=self.frame(name, fx, phase))

    # ---------------------------------------------------------------- Maus
    def on_press(self, ev):
        self.press = (ev.x_root, ev.y_root, self.x, self.y, False)

    def on_motion(self, ev):
        if not self.press:
            return
        px, py, sx, sy, dragging = self.press
        if not dragging and abs(ev.x_root - px) + abs(ev.y_root - py) > 6:
            dragging = True
            self.state = "drag"
            self.hop_t = -1
        if dragging:
            self.x, self.y = sx + ev.x_root - px, sy + ev.y_root - py
            self.press = (px, py, sx, sy, True)
            self._draw(self.drag_frame())

    def on_release(self, _ev):
        if not self.press:
            return
        dragging = self.press[4]
        self.press = None
        if dragging:
            self.surf_key = None  # irgendwo abgesetzt -> zurueck auf ihren Platz
            self.start_travel()
        elif self.state not in ("travel", "drag"):
            self.fx, self.fx_until = "heart", self.t + 40
            self.hop_t = 0
            self.extra = None
            self.set_state("sit", 40, 80)

    # ---------------------------------------------------------------- Menue
    def on_menu(self, ev):
        self.monitors = get_monitors()
        m = self.menu
        m.delete(0, "end")
        mode = self.settings["mode"]
        self.mode_var.set("edge" if mode == "edge" else f"mon{self.settings['monitor']}")
        m.add_radiobutton(label="Im Browser (oben)", variable=self.mode_var, value="edge",
                          command=lambda: self.set_mode("edge"))
        for i, mon in enumerate(self.monitors):
            label = f"Monitor {i + 1}" + (" (Hauptmonitor)" if mon["primary"] else "")
            m.add_radiobutton(label=label, variable=self.mode_var, value=f"mon{i}",
                              command=lambda i=i: self.set_mode("monitor", i))
        browsers = tk.Menu(m, tearoff=0)
        for app in BROWSER_CHOICES:
            browsers.add_radiobutton(label=BROWSER_LABELS.get(app, app), variable=self.browser_var,
                                     value=app, command=lambda app=app: self.set_browser(app))
        m.add_cascade(label="Browser", menu=browsers)
        m.add_separator()
        chars = tk.Menu(m, tearoff=0)
        for c, conf in CHARACTERS.items():
            chars.add_radiobutton(label=conf["label"], variable=self.char_var, value=c,
                                  command=lambda c=c: self.set_char(c))
        m.add_cascade(label="Figur", menu=chars)
        sizes = tk.Menu(m, tearoff=0)
        for s, label in (("klein", "Klein"), ("mittel", "Mittel"), ("gross", "Gross")):
            sizes.add_radiobutton(label=label, variable=self.size_var, value=s,
                                  command=lambda s=s: self.set_size(s))
        m.add_cascade(label="Groesse", menu=sizes)
        m.add_command(label="Schlafen legen", command=lambda: self.set_state("sleep", 600, 1200))
        m.add_separator()
        self.autostart_var.set(autostart_get() is not None)
        m.add_checkbutton(label="Bei Anmeldung starten", variable=self.autostart_var,
                          command=lambda: autostart_set(self.autostart_var.get()))
        m.add_command(label="Beenden", command=self.root.destroy)
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def set_mode(self, mode, monitor=None):
        self.settings["mode"] = mode
        if monitor is not None:
            self.settings["monitor"] = monitor
        save_settings(self.settings)
        self.surf_key = None  # loshuepfen

    def set_browser(self, app):
        if app not in BROWSER_CHOICES:
            return
        self.settings["browser"] = app
        save_settings(self.settings)
        self.browser = app
        self.surf_key = None  # zum neuen Browser huepfen

    def set_size(self, size):
        old_h = self.h
        self.settings["size"] = size
        save_settings(self.settings)
        self.apply_size()
        self.y += old_h - self.h

    def set_char(self, char):
        old_h = self.h
        self.settings["char"] = char
        save_settings(self.settings)
        self.extra = None
        self.apply_size()
        self.y += old_h - self.h

    def run(self):
        self.root.mainloop()


def preview(path, char=DEFAULTS["char"], size="mittel"):
    """Vorschaubild einiger Posen: miezi_mac.py --preview datei.png [figur-id] [klein|mittel|gross]
    (figur-id = Dateiname in common/sprites, z.B. schwarz oder orange)"""
    root = tk.Tk()
    root.withdraw()
    ch = CHARACTERS[char]
    look_name, _ = ch["sizes"][size]
    look = ch["looks"][look_name]
    walk = (ch["walk"] * 2)[:4]
    shots = [(n, False, None, 0) for n in walk] + [
        (ch["sit"][0], False, "heart", 0), (ch["blink"], False, None, 0),
        (ch["sleep"][0], False, "zzz", 1), (ch["sleep"][1], True, "zzz", 2),
        (ch["jump"][-1], True, "heart", 1)]
    shots += [(n, False, None, 0) for seq in ch["extras"].values() for n in sorted({f for f, _ in seq})]
    W, H = look["W"], look["BODY_H"] + look["FX_H"]
    scale, gap = (5 if W <= 40 else 3), 2
    palette = dict(look["PALETTE"])
    palette[" "] = "#eeeeee"  # Hintergrund statt Transparenz (Leerzeichen kommt in keiner Palette vor)
    sheet = tk.PhotoImage(width=len(shots) * (W + gap) * scale, height=H * scale)
    sheet.put("#dddddd", to=(0, 0, sheet.width(), sheet.height()))
    for i, (name, left, fx, ph) in enumerate(shots):
        grid = [r.replace(".", " ") for r in compose(look, name, left, fx, ph)]
        sheet.tk.call(sheet, "copy", grid_to_photo(grid, scale, palette), "-to", i * (W + gap) * scale, 0)
    sheet.write(path, format="png")
    root.destroy()


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        preview(*sys.argv[2:5])
        sys.exit(0)
    single_instance()
    Pet().run()
