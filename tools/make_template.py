"""Erzeugt das Beispiel-Sheet art/vorlage_katze.png (+ .json und eine Ansicht mit Raster)
aus der fertigen schwarzen Katze. So sollte ein Sheet fuer tools/convert_sheet.py aussehen.

Aufruf (im Projektordner):  python tools/make_template.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "common"))
import sheetlib as sl
from sprites import schwarz

PIXEL = 4
look = schwarz.SETS["hi"]
C = schwarz.CHARACTER
ROWS = [
    {"anim": "walk", "frames": C["walk"]},
    {"anim": "sit", "frames": C["sit"]},
    {"anim": "blink", "frames": [C["blink"]]},
    {"anim": "sleep", "frames": C["sleep"]},
    {"anim": "jump", "frames": C["jump"]},
    {"anim": "drag", "frames": C["drag"]},
    {"anim": "fx", "frames": ["heart", "z"]},
]
for name, seq in C["extras"].items():
    order = []
    for f, _ in seq:
        if f not in order:
            order.append(f)
    ROWS.append({"anim": "extra", "name": name, "frames": order,
                 "seq": [[order.index(f) + 1, t] for f, t in seq]})


def rgba(c):
    return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 255)


def main():
    cw, ch = look["W"], look["BODY_H"]
    cols = max(len(r["frames"]) for r in ROWS)
    W, H = cols * cw * PIXEL, len(ROWS) * ch * PIXEL
    clear = (0, 0, 0, 0)
    sheet = [[clear] * W for _ in range(H)]
    for r, row in enumerate(ROWS):
        for i, name in enumerate(row["frames"]):
            if row["anim"] == "fx":
                rows = look["FX"][name]
                rows = ["." * len(rows[0])] * (ch - len(rows)) + rows  # unten links in die Zelle
            else:
                rows = look["SPRITES"][name]
            for y, line in enumerate(rows):
                for x, c in enumerate(line):
                    if c == ".":
                        continue
                    v = rgba(look["PALETTE"][c])
                    for yy in range(PIXEL):
                        sy = (r * ch + y) * PIXEL + yy
                        sheet[sy][(i * cw + x) * PIXEL:(i * cw + x + 1) * PIXEL] = [v] * PIXEL
    art = os.path.join(sl.ROOT, "art")
    sl.write_png(os.path.join(art, "vorlage_katze.png"), sheet)

    # Ansicht mit sichtbaren Zellen (nur zum Anschauen, NICHT als Konverter-Eingabe)
    tiles = ((236, 236, 240, 255), (214, 214, 222, 255))
    view = [[p if p[3] else tiles[((x // (cw * PIXEL)) + (y // (ch * PIXEL))) % 2] for x, p in enumerate(line)]
            for y, line in enumerate(sheet)]
    sl.write_png(os.path.join(art, "vorlage_katze_raster.png"), view)

    conf = {
        "name": "Schwarze Katze (Vorlage)",
        "cell": [cw, ch],
        "pixel": PIXEL,
        "order": 90,
        "walk_ticks": C["walk_ticks"],
        "sizes": {"klein": 1, "mittel": 1, "gross": 2},
        "small_from_half": True,
        "hop": "sit1",
        "rim": None,
        "rows": [{k: (len(v) if k == "frames" and row["anim"] != "fx" else v) for k, v in row.items()}
                 for row in ROWS],
    }
    # lesbar: eine Zeile pro Feld bzw. pro Animation
    lines = ["{"]
    for k, v in conf.items():
        if k == "rows":
            lines.append('  "rows": [')
            rows = [json.dumps(r, ensure_ascii=False) for r in v]
            lines.extend("    " + r + ("," if i < len(rows) - 1 else "") for i, r in enumerate(rows))
            lines.append("  ]")
        else:
            lines.append(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},")
    lines.append("}")
    with open(os.path.join(art, "vorlage_katze.json"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"geschrieben: art/vorlage_katze.png ({W}x{H}), art/vorlage_katze_raster.png, art/vorlage_katze.json")


if __name__ == "__main__":
    main()
