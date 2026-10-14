# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: laundry with everything on the back (window) wall.

  back wall  small utility sink under the window, then a front-load washer and dryer side by side, one
             continuous counter over all of it for folding; upper cabinets either side of
             the window. Starts clear of the mechanical closet's bifold.
  side wall  the powder-room wall becomes full-height storage (brooms, vacuum, ironing
             board, supplies), kept shallow so the walk to the machines and the panel stays
             open.
  shelves    open wall shelves on the pantry wall (past the panel's clear zone) and on the
             alcove wall behind the powder room.
  same       walls, doors, window, powder room and electrical panel are unchanged; the
             folding counter on the pantry wall goes away.

Writes renders/experiments/laundry-back-wall.png (+ DXF) and a 3D model.

    uv run scripts/experiment_laundry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = S.utility_block
EQ, FU = "A-EQPM", "A-FURN"
TALL_D = 18.0            # depth of the tall storage on the powder-room wall
SINK_W = 14.0            # small utility sink, about half a washer's width...
SINK_D = 15.0            # ...and half its depth, so the mech closet's bifold opens clear
SHELF_D = 12.0


def shelves(sh, x0, y0, x1, y1):
    sh.rect(x0, y0, x1, y1, FU)
    rot = 90 if (y1 - y0) > (x1 - x0) else 0
    sh.text("SHELVES", (x0 + x1) / 2, (y0 + y1) / 2, 2.4, rot=rot)


def utility(sh):
    srow = S.face("south hall wall", +1)
    # ---- powder room, as in the plan
    pw0, pw1 = S.face("laundry|powder", +1), S.face("utility|bath", -1)
    pws = S.face("powder|alcove", -1)
    tx = (pw0 + pw1) / 2 + 2
    sh.rect(tx - 9, pws - 28, tx + 9, pws, EQ); sh.text("WC", tx, pws - 14, 3.0)
    sh.rect(pw0, 468.0, pw0 + 12, 486.0, EQ)
    S.room_label(sh, "PWD", pw0, srow, pw1, pws, cx=842.0, cy=496.0, h=4.0)
    # ---- laundry
    l0, l1 = S.face("pantry|laundry", +1), S.face("utility|bath", -1)
    lp = S.face("laundry|powder", -1)
    back = S.S_IN
    x = l0 + 18                                           # clear of the mech closet's bifold
    S.vanity(sh, x, back - SINK_D, x + SINK_W, back, "SINK"); x += SINK_W
    for lbl in ("WASHER", "DRYER"):
        sh.rect(x, back - 30, x + 27, back, EQ); sh.text(lbl, x + 13.5, back - 15, 3.0); x += 27
    sh.rect(x, back - 24, l1, back, FU); sh.text("CAB", (x + l1) / 2, back - 12, 2.5)
    sh.rect(l0 + 18 + SINK_W, back - 30, l1, back, FU)    # folding counter over the machines and cabinet
    sh.text("FOLDING COUNTER OVER  /  UPPERS EACH SIDE OF WINDOW", (l0 + 18 + l1) / 2, back - 36, 2.4)
    t0, t1 = S.face("south hall wall", +1) + 4, S.face("powder|alcove", -1)
    sh.rect(lp - TALL_D, t0, lp, t1, FU)
    sh.text("TALL STORAGE", lp - TALL_D / 2, (t0 + t1) / 2, 2.8, rot=90)
    shelves(sh, l0, 530.0, l0 + SHELF_D, back - 36)                      # pantry wall, past the panel's clear zone
    shelves(sh, lp + 2, S.face("powder|alcove", +1), l1, S.face("powder|alcove", +1) + SHELF_D)   # alcove, behind the powder room
    sh.rect(l0, 495.0, l0 + 4, 515.0, EQ); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)
    S.room_label(sh, "LAUNDRY", l0, srow, lp, back, cx=805.0, cy=563.0, h=4.5)


def main():
    out = S.RENDERS / "experiments"
    S.utility_block = utility
    sh = S.build()
    sh.text("EXPERIMENT: LAUNDRY ON THE BACK WALL", S.LOT_W / 2, S.LOT_D + 115, 10.0)
    sh.doc.saveas(S.ROOT / "Accosting - owner schematic - EXPERIMENT laundry back wall.dxf")
    S.render(sh.doc, out / "laundry-back-wall.png", 620, 420, 1100, 640, width_in=12, dpi=130)
    sc = M.build_schematic()
    M.write_model(sc, out / "laundry-back-wall", sc.meta)
    print("built")
    S.utility_block = BASE


if __name__ == "__main__":
    main()
