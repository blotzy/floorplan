# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: primary bath / walk-in closet arrangements for a jetted tub
that wants open sides (3-side apron "back to wall", or fully freestanding).

Built on the owner schematic (scripts/schematic.py):

  split        - the suite is split east/west instead of north/south: bath
                 8'-6" x 12'-7" on the plumbing side, walk-in closet 6'-4" x
                 12'-7" on the bedroom side. 72" x 48" 3-side-apron tub with
                 its back on the plumbing wall and its foot on the rear wall;
                 its head-end apron faces the DRY part of the bath, so the
                 pump access panel is dry. Shower beside the tub, behind glass.
  freestanding - current layout with a ~62" x 44" freestanding jetted tub
                 standing free in the wet zone (gaps all round are normal).

    uv run scripts/experiment_suite.py

Writes "Accosting - owner schematic - EXPERIMENT suite X.dxf" and
renders/experiments/suite-X.png.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

BASE_WALLS, BASE_OPENINGS = copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS)
BASE_PRIMARY, BASE_WIC = S.primary_bath, S.wic
EQ = "A-EQPM"


def head_x(sh, x, y, d):
    """Shower head on a wall face at x, spraying in x-direction d."""
    sh.circle((x + d * 2.5, y), 2.5, EQ)
    for dy in (-5.0, 0.0, 5.0):
        sh.line((x + d * 5.5, y + dy * 0.4), (x + d * 11.0, y + dy), EQ)


# ---- split: bath on the plumbing side, closet on the bedroom side ---------------------
SPLIT_X = 981.5                          # bath | closet partition centreline


def split_walls(walls, openings):
    walls[:] = [w for w in walls if w[0] != "bath|wic"]
    walls.append(("bath|wic", "y", SPLIT_X, 457.0, S.S_IN, S.INT))
    openings[:] = [o for o in openings
                   if not (o[0] == "bath|wic") and not (o[0] == "south" and o[1] == 972.5)]
    openings.append(("bath|wic", 468.0, 498.0, "door", "a", -1))     # bath door from the closet


def split_bath(sh):
    m0, m1 = S.face("utility|bath", +1), S.face("bath|wic", -1)        # 102" wide
    top = S.face("south hall wall", +1)
    ty = S.S_IN - S.TUB_L                                              # tub head end
    tx = m0 + S.TUB_W
    S.wet_zone(sh, tx, ty, m1, S.S_IN)                                 # shower beside the tub
    S.tub(sh, m0, ty, tx, S.S_IN)
    S.glass(sh, (tx, ty), (m1 - 29, ty))                               # 29" walk-in gap by the closet wall
    S.drain(sh, (m1 - 3, ty + 3), (m1 - 3, S.S_IN - 3))                # floor slopes away from the tub
    S.shower_head(sh, (tx + m1) / 2, S.S_IN, -1)                       # rear wall
    head_x(sh, m1, (ty + S.S_IN) / 2 + 8, -1)                          # closet wall
    sh.text("CURBLESS SHOWER", (tx + m1) / 2, ty + 20, 3.0)
    # Pump access in the tub's head-end apron, facing the dry bath.
    sh.rect(m0 + 26, ty - 2, m0 + 46, ty, EQ)
    sh.text("TUB ACCESS (DRY SIDE)", m0 + 30, ty - 6, 2.5)
    S.vanity(sh, m0 + 8, top, m0 + 68, top + 22, "DOUBLE VANITY 60")  # on the hall wall
    S.wc(sh, m0, 497.0, m0 + 28, 527.0)                                # plumbing wall
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(m0 + 28 + m1) / 2 + 4, cy=512.0, h=4.0)


def split_wic(sh):
    w0, w1 = S.face("bath|wic", +1), S.face("suite|primary", -1)       # 76" wide
    top = S.face("south hall wall", +1)
    for x0 in (w0, w1 - 24):                                           # hanging both sides
        sh.rect(x0, 502.0, x0 + 24, S.S_IN, "A-FURN")
        sh.line((x0 + 12, 502.0), (x0 + 12, S.S_IN), "A-FURN")
    S.room_label(sh, "WIC", w0, top, w1, S.S_IN, cy=560.0, h=4.0)


# ---- freestanding tub in the current layout --------------------------------------------
def freestanding_bath(sh):
    L, Wd = 61.8, 43.7
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + 4 + Wd + 4 + 38.0                                        # 4" gaps, 38" shower zone
    S.wet_zone(sh, m0, top, gx, S.S_IN)
    y0 = (top + S.S_IN - L) / 2
    S.tub(sh, m0 + 4, y0, m0 + 4 + Wd, y0 + L, "62x44 FREESTANDING")
    S.glass(sh, (gx, top + 30), (gx, S.S_IN))
    S.drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - 3))
    sx = m0 + 4 + Wd + 4 + 19
    S.shower_head(sh, sx, top, +1)
    S.shower_head(sh, sx, S.S_IN, -1)
    S.wc(sh, gx + 2.25, S.S_IN - 28, gx + 32.25, S.S_IN)
    S.vanity(sh, m1 - 60, S.S_IN - 22, m1, S.S_IN, "DOUBLE VANITY 60")
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + m1) / 2 + 8, cy=577.0, h=4.0)


VARIANTS = {
    "split": ("SPLIT - bath 8'-6\" on the plumbing side, WIC 6'-4\" on the bedroom side; "
              "tub head end faces the dry bath", split_walls, split_bath, split_wic),
    "freestanding": ("CURRENT LAYOUT + ~62x44 FREESTANDING TUB in the wet zone",
                     None, freestanding_bath, BASE_WIC),
}


def main():
    out_dir = S.RENDERS / "experiments"
    for key, (title, walls_fn, bath_fn, wic_fn) in VARIANTS.items():
        S.WALLS, S.OPENINGS = copy.deepcopy(BASE_WALLS), copy.deepcopy(BASE_OPENINGS)
        if walls_fn:
            walls_fn(S.WALLS, S.OPENINGS)
        S.primary_bath, S.wic = bath_fn, wic_fn
        sh = S.build()
        sh.text(f"EXPERIMENT: {title}", S.LOT_W / 2, S.LOT_D + 115, 10.0)
        sh.text(title, 1000.0, S.S + 22, 6.0)
        dxf = S.ROOT / f"Accosting - owner schematic - EXPERIMENT suite {key}.dxf"
        sh.doc.saveas(dxf)
        print("wrote", dxf.name)
        S.render(sh.doc, out_dir / f"suite-{key}.png", 780, 440, S.W + 20, S.S + 35, width_in=16, dpi=130)
    S.primary_bath, S.wic = BASE_PRIMARY, BASE_WIC


if __name__ == "__main__":
    main()
