# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: end the bedroom hall just past the primary bedroom door, to shorten it.

  - The west exterior door and its transom go; a new wall closes the hall just past the primary
    door, and the office door sits in it, on axis with the hall.
  - The office takes the last stretch of the hall as an alcove (desk); its closet moves to the
    short stretch of hall wall left beside the guest room.
  - The primary bedroom door and the walk-in closet stay as they are.

Writes renders/experiments/office-alcove.png. Not part of the regular build (the current plan for
comparison is renders/experiments/office-end-current.png).

    uv run scripts/experiment_office_alcove.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
END = 1110.5                              # hall end wall centreline: just past the primary door's jamb


def plan():
    ws, ops = S.WALLS, S.OPENINGS
    for i, w in enumerate(ws):
        if w[0] == "bedroom hall wall":                    # stops at the new end wall
            ws[i] = (*w[:4], END + S.INT / 2, w[5])
    ws.append(("hall end", "y", END, S.face("bedroom hall wall", -1), S.face("south hall wall", -1), S.INT))
    drop = {("west", 414.7), ("bedroom hall wall", 1067.0)}
    ops[:] = [o for o in ops if (o[0], o[1]) not in drop]
    ops.append(("hall end", 410.0, 446.0, "door", "a", +1))   # office, at the end of the hall


def build():
    sh = S.build()
    hall_n, hall_s = S.face("bedroom hall wall", -1), S.face("south hall wall", -1)
    box = (1100.0, hall_n - 25, S.W_IN + 1, hall_n + 1)        # the office's old closet on the hall wall
    for e in list(sh.msp):
        try:
            pts = ([tuple(p)[:2] for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else
                   [tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]] if e.dxftype() == "LINE" else
                   [tuple(e.dxf.align_point or e.dxf.insert)[:2]] if e.dxftype() == "TEXT" else None)
        except AttributeError:
            continue
        if pts and all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in pts):
            sh.msp.delete_entity(e)
    fu = "A-FURN"
    c0, c1 = S.face("guest|office", +1), END + S.INT / 2          # closet on the hall-wall stub
    sh.rect(c0, hall_n - 24, c1, hall_n, fu)
    sh.line((c0, hall_n - 12), (c1, hall_n - 12), fu)
    sh.text("CL", (c0 + c1) / 2, hall_n - 18, 4.0)
    m = sh.mark()
    d0 = c1 + 30                                                # desk along the alcove's south wall,
    sh.rect(d0, hall_s - 24, S.W_IN, hall_s, fu)                # clear of the door swing
    sh.text("DESK", (d0 + S.W_IN) / 2, hall_s - 12, 4.0)
    sh.movable_since(m)
    sh.text("ALCOVE", (c1 + S.W_IN) / 2, hall_n + 8, 3.5, "A-AREA-IDEN")
    return sh


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS))
    plan()
    S.render(build().doc, OUT / "office-alcove.png", S.face("lounge|gym", -1) - 20, S.N - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)
    S.WALLS, S.OPENINGS = base


if __name__ == "__main__":
    main()
