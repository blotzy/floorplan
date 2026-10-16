# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: swap the common bath and the laundry, so the bath sits next to the pantry (closer to the
lounge) and the laundry backs onto the walk-in closet, with a laundry pass-through in the closet wall.

  - One plumbing wall still serves both rooms (now the wall between the bath and the laundry).
  - Bath door at its east end, next to the pantry, opening flat against the bath's blank east wall; the
    sink is what you see from the lounge, the toilet sits farther in.
  - Laundry door at its west end, opening flat against the closet wall; the pass-through just past it.
  - The mechanical closet's louvered bifold now opens into the storage room behind the bath, which is
    open to the laundry, so the heat pump water heater still draws on the laundry's air.
  - The subpanel moves to the laundry's closet / primary-bath wall, past the pass-through.

Writes renders/experiments/laundry-swap.png (with the current plan, laundry-current.png, to compare).
Not part of the regular build.

    uv run scripts/experiment_laundry_swap.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
SPLIT = S.face("pantry|laundry", +1) + 52.0 + S.WET / 2      # the shared plumbing wall, 52" clear bath


def swap_plan():
    ws, ops = S.WALLS, S.OPENINGS
    for i, w in enumerate(ws):
        if w[0] == "laundry|bath":
            ws[i] = (w[0], w[1], SPLIT, *w[3:])
        elif w[0] == "bath|storage":
            ws[i] = (w[0], w[1], w[2], 750.0, SPLIT, w[5])
    bath0 = S.face("pantry|laundry", +1)
    laun0, laun1 = SPLIT + S.WET / 2, S.face("utility|bath", -1)
    for i, o in enumerate(ops):
        if o[0] == "south hall wall" and o[1] == 760.0:              # laundry door -> bath door
            ops[i] = ("south hall wall", bath0 + 1.5, bath0 + 31.5, "door", "a", +1)
        elif o[0] == "south hall wall" and o[1] == 849.75:           # bath door -> laundry door
            ops[i] = ("south hall wall", laun1 - 31.5, laun1 - 1.5, "door", "b", +1)
        elif o[0] == "south" and o[1] == 766.5:                      # laundry high window, re-centred
            c = (laun0 + laun1) / 2
            ops[i] = ("south", c - 21.0, c + 21.0, *o[3:])
        elif o[0] == "laundry|bath" and o[3] == "cased":
            pass                                                     # storage still opens to the laundry
    return bath0, laun0, laun1


def swap_block(sh):
    eq, fu = "A-EQPM", "A-FURN"
    hall = S.face("south hall wall", +1)
    b0, b1 = S.face("pantry|laundry", +1), S.face("laundry|bath", -1)        # bath, east of the wet wall
    l0, l1 = S.face("laundry|bath", +1), S.face("utility|bath", -1)          # laundry, west of it
    be = S.face("bath|storage", -1)
    # bath: everything on the wet wall (its west side); 24" shower entry on the open (east) side
    S.vanity(sh, b1 - 20, 466.0, b1, 490.0, "SINK", rot=90)
    S.wc(sh, b1 - 28, 497.0, b1, 527.0)
    gy = 530.0
    S.wet_zone(sh, b0, gy, b1, be)
    sh.rect(b0, gy, b1, be, eq)
    S.glass(sh, (b0 + 24, gy), (b1, gy))
    sh.text("SHOWER", (b0 + b1) / 2, gy + 14, 3.2)
    sh.heads.append((b1, gy + 20, -1.0, 0.0))
    sh.circle((b1 - 2.5, gy + 20), 2.5, eq)
    S.drain(sh, (b0 + 3, be - 3), (b1 - 3, be - 3))
    S.room_label(sh, "COMMON BATH", b0, hall, b1, be, cx=b0 + 13, cy=503.0, h=2.4)
    sh.msp.add_circle((b0 + 13, 520.0), 5.0, dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    # storage behind the bath: open to the laundry, and the mech closet's bifold now opens into it
    s0 = S.face("bath|storage", +1)
    sh.rect(b0 + 12, S.S_IN - 12, b1, S.S_IN, fu); sh.text("SHELVES", (b0 + b1) / 2 + 6, S.S_IN - 6, 2.2)
    S.room_label(sh, "STORAGE", b0, s0, b1, S.S_IN, cx=(b0 + b1) / 2, cy=s0 + 14, h=3.4)
    # laundry: counter + sink, dryer, washer on the wet wall (its east side)
    sh.rect(l0, hall, l0 + 22, 514.0, fu); sh.text("FOLDING COUNTER", l0 + 11, (hall + 499.0) / 2, 2.2, rot=90)
    S.vanity(sh, l0, 500.0, l0 + 18, 514.0, "SINK", rot=90)
    y = 515.0
    for lbl in ("DRYER", "WASHER"):
        sh.rect(l0, y, l0 + 30, y + 27, eq); sh.text(lbl, l0 + 17, y + 13.5, 2.6, rot=90); y += 28
    # closet wall: the door opens flat against it, then the pass-through, then the panel
    sh.msp.add_lwpolyline([(l1, 497.0), (l1 + S.WET, 497.0), (l1 + S.WET, 527.0), (l1, 527.0)], close=True,
                          dxfattribs={"layer": "A-EQPM", "linetype": "DASHED"})
    sh.text("PASS-THROUGH", l1 - 9, 512.0, 2.2, rot=90)
    sh.text("FROM WIC", l1 + S.WET + 3, 512.0, 1.6, rot=90)
    sh.rect(l1 - 4, 540.0, l1, 560.0, eq); sh.text("PANEL", l1 - 10, 550.0, 2.5, rot=90)
    ax0, ax1 = l0 + 34, l0 + 56                                              # airer over the aisle
    sh.msp.add_lwpolyline([(ax0, 520.0), (ax1, 520.0), (ax1, 580.0), (ax0, 580.0)], close=True,
                          dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    sh.rect(l0 + 32, S.S_IN - 12, l1, S.S_IN, fu); sh.text("SHELVES TO 6'", (l0 + 32 + l1) / 2, S.S_IN - 6, 2.0)
    S.room_label(sh, "LAUNDRY", l0, hall, l1, S.S_IN, cx=(l0 + l1) / 2 + 10, cy=470.0, h=4.0)


def render(png):
    sh = S.build()
    S.render(sh.doc, png, S.face("kitchen|pantry", -1) - 30, S.N_IN + 150, S.W - 120, S.S + 70, width_in=14, dpi=200)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS), S.utility_block)
    render(OUT / "laundry-current.png")
    swap_plan()
    S.utility_block = swap_block
    render(OUT / "laundry-swap.png")
    S.WALLS, S.OPENINGS, S.utility_block = base
    print("  ", (OUT / "laundry-swap.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
