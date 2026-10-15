# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: line up the lounge's west wall (shared with the gym) with the kitchen's west wall
(shared with the pantry), so the great room ends on one straight line at the bedroom hall.

  plan      main plan: the lounge wall sits 18" west of the kitchen wall
  aligned   the lounge/gym wall moves 18" east onto the kitchen wall's line: the lounge narrows
            18", the gym grows 18", the bedroom hall wall starts on the same line as the south
            hall wall, and the lounge and gym windows re-centre. The sectional, console and
            coffee table slide 12" toward the TV so there's still a walkway behind the console.

Writes renders/experiments/align-{plan,aligned}.png (plan close-ups), align-facade.png (street
elevations with the stucco gaps between windows) and a 3D model of each with
the Roof menu (the shed options show the vault's edge on one straight line when aligned).

    uv run scripts/experiment_align.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

BASE = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS))
BUILD = S.build
SHIFT = 18.0                                   # lounge/gym wall: 692 -> 674 (the kitchen wall's line)
FURN_SHIFT = 12.0                              # lounge furniture toward the TV


def aligned_plan():
    ws, ops = S.WALLS, S.OPENINGS
    for i, w in enumerate(ws):
        if w[0] == "lounge|gym":
            ws[i] = (w[0], w[1], w[2] - SHIFT, *w[3:])
        elif w[0] == "bedroom hall wall":
            ws[i] = (w[0], w[1], w[2], w[3] - SHIFT, *w[4:])
    lounge = (S.face("foyer wall", +1), S.face("lounge|gym", -1))
    gym = (S.face("lounge|gym", +1), S.face("gym|ensuite", -1))
    for i, o in enumerate(ops):                    # re-centre the lounge (10') and gym (6') windows
        for x0, (lo, hi) in ((511.1, lounge), (722.1, gym)):
            if o[0] == "north" and o[1] == x0:
                c, half = (lo + hi) / 2, (o[2] - o[1]) / 2
                ops[i] = (o[0], c - half, c + half, *o[3:])


def shift_lounge_furniture(sh):
    """Slide the sectional, console and coffee table toward the TV wall."""
    for e in list(sh.msp):
        if e.dxf.layer not in ("A-FURN", "A-ANNO-TEXT") or e.dxftype() not in ("LWPOLYLINE", "TEXT"):
            continue
        if e.dxftype() == "TEXT":
            p = e.dxf.align_point if e.dxf.hasattr("align_point") else e.dxf.insert
            pts = [(p.x, p.y)]
        else:
            pts = [(q[0], q[1]) for q in e.get_points("xy")]
        if all(490 <= x <= 660 and 260 <= y <= 400 for x, y in pts):
            e.translate(-FURN_SHIFT, 0, 0)
    return sh


VARIANTS = {"plan": (None, None), "aligned": (aligned_plan, shift_lounge_furniture)}


def facade(ax, title):
    """Street (north) elevation: windows on the north wall at their sill/head, gaps labelled."""
    from matplotlib.patches import Rectangle
    x0, x1 = S.E, S.W
    ax.add_patch(Rectangle((x0, 0), x1 - x0, 132, fc="#efe9df", ec="k"))
    ax.add_patch(Rectangle((x0, 0), S.PORCH_X - x0, 132, fc="#d8d2c8", ec="k"))        # porch notch
    wins = sorted((o[1], o[2]) for o in S.OPENINGS if o[0] == "north" and o[3] == "window")
    for a, b in wins:
        ax.add_patch(Rectangle((a, 30), b - a, 66, fc="#bfe3f2", ec="k"))
    edges = [S.PORCH_X, *[v for w in wins for v in w], x1]
    for a, b in zip(edges[::2], edges[1::2]):                                           # stucco gaps
        ax.annotate("", (a, 112), (b, 112), arrowprops=dict(arrowstyle="<->", lw=0.6))
        ft, inch = divmod(round(b - a), 12)
        ax.text((a + b) / 2, 116, f"{ft}'-{inch}\"", ha="center", fontsize=7)
    ax.text((x0 + S.PORCH_X) / 2, 60, "PORCH", ha="center", fontsize=7)
    ax.set_title(title, fontsize=10)
    ax.set_xlim(x0 - 20, x1 + 20); ax.set_ylim(-10, 140); ax.set_aspect("equal"); ax.axis("off")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(VARIANTS), 1, figsize=(16, 2.6 * len(VARIANTS)))
    out = S.RENDERS / "experiments"
    for ax, (key, (plan, fix)) in zip(axs, VARIANTS.items()):
        S.WALLS, S.OPENINGS = copy.deepcopy(BASE[0]), copy.deepcopy(BASE[1])
        if plan:
            plan()
        S.build = (lambda f=fix: f(BUILD())) if fix else BUILD
        X.LOUNGE_X = (S.face("foyer wall", +1), S.face("lounge|gym", -1))
        sh = S.build()
        S.render(sh.doc, out / f"align-{key}.png", S.E - 20, S.N - 20, 1080, S.S + 20, width_in=14, dpi=200)
        sc = M.build_schematic()
        X.chosen_exterior(sc)
        M.write_model(sc, out / f"align-{key}", {**sc.meta, "roof_hidden": True, "roof_options": X.roof_options()})
        facade(ax, f"{key}: street elevation, stucco between windows (street on this side; carport end at left)")
    fig.tight_layout()
    try:
        fig.savefig(out / "align-facade.png", dpi=130)
    except OSError:                    # locked by a Windows image viewer
        import time
        fig.savefig(out / f"align-facade-{time.strftime('%H%M%S')}.png", dpi=130)
    plt.close(fig)
    S.WALLS, S.OPENINGS = BASE
    S.build = BUILD
    X.LOUNGE_X = (S.face("foyer wall", +1), S.face("lounge|gym", -1))


if __name__ == "__main__":
    main()
