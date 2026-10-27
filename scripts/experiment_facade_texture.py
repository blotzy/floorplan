# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a textured cladding with relief on the street facade (County facade-variety strategy, and the
second material for the 10% material-variety rule), three ways, on the street elevation:

  A. Vertical-groove fiber cement on the shed's tall wall above the window heads, around the clerestory.
  B. Vertical-groove fiber cement on the bedroom wing's street wall, full height.
  C. Dark ribbed metal on the whole shed block (porch to the wing), the wing staying light stucco.

Each panel gives the clad share of the street facade (windows and doors excluded, as the County counts it).
The County's material-continuity rule: a material can't change at an outside corner; it wraps at least 4' around
it or stops 4' short. So A and C wrap 4' onto the east (carport) face and the shed's side above the gable, and B
wraps 4' onto the west face (not shown on the street elevation).

Writes renders/experiments/facade-texture.png. Not part of the regular build.

    uv run scripts/experiment_facade_texture.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exterior as X  # noqa: E402
import schematic as S  # noqa: E402
import zoning_set as Z  # noqa: E402

OUT = S.RENDERS / "experiments"
WALL_TOP = Z.UNDER(S.N)                                  # the shed's street wall
GLASS = "#bfe3f2"


def glass_rects():
    """Street-facade glass and the front door, as (x0, z0, x1, z1)."""
    out = [(x0, z0, x1, z1) for x0, x1, z0, z1, k in Z.openings_on("north")]
    out += [(x0, z0, x1, z1) for x0, x1, z0, z1, k in Z.openings_on("porch front")]
    lx0, lx1 = X.CLERESTORY_X
    g0 = X.PLATE + (WALL_TOP - X.PLATE - 36) / 2
    out.append((lx0, g0, lx1, g0 + 36))
    return out


def wall_area():
    return (X.WING_X - S.E) * WALL_TOP + (S.W - X.WING_X) * X.PLATE   # the porch recess counted in the plane


def clad(ax, x0, z0, x1, z1, colour, groove, step):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=colour, ec="none", zorder=3))
    x = x0 + step
    while x < x1:
        ax.plot([x, x], [z0, z1], color=groove, lw=0.5, zorder=3.5)
        x += step
    return (x1 - x0) * (z1 - z0)


def redraw_glass(ax, regions):
    lost = 0.0
    for gx0, gz0, gx1, gz1 in glass_rects():
        ax.add_patch(Rectangle((gx0, gz0), gx1 - gx0, gz1 - gz0, fc=GLASS, ec=Z.INK, lw=0.8, zorder=4))
        for x0, z0, x1, z1 in regions:                   # glass inside a clad region doesn't count as cladding
            w = max(0.0, min(gx1, x1) - max(gx0, x0))
            h = max(0.0, min(gz1, z1) - max(gz0, z0))
            lost += w * h
    for k in range(1, X.CLERESTORY_UNITS):               # clerestory mullions
        mx = X.CLERESTORY_X[0] + k * X.CLERESTORY_UNIT
        g0 = X.PLATE + (WALL_TOP - X.PLATE - 36) / 2
        ax.plot([mx, mx], [g0, g0 + 36], color=Z.INK, lw=0.6, zorder=4.5)
    return lost


def variant(ax, title, regions, colour, groove, step):
    Z.elevation(ax, "north")
    area = sum(clad(ax, *r, colour, groove, step) for r in regions)
    area -= redraw_glass(ax, regions)
    net = wall_area() - sum((x1 - x0) * (z1 - z0) for x0, z0, x1, z1 in glass_rects())
    ax.set_title(f"{title}\nclad about {area / 144:.0f} sq ft, {100 * area / net:.0f}% of the street facade "
                 "(windows and doors excluded)", fontsize=9, loc="left")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 13))
    over_porch = (S.E, Z.PORCH_CEIL + 3, S.PORCH_X, WALL_TOP)          # the wall above the porch: same plane
    variant(fig.add_axes([0.02, 0.68, 0.96, 0.28]),
            "A. Vertical-groove fiber cement on the shed's tall wall above the window heads, around the clerestory",
            [over_porch, (S.PORCH_X, 102.0, X.WING_X, WALL_TOP)], "#8a7a68", "#5f5245", 6.0)
    variant(fig.add_axes([0.02, 0.36, 0.96, 0.28]),
            "B. Vertical-groove fiber cement on the bedroom wing's street wall, full height",
            [(X.WING_X, 0.0, S.W, X.PLATE)], "#8a7a68", "#5f5245", 6.0)
    variant(fig.add_axes([0.02, 0.04, 0.96, 0.28]),
            "C. Dark ribbed metal on the whole shed block (porch to the wing); the wing stays light stucco",
            [over_porch, (S.PORCH_X, 0.0, X.WING_X, WALL_TOP)], "#4a4e53", "#2e3135", 4.0)
    fig.savefig(OUT / "facade-texture.png", dpi=110)
    print("  ", (OUT / "facade-texture.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
