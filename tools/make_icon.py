#!/usr/bin/env python3
"""Erzeugt die Programm-Icons aus einer Pose der schwarzen Katze.

  python tools/make_icon.py                  -> art/miezi.ico + art/miezi.icns
  python tools/make_icon.py --frame walk1    -> andere Pose als Motiv
  python tools/make_icon.py --preview p.png  -> zusätzlich eine große PNG zum Anschauen

Die Katze wird aus common/sprites/schwarz.py gerendert (nur Standardbibliothek):
nach Kanten beschnitten, mit Rand auf ein quadratisches Bild gesetzt und per
Flächenmittel herunterskaliert (beim Vergrößern bleiben die Pixelblöcke hart).
Ausgaben:
  art/miezi.ico   Windows: 16/24/32/48 als BMP-Einträge + 256 px als PNG
  art/miezi.icns  macOS:   16..1024 px als PNG-Einträge (ic12..ic10)
"""
import argparse
import importlib.util
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheetlib import write_png  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITE_FILE = os.path.join(ROOT, "common", "sprites", "schwarz.py")
TRANS = (0, 0, 0, 0)


def load_grid(frame):
    """SPRITES[frame] (Zeichenraster) -> Liste von Zeilen mit (r, g, b, a)."""
    spec = importlib.util.spec_from_file_location("schwarz", SPRITE_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    hi = mod.SETS["hi"]
    palette = {}
    for ch, hexval in hi["PALETTE"].items():
        h = hexval.lstrip("#")
        palette[ch] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    grid = []
    for line in hi["SPRITES"][frame]:
        grid.append([TRANS if ch == "." else palette[ch] for ch in line])
    # auf die beschriftete Bildfläche beschneiden
    ys = [i for i, row in enumerate(grid) if any(p[3] for p in row)]
    xs = [x for row in grid for x, p in enumerate(row) if p[3]]
    return [row[min(xs):max(xs) + 1] for row in grid[min(ys):max(ys) + 1]]


def render(size, cat):
    """Katze auf quadratische `size`-Fläche setzen: Flächenmittel, ca. 12 % Rand."""
    ch, cw = len(cat), len(cat[0])
    side = int(size * 0.88)
    scale = min(side / cw, side / ch)
    dw, dh = max(1, round(cw * scale)), max(1, round(ch * scale))
    ox, oy = (size - dw) // 2, (size - dh) // 2
    out = []
    for y in range(size):
        row = []
        for x in range(size):
            tx, ty = x - ox, y - oy
            if not (0 <= tx < dw and 0 <= ty < dh):
                row.append(TRANS)
                continue
            # Quellpixel-Ausschnitt, der in dieses Zielpixel fällt
            x0 = min(cw - 1, int(tx * cw / dw))
            x1 = max(x0 + 1, min(cw, int((tx + 1) * cw / dw)))
            y0 = min(ch - 1, int(ty * ch / dh))
            y1 = max(y0 + 1, min(ch, int((ty + 1) * ch / dh)))
            a_sum = r_sum = g_sum = b_sum = 0.0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    r, g, b, a = cat[yy][xx]
                    a_sum += a
                    r_sum += r * a
                    g_sum += g * a
                    b_sum += b * a
            if a_sum <= 255 * 0.5:
                row.append(TRANS)
            else:
                a = a_sum / ((x1 - x0) * (y1 - y0))
                row.append((int(r_sum / a_sum), int(g_sum / a_sum), int(b_sum / a_sum),
                            min(255, int(a + 64))))
        out.append(row)
    return out


def png_bytes(size, cat, tmpdir):
    path = os.path.join(tmpdir, "icon_%d.png" % size)
    write_png(path, render(size, cat))
    with open(path, "rb") as f:
        return f.read()


# --------------------------------------------------------------------------- ICO
def ico_bmp_entry(size, cat):
    """32-Bit-BMP-Eintrag (BGRA, bottom-up) + AND-Maske aus Nullen."""
    rows = render(size, cat)
    dib = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    body = b"".join(
        bytes(v for p in row for v in (p[2], p[1], p[0], p[3]))
        for row in reversed(rows)
    )
    mask_row = b"\x00" * ((size + 31) // 32 * 4)
    return dib + body + mask_row * size


def write_ico(path, cat):
    sizes = [(16, False), (24, False), (32, False), (48, False), (256, True)]
    tmpdir = os.path.dirname(path) or "."
    payloads = []
    for s, png in sizes:
        if png:
            data = png_bytes(s, cat, tmpdir)
            p = os.path.join(tmpdir, "icon_%d.png" % s)
            if os.path.exists(p):
                os.remove(p)
        else:
            data = ico_bmp_entry(s, cat)
        payloads.append((s, data))
    out = struct.pack("<HHH", 0, 1, len(payloads))
    offset = 6 + 16 * len(payloads)
    for s, data in payloads:
        w = h = 0 if s >= 256 else s
        out += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(out + b"".join(d for _, d in payloads))


# -------------------------------------------------------------------------- ICNS
ICNS_TYPES = [(16, "ic12"), (32, "ic11"), (64, "ic13"), (128, "ic07"),
              (256, "ic08"), (512, "ic09"), (1024, "ic10")]


def write_icns(path, cat):
    tmpdir = os.path.dirname(path) or "."
    entries = []
    for size, tag in ICNS_TYPES:
        data = png_bytes(size, cat, tmpdir)
        p = os.path.join(tmpdir, "icon_%d.png" % size)
        if os.path.exists(p):
            os.remove(p)
        entries.append(tag.encode("ascii") + struct.pack(">I", 8 + len(data)) + data)
    body = b"".join(entries)
    with open(path, "wb") as f:
        f.write(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frame", default="idle1",
                    help="Pose aus dem Sprite (Standard: idle1, die Sitzpose)")
    ap.add_argument("--preview", metavar="PNG", help="zusätzlich große PNG zum Prüfen")
    args = ap.parse_args()

    cat = load_grid(args.frame)
    write_ico(os.path.join(ROOT, "art", "miezi.ico"), cat)
    write_icns(os.path.join(ROOT, "art", "miezi.icns"), cat)
    print("art/miezi.ico, art/miezi.icns geschrieben (Pose: %s, %d x %d px)"
          % (args.frame, len(cat[0]), len(cat)))
    if args.preview:
        write_png(args.preview, render(256, cat))
        print("Vorschau: %s" % args.preview)


if __name__ == "__main__":
    main()
