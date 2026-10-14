# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: turn the powder room into a full bath with a shower stall by taking room from
the laundry (and a little of the walk-in closet), with the washer and dryer on the laundry's
window wall.

The bath and laundry are split across the block instead of along it:
  bath     the powder room widens east into the front of the laundry and west ~2' into the
           closet: about 8'-11" x 5'-6" along the hall. Lavatory and toilet on its back wall,
           a 36" x 36" shower in the corner toward the closet (head on that wall), door hinged
           away from the lavatory.
  laundry  L-shaped: a 34" corridor from the hall (subpanel on its wall) opens into the back
           half, which spans the block. Sink, washer, dryer and a storage cabinet in a row on
           the window wall (window sill raised to clear the machines), ~4' of floor in front.
           The mechanical closet's bifold still opens into it. The primary bath's jetted tub
           backs onto this room, so its pump access panel opens from the laundry.
  closet   loses ~2'-3" at its east end; hanging on both long walls as before.

Writes renders/experiments/powder-bath-full-bath.png (+ DXF) and a 3D model.

    uv run scripts/experiment_powder_bath.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS), S.utility_block, S.wic)
EQ = "A-EQPM"
SPLIT_X = 790.0          # bath | laundry corridor wall (was the laundry | powder wall at 820)
CLOSET_X = 902.25        # bath | closet partition
BACK_Y = 531.2           # bath's back wall (laundry behind it), as the old powder | alcove wall


def walls(ws):
    for i, w in enumerate(ws):
        name, axis, c, a, b, t = w
        if name == "laundry|powder":
            ws[i] = (name, axis, SPLIT_X, a, BACK_Y + S.WET / 2, t)
        elif name == "powder|alcove":
            ws[i] = (name, axis, c, SPLIT_X - S.WET / 2, CLOSET_X, t)
        elif name == "utility|bath":
            ws[i] = (name, axis, c, BACK_Y + S.WET / 2, b, t)      # now laundry | primary bath only
    ws.append(("bath|closet", "y", CLOSET_X, 457.0, S.wall_info("bath|wic")[1], S.INT))


def openings(ops):
    for i, o in enumerate(ops):
        if o[0] == "south hall wall" and o[1] == 760.0:
            ops[i] = ("south hall wall", 755.0, 785.0, "door", "a", +1)    # laundry door into the corridor
        if o[0] == "south hall wall" and o[1] == 838.0:
            ops[i] = ("south hall wall", 838.0, 866.0, "door", "a", +1)    # bath door, away from the lav


def utility(sh):
    eq, srow = EQ, S.face("south hall wall", +1)
    # ---- bath
    b0, b1 = S.face("laundry|powder", +1), S.face("bath|closet", -1)
    back = S.face("powder|alcove", -1)
    S.vanity(sh, b0 + 4, back - 21, b0 + 28, back, "LAV")
    tx = b0 + 47
    S.wc(sh, tx - 15, back - 28, tx + 15, back)
    sx, sy = b1 - 36, back - 36
    sh.rect(sx, sy, b1, back, eq)
    S.glass(sh, (sx, sy), (sx, back))                     # fixed glass beside the toilet
    S.glass(sh, (sx, sy), (sx + 12, sy))                  # front: 12" fixed + 24" door
    sh.text("SHOWER", (sx + b1) / 2, back - 18, 3.2)
    sh.circle((b1 - 3, back - 18), 2.0, eq)
    sh.heads.append((b1, back - 18, -1.0, 0.0))
    S.room_label(sh, "BATH", b0, srow, b1, back, cx=(b0 + sx) / 2 - 6, cy=srow + 14, h=3.6)
    # ---- laundry
    l0 = S.face("pantry|laundry", +1)
    l1 = S.face("utility|bath", -1)
    ly = S.face("powder|alcove", +1)                      # back half starts here
    sh.rect(l0, 495.0, l0 + 4, 515.0, eq); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)
    x = l0 + 16                                           # clear of the mech closet's bifold
    S.vanity(sh, x, S.S_IN - 22, x + 25, S.S_IN, "SINK"); x += 27
    for lbl in ("WASHER", "DRYER"):
        sh.rect(x, S.S_IN - 30, x + 27, S.S_IN, eq); sh.text(lbl, x + 13.5, S.S_IN - 15, 3.0); x += 27
    sh.rect(x + 2, S.S_IN - 24, l1, S.S_IN, "A-FURN"); sh.text("STORAGE", (x + 2 + l1) / 2, S.S_IN - 12, 2.5)
    sh.rect(l1 - 2, ly + 12, l1, ly + 32, eq)             # jetted-tub pump access (tub backs onto this wall)
    sh.text("TUB ACCESS", l1 - 8, ly + 22, 2.2, rot=90)
    S.room_label(sh, "LAUNDRY", l0, srow, l1, S.S_IN, cx=(l0 + l1) / 2, cy=ly + 22, h=4.5)


def closet(sh):
    x0, x1 = S.face("bath|closet", +1), S.face("suite|primary", -1)
    y0, y1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hang(x0, 1031.0, y0, +1)
    hang(x0, 989.0, y1, -1)
    sh.rect(x0, y0 + 24, x0 + 14, y1 - 24, fu)
    sh.text("SHELVES", x0 + 7, (y0 + y1) / 2, 2.2, rot=90)
    S.room_label(sh, "WIC", x0, y0, x1, y1, cx=1000.0, h=5.0)


def main():
    out = S.RENDERS / "experiments"
    S.WALLS, S.OPENINGS = copy.deepcopy(BASE[0]), copy.deepcopy(BASE[1])
    walls(S.WALLS)
    openings(S.OPENINGS)
    S.utility_block, S.wic = utility, closet
    sh = S.build()
    sh.text("EXPERIMENT: POWDER ROOM -> FULL BATH (ROOM FROM THE LAUNDRY)", S.LOT_W / 2, S.LOT_D + 115, 10.0)
    sh.doc.saveas(S.ROOT / "Accosting - owner schematic - EXPERIMENT powder bath full-bath.dxf")
    S.render(sh.doc, out / "powder-bath-full-bath.png", 660, 440, 1080, 640, width_in=12, dpi=130)
    sc = M.build_schematic()
    M.write_model(sc, out / "powder-bath-full-bath", sc.meta)
    print("built")
    S.WALLS, S.OPENINGS, S.utility_block, S.wic = BASE


if __name__ == "__main__":
    main()
