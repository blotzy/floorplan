# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: how the dining and kitchen windows on the south (rear) wall relate.

Every option keeps the 8' head line and standard 5' units; the kitchen window always clears
the counter (sill 42").

  rhythm   main plan: three equal 5' windows 4' apart; dining pair at an 18" sill
  pair     the earlier version: dining 10' (two 5' units) at an 18" sill + kitchen 5'
  matched  dining 10' + kitchen 5', both at a 42" sill (same top and bottom lines)
  ribbon   one band of four 5' units at a 42" sill, dining through to the sink
  tall     rhythm, but the dining pair runs floor to head (French-door look, fixed glass)

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
KITCHEN = (592.0, 652.0, 42.0)       # 5' over the sink, sill above the backsplash

VARIANTS = {   # key -> (title, [(from, to, sill), ...] on the south wall, dining + kitchen)
    "rhythm":  ("Three equal 5' windows, 4' apart; dining sills at 18\" (main plan)",
                [(376.0, 436.0, 18.0), (484.0, 544.0, 18.0), KITCHEN]),
    "pair":    ("Dining 10' (two 5' units) at 18\" + kitchen 5' (earlier version)",
                [(397.0, 517.0, 18.0), KITCHEN]),
    "matched": ("Dining 10' + kitchen 5', both sills at 42\"",
                [(397.0, 517.0, 42.0), KITCHEN]),
    "ribbon":  ("Ribbon: four 5' units at a 42\" sill, dining through to the sink",
                [(412.0, 652.0, 42.0)]),
    "tall":    ("Three equal 5' windows, 4' apart; dining pair floor to head",
                [(376.0, 436.0, 0.0), (484.0, 544.0, 0.0), KITCHEN]),
}


def openings(spec):
    """Main-plan openings with the dining/kitchen south windows replaced by `spec`."""
    x0, x1 = S.E_IN, S.face("kitchen|pantry", -1)
    ops = [o for o in copy.deepcopy(BASE) if not (o[0] == "south" and x0 < o[1] < x1)]
    return ops + [("south", a, b, "window", sill, 96.0) for a, b, sill in spec]


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
        for a, b, sill in spec:
            ax.add_patch(Rectangle((a, sill), b - a, 96 - sill, fc="#bfe3f2", ec="k"))
            for m in range(1, round((b - a) / 60)):                                   # mulled 5' units
                ax.plot([a + 60 * m] * 2, [sill, 96], "k", lw=0.8)
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
