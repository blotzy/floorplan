# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: rearrange the laundry / powder block (between the pantry-mech wall and the
primary-bath wall) so the powder room becomes a full bath with a shower and a window on the
rear wall. The pantry, mech closet, walk-in closet and primary bath are untouched.

  long  bath and laundry side by side, both full depth, both off the hall.
        bath    ~4'-4" x 8'-9": sink, toilet, then a curbless shower across the end; all
                fixtures on the wall shared with the primary bath. No window (exhaust fan).
        storage ~4'-4" x 3'-6" behind the bath, open to the back of the laundry.
        laundry ~5' galley: sink, washer, dryer on the wall shared with the bath; the panel
                near the door (its clear space opposite open floor). The mech closet has no
                door: a wide open (cased) opening onto the galley, so the water heater
                breathes the laundry's air and nothing swings into the aisle.
  back  laundry in front, bath behind, a 3'-6" passage from the hall down the pantry side.
        passage panel, mech closet bifold and attic hatch; bath door at its end.
        laundry ~6' x 5'-4" off the hall: sink, washer, dryer on the wall shared with the bath.
        bath    ~6' x 6'-8": shower in the back corner under a new rear window, toilet beside
                it, vanity on the primary-bath wall.

  pantry  bath across the whole hall frontage (~9'-10" x 6'-3"): shower running east-west
          along the hall wall at the primary-bath end, toilet on the primary-bath wall, vanity
          on the back wall, door at the pantry end. The laundry sits behind it and has no hall
          door: you go through the pantry (a door replaces its back shelf) into the mech
          closet and on through its open side into the laundry. Panel on the laundry side of
          the bath wall; sink, washer, dryer on the rear wall.

Writes renders/experiments/utility-{long,back,pantry}.png (+ DXF) and a 3D model per variant.

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


def drop(ws, *names):
    ws[:] = [w for w in ws if w[0] not in names]


def set_hall_doors(ops, doors):
    """Replace the laundry and powder doors on the hall wall."""
    ops[:] = [o for o in ops if not (o[0] == "south hall wall" and o[1] in (760.0, 838.0))] + doors


def head_x(sh, x, y, d):
    """Shower head on a wall running in y, spraying in x-direction d."""
    sh.heads.append((x, y, float(d), 0.0))
    sh.circle((x + d * 2.5, y), 2.5, EQ)
    for dy in (-5.0, 0.0, 5.0):
        sh.line((x + d * 5.5, y + dy * 0.4), (x + d * 11.0, y + dy), EQ)


def machines_y(sh, x_wall, y0, d):
    """Sink, washer, dryer along a wall running in y (front facing x-direction d), from y0."""
    y = y0
    for w, lbl, deep in ((14, "SINK", 15), (27, "WASHER", 30), (27, "DRYER", 30)):
        x0, x1 = sorted((x_wall, x_wall + d * deep))
        sh.rect(x0, y, x1, y + w, EQ); sh.text(lbl, (x0 + x1) / 2, y + w / 2, 2.6, rot=90); y += w + 1
    return y


def machines_x(sh, x0, y_wall, d):
    """Sink, washer, dryer along a wall running in x (front facing y-direction d), from x0."""
    x = x0
    for w, lbl, deep in ((14, "SINK", 15), (27, "WASHER", 30), (27, "DRYER", 30)):
        y0, y1 = sorted((y_wall, y_wall + d * deep))
        sh.rect(x, y0, x + w, y1, EQ); sh.text(lbl, x + w / 2, (y0 + y1) / 2, 2.6, rot=90 if w < 20 else 0); x += w + 1
    return x


# ---- long: bath and laundry side by side ------------------------------------------------
LONG_BATH_W = 52.0
LONG_SPLIT = B1 - LONG_BATH_W - S.WET / 2
LONG_BATH_END = 566.0            # bath stops here; storage room behind it, open to the laundry


def long_plan(ws, ops):
    drop(ws, "powder|alcove")
    for i, w in enumerate(ws):
        if w[0] == "laundry|powder":
            ws[i] = ("laundry|bath", "y", LONG_SPLIT, 457.0, S.S_IN, S.WET)
    ws.append(("bath|storage", "x", LONG_BATH_END + S.INT / 2, LONG_SPLIT, 874.0, S.INT))
    set_hall_doors(ops, [("south hall wall", 760.0, 790.0, "door", "a", +1),     # laundry
                         ("south hall wall", 820.0, 848.0, "door", "a", +1)])    # bath, against its east wall
    ops.append(("laundry|bath", 574.0, 606.0, "cased"))                          # storage, open to the laundry
    m0 = S.face("pantry|mech", +1)                                               # mech closet: no door,
    ops[:] = [o for o in ops if o[:2] != ("pantry|laundry", 579.2)]              # a wide open (cased)
    ops.append(("pantry|laundry", m0 + 3, S.S_IN - 3, "cased"))                  # opening to the laundry


def long_fit(sh):
    lw = LONG_SPLIT - S.WET / 2                              # laundry side of the split
    b0 = LONG_SPLIT + S.WET / 2
    # bath: everything on the primary-bath wall, shower across the end
    S.vanity(sh, B1 - 20, 466.0, B1, 490.0, "SINK", rot=90)
    S.wc(sh, B1 - 28, 497.0, B1, 527.0)
    gy, ge = 530.0, LONG_BATH_END                            # shower: full width x 36" deep
    S.wet_zone(sh, b0, gy, B1, ge)
    sh.rect(b0, gy, B1, ge, EQ)
    S.glass(sh, (b0 + 24, gy), (B1, gy))                     # 24" open entry on the door side
    sh.text("SHOWER", (b0 + B1) / 2, gy + 14, 3.2)
    head_x(sh, B1, gy + 20, -1)
    S.drain(sh, (b0 + 3, ge - 3), (B1 - 3, ge - 3))
    S.room_label(sh, "BATH", b0, HALL, B1, ge, cx=b0 + 14, cy=505.0, h=3.6)
    # storage room behind the bath, open to the laundry
    s0 = LONG_BATH_END + S.INT
    sh.rect(B1 - 12, s0, B1, S.S_IN, FU); sh.text("SHELVES", B1 - 6, (s0 + S.S_IN) / 2, 2.2, rot=90)
    S.room_label(sh, "STORAGE", b0, s0, B1, S.S_IN, cx=(b0 + B1 - 12) / 2, h=3.4)
    # laundry galley: machines on the bath wall, panel near the door across open floor
    machines_y(sh, lw, 500.0, -1)
    sh.rect(lw - 30, 515.0, lw, 570.0, FU)                    # folding counter over the washer/dryer
    sh.text("COUNTER OVER", lw - 34, 542.0, 2.2, rot=90)
    sh.rect(L0, 466.0, L0 + 4, 486.0, EQ); sh.text("PANEL", L0 + 10, 476.0, 2.5, rot=90)
    S.room_label(sh, "LAUNDRY", L0, HALL, lw, S.S_IN, cx=(L0 + lw) / 2 - 8, cy=595.0, h=4.0)


# ---- back: laundry in front, bath behind, passage down the pantry side ---------------------
PASSAGE = 42.0
PASS_X = L0 + PASSAGE + S.INT / 2            # passage | laundry+bath wall
LAUNDRY_D = 64.0
BACK_Y = HALL + LAUNDRY_D + S.WET / 2        # laundry | bath wall


def back_plan(ws, ops):
    drop(ws, "powder|alcove", "laundry|powder")
    ws.append(("passage", "y", PASS_X, 457.0, S.S_IN, S.INT))
    ws.append(("laundry|bath", "x", BACK_Y, PASS_X - S.INT / 2, 874.0, S.WET))
    set_hall_doors(ops, [("south hall wall", 760.0, 790.0, "door", "a", +1),     # passage
                         ("south hall wall", 836.0, 866.0, "door", "b", +1),     # laundry
                         ("passage", BACK_Y + 6, BACK_Y + 34, "door", "b", +1)])  # bath, at the passage end
    ops.append(("south", 838.0, 866.0, "window"))                                 # over the shower


def back_fit(sh):
    p1 = PASS_X + S.INT / 2
    by = BACK_Y + S.WET / 2
    # laundry: machines on the bath wall
    machines_x(sh, p1 + 2, BACK_Y - S.WET / 2, -1)
    S.room_label(sh, "LAUNDRY", p1, HALL, B1, BACK_Y - S.WET / 2, cx=(p1 + B1) / 2 + 10, cy=HALL + 14, h=3.6)
    # bath: shower in the back corner on the primary side, toilet beside it, vanity on the primary wall
    sx0 = B1 - 36
    S.wet_zone(sh, sx0, S.S_IN - 36, B1, S.S_IN)
    sh.rect(sx0, S.S_IN - 36, B1, S.S_IN, EQ)
    S.glass(sh, (sx0, S.S_IN - 36), (sx0, S.S_IN))
    S.glass(sh, (sx0, S.S_IN - 36), (sx0 + 12, S.S_IN - 36))
    sh.text("SHOWER", (sx0 + B1) / 2, S.S_IN - 18, 3.0)
    head_x(sh, B1, S.S_IN - 18, -1)
    tx = sx0 - 16
    S.wc(sh, tx - 15, S.S_IN - 28, tx + 15, S.S_IN)
    S.vanity(sh, B1 - 21, by + 3, B1, by + 33, "VANITY", rot=90)
    S.room_label(sh, "BATH", p1, by, B1, S.S_IN, cx=(p1 + sx0) / 2 + 4, cy=by + 22, h=3.6)
    # passage: panel, mech bifold (already on the pantry/mech wall), attic hatch
    sh.rect(L0, 495.0, L0 + 4, 515.0, EQ); sh.text("PANEL", L0 + 10, 505.0, 2.5, rot=90)
    hx = L0 + 12                                          # attic hatch past the door swing; the
    sh.rect(hx, 500.0, hx + 22.5, 554.0, FU)              # ladder lands toward the mech closet
    sh.text("ATTIC HATCH", hx + 11.25, 527.0, 2.2, rot=90)
    sh.text("PASSAGE", (L0 + PASS_X) / 2, 590.0, 3.0, rot=90)


# ---- pantry: bath across the hall frontage, laundry behind it, reached through pantry + mech --
PB_D = 75.0                                  # bath depth from the hall wall
PB_Y = HALL + PB_D + S.WET / 2               # bath | laundry wall
PANTRY_DOOR = (700.0, 728.0)                 # pantry back wall -> mech closet


def pantry_plan(ws, ops):
    drop(ws, "powder|alcove", "laundry|powder")
    ws.append(("bath|laundry", "x", PB_Y, 750.0, 874.0, S.WET))
    set_hall_doors(ops, [("south hall wall", 760.0, 790.0, "door", "a", +1)])    # bath (the only hall door)
    ops.append(("pantry|mech", *PANTRY_DOOR, "door", "a", +1))                    # pantry -> mech
    m0 = S.face("pantry|mech", +1)                                               # mech open to the laundry
    ops[:] = [o for o in ops if o[:2] != ("pantry|laundry", 579.2)]
    ops.append(("pantry|laundry", m0 + 3, S.S_IN - 3, "cased"))


def pantry_fit(sh):
    b0 = L0
    back = PB_Y - S.WET / 2
    # bath: shower along the hall wall (east-west) at the primary-bath end
    sx0, sy1 = B1 - 60, HALL + 36
    S.wet_zone(sh, sx0, HALL, B1, sy1)
    sh.rect(sx0, HALL, B1, sy1, EQ)
    S.glass(sh, (sx0 + 24, sy1), (B1, sy1))                  # 24" open entry at the door end
    S.glass(sh, (sx0, HALL), (sx0, HALL + 6))                # short return at the open end
    sh.text("SHOWER", (sx0 + B1) / 2, HALL + 18, 3.2)
    head_x(sh, B1, HALL + 18, -1)
    S.drain(sh, (sx0 + 3, sy1 - 3), (B1 - 3, sy1 - 3))
    S.wc(sh, B1 - 28, sy1 + 6, B1, sy1 + 36)                 # toilet on the primary-bath wall
    S.vanity(sh, 776.0, back - 21, 812.0, back, "VANITY 36")
    S.room_label(sh, "BATH", b0, HALL, B1, back, cx=(b0 + sx0) / 2 + 2, cy=HALL + 14, h=3.6)
    # laundry behind the bath: machines on the back wall, panel on the bath wall
    l0y = PB_Y + S.WET / 2
    x = machines_x(sh, 800.0, S.S_IN, -1)
    sh.rect(815.0, S.S_IN - 30, x, S.S_IN, FU)
    sh.text("COUNTER OVER", (815.0 + x) / 2, S.S_IN - 34, 2.2)
    sh.rect(760.0, l0y, 780.0, l0y + 4, EQ); sh.text("PANEL", 770.0, l0y + 9, 2.5)
    S.room_label(sh, "LAUNDRY", L0, l0y, B1, S.S_IN, cx=790.0, cy=l0y + 22, h=3.6)


def pantry_build_fix(sh):
    """The pantry's back shelf gives way to the door into the mech closet."""
    p0, p1, pm = S.face("kitchen|pantry", +1), S.face("pantry|laundry", -1), S.face("pantry|mech", -1)
    target = (p0 + 16, pm - 16, p1 - 16, pm)
    for e in list(sh.msp.query("LWPOLYLINE")):
        xs, ys = zip(*[(q[0], q[1]) for q in e.get_points("xy")])
        if all(abs(a - b) < 0.01 for a, b in zip((min(xs), min(ys), max(xs), max(ys)), target)):
            sh.msp.delete_entity(e)


VARIANTS = {"long": (long_plan, long_fit, "BATH AND LAUNDRY SIDE BY SIDE, FULL DEPTH"),
            "back": (back_plan, back_fit, "LAUNDRY IN FRONT, BATH BEHIND, PASSAGE"),
            "pantry": (pantry_plan, pantry_fit, "BATH ALONG THE HALL, LAUNDRY BEHIND VIA PANTRY AND MECH")}
FIXES = {"pantry": pantry_build_fix}


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
        S.render(sh.doc, out / f"utility-{key}.png", 660, 440, 1080, 640, width_in=12, dpi=130)
        sc = M.build_schematic()
        M.write_model(sc, out / f"utility-{key}", sc.meta)
    S.WALLS, S.OPENINGS, S.utility_block = BASE
    S.build = BUILD


if __name__ == "__main__":
    main()
