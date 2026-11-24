"""Erzeugt common/sprites/orange.py: Pixel-Katze im 40x26-Raster aus einfachen Grundformen.

Aufruf (im Projektordner):  python tools/gen_cat_sprites.py
Die Ausgabe sind reine Text-Raster; die App braucht diesen Generator zur Laufzeit nicht.

Zeichen: . transparent, k Kontur, o Fell, h Glanz, d Streifen/Schatten, D tiefer Schatten,
         w Weiss, W Weiss-Schatten, p Rosa, e Auge, g Iris, s Lichtpunkt
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetlib

W, BH = 40, 26
PALETTE = {
    "k": "#2b2024", "o": "#f4a340", "h": "#ffc874", "d": "#d9822b", "D": "#b8651f",
    "w": "#fff3e0", "W": "#e3cdb5", "p": "#ff8fab", "e": "#141014", "g": "#5f9e3a", "s": "#ffffff",
    "r": "#ff4d6d", "z": "#7aa2ff",
}
CHARACTER = {
    "label": "Orange Katze",
    "order": 2,
    "sizes": {"klein": ("std", 1), "mittel": ("std", 2), "gross": ("std", 3)},
    "walk": ["walk0", "walk1", "walk2", "walk3"], "walk_ticks": 2,
    "sit": ["sit"], "blink": "blink", "sleep": ["sleep0", "sleep1"],
    "jump": ["walk0"], "drag": ["walk1"], "hop": "walk0", "extras": {},
}


class Canvas:
    def __init__(self):
        self.g = [["."] * W for _ in range(BH)]

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < W and 0 <= y < BH else "."

    def put(self, x, y, ch):
        if 0 <= x < W and 0 <= y < BH:
            self.g[y][x] = ch

    def ellipse(self, cx, cy, rx, ry, ch="o", shade=False, only_on=None):
        for y in range(BH):
            for x in range(W):
                nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                if nx * nx + ny * ny > 1:
                    continue
                if only_on and self.get(x, y) not in only_on:
                    continue
                c = ch
                if shade:
                    above = ((x + 0.5 - cx) / rx) ** 2 + ((y - 0.5 - cy) / ry) ** 2 > 1
                    if above:
                        c = "h"
                    elif ny > 0.55:
                        c = "d"
                self.put(x, y, c)

    def tri(self, pts, ch):
        (x1, y1), (x2, y2), (x3, y3) = pts
        for y in range(BH):
            for x in range(W):
                px, py = x + 0.5, y + 0.5
                d1 = (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
                d2 = (px - x3) * (y2 - y3) - (x2 - x3) * (py - y3)
                d3 = (px - x1) * (y3 - y1) - (x3 - x1) * (py - y1)
                neg = d1 < 0 or d2 < 0 or d3 < 0
                pos = d1 > 0 or d2 > 0 or d3 > 0
                if not (neg and pos):
                    self.put(x, y, ch)

    def stroke(self, p0, p1, p2, r, ch="o", bands=None, outline=False):
        """Quadratische Bezierkurve als dicker Strich (z.B. Schwanz)."""
        steps = 60
        for pass_r, pass_ch in ((r + 1, "k"), (r, None)) if outline else ((r, None),):
            for i in range(steps + 1):
                t = i / steps
                bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
                c = pass_ch or (bands[int(t * len(bands)) % len(bands)] if bands else ch)
                for y in range(int(by - pass_r) - 1, int(by + pass_r) + 2):
                    for x in range(int(bx - pass_r) - 1, int(bx + pass_r) + 2):
                        if (x + 0.5 - bx) ** 2 + (y + 0.5 - by) ** 2 <= pass_r * pass_r:
                            self.put(x, y, c)

    def outline(self):
        add = []
        for y in range(BH):
            for x in range(W):
                if self.g[y][x] != ".":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy) not in (".", "k"):
                        add.append((x, y))
                        break
        for x, y in add:
            self.g[y][x] = "k"

    def rows(self):
        return ["".join(r) for r in self.g]


def leg(c, hip, foot_x, lift, far):
    hx, hy = hip
    fy = 23.2 - lift
    body = "d" if far else "o"
    c.stroke((hx, hy), ((hx + foot_x) / 2, (hy + fy) / 2), (foot_x, fy - 1), 1.5, body)
    c.ellipse(foot_x, fy, 2.2, 1.3, "W" if far else "w")


def head(c, cx, cy, eyes="open"):
    # Ohren (aussen Fell, innen rosa)
    c.tri([(cx - 6, cy - 3), (cx - 4.2, cy - 8.6), (cx - 0.5, cy - 5.5)], "o")
    c.tri([(cx + 0.5, cy - 5.5), (cx + 4.2, cy - 8.6), (cx + 6, cy - 3)], "o")
    c.tri([(cx - 4.6, cy - 3.6), (cx - 4, cy - 7.2), (cx - 2, cy - 5)], "p")
    c.tri([(cx + 2, cy - 5), (cx + 4, cy - 7.2), (cx + 4.6, cy - 3.6)], "p")
    c.ellipse(cx, cy, 6.6, 5.6, "o", shade=True)
    # Stirnstreifen
    ix, iy = int(cx), int(cy)
    for sx in (-2, 0, 2):
        c.put(ix + sx, iy - 4, "d")
        c.put(ix + sx, iy - 3, "d")
    # Schnauze, Wangen
    c.ellipse(cx + 0.5, cy + 2.6, 3.2, 1.9, "w", only_on="ohd")
    c.put(ix - 4, iy + 2, "p")
    c.put(ix + 5, iy + 2, "p")
    # Augen
    for ex in (ix - 3, ix + 2):
        if eyes == "open":
            c.put(ex, iy - 1, "e"); c.put(ex + 1, iy - 1, "s")
            c.put(ex, iy, "e"); c.put(ex + 1, iy, "e")
            c.put(ex, iy + 1, "g"); c.put(ex + 1, iy + 1, "e")
        else:
            c.put(ex, iy + 1, "k"); c.put(ex + 1, iy + 1, "k")
    # Nase und Mund
    c.put(ix, iy + 2, "p"); c.put(ix + 1, iy + 2, "p")
    c.put(ix, iy + 3, "k"); c.put(ix + 1, iy + 3, "k")


TAIL_BANDS = ["o", "o", "d", "o", "o", "d", "o", "d"]


def walk(frame, eyes="open"):
    c = Canvas()
    dxs, lifts = [2, 0, -2, 0], [0, 0, 0, 1.3]
    bob = 0.4 if frame in (1, 3) else 0
    sway = [0, 1, 0, -1][frame]
    # hintere Beine (weiter weg, dunkler)
    for hip, phase in (((11, 17), 2), ((26, 17), 0)):
        p = (frame + phase) % 4
        leg(c, hip, hip[0] + dxs[p], lifts[p], far=True)
    c.stroke((9, 15), (1.5, 15), (3 + sway, 4.5), 1.3, bands=TAIL_BANDS)
    c.ellipse(18.5, 14 + bob, 11.5, 5.4, "o", shade=True)
    # Ruecken-Streifen
    for x0 in (11, 15, 19):
        for r in range(4):
            x, y = x0 + r // 2, int(8.8 + bob) + r
            if c.get(x, y) in "oh":
                c.put(x, y, "d")
    c.ellipse(26.5, 16 + bob, 3.6, 3.2, "w", only_on="od")  # Brust
    for hip, phase in (((9, 17), 0), ((24, 17), 2)):
        p = (frame + phase) % 4
        leg(c, hip, hip[0] + dxs[p], lifts[p], far=False)
    head(c, 31, 10 + bob, eyes)
    c.outline()
    return c.rows()


def sit(eyes="open"):
    c = Canvas()
    c.stroke((12, 21), (2, 24), (3.5, 12), 1.3, bands=TAIL_BANDS)
    c.ellipse(16.5, 18.8, 7.2, 5.4, "o", shade=True)  # Keule
    c.ellipse(22, 16.5, 5.6, 6.8, "o", shade=True)    # Oberkoerper
    for x, far in ((25.5, True), (21.5, False)):
        c.stroke((x, 15), (x, 19), (x, 22), 1.5, "d" if far else "o")
        c.ellipse(x, 23.2, 2.2, 1.3, "W" if far else "w")
    c.ellipse(23.8, 16, 2.6, 3.4, "w", only_on="oh")  # Brustlatz
    # Streifen auf der Keule
    for x0 in (13, 16):
        for r in range(3):
            if c.get(x0 + r // 2, 15 + r) in "oh":
                c.put(x0 + r // 2, 15 + r, "d")
    head(c, 23, 10, eyes)
    c.outline()
    return c.rows()


def sleep(breath):
    c = Canvas()
    ry = 5.0 + 0.5 * breath
    c.ellipse(17.5, 19.6 - 0.5 * breath, 12.5, ry, "o", shade=True)
    for x0 in (9, 13, 17, 21):
        for r in range(3):
            x, y = x0 + r // 2, int(19.6 - ry - 0.5 * breath) + 1 + r
            if c.get(x, y) in "oh":
                c.put(x, y, "d")
    c.stroke((7, 21), (15, 24.5), (25, 22.2), 1.3, bands=TAIL_BANDS, outline=True)
    c.ellipse(30, 18.2, 7.6, 6.6, "k")  # Kontur trennt Kopf vom Koerper
    head(c, 30, 18.2, "closed")
    c.outline()
    return c.rows()


FX = {
    "heart": [
        ".kk...kk.",
        "krrk.krrk",
        "krsrkrrrk",
        "krrrrrrrk",
        ".krrrrrk.",
        "..krrrk..",
        "...krk...",
        "....k....",
    ],
    "z1": ["zzzz", "..z.", ".z..", "zzzz"],
    "z2": ["zzzzz", "...z.", "..z..", ".z...", "zzzzz"],
}


def main():
    sprites = {f"walk{i}": walk(i) for i in range(4)}
    sprites["walkblink"] = walk(0, "closed")
    sprites["sit"] = sit()
    sprites["blink"] = sit("closed")
    sprites["sleep0"] = sleep(0)
    sprites["sleep1"] = sleep(1)

    look = {
        "W": W, "BODY_H": BH, "FX_H": 10, "PALETTE": PALETTE,
        # Effekte (Herz, Zzz) an festen Spalten statt Kopf-Ankern: Bildname-Praefix -> Spalte
        "FX_COL": {"walk": 27, "sleep": 31, "": 19},
        "SPRITES": sprites, "FX": FX,
    }
    sheetlib.write_module("orange", "tools/gen_cat_sprites.py", CHARACTER, {"std": look})


if __name__ == "__main__":
    main()
