# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: dressing up the corner porch (all noncombustible, it's inside the 5' zone).

  plain    no porch details
  plan     wood-look feature wall (fiber-cement or porcelain wood-grain) on the porch's back
           walls, wrapping onto the porch ceiling: the main plan
  post     the main plan plus a slim black steel corner post
  breeze   the main plan plus a breeze-block screen on the seat wall (about 6' total: over the
           County's 42" limit for walls in the front yard)

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
VIEWS = {"court": ((300, 120, 60), (415, 290, 70)),      # from the entry court, toward the door
         "street": ((470, -170, 64), (420, 280, 70))}     # from the street, square to the porch


def post(sc):
    sc.mat["post"] = {"color": 0x1F2124, "roughness": 0.5, "metalness": 0.6}


VARIANTS = {
    "plain": ("No porch details", []),
    "plan": ("Wood-look feature wall and porch ceiling (main plan)", [X.porch_feature]),
    "post": ("Main plan + a slim black steel corner post", [X.porch_feature, post]),
    "breeze": ("Main plan + breeze-block screen on the seat wall (over the 42\" front-yard limit)",
               [X.porch_feature, X.porch_breeze]),
}


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shots = []
    for key, (title, steps) in VARIANTS.items():
        sc = M.build_schematic()
        X.chosen_exterior(sc, porch=False)
        for step in steps:
            step(sc)
        out_dir = OUT / f"porch-{key}"
        M.write_model(sc, out_dir, {**sc.meta})
        for view, cam in VIEWS.items():
            png = OUT / f"porch-{key}-{view}.png"
            X.screenshot(out_dir / "house.html", png, *cam)
        shots.append((key, f"{key}: {title}"))
    for view, where in (("court", "from the entry court"), ("street", "from the street")):
        fig, axs = plt.subplots(2, 2, figsize=(14, 9))
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
