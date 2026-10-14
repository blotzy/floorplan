# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: turn the powder room into a full bath with a shower stall, taking a little of
the walk-in closet. The laundry keeps its side-by-side washer/dryer/sink alcove (only the
folding counter goes).

The powder room widens west into the east end of the walk-in closet (a new partition replaces
the old plumbing wall between them). From the door: lavatory on the laundry-side wall past the
door swing, toilet on the back wall (the plumbing wall shared with the laundry alcove), and the
The powder room stays as it is (toilet on the back wall, small sink by the door) and gains a
36"-wide shower strip taken from the east end of the walk-in closet (~3'; closet ~12'-4"
long). Glass panel with an opening at the hall end; head on the back (plumbing) wall. The
jetted tub's pump access panel is on the closet side, just past the new bath, with the
closet's hanging stopping short of it.

  shower-strip  36" x 5'-6" walk-in shower filling the strip
  shower-linen  36" x 48" shower at the back, linen cabinet at the hall end

Writes renders/experiments/powder-bath-<variant>.png (+ DXF) and a 3D model per variant.

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


def walls(walls, wall_x):
    """Partition between the new bath and the closet at x = wall_x; the old plumbing wall
    now only runs from the powder/alcove wall to the rear (laundry alcove | primary bath)."""
    for i, w in enumerate(walls):
        if w[0] == "utility|bath":
            walls[i] = (w[0], w[1], w[2], S.face("powder|alcove", -1), w[4], w[5])
    walls.append(("bath|closet", "y", wall_x, 457.0, S.wall_info("bath|wic")[1], S.INT))


def openings(ops):
    """Bath door hinged on the strip side: its swing clears the sink and the shower glass."""
    for i, o in enumerate(ops):
        if o[0] == "south hall wall" and o[1] == 838.0:
            ops[i] = ("south hall wall", 838.0, 866.0, "door", "b", +1)


def utility(sh, wall_x, linen):
    eq, srow = EQ, S.face("south hall wall", +1)
    # laundry: alcove unchanged, folding counter gone
    l0, l1 = S.face("pantry|laundry", +1), S.face("utility|bath", -1)
    S.room_label(sh, "LAUNDRY", l0, srow, S.face("laundry|powder", -1), S.S_IN, cy=520.0, h=5.0)
    y = S.S_IN
    for d, lbl in ((27, "DRYER"), (27, "WASHER"), (25, "SINK")):
        sh.rect(l1 - 30, y - d, l1, y, eq); sh.text(lbl, l1 - 15, y - d / 2, 3.0, rot=90); y -= d
    sh.rect(l0, 495.0, l0 + 4, 515.0, eq); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)
    b0, b1 = S.face("laundry|powder", +1), wall_x - S.INT / 2
    back = S.face("powder|alcove", -1)                    # plumbing wall shared with the laundry alcove
    sx = S.face("utility|bath", -1)                       # old powder room's west face / start of the strip
    nook = S.face("bath|wic", -1)
    # wall-hung sink on the laundry-side wall (outside the door swing)
    sh.rect(b0, 468.0, b0 + 12, 486.0, eq); sh.text("LAV", b0 + 6, 477.0, 2.5, rot=90)
    # shower where the powder room's toilet was: 47" x 36" on the back wall, door on its front
    sy = back - 36
    sh.rect(b0, sy, sx, back, eq)
    S.glass(sh, (b0, sy), (sx - 26, sy))                  # fixed glass + 24" door at the strip end
    sh.text("SHOWER", (b0 + sx) / 2, back - 18, 3.2)
    hx = (b0 + sx) / 2
    sh.circle((hx, back - 3), 2.0, eq)
    sh.heads.append((hx, back, 0.0, -1.0))
    # toilet in the strip taken from the closet, on the back wall; niche shelf above the tank
    tx = (sx + b1) / 2
    S.wc(sh, tx - 15, back - 28, tx + 15, back)
    sh.rect(S.face("utility|bath", +1), back, b1, nook, eq); sh.text("NICHE", tx + 2, back + 4, 2.0)
    if linen:                                             # shallow linen cabinet at the hall end
        sh.rect(sx + 2, srow, b1, srow + 13, "A-FURN"); sh.line((sx + 2, srow), (b1, srow + 13), "A-FURN")
        sh.text("LINEN", tx, srow + 6.5, 2.5)
    S.room_label(sh, "BATH", b0, srow, b1, back, cx=b0 + 28, cy=srow + 20, h=3.6)


def closet(sh, wall_x):
    x0, x1 = wall_x + S.INT / 2, S.face("suite|primary", -1)
    y0, y1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hang(x0, 1031.0, y0, +1)
    hang(x0 + 16, 989.0, y1, -1)                          # stops short: tub access panel below
    sh.rect(x0, y0 + 24, x0 + 14, y1 - 24, fu)
    sh.text("SHELVES", x0 + 7, (y0 + y1) / 2, 2.2, rot=90)
    sh.rect(x0 + 1, y1 - 2, x0 + 13, y1, "A-EQPM")       # jetted-tub pump access (tub's north end)
    sh.text("TUB ACCESS", x0 + 7, y1 - 8, 2.2)
    S.room_label(sh, "WIC", x0, y0, x1, y1, cx=1000.0, h=5.0)


VARIANTS = {"full-bath": (910.0, True)}


def main():
    out = S.RENDERS / "experiments"
    for key, (wall_x, linen) in VARIANTS.items():
        S.WALLS, S.OPENINGS = copy.deepcopy(BASE[0]), copy.deepcopy(BASE[1])
        walls(S.WALLS, wall_x)
        openings(S.OPENINGS)
        S.utility_block = lambda sh, wx=wall_x, ln=linen: utility(sh, wx, ln)
        S.wic = lambda sh, wx=wall_x: closet(sh, wx)
        sh = S.build()
        sh.text(f"EXPERIMENT: POWDER ROOM -> FULL BATH ({key.upper()})", S.LOT_W / 2, S.LOT_D + 115, 10.0)
        sh.doc.saveas(S.ROOT / f"Accosting - owner schematic - EXPERIMENT powder bath {key}.dxf")
        S.render(sh.doc, out / f"powder-bath-{key}.png", 660, 440, 1080, 640, width_in=12, dpi=130)
        sc = M.build_schematic()
        M.write_model(sc, out / f"powder-bath-{key}", sc.meta)
        print("built", key)
    S.WALLS, S.OPENINGS, S.utility_block, S.wic = BASE


if __name__ == "__main__":
    main()
