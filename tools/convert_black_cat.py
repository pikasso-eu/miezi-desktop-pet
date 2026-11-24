"""Erzeugt common/sprites/schwarz.py aus dem KI-generierten Sheet der schwarzen Katze.

Aufruf (im Projektordner):  python tools/convert_black_cat.py [art/schwarze_katze_ki_sheet.png]

Sonderfall-Konverter: Das KI-Sheet hat kein exaktes Raster (die "Pixel" sind ca. 3,1 px
gross und leicht ungleichmaessig) und die Bilder liegen frei verteilt, darum stehen die
Ausschnitte unten fest im Code. Fuer neue Tiere besser ein Sheet nach Vorlage bauen und
tools/convert_sheet.py nehmen (siehe README).

Ablauf: gemeinsames Pixelraster schaetzen -> jedes Bild auf das Raster herunterrechnen
(harte Alpha-Kante) -> am Kopf ausrichten, Fuesse unten -> Silhouetten-Rand aufhellen ->
Farben reduzieren. Zwei Saetze: "hi" (volle Aufloesung) und "lo" (halbe, fuer "Klein").
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetlib as sl

DEFAULT_SHEET = os.path.join(sl.ROOT, "art", "schwarze_katze_ki_sheet.png")

# name, x0, x1, y0, y1 (Sheet-Pixel), Groessenfaktor (die Zusatzbilder sind kleiner gemalt)
BOXES = [
    ("walk1", 160, 352, 20, 160, 1), ("walk2", 400, 592, 20, 160, 1), ("walk3", 640, 832, 20, 160, 1),
    ("walk4", 880, 1068, 20, 160, 1), ("walk5", 1120, 1308, 20, 160, 1),
    # walk_06 endet am Sheet-Rand (Kopf leicht nach links gedreht); rechts davon ist transparent
    ("walk6", 1360, 1536, 20, 160, 1),
    ("idle1", 168, 316, 200, 348, 1), ("idle2", 408, 552, 200, 348, 1), ("blink", 648, 788, 204, 348, 1),
    ("sleep1", 172, 344, 420, 504, 1), ("sleep2", 412, 584, 420, 504, 1),
    ("jump1", 168, 348, 576, 664, 1), ("jump2", 404, 596, 556, 660, 1), ("jump3", 652, 836, 564, 668, 1),
    ("drag1", 184, 312, 708, 836, 1), ("drag2", 432, 556, 712, 836, 1),
    ("groom1", 548, 660, 876, 984, 1.32), ("groom2", 680, 764, 880, 984, 1.32),
    ("stretch1", 804, 920, 872, 984, 1.32), ("stretch2", 936, 1084, 900, 984, 1.32),
    ("yawn1", 1104, 1192, 880, 984, 1.32), ("yawn2", 1200, 1264, 888, 984, 1.32),
    ("turn1", 1308, 1388, 876, 984, 1.32), ("turn2", 1416, 1520, 876, 984, 1.32),
]
FX_BOXES = [("heart", 168, 232, 904, 964, 1), ("z", 276, 340, 896, 956, 1)]
PAD = 3
ALPHA_MIN = 160
RIM = (0x5a, 0x53, 0x63)  # aufgehellter Rand

CHARACTER = {
    "label": "Schwarze Katze",
    "order": 1,
    "sizes": {"klein": ("lo", 1), "mittel": ("hi", 1), "gross": ("hi", 2)},
    "walk": ["walk1", "walk2", "walk3", "walk4", "walk5", "walk6"], "walk_ticks": 3,
    "sit": ["idle1", "idle2"], "blink": "blink", "sleep": ["sleep1", "sleep2"],
    "jump": ["jump1", "jump2", "jump3"], "drag": ["drag1", "drag2"], "hop": "idle1",
    "extras": {  # gelegentliche Einlagen beim Sitzen: (Bild, Ticks a 50 ms)
        "putzen": [("groom1", 10), ("groom2", 6), ("groom1", 4), ("groom2", 6), ("groom1", 4),
                   ("groom2", 6), ("groom1", 10)],
        "strecken": [("stretch1", 12), ("stretch2", 30), ("stretch1", 10)],
        "gaehnen": [("yawn1", 6), ("yawn2", 20), ("yawn1", 6)],
        "umdrehen": [("turn1", 8), ("turn2", 40), ("turn1", 8)],
    },
}


def edge_positions(px, x0, x1, y0, y1):
    def diff(a, b):
        return abs(a[3] - b[3]) > 100 or (a[3] > 128 and b[3] > 128 and sum(abs(a[i] - b[i]) for i in range(3)) > 30)
    xs = [x for y in range(y0, y1) for x in range(x0 + 1, x1) if diff(px(x - 1, y), px(x, y))]
    ys = [y for x in range(x0, x1) for y in range(y0 + 1, y1) if diff(px(x, y - 1), px(x, y))]
    return xs, ys


def phase_strength(pos, p):
    cs = sum(math.cos(2 * math.pi * v / p) for v in pos)
    sn = sum(math.sin(2 * math.pi * v / p) for v in pos)
    return math.hypot(cs, sn) / max(1, len(pos)), (math.atan2(sn, cs) / (2 * math.pi) * p) % p


def sample(px, x0, x1, y0, y1, period, offx, offy):
    """Ein Rasterpixel = 3x3 Stichproben in seiner Zelle; deckend, wenn >= 5 deckend."""
    grid, gy = [], 0
    while y0 + offy + gy * period < y1:
        line, gx = [], 0
        while x0 + offx + gx * period < x1:
            hits = []
            for sy in (0.2, 0.5, 0.8):
                for sx in (0.2, 0.5, 0.8):
                    x = int(x0 + offx + (gx + sx) * period)
                    y = int(y0 + offy + (gy + sy) * period)
                    if x < x1 and y < y1:
                        v = px(x, y)
                        if v[3] >= ALPHA_MIN:
                            hits.append(v[:3])
            line.append(sl.pick_color(hits) if len(hits) >= 5 else None)
            gx += 1
        grid.append(line)
        gy += 1
    return sl.crop(grid)


def build_set(px, period, edges):
    def cut(box):
        name, x0, x1, y0, y1, f = box
        p = period / f
        x0, x1, y0, y1 = x0 - PAD, x1 + PAD, y0 - PAD, y1 + PAD
        xs, ys = edges[name]
        offx = (phase_strength(xs, p)[1] - x0) % p
        offy = (phase_strength(ys, p)[1] - y0) % p
        return sample(px, x0, x1, y0, y1, p, offx, offy)

    frames = {b[0]: sl.add_rim(cut(b), RIM) for b in BOXES}
    fx = {b[0]: cut(b) for b in FX_BOXES}

    # Ausrichtung: Kopf der Laufbilder in gleicher Spalte, alles andere moeglichst dorthin
    hx = {n: sl.head_anchor(g)[0] for n, g in frames.items()}
    walk = [n for n in frames if n.startswith("walk")]
    target = max(hx[n] for n in walk)
    dx = {n: target - hx[n] for n in walk}
    left = min(dx.values())
    dx = {n: v - left for n, v in dx.items()}
    target -= left
    width = max([dx[n] + len(frames[n][0]) for n in walk] + [len(g[0]) for g in frames.values()])
    for n, g in frames.items():
        if n not in dx:
            dx[n] = max(0, min(width - len(g[0]), target - hx[n]))
    body_h = max(len(g) for g in frames.values())
    canvas = {n: sl.place(g, width, body_h, dx[n]) for n, g in frames.items()}
    return sl.make_look(canvas, fx, keep=(RIM,))


def main():
    sheet = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SHEET
    w, h, px = sl.read_png(sheet)

    edges = {b[0]: edge_positions(px, b[1] - PAD, b[2] + PAD, b[3] - PAD, b[4] + PAD) for b in BOXES + FX_BOXES}
    best = None  # gemeinsame Periode ueber die Hauptbilder (ohne die kleiner gemalten Zusatzbilder)
    for i in range(0, 81):
        p = 2.8 + i * 0.01
        s = sum(phase_strength(xs, p)[0] + phase_strength(ys, p)[0]
                for n, (xs, ys) in edges.items() if not n.startswith(("groom", "stretch", "yawn", "turn")))
        if best is None or s > best[0]:
            best = (s, p)
    period = best[1]
    print(f"Pixelraster: {period:.2f} Sheet-Pixel")

    sets = {}
    for set_name, mult in (("hi", 1), ("lo", 2)):
        s = build_set(px, period * mult, edges)
        print(f"{set_name}: {s['W']}x{s['BODY_H']} (+{s['FX_H']} Effektzeilen), {len(s['PALETTE'])} Farben")
        sets[set_name] = s
    sl.write_module("schwarz", "tools/convert_black_cat.py", CHARACTER, sets)


if __name__ == "__main__":
    main()
