"""Gemeinsame Helfer der Sprite-Werkzeuge (nur Standardbibliothek, kein Pillow).

Ein Raster ("grid") ist eine Liste von Zeilen; jedes Pixel ist ein (r, g, b)-Tupel
oder None (transparent). Daraus entsteht ein "Look" fuer common/sprites/<id>.py:
    W, BODY_H, FX_H  Leinwand (Koerper + Effektzeilen darueber)
    PALETTE          Zeichen -> "#rrggbb" (ein Zeichen pro Farbe, "." = transparent)
    SPRITES          Bildname -> Textzeilen (W x BODY_H, Fuesse auf der Unterkante)
    HEAD             Bildname -> (x, oberste Zeile): Kopfmitte, dort erscheinen Herz/Zzz
    FX               "heart", "z" -> Textzeilen
"""
import os
import pprint
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITE_DIR = os.path.join(ROOT, "common", "sprites")
CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!$%&()*+,-/:;<=>?@[]^_|~"
MAX_COLORS = 80


# --------------------------------------------------------------------------- PNG
def read_png(path):
    """8-bit RGBA- oder RGB-PNG ohne Interlacing -> (w, h, px) mit px(x, y) -> (r, g, b, a)."""
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("keine PNG-Datei: " + path)
    i, idat = 8, b""
    while i < len(d):
        n, = struct.unpack(">I", d[i:i + 4])
        t = d[i + 4:i + 8]
        if t == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", d[i + 8:i + 21])
        elif t == b"IDAT":
            idat += d[i + 8:i + 8 + n]
        i += 12 + n
    if depth != 8 or ctype not in (2, 6) or inter:
        raise SystemExit(f"{path}: erwartet 8-bit RGB/RGBA ohne Interlacing (bitte so exportieren)")
    bpp = 4 if ctype == 6 else 3
    raw, stride = zlib.decompress(idat), w * bpp
    rows, prev, p = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line

    def px(x, y):
        if 0 <= x < w and 0 <= y < h:
            o = x * bpp
            v = rows[y][o:o + bpp]
            return tuple(v) if bpp == 4 else tuple(v) + (255,)
        return (0, 0, 0, 0)

    return w, h, px


def write_png(path, pixels):
    """pixels: Liste von Zeilen mit (r, g, b, a)-Tupeln."""
    h, w = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + bytes(v for p in line for v in p) for line in pixels)

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# --------------------------------------------------------------------------- Raster
def crop(grid):
    ys = [i for i, line in enumerate(grid) if any(line)]
    xs = [i for line in grid for i, v in enumerate(line) if v]
    if not ys:
        return [[None]]
    return [line[min(xs):max(xs) + 1] for line in grid[min(ys):max(ys) + 1]]


def head_anchor(grid):
    """(x, y) der Kopfmitte: Mitte der obersten Zeilen (= zwischen den Ohren), y = oberste Zeile."""
    ys = [i for i, line in enumerate(grid) if any(line)]
    if not ys:
        return (len(grid[0]) // 2, 0)
    top = ys[0]
    span = max(2, (ys[-1] - top + 1) // 8)
    xs = [x for line in grid[top:top + span] for x, v in enumerate(line) if v]
    return ((min(xs) + max(xs) + 1) // 2, top)  # immer gleich runden (verschiebungsfest)


def add_rim(grid, rim):
    """Aeusserste Pixel der Silhouette in Farbe rim umfaerben (Sichtbarkeit auf dunklem Grund)."""
    h, w = len(grid), len(grid[0])
    out = [list(line) for line in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] is None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or grid[ny][nx] is None:
                    out[y][x] = rim
                    break
    return out


def pick_color(hits):
    """Repraesentative Farbe einer Pixelgruppe: helle Farben (Augen, Herz) setzen sich durch,
    sonst die Farbe am naechsten am Mittelwert (bleibt knackig statt verwaschen)."""
    bright = [c for c in hits if max(c) > 110]
    if len(bright) >= 2:
        hits = bright
    m = [sum(c[i] for c in hits) / len(hits) for i in range(3)]
    return min(hits, key=lambda c: sum((c[i] - m[i]) ** 2 for i in range(3)))


def halve(grid):
    """Halbe Aufloesung: 2x2-Bloecke, deckend ab 2 von 4 Pixeln."""
    h, w = len(grid), len(grid[0])
    out = []
    for y in range(0, h - 1 if h % 2 else h, 2):
        line = []
        for x in range(0, w - 1 if w % 2 else w, 2):
            hits = [grid[y + dy][x + dx] for dy in (0, 1) for dx in (0, 1)
                    if y + dy < h and x + dx < w and grid[y + dy][x + dx]]
            line.append(pick_color(hits) if len(hits) >= 2 else None)
        out.append(line)
    return out


def place(grid, w, h, dx):
    """Ausgeschnittenes Bild in eine w x h-Leinwand setzen: Spalte dx, unten buendig."""
    canvas = [[None] * w for _ in range(h)]
    top = h - len(grid)
    for y, line in enumerate(grid):
        for x, c in enumerate(line):
            if c and 0 <= top + y < h and 0 <= dx + x < w:
                canvas[top + y][dx + x] = c
    return canvas


def quantize(weights, k):
    """Farben -> hoechstens k Farben (gewichtetes k-means, Start per Farthest-Point, damit
    seltene, aber auffaellige Farben wie gelbe Augen ihren eigenen Platz behalten)."""
    items = list(weights.items())
    if len(items) <= k:
        return {c: c for c, _ in items}
    d2 = lambda a, b: sum((a[t] - b[t]) ** 2 for t in range(3))
    pool = [c for c, n in items if n >= 2] or [c for c, _ in items]
    centers = [max(items, key=lambda it: it[1])[0]]
    near = {c: d2(c, centers[0]) for c in pool}
    while len(centers) < min(k, len(pool)):
        nxt = max(pool, key=lambda c: near[c])
        if near[nxt] == 0:
            break
        centers.append(nxt)
        for c in pool:
            near[c] = min(near[c], d2(c, nxt))
    for _ in range(10):
        acc = [[0, 0, 0, 0] for _ in centers]
        for c, n in items:
            j = min(range(len(centers)), key=lambda i: d2(c, centers[i]))
            a = acc[j]
            a[0] += c[0] * n
            a[1] += c[1] * n
            a[2] += c[2] * n
            a[3] += n
        centers = [(a[0] / a[3], a[1] / a[3], a[2] / a[3]) if a[3] else centers[i] for i, a in enumerate(acc)]
    centers = [tuple(int(round(v)) for v in c) for c in centers]
    return {c: min(centers, key=lambda z: d2(c, z)) for c, _ in items}


def make_look(frames, fx, keep=()):
    """frames: Name -> Leinwand-Raster (alle gleich gross); fx: Name -> ausgeschnittenes Raster.
    keep: Farben, die exakt erhalten bleiben (z.B. die Randfarbe)."""
    first = next(iter(frames.values()))
    width, body_h = len(first[0]), len(first)
    weights = {}
    for g in list(frames.values()) + list(fx.values()):
        for line in g:
            for c in line:
                if c and c not in keep:
                    weights[c] = weights.get(c, 0) + 1
    mapping = quantize(weights, MAX_COLORS - len(keep))
    mapping.update({c: c for c in keep})
    colors = sorted(set(mapping.values()))
    if len(colors) > len(CHARS):
        raise SystemExit("zu viele Farben")
    code = {c: CHARS[i] for i, c in enumerate(colors)}

    def enc(g):
        return ["".join(code[mapping[c]] if c else "." for c in line) for line in g]

    return {
        "W": width, "BODY_H": body_h, "FX_H": (max(len(g) for g in fx.values()) + 2) if fx else 0,
        "PALETTE": {code[c]: "#%02x%02x%02x" % c for c in colors},
        "HEAD": {n: head_anchor(g) for n, g in frames.items()},
        "SPRITES": {n: enc(g) for n, g in frames.items()},
        "FX": {n: enc(g) for n, g in fx.items()},
    }


# --------------------------------------------------------------------------- Ausgabe
def write_module(char_id, source, character, sets, out_dir=SPRITE_DIR):
    """Schreibt common/sprites/<char_id>.py (wird von common/characters.py automatisch gefunden)."""
    out = [f'"""Figur "{character["label"]}" - automatisch erzeugt von {source}, nicht von Hand bearbeiten."""',
           "", "CHARACTER = " + pprint.pformat(character, width=100, sort_dicts=False), "", "SETS = {"]
    for set_name, s in sets.items():
        out.append(f"    {set_name!r}: {{")
        for key, val in s.items():
            if key in ("SPRITES", "FX"):
                out.append(f"        {key!r}: {{")
                for n, rows in val.items():
                    out.append(f"            {n!r}: [")
                    out.extend(f"                {line!r}," for line in rows)
                    out.append("            ],")
                out.append("        },")
            else:
                out.append(f"        {key!r}: {val!r},")
        out.append("    },")
    out.append("}")
    path = os.path.join(out_dir, char_id + ".py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("geschrieben:", path)
    if os.path.abspath(out_dir) == os.path.abspath(SPRITE_DIR):
        update_registry()
    return path


def update_registry():
    """common/sprites/__init__.py mit festen Imports aller Figuren neu schreiben.
    (Feste Imports, damit PyInstaller sie sicher in die EXE/App packt.)"""
    ids = sorted(f[:-3] for f in os.listdir(SPRITE_DIR)
                 if f.endswith(".py") and f != "__init__.py" and not f.startswith("_"))
    out = ['"""Figuren-Verzeichnis - automatisch gepflegt von tools/sheetlib.py (update_registry).',
           "", "Jede Datei <id>.py hier ist eine Figur mit CHARACTER und SETS. Die Werkzeuge in tools/",
           'tragen neue Figuren hier selbst ein; von Hand: python tools/sheetlib.py"""', ""]
    out += [f"from . import {i}" for i in ids]
    out += ["", "MODULES = {" + ", ".join(f"{i!r}: {i}" for i in ids) + "}"]
    path = os.path.join(SPRITE_DIR, "__init__.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("Figuren-Verzeichnis:", ", ".join(ids))


if __name__ == "__main__":
    update_registry()
