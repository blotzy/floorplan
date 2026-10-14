# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: an entry court in front of the porch, with and without a low wall.

  wall - paved court (~12' x 7') in front of the porch, edged on the street side by a
         24"-high seat wall (8" block) with a short return to the house; you walk in
         through a 3' opening on the driveway side, where the wall stays low for visibility.
  open - the same court with no wall: a low planting bed where the wall would be.

Writes renders/experiments/entry-court-{wall,open}-plan.png and a 3D model per variant
in renders/experiments/entry-court-{wall,open}/house.html.

    uv run scripts/experiment_entry_court.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

X0, Y0, X1 = S.E, 156.0, 504.0          # court: porch corner out to x 504, street edge at y 156
Y1 = S.N                                 # ...back to the house face
T, H = 8.0, 24.0                         # wall thickness and height
GAP = 36.0                               # opening on the driveway side
COURT = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
WALLS = [(X0 + GAP, Y0, X1, Y0 + T), (X1 - T, Y0 + T, X1, Y1)]     # street side + return
BED = (X0 + GAP, Y0 - 30, X1, Y0)                                   # 'open' variant planting


def plan(key: str, wall: bool):
    sh = S.build()
    sh.msp.add_lwpolyline(COURT, close=True, dxfattribs={"layer": "L-SITE"})
    sh.text("ENTRY COURT", (X0 + X1) / 2, (Y0 + Y1) / 2 + 8, 6.0, "A-AREA-IDEN")
    if wall:
        for b in WALLS:
            sh.rect(*b, "A-WALL")
        sh.text('24" SEAT WALL', (X0 + GAP + X1) / 2, Y0 - 10, 5.0)
        sh.text("IN", X0 + GAP / 2, Y0 - 10, 5.0)
    else:
        sh.rect(*BED, "L-PLNT")
        sh.text("LOW PLANTING", (BED[0] + BED[2]) / 2, (BED[1] + BED[3]) / 2, 5.0)
    out = S.RENDERS / "experiments" / f"entry-court-{key}-plan.png"
    S.render(sh.doc, out, 100, 40, 760, 360, width_in=12, dpi=130)


def model(key: str, wall: bool):
    sc = M.build_schematic()
    sc.polys["pavers"].append([[list(p) for p in COURT], 0.0, 2.0])
    if wall:
        for x0, y0, x1, y1 in WALLS:
            sc.boxes["concrete"].append([x0, y0, x1, y1, 0, H])
        sc.boxes["post"].append([X1 - 30, Y0 - 0.5, X1 - 12, Y0, 10, 16])     # lit house numbers
    else:
        sc.polys["lawn"].append([[[BED[0], BED[1]], [BED[2], BED[1]], [BED[2], BED[3]], [BED[0], BED[3]]], 0.0, 6.0])
    M.write_model(sc, S.RENDERS / "experiments" / f"entry-court-{key}", sc.meta)


def main():
    for key, wall in (("wall", True), ("open", False)):
        plan(key, wall)
        model(key, wall)


if __name__ == "__main__":
    main()
