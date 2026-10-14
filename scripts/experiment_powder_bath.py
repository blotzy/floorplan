# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the powder room becomes a three-quarter bath (shower, toilet, sink) by taking the
front of the laundry. The walk-in closet and the primary bath are untouched.

  bath     the powder room widens east into the front of the laundry: about 5'-10" x 5'-6".
           36" x 36" shower in the back corner on the primary-bath side (head on the back
           wall), toilet in the other back corner, a small wall-hung sink on the hall wall
           opposite it. The door stays where the powder-room door is and swings clear of all
           three.
  laundry  keeps its own door off the hall: a 3'-6" passage (electrical panel on its wall)
           leads to the machine area behind the bath, laid out as in the plan (sink, washer,
           dryer, folding counter on the back wall; open shelves on the bath's back wall).
           The tall storage on the old powder-room wall goes away.

Writes renders/experiments/powder-bath.png (+ DXF) and a 3D model.

    uv run scripts/experiment_powder_bath.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = (copy.deepcopy(S.WALLS), S.utility_block)
EQ, FU = "A-EQPM", "A-FURN"
PASSAGE = 42.0                                   # clear width of the laundry passage


def split_x():
    return S.face("pantry|laundry", +1) + PASSAGE + S.WET / 2


def walls(ws):
    sx = split_x()
    for i, (name, axis, c, a, b, t) in enumerate(ws):
        if name == "laundry|powder":
            ws[i] = (name, axis, sx, a, b, t)
        elif name == "powder|alcove":
            ws[i] = (name, axis, c, sx - S.WET / 2, b, t)


def utility(sh):
    srow = S.face("south hall wall", +1)
    # ---- bath
    b0, b1 = S.face("laundry|powder", +1), S.face("utility|bath", -1)
    back = S.face("powder|alcove", -1)
    sx0, sy0 = b1 - 36, back - 36                         # shower, back corner on the primary-bath side
    S.wet_zone(sh, sx0, sy0, b1, back)
    sh.rect(sx0, sy0, b1, back, EQ)
    S.glass(sh, (sx0, sy0), (sx0, back))                  # fixed glass beside the toilet
    S.glass(sh, (sx0, sy0), (sx0 + 12, sy0))              # front: 12" fixed + 24" door
    sh.text("SHOWER", (sx0 + b1) / 2, back - 20, 3.2)
    S.shower_head(sh, (sx0 + b1) / 2, back, -1)
    tx = b0 + 16                                          # toilet in the other back corner
    S.wc(sh, tx - 15, back - 28, tx + 15, back)           # (its 24" clear floor stays open)
    S.vanity(sh, tx - 9, srow, tx + 9, srow + 14, "SINK")  # small wall-hung sink on the hall wall,
                                                          # facing the toilet, clear of the door swing
    S.room_label(sh, "BATH", b0, srow, b1, back, cx=(sx0 + b1) / 2, cy=srow + 20, h=3.2)
    # ---- laundry (as in the plan, minus the tall storage)
    l0, l1 = S.face("pantry|laundry", +1), b1
    lp, bk = S.face("laundry|powder", -1), S.S_IN
    x = l0 + 36                                           # open floor in front of the mech closet's bifold
    S.vanity(sh, x, bk - 15, x + 14, bk, "SINK", rot=90)
    x = w0 = x + 16
    for lbl in ("WASHER", "DRYER"):
        sh.rect(x, bk - 30, x + 27, bk, EQ); sh.text(lbl, x + 13.5, bk - 15, 3.0); x += 27
    sh.rect(w0, bk - 30, x, bk, FU)
    sh.text("FOLDING COUNTER OVER  /  UPPERS ABOVE", (w0 + x) / 2, bk - 36, 2.4)
    a0 = S.face("powder|alcove", +1)
    sh.rect(lp + 2, a0, l1, a0 + 12, FU); sh.text("SHELVES", (lp + 2 + l1) / 2, a0 + 6, 2.4)
    sh.rect(l0, 495.0, l0 + 4, 515.0, EQ); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)
    S.room_label(sh, "LAUNDRY", l0, srow, lp, bk, cx=805.0, cy=563.0, h=4.5)


def main():
    out = S.RENDERS / "experiments"
    S.WALLS = copy.deepcopy(BASE[0])
    walls(S.WALLS)
    S.utility_block = utility
    sh = S.build()
    sh.text("EXPERIMENT: POWDER ROOM -> 3/4 BATH (FRONT OF THE LAUNDRY)", S.LOT_W / 2, S.LOT_D + 115, 10.0)
    sh.doc.saveas(S.ROOT / "Accosting - owner schematic - EXPERIMENT powder bath.dxf")
    S.render(sh.doc, out / "powder-bath.png", 660, 440, 1080, 640, width_in=12, dpi=130)
    sc = M.build_schematic()
    M.write_model(sc, out / "powder-bath", sc.meta)
    b = (S.face("laundry|powder", +1), S.face("utility|bath", -1), S.face("south hall wall", +1), S.face("powder|alcove", -1))
    print(f"bath {b[1] - b[0]:.1f} x {b[3] - b[2]:.1f} in; passage {S.face('laundry|powder', -1) - S.face('pantry|laundry', +1):.1f} in")
    S.WALLS, S.utility_block = BASE


if __name__ == "__main__":
    main()
