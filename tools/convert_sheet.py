"""Macht aus einem Sheet nach Vorlage eine Figur: common/sprites/<id>.py

Aufruf (im Projektordner):
    python tools/convert_sheet.py art/mein_tier.png mein_tier
    python tools/convert_sheet.py art/mein_tier.png mein_tier --json art/mein_tier.json

Zum Sheet gehoert eine JSON-Beschreibung (Standard: gleicher Name, Endung .json).
Aufbau und alle Felder: siehe README.md, Abschnitt "Neues Tier einbinden", und das
Beispiel art/vorlage_katze.png + art/vorlage_katze.json.

Kurz: festes Raster, jede Zeile eine Animation, jede Zelle cell[0] x cell[1] Sprite-Pixel,
jedes Sprite-Pixel pixel x pixel Sheet-Pixel, transparenter Hintergrund, Tier schaut nach
rechts, Fuesse auf der Zellunterkante.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetlib as sl

ANIMS = ("walk", "sit", "blink", "sleep", "jump", "drag", "fx", "extra")


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", help="PNG nach Vorlage")
    ap.add_argument("id", help="Figur-Kennung = Dateiname in common/sprites (a-z, 0-9, _)")
    ap.add_argument("--json", help="Beschreibung (Standard: <sheet>.json)")
    ap.add_argument("--out-dir", default=sl.SPRITE_DIR, help="Zielordner (Standard: common/sprites)")
    a = ap.parse_args()
    if not a.id.replace("_", "").isalnum() or not a.id[0].isalpha() or a.id != a.id.lower():
        raise SystemExit("id bitte nur aus Kleinbuchstaben, Ziffern und _ (z.B. hund oder graue_katze)")
    conf_path = a.json or os.path.splitext(a.sheet)[0] + ".json"
    with open(conf_path, encoding="utf-8") as f:
        conf = json.load(f)

    w, h, px = sl.read_png(a.sheet)
    cw, ch = conf["cell"]
    pix = conf.get("pixel", 1)
    gap = conf.get("gap", 0)  # Abstand zwischen Zellen in Sheet-Pixeln
    rim = hex_rgb(conf["rim"]) if conf.get("rim") else None
    alpha_min = conf.get("alpha_min", 128)

    def cell(row, col):
        x0, y0 = col * (cw * pix + gap), row * (ch * pix + gap)
        if x0 + cw * pix > w or y0 + ch * pix > h:
            raise SystemExit(f"Zelle Zeile {row + 1}, Spalte {col + 1} liegt ausserhalb des Sheets "
                             f"({w}x{h}) - stimmen cell/pixel/gap und die Anzahl der Bilder?")
        grid = []
        for gy in range(ch):
            line = []
            for gx in range(cw):
                v = px(x0 + gx * pix + pix // 2, y0 + gy * pix + pix // 2)
                line.append(v[:3] if v[3] >= alpha_min else None)
            grid.append(line)
        if not any(any(line) for line in grid):
            raise SystemExit(f"Zelle Zeile {row + 1}, Spalte {col + 1} ist leer")
        return grid

    frames, fx, groups, extras = {}, {}, {}, {}
    for r, row in enumerate(conf["rows"]):
        anim = row["anim"]
        if anim not in ANIMS:
            raise SystemExit(f"Zeile {r + 1}: unbekannte Animation {anim!r} (erlaubt: {', '.join(ANIMS)})")
        if anim == "fx":
            for i, name in enumerate(row["frames"]):
                fx[name] = sl.crop(cell(r, i))
            continue
        base = row["name"] if anim == "extra" else anim
        names = []
        for i in range(row["frames"]):
            n = f"{base}{i + 1}"
            g = cell(r, i)
            frames[n] = sl.add_rim(g, rim) if rim else g
            names.append(n)
        if anim == "extra":
            seq = row.get("seq") or [[i + 1, 10] for i in range(len(names))]
            extras[base] = [(f"{base}{k}", ticks) for k, ticks in seq]
        else:
            groups[anim] = names

    for need in ("walk", "sit", "sleep"):
        if need not in groups:
            raise SystemExit(f"Pflicht-Animation fehlt: {need}")
    if "heart" not in fx or "z" not in fx:
        raise SystemExit("Zeile mit anim \"fx\" und frames [\"heart\", \"z\"] fehlt")

    sizes = conf.get("sizes", {"klein": 1, "mittel": 2, "gross": 3})
    sets = {"std": sl.make_look(frames, fx, keep=(rim,) if rim else ())}
    char_sizes = {k: ("std", v) for k, v in sizes.items()}
    if conf.get("small_from_half"):  # "Klein" = eigene halbe Aufloesung statt Vergroesserung
        half = {n: sl.halve(g) for n, g in frames.items()}
        if rim:
            half = {n: sl.add_rim(g, rim) for n, g in half.items()}
        sets["lo"] = sl.make_look(half, {n: sl.crop(sl.halve(g)) for n, g in fx.items()},
                                  keep=(rim,) if rim else ())
        char_sizes["klein"] = ("lo", 1)

    sleep = groups["sleep"] * 2 if len(groups["sleep"]) == 1 else groups["sleep"][:2]
    character = {
        "label": conf["name"],
        "order": conf.get("order", 50),
        "sizes": char_sizes,
        "walk": groups["walk"], "walk_ticks": conf.get("walk_ticks", 2),
        "sit": groups["sit"],
        "blink": groups.get("blink", groups["sit"])[0],
        "sleep": sleep,
        "jump": groups.get("jump", [groups["walk"][0]]),
        "drag": groups.get("drag", [groups["walk"][0]]),
        "hop": conf.get("hop", groups["sit"][0]),
        "extras": extras,
    }
    for s_name, s in sets.items():
        print(f"{s_name}: {s['W']}x{s['BODY_H']} (+{s['FX_H']} Effektzeilen), {len(s['PALETTE'])} Farben")
    sl.write_module(a.id, "tools/convert_sheet.py aus " + os.path.basename(a.sheet), character, sets, a.out_dir)


if __name__ == "__main__":
    main()
