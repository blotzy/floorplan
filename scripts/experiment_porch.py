# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: dressing up the corner porch (all noncombustible, it's inside the 5' zone).

  plain    the porch as planned
  feature  wood-look feature wall (fiber-cement or porcelain wood-grain) on the porch's back
           walls, wrapping onto the porch ceiling
  post     a slim black steel corner post
  sconces  a pair of cylinder up/down sconces either side of the front door
  breeze   a breeze-block screen on top of the entry court's street-side seat wall
  all      everything together

Each on the main plan's exterior (MCM gable, stucco). Writes renders/experiments/porch-<option>/
(3D model), porch-<option>-{court,street}.png and the sheets porch-compare-{court,street}.png.

    uv run scripts/experiment_porch.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
E, N, PX, PY = S.E, S.N, S.PORCH_X, S.PORCH_Y          # porch: x E..PX, y N..PY (outer faces)
DOOR = next(o for o in S.OPENINGS if o[0] == "porch front" and o[3] == "door")[1:3]
SIDE_WIN = next(o for o in S.OPENINGS if o[0] == "porch side" and o[3] == "window")[1:3]
COLOURS = {"feature": 0xA8754B, "breeze": 0xECE7DD, "sconce": 0x2B2D30,
           "glow": {"color": 0xFFE2A0, "emissive": 0xFFC86B, "emissiveIntensity": 1.2}}
VIEWS = {"court": ((300, 120, 60), (415, 290, 70)),      # from the entry court, toward the door
         "street": ((470, -170, 64), (420, 280, 70))}     # from the street, square to the porch


def feature(sc):
    """Wood-look cladding on the porch's two back walls (around the door and the side window)
    and on the porch ceiling."""
    y = PY - 0.4                                         # just proud of the front wall
    d0, d1 = DOOR
    for a, b, z0, z1 in ((E, d0, 0, 120), (d1, PX, 0, 120), (d0, d1, 96, 120)):
        sc.quad("feature", (a, y), (b, y), z0, z1)
    x = PX - 0.4                                         # side wall, around the reeded window
    w0, w1 = SIDE_WIN
    for a, b, z0, z1 in ((N, w0, 0, 120), (w1, PY, 0, 120), (w0, w1, 0, 30), (w0, w1, 96, 120)):
        sc.quad("feature", (x, a), (x, b), z0, z1)
    sc.boxes["feature"].append([E + 6, N, PX, PY, 118.5, 119.5])      # porch ceiling


def post(sc):
    sc.mat["post"] = {"color": 0x1F2124, "roughness": 0.5, "metalness": 0.6}


def sconces(sc):
    d0, d1 = DOOR
    for cx in (d0 - 7, d1 + 7):
        sc.cyls["sconce"].append([cx, PY - 3.5, 2.5, 62, 76])
        sc.cyls["glow"].append([cx, PY - 3.5, 2.6, 60, 62])       # light spilling down
        sc.cyls["glow"].append([cx, PY - 3.5, 2.6, 76, 78])       # and up


def breeze(sc):
    """Breeze-block screen (12" blocks, open centres) on the street-side seat wall."""
    x0, y0, x1, y1 = S.ENTRY_WALLS[0]
    z0, rows, t = S.ENTRY_WALL_H, 4, 2.0
    n = int((x1 - x0) // 12)
    xs = x1 - n * 12
    for i in range(n):
        for j in range(rows):
            a, c = xs + i * 12, z0 + j * 12
            for bx0, bx1, bz0, bz1 in ((a, a + 12, c, c + t), (a, a + 12, c + 12 - t, c + 12),
                                       (a, a + t, c, c + 12), (a + 12 - t, a + 12, c, c + 12)):
                sc.boxes["breeze"].append([bx0, y0, bx1, y1, bz0, bz1])


VARIANTS = {
    "plain": ("As planned", []),
    "feature": ("Wood-look feature wall and porch ceiling", [feature]),
    "post": ("Slim black steel corner post", [post]),
    "sconces": ("Cylinder sconces either side of the door", [sconces]),
    "breeze": ("Breeze-block screen on the street-side seat wall", [breeze]),
    "all": ("All of the above", [feature, post, sconces, breeze]),
}


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shots = []
    for key, (title, steps) in VARIANTS.items():
        sc = M.build_schematic()
        X.chosen_exterior(sc)
        sc.mat.update({k: (v if isinstance(v, dict) else {"color": v}) for k, v in COLOURS.items()})
        for step in steps:
            step(sc)
        out_dir = OUT / f"porch-{key}"
        M.write_model(sc, out_dir, {**sc.meta})
        for view, cam in VIEWS.items():
            png = OUT / f"porch-{key}-{view}.png"
            X.screenshot(out_dir / "house.html", png, *cam)
        shots.append((key, f"{key}: {title}"))
    for view, where in (("court", "from the entry court"), ("street", "from the street")):
        fig, axs = plt.subplots(3, 2, figsize=(14, 13))
        for ax, (key, title) in zip(axs.flat, shots):
            png = OUT / f"porch-{key}-{view}.png"
            if png.exists():
                ax.imshow(plt.imread(png))
            ax.set_title(title, fontsize=11); ax.axis("off")
        fig.suptitle(f"Corner porch options, {where} (MCM gable, stucco)", fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        sheet = OUT / f"porch-compare-{view}.png"
        fig.savefig(sheet, dpi=90)
        plt.close(fig)
        print("  ", sheet.relative_to(S.ROOT))


if __name__ == "__main__":
    main()
