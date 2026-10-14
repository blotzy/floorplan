# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: turn the powder room into a full bath with a shower stall.

The powder room takes over the laundry's washer/dryer alcove behind it, so the bath runs the
full depth of the block, and the laundry/powder wall moves ~4.5" into the laundry so a toilet
fits on the plumbing wall with 24" clear in front (bath 52" wide, laundry 60"). The bath door
swings toward the laundry wall. From the hall: lavatory, toilet, then a 52" x 36" shower across
the back with a small high window. No folding counter in the laundry.

  side-by-side  washer + dryer side by side on the laundry's plumbing wall, sink beside them
                (about a 30" aisle in front of the machines: tight).
  stacked       stacked washer/dryer in the back corner, sink beside it, laundry window moved
                over the open floor; the panel wall and floor stay free for storage.

Both keep the mechanical closet's bifold and the subpanel's working space clear.

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

BASE_WALLS, BASE_OPENINGS, BASE_BLOCK = copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS), S.utility_block
WALL_C = 815.5                     # laundry | bath wall centreline (was 820): bath 52", laundry 60"
EQ = "A-EQPM"


def walls_and_openings(walls, openings, laundry_window):
    walls[:] = [w for w in walls if w[0] != "powder|alcove"]
    for i, w in enumerate(walls):
        if w[0] == "laundry|powder":
            walls[i] = (w[0], w[1], WALL_C, w[3], S.S_IN, w[5])     # full depth now
    for i, o in enumerate(openings):
        if o[0] == "south" and o[1] == 778.0:
            openings[i] = ("south", *laundry_window, "window")       # laundry window moves
        if o[0] == "south hall wall" and o[1] == 838.0:
            openings[i] = ("south hall wall", 838.0, 866.0, "door", "a", +1)   # swings to the laundry wall
    openings.append(("south", 834.0, 858.0, "window"))               # small high window over the shower


def bath(sh):
    b0, b1 = S.face("laundry|powder", +1), S.face("utility|bath", -1)
    srow = S.face("south hall wall", +1)
    S.room_label(sh, "BATH", b0, srow, b1, S.S_IN, cx=b0 + 17, cy=530.0, h=4.0)
    S.vanity(sh, b1 - 20, srow + 31, b1, srow + 51, "LAV", rot=90)                # just past the door swing
    S.wc(sh, b1 - 28, 528.0, b1, 558.0)                                            # 24" clear in front
    sy = S.S_IN - 36                                                               # 52" x 36" shower
    sh.rect(b0, sy, b1, S.S_IN, EQ)
    sh.line((b0, sy + 1), (b1, sy + 1), EQ)                                        # door / curtain line
    sh.text("SHOWER", (b0 + b1) / 2, S.S_IN - 18, 3.5)
    sh.circle((b1 - 3, S.S_IN - 18), 2.0, EQ)
    sh.heads.append((b1, S.S_IN - 18, -1.0, 0.0))                                  # head on the plumbing wall


def laundry_side_by_side(sh):
    l0, l1 = S.face("pantry|laundry", +1), S.face("laundry|powder", -1)
    srow = S.face("south hall wall", +1)
    S.room_label(sh, "LAUNDRY", l0, srow, l1, S.S_IN, cx=l0 + 15, cy=545.0, h=4.5)
    y = 520.0
    for lbl in ("WASHER", "DRYER"):                                                # on the plumbing wall
        sh.rect(l1 - 30, y, l1, y + 27, EQ); sh.text(lbl, l1 - 15, y + 13.5, 3.0, rot=90); y += 27
    S.vanity(sh, l1 - 22, 577.0, l1, 602.0, "SINK", rot=90)
    sh.rect(l0, 495.0, l0 + 4, 515.0, EQ); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)


def laundry_stacked(sh):
    l0, l1 = S.face("pantry|laundry", +1), S.face("laundry|powder", -1)
    srow = S.face("south hall wall", +1)
    S.room_label(sh, "LAUNDRY", l0, srow, l1, S.S_IN, cy=520.0, h=4.5)
    sh.rect(l1 - 27, S.S_IN - 30, l1, S.S_IN, EQ)                                 # stacked W/D, back corner
    sh.text("W/D", l1 - 13.5, S.S_IN - 19, 3.0); sh.text("STACKED", l1 - 13.5, S.S_IN - 12, 2.2)
    S.vanity(sh, l1 - 22, S.S_IN - 57, l1, S.S_IN - 32, "SINK", rot=90)
    sh.rect(l0, 495.0, l0 + 4, 515.0, EQ); sh.text("PANEL", l0 + 12, 505.0, 2.5, rot=90)
    sh.rect(l1 - 16, srow + 34, l1, srow + 70, "A-FURN")                          # broom/storage cabinet
    sh.text("STORAGE", l1 - 8, srow + 52, 2.2, rot=90)


VARIANTS = {
    "side-by-side": (laundry_side_by_side, (763.0, 799.0)),
    "stacked": (laundry_stacked, (756.0, 780.0)),
}


def main():
    out = S.RENDERS / "experiments"
    for key, (laundry, window) in VARIANTS.items():
        S.WALLS, S.OPENINGS = copy.deepcopy(BASE_WALLS), copy.deepcopy(BASE_OPENINGS)
        walls_and_openings(S.WALLS, S.OPENINGS, window)
        S.utility_block = lambda sh, laundry=laundry: (bath(sh), laundry(sh))
        sh = S.build()
        sh.text(f"EXPERIMENT: POWDER ROOM -> FULL BATH ({key.upper()} LAUNDRY)", S.LOT_W / 2, S.LOT_D + 115, 10.0)
        sh.doc.saveas(S.ROOT / f"Accosting - owner schematic - EXPERIMENT powder bath {key}.dxf")
        S.render(sh.doc, out / f"powder-bath-{key}.png", 640, 440, 900, 640, width_in=10, dpi=140)
        sc = M.build_schematic()
        M.write_model(sc, out / f"powder-bath-{key}", sc.meta)
        print("built", key)
    S.WALLS, S.OPENINGS, S.utility_block = BASE_WALLS, BASE_OPENINGS, BASE_BLOCK


if __name__ == "__main__":
    main()
