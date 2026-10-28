# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a solar layout on the roof plan.

The shed and the wing's rear slope are one plane (2:12, facing about 202°, SSW), so every panel on them
produces the same; the wing's street slope faces NNE and is left out. Panels (about 44.6" x 67.8", ~430 W)
in portrait, flush-mounted, inside the PV area of the A-3 roof plan (setbacks at the ends, the shed's high
edge and the ridge), clear of the roof penetrations by 18". Shows the most that fits and a suggested
~10 kW block on the shed, clear of the range cap and away from the west neighbour's two-story house.

Writes renders/experiments/solar-layout.png. Not part of the regular build.

    uv run scripts/experiment_solar.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle  # noqa: E402
from shapely.geometry import Point, Polygon, box  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402
import exterior as X  # noqa: E402
import permit_set as P  # noqa: E402

OUT = S.RENDERS / "experiments" / "solar-layout.png"
PW, PL, WATTS = 44.6, 67.8 * (12 / (12 ** 2 + 2 ** 2) ** 0.5), 430   # panel width; length in plan (2:12 slope)
KEEP = 18.0                                                         # clear of each penetration
BLOCK = (6, 4)                                                      # suggested block: columns x rows


def penetrations():
    sh = S.build()                                                   # as on A-3: the rear-slope row (skylight, fan
    y = P.text_at(sh, "SKYLIGHT")[1]                                 # cap, vent, primary bath fan cap) and the
    return {"RANGE CAP": P.text_at(sh, "RANGE"), "SK": (868.0, y), "EXH": (906.0, y), "VTR-2": (944.0, y),   # kitchen
            "EXH-P": (982.0, y), "VTR-3": (590.0, 612.0)}           # sink's vent at the rear wall line


def grid(x0, y0, cols, rows):
    return [box(x0 + c * PW, y0 + r * PL, x0 + (c + 1) * PW, y0 + (r + 1) * PL) for c in range(cols) for r in range(rows)]


def main():
    area = Polygon(P.pv_area())
    pens = penetrations()
    keep = [Point(p).buffer(KEEP + 6) for p in pens.values()]          # 6": the penetration itself
    ok = lambda b: area.contains(b) and not any(b.intersects(k) for k in keep)   # noqa: E731
    (ax0, ay0), shed_x1 = P.pv_area()[0], X.WING_X
    shed = [b for b in grid(ax0, ay0, int((shed_x1 - ax0) // PW), int((S.S + X.EAVE - ay0) // PL)) if ok(b)]
    gy0 = X.RIDGE_Y + 18
    wing = [b for b in grid(shed_x1, gy0, int((S.W + X.EAVE - 36 - shed_x1) // PW),
                            int((S.S + X.EAVE - gy0) // PL)) if ok(b)]
    block = [b for b in grid(ax0, ay0, *BLOCK) if ok(b)]
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_aspect("equal"); ax.axis("off")
    E0, E1, N0, N1 = S.E - X.EAVE, S.W + X.EAVE, S.N - X.EAVE, S.S + X.EAVE
    ax.add_patch(Rectangle((E0, N0), E1 - E0, N1 - N0, fc="#e6e6e6", ec="#222", lw=1.5))
    ax.plot([X.WING_X] * 2, [N0, N1], color="#222", lw=1.2)
    ax.plot([X.WING_X, E1], [X.RIDGE_Y] * 2, color="#222", lw=1.8)
    ax.text(E1 - 6, X.RIDGE_Y - 6, "RIDGE", ha="right", fontsize=7)
    ax.add_patch(MPoly(P.pv_area(), closed=True, fill=False, ec="#c0392b", ls="--", lw=1))
    for b in shed + wing:
        ax.add_patch(Rectangle(b.bounds[:2], PW, PL, fc="#dbe6f5", ec="#7a90b0", lw=0.6))
    for b in block:
        ax.add_patch(Rectangle(b.bounds[:2], PW, PL, fc="#1e2a44", ec="#7a90b0", lw=0.6))
    for name, (x, y) in pens.items():
        ax.add_patch(Circle((x, y), 6, fc="#c0392b"))
        ax.add_patch(Circle((x, y), KEEP + 6, fill=False, ec="#c0392b", ls=":"))
        ax.text(x, y + KEEP + 14, name, ha="center", fontsize=6.5, color="#c0392b", va="top")
    ax.text((E0 + X.WING_X) / 2, N0 - 30, "SHED 2:12 (high edge at the street)", ha="center", fontsize=8)
    ax.text((X.WING_X + E1) / 2, N0 - 30, "GABLE: street slope faces NNE (no panels)", ha="center", fontsize=8)
    ax.text((E0 + E1) / 2, N1 + 40, "REAR (faces ~202°, SSW)   ·   STREET at the top", ha="center", fontsize=8)
    n_max = len(shed) + len(wing)
    ax.set_title(f"Solar layout: up to {n_max} panels fit (~{n_max * WATTS / 1000:.0f} kW, light blue); "
                 f"suggested block {len(block)} panels (~{len(block) * WATTS / 1000:.1f} kW, dark) on the shed",
                 fontsize=10)
    ax.set_xlim(E0 - 20, E1 + 20); ax.set_ylim(N1 + 70, N0 - 60)   # east on the left, the street at the top
    fig.savefig(OUT, dpi=130, bbox_inches="tight")
    print(len(shed), len(wing), len(block))


if __name__ == "__main__":
    main()
