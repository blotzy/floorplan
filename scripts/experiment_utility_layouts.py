# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the main plan's common bath + laundry block with the mech closet and the storage
room behind the bath swapped.

  swap  water heater, softener and filters behind the bath (open to the laundry); the washer and
        dryer side by side in the main plan's mech-closet spot against the kitchen-side wall,
        open to the laundry; the galley becomes a laundry room with counter, sink, panel and a
        network cabinet in the front corner across from the panel, and a shallow
        full-height cabinet on the rear wall between the two side openings. (The heat pump's
        outdoor unit would move off that rear wall if the dryer vents there.)

Writes renders/experiments/utility-swap.png (+ DXF) and a 3D model.

    uv run scripts/experiment_utility_layouts.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS), S.utility_block)
BUILD = S.build
EQ, FU = "A-EQPM", "A-FURN"
L0 = 752.25                      # laundry side of the pantry/mech wall
B1 = 870.75                      # bath side of the primary-bath wall
HALL = 461.45                    # inside face of the hall wall


def head_x(sh, x, y, d):
    """Shower head on a wall running in y, spraying in x-direction d."""
    sh.heads.append((x, y, float(d), 0.0))
    sh.circle((x + d * 2.5, y), 2.5, EQ)
    for dy in (-5.0, 0.0, 5.0):
        sh.line((x + d * 5.5, y + dy * 0.4), (x + d * 11.0, y + dy), EQ)


BATH_W = 52.0
SPLIT = B1 - BATH_W - S.WET / 2
BATH_END = 566.0            # bath stops here; storage room behind it, open to the laundry


def swap_plan(ws, ops):
    """The washer/dryer alcove (the main plan's mech closet) is wide open to the laundry."""
    m0 = S.face("pantry|mech", +1)
    ops[:] = [o for o in ops if not (o[0] == "pantry|laundry" and o[3] == "bifold")]
    ops.append(("pantry|laundry", m0 + 3, S.S_IN - 3, "cased"))


# ---- swap: mech moves behind the bath, washer/dryer into the mech closet's spot ----------
def swap_fit(sh):
    lw = SPLIT - S.WET / 2
    b0 = SPLIT + S.WET / 2
    # bath: as in the main plan
    S.vanity(sh, B1 - 20, 466.0, B1, 490.0, "SINK", rot=90)
    S.wc(sh, B1 - 28, 497.0, B1, 527.0)
    gy, ge = 530.0, BATH_END
    S.wet_zone(sh, b0, gy, B1, ge)
    sh.rect(b0, gy, B1, ge, EQ)
    S.glass(sh, (b0 + 24, gy), (B1, gy))
    sh.text("SHOWER", (b0 + B1) / 2, gy + 14, 3.2)
    head_x(sh, B1, gy + 20, -1)
    S.drain(sh, (b0 + 3, ge - 3), (B1 - 3, ge - 3))
    S.room_label(sh, "COMMON BATH", b0, HALL, B1, ge, cx=b0 + 12, cy=505.0, h=2.4)
    # mech behind the bath, open to the laundry: water heater, softener + brine, wall-hung filters
    s0 = BATH_END + S.INT
    sh.circle((B1 - 13, S.S_IN - 13), 12.0, EQ); sh.text("HPWH", B1 - 13, S.S_IN - 13, 3.0)
    sh.circle((b0 + 18, S.S_IN - 9), 8.0, EQ); sh.text("SOFT", b0 + 18, S.S_IN - 9, 2.2)
    sh.circle((b0 + 9, s0 + 9), 7.0, EQ); sh.text("BRINE", b0 + 9, s0 + 9, 2.0)
    sh.rect(b0 + 20, s0, B1 - 2, s0 + 6, EQ)                 # filters, RO, manifold on the wall
    sh.text("FILTERS / RO ON WALL", (b0 + 20 + B1) / 2, s0 + 10, 1.8)
    S.room_label(sh, "MECH", b0, s0, B1, S.S_IN, cx=b0 + 26, cy=s0 + 23, h=3.0)
    # laundry room: counter + sink along the bath wall, panel and network rack on the pantry wall
    sh.rect(lw - 24, 495.0, lw, 568.0, FU)
    S.vanity(sh, lw - 22, 520.0, lw, 545.0, "SINK", rot=90)
    sh.text("COUNTER + UPPERS", lw - 12, 506.0, 1.8, rot=90)
    sh.rect(L0, 466.0, L0 + 4, 486.0, EQ); sh.text("PANEL", L0 + 10, 476.0, 2.5, rot=90)
    sh.rect(lw - 20, HALL, lw, HALL + 30, EQ)                 # network cabinet in the front corner across
    sh.text("NETWORK RACK", lw - 10, HALL + 15, 2.0, rot=90)  # from the panel, past the door swing
    sh.rect(L0 + 12, S.S_IN - 12, lw - 12, S.S_IN, FU)       # rear wall: 12"-deep floor-to-ceiling cabinet
    sh.text("TALL CABINET", (L0 + lw) / 2, S.S_IN - 6, 2.2)          # brooms, vacuum, ironing, supplies
    S.room_label(sh, "LAUNDRY", L0, HALL, lw, S.S_IN, cx=(L0 + lw) / 2 + 2, cy=595.0, h=3.6)


def swap_build_fix(sh):
    """Clear the old mech closet's equipment and label; put the washer and dryer there, side by
    side against the kitchen-side wall, facing the laundry."""
    x0, x1 = S.face("kitchen|pantry", +1), S.face("pantry|laundry", -1)
    y0, y1 = S.face("pantry|mech", +1), S.S_IN
    keep = {"A-WALL", "A-DOOR", "A-GLAZ"}
    for e in list(sh.msp):
        if e.dxf.layer in keep or e.dxftype() not in ("LWPOLYLINE", "CIRCLE", "TEXT", "LINE"):
            continue
        if e.dxftype() == "CIRCLE":
            pts = [(e.dxf.center.x, e.dxf.center.y)]
        elif e.dxftype() == "TEXT":
            pt = e.dxf.align_point if e.dxf.hasattr("align_point") else e.dxf.insert
            pts = [(pt.x, pt.y)]
        elif e.dxftype() == "LINE":
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
        else:
            pts = [(q[0], q[1]) for q in e.get_points("xy")]
        if all(x0 - 0.5 <= x <= x1 + 0.5 and y0 - 0.5 <= y <= y1 + 0.5 for x, y in pts):
            sh.msp.delete_entity(e)
    y = y0 + 0.5
    for lbl in ("WASHER", "DRYER"):
        sh.rect(x0, y, x0 + 30, y + 27, EQ); sh.text(lbl, x0 + 15, y + 13.5, 3.0); y += 27
    sh.text("W/D ALCOVE", (x0 + 30 + x1) / 2, (y0 + y1) / 2, 3.2, "A-AREA-IDEN")


VARIANTS = {"swap": (swap_plan, swap_fit, "MECH BEHIND THE BATH, WASHER/DRYER IN THE MECH CLOSET'S SPOT")}
FIXES = {"swap": swap_build_fix}


def main():
    out = S.RENDERS / "experiments"
    for key, (plan, fit, title) in VARIANTS.items():
        S.WALLS, S.OPENINGS = copy.deepcopy(BASE[0]), copy.deepcopy(BASE[1])
        plan(S.WALLS, S.OPENINGS)
        S.utility_block = fit
        fix = FIXES.get(key)
        S.build = (lambda f=fix: (lambda sh: (f(sh), sh)[1])(BUILD())) if fix else BUILD
        sh = S.build()
        sh.text(f"EXPERIMENT: {title}", S.LOT_W / 2, S.LOT_D + 115, 10.0)
        sh.doc.saveas(S.ROOT / f"Accosting - owner schematic - EXPERIMENT utility {key}.dxf")
        S.render(sh.doc, out / f"utility-{key}.png", 660, 440, 1080, 640, width_in=12, dpi=260)
        sc = M.build_schematic()
        M.write_model(sc, out / f"utility-{key}", sc.meta)
    S.WALLS, S.OPENINGS, S.utility_block = BASE
    S.build = BUILD


if __name__ == "__main__":
    main()
