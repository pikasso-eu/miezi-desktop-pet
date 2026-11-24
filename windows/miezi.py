"""Miezi - ein kleines Desktop-Pet fuer Windows (Python + tkinter, keine Zusatzpakete).

Modi (Rechtsklick auf die Katze):
  * Edge-Browser: laeuft oben auf dem Edge-Fenster (bzw. ueber die Tab-Leiste, wenn
    das Fenster maximiert ist). Ist kein Edge offen, wartet sie auf dem zweiten Monitor.
  * Monitor N: laeuft auf der Taskleisten-Kante des gewaehlten Monitors.

Linksklick = streicheln, Ziehen = hochheben und woanders hinsetzen.
Start: Sie erscheint am Mauszeiger und huepft von dort zu ihrem Platz.
"""
import ctypes
import json
import math
import os
import random
import sys
import time
import tkinter as tk
from ctypes import wintypes as wt

# Figuren und Bild-Zusammenbau sind plattformunabhaengig und liegen in ../common
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from characters import CHARACTERS, KEY, compose, grid_to_photo  # noqa: E402

# --------------------------------------------------------------------------- Win32
try:  # Physische Pixel, damit Tk- und Win32-Koordinaten zusammenpassen
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


def _sig(fn, args, res=None):
    fn.argtypes = args
    if res is not None:
        fn.restype = res


_sig(user32.EnumWindows, [WNDENUMPROC, wt.LPARAM], wt.BOOL)
_sig(user32.EnumDisplayMonitors, [wt.HDC, ctypes.POINTER(wt.RECT), MONITORENUMPROC, wt.LPARAM], wt.BOOL)
_sig(user32.GetMonitorInfoW, [wt.HMONITOR, ctypes.POINTER(MONITORINFO)], wt.BOOL)
_sig(user32.MonitorFromWindow, [wt.HWND, wt.DWORD], wt.HMONITOR)
_sig(user32.MonitorFromPoint, [wt.POINT, wt.DWORD], wt.HMONITOR)
_sig(user32.GetWindow, [wt.HWND, wt.UINT], wt.HWND)
_sig(user32.GetForegroundWindow, [], wt.HWND)
_sig(user32.SetForegroundWindow, [wt.HWND], wt.BOOL)
_sig(user32.IsWindow, [wt.HWND], wt.BOOL)
_sig(user32.IsWindowVisible, [wt.HWND], wt.BOOL)
_sig(user32.IsIconic, [wt.HWND], wt.BOOL)
_sig(user32.GetClassNameW, [wt.HWND, wt.LPWSTR, ctypes.c_int], ctypes.c_int)
_sig(user32.GetWindowTextLengthW, [wt.HWND], ctypes.c_int)
_sig(user32.GetWindowThreadProcessId, [wt.HWND, ctypes.POINTER(wt.DWORD)], wt.DWORD)
_sig(user32.GetWindowRect, [wt.HWND, ctypes.POINTER(wt.RECT)], wt.BOOL)
_sig(user32.GetWindowLongPtrW, [wt.HWND, ctypes.c_int], ctypes.c_ssize_t)
_sig(user32.SetWindowLongPtrW, [wt.HWND, ctypes.c_int, ctypes.c_ssize_t], ctypes.c_ssize_t)
_sig(user32.SetWindowPos, [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT], wt.BOOL)
_sig(user32.GetCursorPos, [ctypes.POINTER(wt.POINT)], wt.BOOL)
_sig(dwmapi.DwmGetWindowAttribute, [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD], ctypes.c_long)
_sig(kernel32.OpenProcess, [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE)
_sig(kernel32.QueryFullProcessImageNameW, [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)], wt.BOOL)
_sig(kernel32.CloseHandle, [wt.HANDLE], wt.BOOL)
_sig(kernel32.CreateMutexW, [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR], wt.HANDLE)

GW_OWNER, GW_HWNDPREV = 4, 3
GWL_EXSTYLE = -20
WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, WS_EX_NOACTIVATE = 0x8, 0x80, 0x40000, 0x08000000
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_NOOWNERZORDER = 0x1, 0x2, 0x10, 0x200
MONITOR_DEFAULTTONEAREST = 2
DWMWA_EXTENDED_FRAME_BOUNDS, DWMWA_CLOAKED = 9, 14
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def rect_t(r):
    return (r.left, r.top, r.right, r.bottom)


def get_monitors():
    """Alle Monitore, von links nach rechts sortiert."""
    mons = []

    def cb(hmon, _hdc, _rc, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            mons.append({"full": rect_t(mi.rcMonitor), "work": rect_t(mi.rcWork), "primary": bool(mi.dwFlags & 1)})
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    mons.sort(key=lambda m: (m["full"][0], m["full"][1]))
    return mons


def monitor_of_window(hwnd):
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST), ctypes.byref(mi))
    return {"full": rect_t(mi.rcMonitor), "work": rect_t(mi.rcWork)}


def window_rect(hwnd):
    r = wt.RECT()
    if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(r), ctypes.sizeof(r)) != 0:
        user32.GetWindowRect(hwnd, ctypes.byref(r))
    return rect_t(r)


_proc_cache = {}


def process_name(pid):
    if pid in _proc_cache:
        return _proc_cache[pid]
    name = ""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if h:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            name = os.path.basename(buf.value).lower()
        kernel32.CloseHandle(h)
    if len(_proc_cache) > 500:
        _proc_cache.clear()
    _proc_cache[pid] = name
    return name


def is_usable_edge_window(hwnd):
    if not hwnd or not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
        return False
    cls = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, cls, 64)
    if cls.value != "Chrome_WidgetWin_1" or user32.GetWindow(hwnd, GW_OWNER):
        return False
    if user32.GetWindowTextLengthW(hwnd) == 0:
        return False
    cloaked = wt.DWORD(0)  # Fenster auf anderen virtuellen Desktops
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    if cloaked.value:
        return False
    l, t, r, b = window_rect(hwnd)
    if r - l < 300 or b - t < 150:
        return False
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return process_name(pid.value) == "msedge.exe"


def edge_windows():
    """Sichtbare Edge-Hauptfenster in Z-Reihenfolge (oberstes zuerst)."""
    found = []

    def cb(hwnd, _lp):
        if is_usable_edge_window(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found


# --------------------------------------------------------------------------- Einstellungen
SETTINGS_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Miezi")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
DEFAULTS = {"mode": "edge", "monitor": 1, "size": "mittel", "char": "schwarz"}


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


# --------------------------------------------------------------------------- Autostart
# Eintrag unter HKCU\...\Run: nur fuer den eigenen Benutzer, ohne Adminrechte.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Miezi"


def autostart_command():
    if getattr(sys, "frozen", False):  # als Miezi.exe
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pyw if os.path.exists(pyw) else sys.executable}" "{os.path.abspath(__file__)}"'


def autostart_get():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, RUN_NAME)[0]
    except OSError:
        return None


def autostart_set(on):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        log_error(exc)


def log_error(exc):
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(os.path.join(SETTINGS_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {exc!r}\n")
    except Exception:
        pass


# --------------------------------------------------------------------------- Pet
TICK_MS = 50


class Pet:
    def __init__(self):
        self.settings = load_settings()
        self.root = tk.Tk()
        self.root.title("Miezi")
        self.root.overrideredirect(True)
        self.root.config(bg=KEY)
        self.root.attributes("-transparentcolor", KEY)
        self.lbl = tk.Label(self.root, bg=KEY, bd=0, highlightthickness=0, cursor="hand2")
        self.lbl.pack()

        try:
            self.dpi = user32.GetDpiForSystem()
        except Exception:
            self.dpi = 96
        self.frames = {}
        self.apply_size()

        self.root.update_idletasks()
        self.hwnd = int(self.root.wm_frame(), 16)
        self.fix_exstyle()

        self.monitors = get_monitors()
        self.edge_hwnd = None
        self.edge_scan_t = -999
        self.topmost = None
        self.visible = True

        # Start am Mauszeiger
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        self.x, self.y = pt.x - self.w // 2, pt.y - self.h // 2
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
            widget.bind("<Button-3>", self.on_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.mode_var = tk.StringVar()
        self.size_var = tk.StringVar(value=self.settings["size"])
        self.char_var = tk.StringVar(value=self.settings["char"])
        self.autostart_var = tk.BooleanVar()
        cmd = autostart_get()
        if cmd and getattr(sys, "frozen", False) and cmd != autostart_command():
            autostart_set(True)  # EXE wurde verschoben -> Eintrag auf neuen Pfad
        self.root.after(TICK_MS, self.tick)

    # ---------------------------------------------------------------- Fenster
    def fix_exstyle(self):
        ex = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        new = (ex | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
        if new != ex:
            user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, new)

    def apply_size(self):
        if self.settings.get("char") not in CHARACTERS:
            self.settings["char"] = DEFAULTS["char"] if DEFAULTS["char"] in CHARACTERS else next(iter(CHARACTERS))
        self.char = CHARACTERS[self.settings["char"]]
        look_name, zoom = self.char["sizes"].get(self.settings["size"], self.char["sizes"]["mittel"])
        self.look = self.char["looks"][look_name]
        self.scale = max(1, round(zoom * self.dpi / 96))
        self.frames.clear()
        self.w = self.look["W"] * self.scale
        self.h = (self.look["BODY_H"] + self.look["FX_H"]) * self.scale
        self.body_h = self.look["BODY_H"] * self.scale
        self.unit = self.w / 40  # Bewegungseinheit = 1/40 Koerperbreite (orange Katze: = scale)

    def frame(self, name, fx=None, phase=0):
        key = (name, self.facing_left, fx, phase)
        img = self.frames.get(key)
        if img is None:
            grid = compose(self.look, name, self.facing_left, fx, phase)
            img = grid_to_photo(grid, self.scale, self.look["PALETTE"])
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
            self.topmost = on
            self.fix_exstyle()

    def stack_above(self, target):
        """Katze direkt ueber das Edge-Fenster legen (nicht ueber alles)."""
        prev = user32.GetWindow(target, GW_HWNDPREV)
        if prev == self.hwnd:
            return
        after = prev
        if not prev or user32.GetWindowLongPtrW(prev, GWL_EXSTYLE) & WS_EX_TOPMOST:
            after = None  # HWND_TOP
        user32.SetWindowPos(self.hwnd, after, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER)

    def show(self, on):
        if self.visible != on:
            self.root.attributes("-alpha", 1.0 if on else 0.0)
            self.visible = on

    # ---------------------------------------------------------------- Untergrund
    def pick_monitor(self, index):
        if not self.monitors:
            self.monitors = get_monitors()
        index = max(0, min(index, len(self.monitors) - 1))
        return self.monitors[index]

    def fallback_monitor(self):
        """Ohne Edge: auf den zweiten Monitor (falls vorhanden), sonst Hauptmonitor."""
        for m in self.monitors:
            if not m["primary"]:
                return m
        return self.monitors[0]

    def find_edge(self):
        if self.t - self.edge_scan_t >= 8 or not is_usable_edge_window(self.edge_hwnd):
            self.edge_scan_t = self.t
            wins = edge_windows()
            fg = user32.GetForegroundWindow()
            if fg in wins:
                self.edge_hwnd = fg
            elif self.edge_hwnd not in wins:
                self.edge_hwnd = wins[0] if wins else None
        return self.edge_hwnd

    def surface(self):
        """Liefert (key, left, right, floor_y, topmost, above_hwnd) oder None = verstecken."""
        if self.t % 40 == 0:
            self.monitors = get_monitors()
        if self.settings["mode"] == "edge":
            hw = self.find_edge()
            if hw:
                l, t, r, b = window_rect(hw)
                mon = monitor_of_window(hw)
                fl, ft, fr, fb = mon["full"]
                if l <= fl and t <= ft and r >= fr and b >= fb:
                    return None  # Vollbild (Video, F11) -> nicht stoeren
                if t - mon["work"][1] >= self.body_h:
                    # Platz ueber dem Fenster: auf der Oberkante laufen
                    return (("edge", hw), l, r, t + self.scale, False, hw)
                # Maximiert: in der Tab-Leiste laufen, Fenster-Knoepfe rechts frei lassen
                margin = round(150 * self.dpi / 96)
                return (("edge", hw), l + 8, r - margin, t + self.body_h + 2, False, hw)
            mon = self.fallback_monitor()
        else:
            mon = self.pick_monitor(self.settings["monitor"])
        l, t, r, b = mon["work"]
        return (("mon", mon["full"]), l, r, b, True, None)

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
        key, left, right, floor, topmost, above = surf
        self.set_topmost(topmost or self.state == "drag")
        if above and self.state != "drag":
            self.stack_above(above)

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
        self.lbl.config(image=self.frame(name, fx, phase))
        self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

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
        m.add_radiobutton(label="Im Edge-Browser (oben)", variable=self.mode_var, value="edge",
                          command=lambda: self.set_mode("edge"))
        for i, mon in enumerate(self.monitors):
            label = f"Monitor {i + 1}" + (" (Hauptmonitor)" if mon["primary"] else "")
            m.add_radiobutton(label=label, variable=self.mode_var, value=f"mon{i}",
                              command=lambda i=i: self.set_mode("monitor", i))
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
        m.add_checkbutton(label="Mit Windows starten", variable=self.autostart_var,
                          command=lambda: autostart_set(self.autostart_var.get()))
        m.add_command(label="Beenden", command=self.root.destroy)
        user32.SetForegroundWindow(self.hwnd)
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
    """Vorschaubild einiger Posen: miezi.py --preview datei.png [figur-id] [klein|mittel|gross]
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
    mutex = kernel32.CreateMutexW(None, False, "Local\\MieziDesktopPet")
    if ctypes.get_last_error() == 183:  # laeuft schon
        sys.exit(0)
    Pet().run()
