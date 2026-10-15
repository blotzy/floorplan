# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: glass layouts for the front door (36" x 8' slab), all common off-the-shelf types.

  rect      one 24" x 12" horizontal lite near the top (the main plan)
  narrow    one narrow vertical lite, ~8" x 72", on the hinge side
  slots     four stacked horizontal slots, ~20" x 4", on the hinge side
  staggered three small lites stepping diagonally (the classic Eichler "atomic" door)
  half      a centred half lite, ~22" x 36"

Writes renders/experiments/door-<option>.png (close-up from the entry court), door-compare.png and a
3D model per option.

    uv run scripts/experiment_door.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
D0, D1 = next(o for o in S.OPENINGS if o[0] == "porch front" and o[3] == "door")[1:3]
Y0, Y1 = S.PORCH_Y + 1.8, S.PORCH_Y + 5.2           # glass just proud of both door faces
HINGE = D0 + 4                                        # door hinges on its east (D0) side

VARIANTS = {   # key -> (title, [(x0, x1, z0, z1), ...])
    "rect": ("One 24\" x 12\" horizontal lite near the top (main plan)",
             [((D0 + D1) / 2 - 12, (D0 + D1) / 2 + 12, 78, 90)]),
    "narrow": ("Narrow vertical lite, ~8\" x 72\", hinge side", [(HINGE, HINGE + 8, 14, 86)]),
    "slots": ("Four stacked horizontal slots, ~20\" x 4\", hinge side",
              [(HINGE, HINGE + 20, z, z + 4) for z in (56, 64, 72, 80)]),
    "staggered": ("Three small lites stepping diagonally (Eichler 'atomic')",
                  [(HINGE + 2 + 9 * i, HINGE + 8 + 9 * i, 80 - 12 * i, 88 - 12 * i) for i in range(3)]),
    "half": ("Centred half lite, ~22\" x 36\"",
             [((D0 + D1) / 2 - 11, (D0 + D1) / 2 + 11, 48, 84)]),
}
VIEW = ((404, 150, 58), (404, 290, 52))               # from the entry court, square to the door


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for key, (_, lites) in VARIANTS.items():
        sc = M.build_schematic()
        X.chosen_exterior(sc)
        sc.boxes["glass"] = [b for b in sc.boxes["glass"] if b[1] != Y0]       # drop the plan's lite
        for x0, x1, z0, z1 in lites:
            sc.boxes["glass"].append([x0, Y0, x1, Y1, z0, z1])
        out_dir = OUT / f"door-{key}"
        M.write_model(sc, out_dir, sc.meta)
        X.screenshot(out_dir / "house.html", OUT / f"door-{key}.png", *VIEW)
    fig, axs = plt.subplots(2, 3, figsize=(15, 7.5))
    for ax, (key, (title, _)) in zip(axs.flat, VARIANTS.items()):
        png = OUT / f"door-{key}.png"
        if png.exists():
            im = plt.imread(png)
            h, w = im.shape[:2]
            ax.imshow(im[int(h * .05):int(h * .95), int(w * .3):int(w * .7)])
        ax.set_title(f"{key}: {title}", fontsize=9); ax.axis("off")
    axs.flat[-1].axis("off")
    fig.suptitle("Front door glass options (from the entry court)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "door-compare.png", dpi=100)
    plt.close(fig)
    print("  ", (OUT / "door-compare.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
