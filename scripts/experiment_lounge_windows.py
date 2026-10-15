# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the lounge's street (north) window under the shed roof's 3' clerestory band.

  one10   one 10' window (two 5' units), centred: the main plan
  one6    one 6' window, centred
  two3    two 3' windows, symmetrical, evenly spaced along the lounge wall
  two4    two 4' windows, symmetrical, evenly spaced

All keep the 30" sill and 8' head. Writes renders/experiments/lounge-windows-compare.png (the
lounge's street wall seen from the street, with the clerestory band and each option's glass total)
and a 3D model per option with the shingle shed roof (great room vaulted, 3' band).

    uv run scripts/experiment_lounge_windows.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = copy.deepcopy(S.OPENINGS)
L0, L1 = X.LOUNGE_X                       # lounge's inside faces along the street wall
MID = (L0 + L1) / 2
BAND = 36.0
LIMIT = 0.20 * 2238                       # Title 24 prescriptive glazing limit (sq ft)


def even(n, w):
    """n windows of width w spaced evenly (equal gaps, ends included) along the lounge wall."""
    g = (L1 - L0 - n * w) / (n + 1)
    return [(L0 + g + i * (w + g), L0 + g + i * (w + g) + w) for i in range(n)]


VARIANTS = {
    "one10": ("One 10' window (two 5' units), centred: main plan", [(MID - 60, MID + 60)]),
    "one6": ("One 6' window, centred", [(MID - 36, MID + 36)]),
    "two3": ("Two 3' windows, symmetrical, evenly spaced", even(2, 36)),
    "two4": ("Two 4' windows, symmetrical, evenly spaced", even(2, 48)),
}


def openings(wins):
    ops = [o for o in copy.deepcopy(BASE) if not (o[0] == "north" and L0 <= o[1] < L1)]
    return ops + [("north", a, b, "window") for a, b in wins]


def glass(ops):
    tot = 0.0
    for o in ops:
        if o[0] not in S.EXT_WALLS or o[3] not in ("window", "slider", "transom"):
            continue
        h = 96.0 if o[3] == "slider" else (o[5] - o[4] if len(o) > 4 else 66.0)
        tot += (o[2] - o[1]) * h / 144
    return tot + (L1 - L0) * BAND / 144             # + the clerestory band


def sheet(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    top = X.shed_vault_under(2 / 12)(S.N)           # street wall rises to the roof underside
    g0 = X.PLATE + (top - X.PLATE - BAND) / 2
    x0, x1 = S.PORCH_X, S.face("lounge|gym", +1) + 40
    fig, axs = plt.subplots(len(VARIANTS), 1, figsize=(10, 3.4 * len(VARIANTS)))
    for ax, (key, (title, wins)) in zip(axs, VARIANTS.items()):
        ax.add_patch(Rectangle((x0, 0), x1 - x0, top, fc="#efe9df", ec="k"))
        ax.add_patch(Rectangle((L0, g0), L1 - L0, BAND, fc="#bfe3f2", ec="k"))   # clerestory band
        for a, b in wins:
            ax.add_patch(Rectangle((a, 30), b - a, 66, fc="#bfe3f2", ec="k"))
            if b - a > 100:
                ax.plot([(a + b) / 2] * 2, [30, 96], "k", lw=0.8)
        ax.add_patch(Rectangle((x0 - 36, top), x1 - x0 + 72, 10, fc="#3c3f44"))   # roof edge
        ax.plot([L1 + 2.25] * 2, [0, 120], ls=":", c="#999", lw=0.8)              # gym wall
        ax.text(MID, -14, "LOUNGE", ha="center", fontsize=9)
        ax.text((L1 + x1) / 2, -14, "GYM", ha="center", fontsize=9)
        g = glass(openings(wins))
        flag = "under" if g <= LIMIT else "over"
        ax.set_title(f"{key}: {title}   (house glass ~{g:.0f} sq ft, {g / 22.38:.1f}%, {flag} 20%)",
                     fontsize=10)
        ax.set_xlim(x0 - 50, x1 + 50); ax.set_ylim(-25, top + 20); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("Lounge street wall from the street, under the shed roof's 3' clerestory band", fontsize=11)
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
    sheet(out / "lounge-windows-compare.png")
    for key, (_, wins) in VARIANTS.items():
        S.OPENINGS = openings(wins)
        sc = M.build_schematic()
        X.band(sc, "exterior", X.WALL_TOP, X.PLATE)
        X.shed_vault_great(sc, 2 / 12, 36, band=BAND)
        X.front_door(sc)
        sc.mat = {k: {"color": v} for k, v in X.STYLES["mcm-gable"][1].items()}
        M.write_model(sc, out / f"lounge-windows-{key}", sc.meta)
    S.OPENINGS = BASE


if __name__ == "__main__":
    main()
