# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: long horizontal bands on the street wall, between the window heads and the clerestory,
as the second building-articulation strategy instead of canopies (Table 22.140.520-C: "horizontal
or vertical banding or material, projected or recessed 6 inches, entire length of the building").
Every option keeps the recessed street windows and has no canopies.

  recessed     recessed windows only (reference)
  band-9       one band 8" tall, 6" proud, at the porch ceiling line (9'), the whole length
  band-9-dark  the same band in dark metal, matching the fascia
  band-two     two bands: one at 9', one under the clerestory glass
  band-wood    one tall wood-look band, 6" proud, filling the wall from 9' to the clerestory
  reveal       a 4" recessed reveal (shadow line) at 10', the whole length

Writes renders/experiments/band-<option>/house.html, band-<option>-{street,front,close}.png and
band-compare-{street,front,close}.png.

    uv run scripts/experiment_bands.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_articulation as A  # noqa: E402
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

E, W, N = S.E, S.W, S.N
OUT = S.RENDERS / "experiments"
TOP = X.shed_vault_under(2 / 12)(N)
G0 = X.PLATE + (TOP - X.PLATE - 36.0) / 2           # underside of the clerestory glass
GREY, DARK, WOOD = 0x8E8A84, 0x2B2D30, 0xA8754B


def band(z0, z1, colour, proud=6.0):
    def f(sc):
        sc.boxes["band"].append([E, N - proud, W, N, z0, z1])
        sc.mat["band"] = {"color": colour}
    return f


def reveal(z0, z1):
    def f(sc):                                       # drawn as the reveal's shadow on the wall face
        sc.boxes["band"].append([E, N - 0.3, W, N, z0, z1])
        sc.mat["band"] = {"color": 0x6E6A64}
    return f


VARIANTS = {   # key -> (title, [steps])
    "recessed": ("Recessed windows only (no band)", [A.recessed]),
    "band-9": ("One 8\" band, 6\" proud, at the porch ceiling line", [A.recessed, band(108, 116, GREY)]),
    "band-9-dark": ("The same band in dark metal (matches the fascia)", [A.recessed, band(108, 116, DARK)]),
    "band-two": ("Two bands: 9' and under the clerestory", [A.recessed, band(108, 116, GREY),
                                                            band(G0 - 8, G0, GREY)]),
    "band-wood": ("Tall wood-look band, 6\" proud, 9' to the clerestory", [A.recessed, band(108, G0, WOOD)]),
    "reveal": ("4\" recessed reveal at 10' (shadow line)", [A.recessed, reveal(120, 124)]),
}


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for key, (_, steps) in VARIANTS.items():
        sc = M.build_schematic()
        X.chosen_exterior(sc, facade=False)
        for step in steps:
            step(sc)
        out_dir = OUT / f"band-{key}"
        M.write_model(sc, out_dir, sc.meta)
        for view, (cam, tgt) in A.VIEWS.items():
            X.screenshot(out_dir / "house.html", OUT / f"band-{key}-{view}.png", cam, tgt)
    for view in A.VIEWS:
        fig, axs = plt.subplots(3, 2, figsize=(16, 11.7 if view == "street" else 14.7))
        for ax, (key, (title, _)) in zip(axs.flat, VARIANTS.items()):
            png = OUT / f"band-{key}-{view}.png"
            if png.exists():
                im = plt.imread(png)
                h, w = im.shape[:2]
                ax.imshow(im[int(h * .12):int(h * .75), int(w * .08):int(w * .95)] if view == "street" else im)
            ax.set_title(f"{key}: {title}", fontsize=11); ax.axis("off")
        fig.tight_layout()
        try:
            fig.savefig(OUT / f"band-compare-{view}.png", dpi=90)
        except OSError:                    # locked by a Windows image viewer
            import time
            fig.savefig(OUT / f"band-compare-{view}-{time.strftime('%H%M%S')}.png", dpi=90)
        plt.close(fig)
        print("  ", (OUT / f"band-compare-{view}.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
