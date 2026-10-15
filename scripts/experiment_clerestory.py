# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the shed roof's lounge clerestory as one long band or as two or three windows.

All 3' tall, centred in the tall street wall over the lounge, with the lounge's 10' street window
below as in the main plan.

  band    one band the full width of the lounge (~19'-8")
  two8    two 8' windows, evenly spaced
  two6    two 6' windows, evenly spaced
  two5    two 5' windows, evenly spaced
  three5  three 5' windows, evenly spaced
  three4  three 4' windows, evenly spaced
  three3  three 3' windows, evenly spaced

Writes renders/experiments/clerestory-compare.png (the lounge's street wall seen from the street,
with each option's house glass total) and a 3D model per option (shingle shed, 2:12, great room
vaulted).

    uv run scripts/experiment_clerestory.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

L0, L1 = X.LOUNGE_X                       # lounge's inside faces along the street wall
H = 36.0                                  # clerestory glass height
LIMIT = 0.20 * 2238                       # Title 24 prescriptive glazing limit (sq ft)


def even(n, w):
    """n pieces of width w spaced evenly (equal gaps, ends included) along the lounge wall."""
    g = (L1 - L0 - n * w) / (n + 1)
    return [(L0 + g + i * (w + g), L0 + g + i * (w + g) + w, H) for i in range(n)]


VARIANTS = {
    "band": ("One band, the full lounge width", [(L0, L1, H)]),
    "two8": ("Two 8' windows, evenly spaced", even(2, 96)),
    "two6": ("Two 6' windows, evenly spaced", even(2, 72)),
    "two5": ("Two 5' windows, evenly spaced", even(2, 60)),
    "three5": ("Three 5' windows, evenly spaced", even(3, 60)),
    "three4": ("Three 4' windows, evenly spaced", even(3, 48)),
    "three3": ("Three 3' windows, evenly spaced", even(3, 36)),
}


def glass(pieces):
    tot = 0.0
    for o in S.OPENINGS:
        if o[0] not in S.EXT_WALLS or o[3] not in ("window", "slider", "transom"):
            continue
        h = 96.0 if o[3] == "slider" else (o[5] - o[4] if len(o) > 4 else 66.0)
        tot += (o[2] - o[1]) * h / 144
    return tot + sum((b - a) * h for a, b, h in pieces) / 144


def sheet(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    top = X.shed_vault_under(2 / 12)(S.N)           # street wall rises to the roof underside
    x0, x1 = S.PORCH_X, S.face("lounge|gym", +1) + 40
    lounge = [o for o in S.OPENINGS if o[0] == "north" and L0 <= o[1] < L1]
    fig, axs = plt.subplots(len(VARIANTS), 1, figsize=(10, 3.4 * len(VARIANTS)))
    for ax, (key, (title, pieces)) in zip(axs, VARIANTS.items()):
        ax.add_patch(Rectangle((x0, 0), x1 - x0, top, fc="#efe9df", ec="k"))
        for a, b, h in pieces:
            g0 = X.PLATE + (top - X.PLATE - h) / 2
            ax.add_patch(Rectangle((a, g0), b - a, h, fc="#bfe3f2", ec="k"))
        for o in lounge:                                                       # lounge window below
            ax.add_patch(Rectangle((o[1], 30), o[2] - o[1], 66, fc="#bfe3f2", ec="k"))
            ax.plot([(o[1] + o[2]) / 2] * 2, [30, 96], "k", lw=0.8)
        ax.add_patch(Rectangle((x0 - 36, top), x1 - x0 + 72, 10, fc="#3c3f44"))   # roof edge
        ax.plot([L1 + 2.25] * 2, [0, 120], ls=":", c="#999", lw=0.8)              # gym wall
        ax.text((L0 + L1) / 2, -14, "LOUNGE", ha="center", fontsize=9)
        ax.text((L1 + x1) / 2, -14, "GYM", ha="center", fontsize=9)
        g = glass(pieces)
        ax.set_title(f"{key}: {title}   (house glass ~{g:.0f} sq ft, {g / 22.38:.1f}%, "
                     f"{'under' if g <= LIMIT else 'over'} 20%)", fontsize=10)
        ax.set_xlim(x0 - 50, x1 + 50); ax.set_ylim(-25, top + 20); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("Lounge street wall from the street: the shed roof's 3' clerestory", fontsize=11)
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
    sheet(out / "clerestory-compare.png")
    for key, (_, pieces) in VARIANTS.items():
        sc = M.build_schematic()
        X.band(sc, "exterior", X.WALL_TOP, X.PLATE)
        X.shed_vault_great(sc, 2 / 12, 36, pieces=pieces)
        X.front_door(sc)
        sc.mat = {k: {"color": v} for k, v in X.STYLES["mcm-gable"][1].items()}
        M.write_model(sc, out / f"clerestory-{key}", sc.meta)


if __name__ == "__main__":
    main()
