"""Figuren laden und Einzelbilder zusammensetzen - plattformunabhaengig (Windows und macOS).

Jede Figur ist ein Modul common/sprites/<id>.py mit
    CHARACTER  Beschreibung: Name, Groessen, welche Bilder zu welcher Animation gehoeren
    SETS       ein oder mehrere Sprite-Saetze ("Looks"), z.B. volle und halbe Aufloesung
Die Werkzeuge in tools/ tragen neue Module in common/sprites/__init__.py (MODULES) ein.
"""
import tkinter as tk

import sprites

KEY = "#ff00ff"  # Farbe, die das Fenster transparent macht (Windows: -transparentcolor)


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
