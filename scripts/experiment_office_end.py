# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: end the bedroom hall at the office, to shorten it.

  - The west exterior door and its transom go; the hall stops at the guest|office wall, and the
    office door sits in that end wall, on axis with the hall.
  - The office takes the old hall strip past that wall (one deeper room); its closet moves to the
    south wall, against the primary bedroom.
  - The primary bedroom is entered through a small foyer carved from the west end of the walk-in
    closet: a pocket door from the hall, the closet opening on the left, the bedroom opening on
    the right.

Writes renders/experiments/office-end.png (with the current plan, office-end-current.png, to
compare). Not part of the regular build.

    uv run scripts/experiment_office_end.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
FOYER_WALL = 1009.5                       # wic|foyer centreline: 4'-0" clear foyer to the bedroom wall
WIC_OPEN = (469.0, 499.0)                 # 30" cased opening, foyer -> closet (hall-side end of the aisle)
ROOM_OPEN = (469.0, 505.0)                # 36" cased opening, foyer -> bedroom


def plan():
    ws, ops = S.WALLS, S.OPENINGS
    for i, w in enumerate(ws):
        if w[0] == "guest|office":                         # now runs across the hall: the hall's end wall
            ws[i] = (*w[:4], S.face("south hall wall", -1), w[5])
        elif w[0] == "bedroom hall wall":                  # stops at the office
            ws[i] = (*w[:4], 1062.0 + S.INT / 2, w[5])
    ws.append(("wic|foyer", "y", FOYER_WALL, 459.2, 534.95, S.INT))
    drop = {("west", 414.7), ("bedroom hall wall", 1067.0), ("south hall wall", 1070.0),
            ("suite|primary", 463.0)}
    ops[:] = [o for o in ops if (o[0], o[1]) not in drop]
    ops += [
        ("guest|office", 410.0, 446.0, "door", "b", +1),          # office, at the end of the hall
        ("south hall wall", FOYER_WALL + S.INT / 2 + 3.0, FOYER_WALL + S.INT / 2 + 39.0,
         "pocket", "a"),                                           # primary foyer, 36" pocket door
        ("wic|foyer", *WIC_OPEN, "cased"),
        ("suite|primary", *ROOM_OPEN, "cased"),
    ]


def wic(sh):
    x0, x1 = S.face("utility|bath", +1), S.face("wic|foyer", -1)
    y0, y1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hang(x0 + 24, x1 - 30, y0, +1)          # hall side stops short of the opening (landing)
    hang(x0 + 24, x1, y1, -1)
    for ya, yb in ((y0, y0 + 24), (y1 - 24, y1)):
        sh.rect(x0, ya, x0 + 24, yb, fu)
        sh.text("SHELVES", x0 + 12, (ya + yb) / 2, 2.2)
    sh.rect(x0, y0 + 24, x0 + 20, y1 - 24, fu)
    sh.text("DRAWERS", x0 + 10, (y0 + y1) / 2, 2.2, rot=90)
    S.room_label(sh, "WIC", x0, y0, x1, y1, cx=955.0, h=5.0)
    f0, f1 = S.face("wic|foyer", +1), S.face("suite|primary", -1)
    S.room_label(sh, "FOYER", f0, y0, f1, y1, cy=518.0, h=3.0)


def build():
    real_label = S.room_label

    def label(sh, name, x0, y0, x1, y1, **k):
        if name == "OFFICE":                               # office now runs to the south hall wall
            y1 = S.face("south hall wall", -1)
        real_label(sh, name, x0, y0, x1, y1, **k)

    S.room_label = label
    try:
        sh = S.build()
    finally:
        S.room_label = real_label
    # the office's old closet on the (removed) hall wall -> a closet on its south wall
    hall_n = 400.95
    box = (1100.0, hall_n - 25, S.W_IN + 1, hall_n + 1)
    for e in list(sh.msp):
        try:
            pts = ([tuple(p)[:2] for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else
                   [tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]] if e.dxftype() == "LINE" else
                   [tuple(e.dxf.align_point or e.dxf.insert)[:2]] if e.dxftype() == "TEXT" else None)
        except AttributeError:
            continue
        if pts and all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in pts):
            sh.msp.delete_entity(e)
    ys = S.face("south hall wall", -1)
    sh.rect(1104.0, ys - 24, S.W_IN, ys, "A-FURN")
    sh.line((1104.0, ys - 12), (S.W_IN, ys - 12), "A-FURN")
    sh.text("CL", (1104.0 + S.W_IN) / 2, ys - 18, 4.0)
    return sh


def render(png, sh):
    S.render(sh.doc, png, S.face("lounge|gym", -1) - 20, S.N - 40, S.W + 40, S.S + 40, width_in=14, dpi=200)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS), S.wic)
    render(OUT / "office-end-current.png", S.build())
    plan()
    S.wic = wic
    render(OUT / "office-end.png", build())
    S.WALLS, S.OPENINGS, S.wic = base


if __name__ == "__main__":
    main()
