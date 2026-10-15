# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: how the dining and kitchen windows on the south (rear) wall relate.

Every option keeps the 8' head line and standard 5' units; the kitchen window always clears
the counter (sill 42").

  rhythm   main plan: three equal 5' windows 4' apart; dining pair at an 18" sill
  narrow24 main plan + a 2' window of the same height centred between the dining pair (12" piers)
  narrow18 the same with a 1'-6" window (15" piers)
  one12    one continuous 12' dining window centred on the wall and table; kitchen unchanged
  one14    one continuous 14' dining window spanning the main plan pair's full extent; kitchen unchanged
  pair     the earlier version: dining 10' (two 5' units) at an 18" sill + kitchen 5'
  matched  dining 10' + kitchen 5', both at a 42" sill (same top and bottom lines)
  ribbon   one band of four 5' units at a 42" sill, dining through to the sink
  tall     rhythm, but the dining pair runs floor to head (French-door look, fixed glass)

Bigger kitchen windows (the kitchen's south wall runs from the peninsula end to the corner):
  kitchen6     main plan with a 6' kitchen window centred on the sink
  kitchen8     dining 10' pair + an 8' kitchen window from over the peninsula end to the corner
  backsplash   kitchen8 with the kitchen glass down to the counter (glass backsplash)
  ribbon-wide  one 42"-sill band from the dining room's east end to the kitchen corner

The ribbon broken in two (heads in line, kitchen part always at 42"):
  split-even      two equal 8' bands, the dining one centred on the table
  split-12-8      dining 12' centred on the table + kitchen 8'
  split-pier      split by a narrow pier right at the peninsula end: dining 12' + kitchen 9'
  split-pier-low  split-pier with the dining part at an 18" sill (the sill steps where the counter starts)

Writes renders/experiments/south-windows-compare.png (the south wall seen from inside, one
row per option, with each option's glass total), and a 3D model per option.

    uv run scripts/experiment_south_windows.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = copy.deepcopy(S.OPENINGS)
PEN_OUT = 546.9                      # peninsula's dining-side face, where it meets the wall
KITCHEN = (588.0, 648.0, 42.0)       # 5' over the sink, sill above the backsplash

VARIANTS = {   # key -> (title, [(from, to, sill), ...] on the south wall, dining + kitchen)
    "rhythm":  ("Three equal 5' windows, 4' apart; dining sills at 18\" (main plan)",
                [(372.0, 432.0, 18.0), (480.0, 540.0, 18.0), KITCHEN]),
    "narrow24": ("Main plan + a narrow 2' window of the same height centred between the dining pair",
                 [(372.0, 432.0, 18.0), (444.0, 468.0, 18.0), (480.0, 540.0, 18.0), KITCHEN]),
    "narrow18": ("Main plan + a narrower 1'-6\" window of the same height between the dining pair",
                 [(372.0, 432.0, 18.0), (447.0, 465.0, 18.0), (480.0, 540.0, 18.0), KITCHEN]),
    "one12":   ("One continuous 12' dining window (two 6' units) at 18\", centred; kitchen as main plan",
                [(384.0, 528.0, 18.0, 2), KITCHEN]),
    "one14":   ("One continuous 14' dining window (two 7' units) at 18\", the pair's full extent; kitchen as main plan",
                [(372.0, 540.0, 18.0, 2), KITCHEN]),
    "pair":    ("Dining 10' (two 5' units) at 18\" + kitchen 5' (earlier version)",
                [(396.0, 516.0, 18.0), KITCHEN]),
    "matched": ("Dining 10' + kitchen 5', both sills at 42\"",
                [(396.0, 516.0, 42.0), KITCHEN]),
    "ribbon":  ("Ribbon: four 5' units at a 42\" sill, dining through to the sink",
                [(412.0, 652.0, 42.0)]),
    "tall":    ("Three equal 5' windows, 4' apart; dining pair floor to head",
                [(372.0, 432.0, 0.0), (480.0, 540.0, 0.0), KITCHEN]),
    # bigger kitchen windows
    "kitchen6":  ("Main plan with the kitchen window 6' (centred on the sink)",
                  [(372.0, 432.0, 18.0), (480.0, 540.0, 18.0), (582.0, 654.0, 42.0)]),
    "kitchen8":  ("Dining 10' at 18\" + kitchen 8' at 42\", from over the peninsula end to the corner",
                  [(396.0, 516.0, 18.0), (568.0, 664.0, 42.0)]),
    "backsplash": ("Dining 10' at 18\" + kitchen 8' down to the counter (glass backsplash)",
                   [(396.0, 516.0, 18.0), (568.0, 664.0, 37.0)]),
    "ribbon-wide": ("Ribbon to the corner: four 6' units at 42\", dining through the kitchen",
                    [(376.0, 664.0, 42.0, 4)]),
    # the ribbon broken into a dining part and a kitchen part
    "split-even":     ("Two equal 8' bands (4' units) at 42\": one centred on the table, one to the kitchen corner",
                       [(408.0, 504.0, 42.0, 2), (568.0, 664.0, 42.0, 2)]),
    "split-12-8":     ("Dining 12' (two 6') centred on the table + kitchen 8', both at 42\"",
                       [(384.0, 528.0, 42.0, 2), (568.0, 664.0, 42.0, 2)]),
    "split-pier":     ("Ribbon split by a 16\" pier at the peninsula end: dining 12' + kitchen 9' (3' units), 42\"",
                       [(396.0, 540.0, 42.0, 2), (556.0, 664.0, 42.0, 3)]),
    "split-pier-low": ("Same split at the peninsula, but the dining part drops to an 18\" sill",
                       [(396.0, 540.0, 18.0, 2), (556.0, 664.0, 42.0, 3)]),
}


def openings(spec):
    """Main-plan openings with the dining/kitchen south windows replaced by `spec`."""
    x0, x1 = S.E_IN, S.face("kitchen|pantry", -1)
    ops = [o for o in copy.deepcopy(BASE) if not (o[0] == "south" and x0 < o[1] < x1)]
    return ops + [("south", w[0], w[1], "window", w[2], 96.0) for w in spec]


def glass_total(ops):
    tot = 0.0
    for o in ops:
        if o[0] not in S.EXT_WALLS or o[3] not in ("window", "slider", "transom"):
            continue
        h = 96.0 if o[3] == "slider" else (o[5] - o[4] if len(o) > 4 else 66.0)
        tot += (o[2] - o[1]) * h / 144
    return tot


def sheet(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    x0, x1 = S.E_IN, S.face("kitchen|pantry", -1)
    fig, axs = plt.subplots(len(VARIANTS), 1, figsize=(11, 3.1 * len(VARIANTS)))
    for ax, (key, (title, spec)) in zip(axs, VARIANTS.items()):
        ax.add_patch(Rectangle((x0, 0), x1 - x0, 120, fc="#f2efe9", ec="k"))
        ax.add_patch(Rectangle((PEN_OUT, 0), x1 - PEN_OUT, 36, fc="#ccc", ec="k"))   # peninsula + sink run
        for a, b, sill, *units in spec:
            ax.add_patch(Rectangle((a, sill), b - a, 96 - sill, fc="#bfe3f2", ec="k"))
            n = units[0] if units else (round((b - a) / 60) if b - a > 100 else 1)   # mulled units
            for m in range(1, n):
                ax.plot([a + (b - a) * m / n] * 2, [sill, 96], "k", lw=0.8)
        ax.plot([x0, x1], [96, 96], ls=":", c="#999", lw=0.8)
        ax.text((x0 + PEN_OUT) / 2, -11, "DINING", ha="center", fontsize=9)
        ax.text((PEN_OUT + x1) / 2, -11, "KITCHEN", ha="center", fontsize=9)
        g = glass_total(openings(spec))
        ax.set_title(f"{key}: {title}   (house glass ~{g:.0f} sq ft, {g / 22.38:.1f}%)", fontsize=10)
        ax.set_xlim(x0 - 10, x1 + 10); ax.set_ylim(-20, 125); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("South wall of the dining room and kitchen, seen from inside (counter grey, 8' head dotted)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    try:
        fig.savefig(path, dpi=130)
    except OSError:                    # locked by a Windows image viewer
        import time
        path = path.with_name(f"{path.stem}-{time.strftime('%H%M%S')}{path.suffix}")
        fig.savefig(path, dpi=130)
    plt.close(fig)
    print("  ", path.relative_to(S.ROOT))


def main():
    out = S.RENDERS / "experiments"
    sheet(out / "south-windows-compare.png")
    for key, (_, spec) in VARIANTS.items():
        S.OPENINGS = openings(spec)
        sc = M.build_schematic()
        M.write_model(sc, out / f"south-windows-{key}", sc.meta)
    S.OPENINGS = BASE


if __name__ == "__main__":
    main()
