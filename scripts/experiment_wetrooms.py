# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: wet rooms (72" x 48" two-person jetted tub + curbless shower
behind one glass panel) in the common bath and the primary bath.

Built on the owner schematic (scripts/schematic.py). The common bath is the
same in every variant; the primary bath has three versions:

  A  in place        - no walls move; single vanity
  B  borrow from WIC - bath/WIC wall moves 18" north; double vanity
  C  borrow from bed - bath/primary wall moves 30" west; double vanity

    uv run scripts/experiment_wetrooms.py

Writes "Accosting - owner schematic - EXPERIMENT wetroom X.dxf" and
renders/experiments/wetroom-X.png.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

TUB_L, TUB_W = 72.0, 48.0
BASE_WALLS, BASE_OPENINGS = copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS)
EQ = "A-EQPM"


# ---- symbols ----------------------------------------------------------------------
def wet_zone(sh, x0, y0, x1, y1):
    h = sh.msp.add_hatch(color=151, dxfattribs={"layer": "A-EQPM"})
    h.paths.add_polyline_path([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], is_closed=True)
    h.transparency = 0.75


def tub(sh, x0, y0, x1, y1):
    sh.rect(x0, y0, x1, y1, EQ)
    sh.rect(x0 + 4, y0 + 4, x1 - 4, y1 - 4, EQ)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rot = 90 if (y1 - y0) > (x1 - x0) else 0
    sh.text("72x48 JET TUB", cx, cy, 4.0, rot=rot)


def glass(sh, a, b):
    """Fixed glass panel from point a to point b (axis-aligned), drawn 1" thick."""
    (ax, ay), (bx, by) = a, b
    if ax == bx:
        sh.rect(ax - 0.5, min(ay, by), ax + 0.5, max(ay, by), "A-GLAZ")
    else:
        sh.rect(min(ax, bx), ay - 0.5, max(ax, bx), ay + 0.5, "A-GLAZ")


def drain(sh, a, b):
    sh.line(a, b, EQ)
    sh.circle(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 1.0, EQ)


def wc(sh, x0, y0, x1, y1):
    sh.rect(x0, y0, x1, y1, EQ); sh.text("WC", (x0 + x1) / 2, (y0 + y1) / 2, 3.0)


def vanity(sh, x0, y0, x1, y1, label, rot=0):
    sh.rect(x0, y0, x1, y1, EQ); sh.text(label, (x0 + x1) / 2, (y0 + y1) / 2, 3.0, rot=rot)


# ---- common bath (all variants) --------------------------------------------------
def common_wet(sh):
    c0, c1 = S.face("bed2|c.bath", +1), S.face("c.bath|bed3", -1)   # 73.5" clear
    hall = S.face("bedroom hall wall", -1)
    n = S.N_IN
    wet_y = n + TUB_W + 42.0                                          # tub + 42" shower zone
    wet_zone(sh, c0, n, c1, wet_y)
    tub(sh, c1 - TUB_L, n, c1, n + TUB_W)                             # fur the east end ~1.5"
    sh.text("CURBLESS SHOWER", (c0 + c1) / 2, n + TUB_W + 21, 3.5)
    glass(sh, (c0, wet_y), (c1 - 24, wet_y))                          # 24" walk-in gap, west side
    drain(sh, (c0 + 3, wet_y - 3), (c1 - 3, wet_y - 3))
    wc(sh, c0, wet_y + 2, c0 + 28, wet_y + 32)                        # 16.8" to glass, 23" to vanity
    vanity(sh, c0, hall - 21, c0 + 36, hall, "VAN 36")
    S.room_label(sh, "C. BATH", c0, n, c1, hall, cx=(c0 + 28 + c1) / 2 + 2, cy=wet_y + 20, h=4.5)
    # jetted-tub pump access from the gym side of the east wall
    a = S.face("bed2|c.bath", -1)
    sh.rect(a - 2, n + 8, a, n + 40, EQ)
    sh.text("TUB ACCESS", a - 7, n + 24, 3.0, rot=90)


# ---- primary bath variants -------------------------------------------------------
def primary_a(sh):
    """No walls move: tub N-S on the plumbing wall, shower beside it, WC + 47" vanity."""
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + TUB_W + 42.0
    wet_zone(sh, m0, top, gx, S.S_IN)
    tub(sh, m0, S.S_IN - TUB_L, m0 + TUB_W, S.S_IN)
    sh.text("CURBLESS", m0 + TUB_W + 21, 575.0, 3.5, rot=90)
    glass(sh, (gx, top + 30), (gx, S.S_IN))                           # walk in at the north end
    drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - 3))
    wc(sh, gx + 2.5, S.S_IN - 28, gx + 32.5, S.S_IN)
    vanity(sh, m1 - 21, top + 32, m1, S.S_IN, "VANITY 47", rot=90)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=gx + 21, cy=574.0, h=3.6)


def primary_b(sh):
    """Bath/WIC wall moves 18" north: tub E-W on the rear wall, shower in front."""
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + TUB_L + 6.0                                             # 6" tub deck clears the window
    wet_zone(sh, m0, top, gx, S.S_IN)
    tub(sh, m0, S.S_IN - TUB_W, m0 + TUB_L, S.S_IN)
    sh.text("CURBLESS SHOWER", (m0 + gx) / 2, (top + S.S_IN - TUB_W) / 2, 3.5)
    glass(sh, (gx, top + 30), (gx, S.S_IN))
    drain(sh, (m0 + 3, S.S_IN - TUB_W - 3), (gx - 3, S.S_IN - TUB_W - 3))
    vanity(sh, m1 - 61, S.S_IN - 22, m1 - 1, S.S_IN, "DOUBLE VANITY 60")
    wc(sh, m1 - 28, 545.0, m1, 575.0)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + m1 - 28) / 2, cy=562.0, h=4.0)


def primary_c(sh):
    """Bath/primary wall moves 30" west: layout A plus a double vanity."""
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + TUB_W + 42.0
    wet_zone(sh, m0, top, gx, S.S_IN)
    tub(sh, m0, S.S_IN - TUB_L, m0 + TUB_W, S.S_IN)
    sh.text("CURBLESS", m0 + TUB_W + 21, 575.0, 3.5, rot=90)
    glass(sh, (gx, top + 30), (gx, S.S_IN))
    drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - 3))
    wc(sh, gx + 2.25, S.S_IN - 28, gx + 32.25, S.S_IN)                # 17.25" to glass, 15.25" to vanity
    vanity(sh, m1 - 60, S.S_IN - 22, m1, S.S_IN, "DOUBLE VANITY 60")
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + m1) / 2, cy=576.0, h=4.5)


# ---- variants ----------------------------------------------------------------------
def set_wall(walls, name, **kw):
    keys = ("name", "axis", "c", "a", "b", "t")
    for i, w in enumerate(walls):
        if w[0] == name:
            d = dict(zip(keys, w)); d.update(kw)
            walls[i] = tuple(d[k] for k in keys)
            return
    raise KeyError(name)


def set_opening(openings, wall, old_from, new_from, new_to, *rest):
    for i, o in enumerate(openings):
        if o[0] == wall and o[1] == old_from:
            openings[i] = (wall, new_from, new_to, *(rest or o[3:]))
            return
    raise KeyError((wall, old_from))


def variant_a(walls, openings):
    return "A - in place, no walls move; single 47\" vanity", primary_a


def variant_b(walls, openings):
    set_wall(walls, "bath|wic", c=531.2 - 18)
    set_opening(openings, "bath|wic", 993.5, 966.0, 996.0, "door", "b", +1)
    return "B - bath/WIC wall 18\" north (WIC 4'-2\" deep); double vanity", primary_b


def variant_c(walls, openings):
    set_wall(walls, "suite|primary", c=1032.0 + 30)
    set_wall(walls, "bath|wic", b=1062.0)
    set_opening(openings, "south", 1064.0, 1083.6, 1191.6)            # bedroom window recentred
    set_opening(openings, "south hall wall", 1040.5, 1070.0, 1106.0)  # bedroom door
    return "C - bath/primary wall 30\" west (bedroom 12'-3\" wide); double vanity", primary_c


def main():
    out_dir = S.RENDERS / "experiments"
    for key, fn in (("A", variant_a), ("B", variant_b), ("C", variant_c)):
        S.WALLS, S.OPENINGS = copy.deepcopy(BASE_WALLS), copy.deepcopy(BASE_OPENINGS)
        title, prim = fn(S.WALLS, S.OPENINGS)
        S.common_bath, S.primary_bath = common_wet, prim
        sh = S.build()
        sh.text(f"EXPERIMENT: WET ROOMS {title}", S.LOT_W / 2, S.LOT_D + 115, 12.0)
        sh.text(f"WET ROOMS {title}", (700 + S.W) / 2, S.S + 22, 9.0)
        dxf = S.ROOT / f"Accosting - owner schematic - EXPERIMENT wetroom {key}.dxf"
        sh.doc.saveas(dxf)
        print("wrote", dxf.name)
        S.render(sh.doc, out_dir / f"wetroom-{key}.png", 690, S.N - 45, S.W + 20, S.S + 35,
                 width_in=20, dpi=120)


if __name__ == "__main__":
    main()
