"""Figuren laden und Einzelbilder zusammensetzen - plattformunabhaengig (Windows und macOS).

Jede Figur ist ein Modul common/sprites/<id>.py mit
    CHARACTER  Beschreibung: Name, Groessen, welche Bilder zu welcher Animation gehoeren
    SETS       ein oder mehrere Sprite-Saetze ("Looks"), z.B. volle und halbe Aufloesung
Die Werkzeuge in tools/ tragen neue Module in common/sprites/__init__.py (MODULES) ein.
"""
import colorsys
import tkinter as tk

import sprites

KEY = "#ff00ff"  # Farbe, die das Fenster transparent macht (Windows: -transparentcolor)

# Fellfarben fuer das Menue "Farbe" (None = Originalfarben der Figur)
COLORS = (("Original", None), ("Grau", "#8c8c94"), ("Rot", "#d0732e"), ("Creme", "#e6d2a6"),
          ("Weiss", "#f2f0ec"), ("Blaugrau", "#6c7c98"), ("Braun", "#7a5232"))


def load_characters():
    """id -> Figur (CHARACTER mit "looks" = SETS), sortiert nach "order", dann Name."""
    chars = {}
    for char_id, mod in sprites.MODULES.items():
        if not hasattr(mod, "CHARACTER") or not hasattr(mod, "SETS"):
            continue
        c = dict(mod.CHARACTER)
        c["looks"] = mod.SETS
        c.setdefault("walk_ticks", 2)
        c.setdefault("blink", c["sit"][0])
        c.setdefault("jump", [c["walk"][0]])
        c.setdefault("drag", [c["walk"][min(1, len(c["walk"]) - 1)]])
        c.setdefault("hop", c["jump"][len(c["jump"]) // 2])
        c.setdefault("extras", {})
        chars[char_id] = c
    return dict(sorted(chars.items(), key=lambda kv: (kv[1].get("order", 99), kv[1]["label"])))


CHARACTERS = load_characters()


def fx_column(look, name):
    """Feste Effekt-Spalte (Figuren ohne Kopf-Anker, z.B. die orange Katze)."""
    cols = look["FX_COL"]
    for prefix in sorted(cols, key=len, reverse=True):
        if name.startswith(prefix):
            return cols[prefix]
    return look["W"] // 2


def compose(look, name, facing_left, fx=None, fx_phase=0):
    """Einzelbild als Textzeilen (W x BODY_H+FX_H), optional gespiegelt und mit Herz/Zzz."""
    W, H = look["W"], look["BODY_H"] + look["FX_H"]
    FX = look["FX"]
    rows = [r.ljust(W, ".")[:W] for r in look["SPRITES"][name]]
    rows = ["." * W] * (H - len(rows)) + rows
    if facing_left:
        rows = [r[::-1] for r in rows]
    grid = [list(r) for r in rows]

    def stamp(glyph, col, row):
        gw = len(glyph[0])
        if facing_left:
            col = W - col - gw
        for dy, line in enumerate(glyph):
            for dx, ch in enumerate(line):
                y, x = row + dy, col + dx
                if ch != "." and 0 <= y < H and 0 <= x < W:
                    grid[y][x] = ch

    if "HEAD" in look:  # Effekte ueber der Kopfmitte (vom Konverter ermittelt)
        hx, top = look["HEAD"][name]
        top += look["FX_H"]
        if fx == "heart":
            g = FX["heart"]
            stamp(g, hx - len(g[0]) // 2, max(0, top - len(g) - 1 + (fx_phase % 2)))
        elif fx == "zzz":
            g = FX["z"]
            stamp(g, hx + 1, max(0, top - len(g) + 2 - (fx_phase % 3)))
    else:
        col = fx_column(look, name)
        if fx == "heart":
            stamp(FX["heart"], col, 0 if fx_phase % 2 else 1)
        elif fx == "zzz":
            stamp(FX["z1"], col + 4, 14 - (fx_phase % 3))
            if fx_phase % 3:
                stamp(FX["z2"], col, 8 - 2 * (fx_phase % 3))
    return ["".join(r) for r in grid]


# --------------------------------------------------------------------------- Fellfarbe
# Umgefaerbt wird nur die Palette (bei dunklen Figuren zusaetzlich die Pupillen-Pixel), die
# Bilder selbst bleiben. Zwei Wege:
#   * CHARACTER["fur"] nennt die Fellfarben (orange Katze): Zielfarbe mit deren relativer Helligkeit.
#   * Dunkle Figur ohne "fur" (schwarze Katze, KI-Palette ohne Namen): die Helligkeit jedes
#     Felltons wird auf einen Verlauf der Zielfarbe gelegt, damit die Schattierung bleibt.
FUR_MAX_V = 0.13  # dunkle Figuren: alles bis zu dieser Helligkeit (HSV-Wert) ist Fell
PUPIL = "§"  # eigenes Zeichen fuer Pupillen/Augenrand, kommt in keiner Palette vor
PUPIL_COLOR = "#121216"


def _rgb(color):
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _hsv(color):
    return colorsys.rgb_to_hsv(*_rgb(color))


def _shade(color, f):
    """Farbe abdunkeln (f < 1) oder Richtung Weiss aufhellen (f > 1)."""
    r, g, b = _rgb(color)
    if f <= 1:
        rgb = (r * f, g * f, b * f)
    else:
        k = min(1.0, f - 1)
        rgb = (r + (1 - r) * k, g + (1 - g) * k, b + (1 - b) * k)
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v * 255))) for v in rgb)


def _dark_keys(look):
    return {k for k, v in look["PALETTE"].items() if _hsv(v)[2] <= FUR_MAX_V}


def _pixels(look):
    for rows in look["SPRITES"].values():
        for row in rows:
            for c in row:
                if c != ".":
                    yield c


def can_recolor(char):
    """Figur mit benannten Fellfarben oder ueberwiegend dunkle Figur."""
    if char.get("fur"):
        return True
    for look in char["looks"].values():
        dark = _dark_keys(look)
        n = d = 0
        for c in _pixels(look):
            n += 1
            d += c in dark
        if not n or d / n <= 0.5:
            return False
    return True


def _rim(look, dark):
    """Haeufigste Farbe auf der Silhouettenkante, falls sie nicht zum Fell gehoert - der helle
    Rand, den der Konverter fuer dunklen Untergrund setzt. Er wird zur dunklen Kontur."""
    counts = {}
    for rows in look["SPRITES"].values():
        def at(x, y):
            return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else "."
        for y, row in enumerate(rows):
            for x, c in enumerate(row):
                if c != "." and "." in (at(x - 1, y), at(x + 1, y), at(x, y - 1), at(x, y + 1)):
                    counts[c] = counts.get(c, 0) + 1
    if not counts:
        return None
    rim = max(counts, key=counts.get)
    return rim if rim not in dark and counts[rim] * 2 > sum(counts.values()) else None


def _is_eye(color):
    h, s, v = _hsv(color)
    return 30 <= h * 360 <= 200 and s > 0.5 and v > 0.3  # gelb bis gruen, kraeftig


def _keep_pupils(look, dark):
    """Dunkle Pixel mit mindestens zwei Augen-Nachbarn (8er-Nachbarschaft) bekommen das Zeichen
    PUPIL - sie gehoeren zu Pupille oder Augenrand und sollen dunkel bleiben."""
    eye = {k for k, v in look["PALETTE"].items() if _is_eye(v)}
    out = {}
    for name, rows in look["SPRITES"].items():
        new = []
        for y, row in enumerate(rows):
            line = list(row)
            for x, c in enumerate(row):
                if c not in dark:
                    continue
                n = sum(1 for yy in (y - 1, y, y + 1) for xx in (x - 1, x, x + 1)
                        if (yy, xx) != (y, x) and 0 <= yy < len(rows) and 0 <= xx < len(rows[yy])
                        and rows[yy][xx] in eye)
                if n >= 2:
                    line[x] = PUPIL
            new.append("".join(line))
        out[name] = new
    return out


def recolor(char, look, color):
    """Look mit Fellfarbe `color` ("#rrggbb"); ohne Farbe oder bei nicht umfaerbbarer Figur
    unveraendert. Liefert eine Kopie, das Original bleibt."""
    if not color or not can_recolor(char):
        return look
    pal = look["PALETTE"]
    new = dict(look)
    new_pal = dict(pal)
    fur = char.get("fur")
    if fur:
        base_v = _hsv(pal[fur[0]])[2] or 1
        for k in fur:
            if k in pal:
                new_pal[k] = _shade(color, _hsv(pal[k])[2] / base_v)
    else:
        dark = _dark_keys(look)
        for k in dark:
            new_pal[k] = _shade(color, 0.55 + 0.6 * _hsv(pal[k])[2] / FUR_MAX_V)  # 55 % .. 115 %
        rim = _rim(look, dark)
        if rim:
            new_pal[rim] = _shade(color, 0.38)
        new_pal[PUPIL] = PUPIL_COLOR
        new["SPRITES"] = _keep_pupils(look, dark)
    new["PALETTE"] = new_pal
    return new


def grid_to_photo(grid, scale, palette, transparent=KEY):
    """Textzeilen -> tk.PhotoImage (ganzzahlig vergroessert). Transparente Pixel bekommen die
    Farbe `transparent` (Windows: KEY). Mit transparent=None bleiben sie echt durchsichtig."""
    img = tk.PhotoImage(width=len(grid[0]), height=len(grid))
    if transparent is None:
        # ein einziger put-Aufruf: leere Farben laesst Tk unveraendert, also echt durchsichtig
        img.put([[palette[c] if c != "." else "" for c in row] for row in grid], to=(0, 0))
    else:
        img.put(" ".join("{" + " ".join(transparent if c == "." else palette[c] for c in row) + "}"
                         for row in grid), to=(0, 0))
    return img.zoom(scale, scale) if scale > 1 else img
