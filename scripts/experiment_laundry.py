# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: laundry with everything on the back (window) wall.

  back wall  sink under the window, then a front-load washer and dryer side by side, one
             continuous counter over all of it for folding; upper cabinets either side of
             the window. Starts clear of the mechanical closet's bifold.
  side wall  the powder-room wall becomes full-height storage (brooms, vacuum, ironing
             board, supplies), kept shallow so the walk to the machines and the panel stays
             open.
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
    S.vanity(sh, x, back - 22, x + 25, back, "SINK"); x += 25
    for lbl in ("WASHER", "DRYER"):
        sh.rect(x, back - 30, x + 27, back, EQ); sh.text(lbl, x + 13.5, back - 15, 3.0); x += 27
    sh.rect(x, back - 24, l1, back, FU); sh.text("CAB", (x + l1) / 2, back - 12, 2.5)
    sh.rect(l0 + 18, back - 30, l1, back, FU)             # continuous folding counter over all of it
    sh.text("FOLDING COUNTER OVER  /  UPPERS EACH SIDE OF WINDOW", (l0 + 18 + l1) / 2, back - 36, 2.4)
    t0, t1 = S.face("south hall wall", +1) + 4, S.face("powder|alcove", -1)
    sh.rect(lp - TALL_D, t0, lp, t1, FU)
    sh.text("TALL STORAGE", lp - TALL_D / 2, (t0 + t1) / 2, 2.8, rot=90)
    sh.rect(l0, 495.0, l0 + 4, 515.0, EQ); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)
    S.room_label(sh, "LAUNDRY", l0, srow, lp, back, cx=(l0 + lp - TALL_D) / 2 + 4, cy=548.0, h=5.0)


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
