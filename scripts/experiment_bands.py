# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: long horizontal bands on the street wall, between the window heads and the clerestory,
as the second building-articulation strategy instead of canopies (Table 22.140.520-C: "horizontal
or vertical banding or material, projected or recessed 6 inches, entire length of the building").
Every option keeps the recessed street windows and has no canopies.

  recessed     recessed windows only (reference)
  band-9-dark  one dark metal band, 8" tall and 6" proud, at the porch ceiling line (9')
  mid          one band centred between the window heads and the clerestory glass
  mid-wrap     the centred band continued around both ends of the house
  mid-all      the centred band all the way round, rear wall too
  mid-dark     the same band in dark metal
  thirds       two bands splitting the wall between the window heads and the clerestory into thirds
  edges-dark   a band filling the course from 9' to the 11' wall plate (between the model's edge
               lines, below the clerestory), dark, 6" proud
  edges-wood   the same band in wood-look
  tone-dark    two-tone: everything above the 9' ceiling line a dark stucco, all round the house
  tone-wood    two-tone: wood-look above the 9' line, all round
  tone-mid     two-tone dark, split at the midpoint between the window heads and the clerestory

Writes renders/experiments/band-<option>/house.html, band-<option>-{street,front,close,west,rear}.png and
band-compare-{street,front,close,west,rear}.png.

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


VIEWS = {**A.VIEWS, "west": ((1560, -160, 70), (1000, 330, 100)), "rear": ((1450, 1150, 150), (800, 450, 90))}
HEAD = 96.0                                          # window heads
MID = (HEAD + G0) / 2


def band(z0, z1, colour, proud=6.0):
    def f(sc):
        sc.boxes["band"].append([E, N - proud, W, N, z0, z1])
        sc.mat["band"] = {"color": colour}
    return f


def band_wrap(z0, z1, colour, rear=False, proud=6.0):
    """The band continued around both ends of the house (and the rear), meeting at the corners."""
    Sth = S.S
    def f(sc):
        ys = Sth + (proud if rear else 0.0)
        sc.boxes["band"] += [[E - proud, N - proud, W + proud, N, z0, z1],          # street
                             [E - proud, N, E, ys, z0, z1], [W, N, W + proud, ys, z0, z1]]   # ends
        if rear:
            sc.boxes["band"].append([E - proud, Sth, W + proud, Sth + proud, z0, z1])
        sc.mat["band"] = {"color": colour}
    return f


def centred(zc, h=8.0):
    return zc - h / 2, zc + h / 2


def tone(z, colour):
    """A second colour on every wall above height z (just proud of the stucco), around the clerestory."""
    under = X.shed_vault_under(2 / 12)
    Sth, d = S.S, 0.3
    lx0, lx1 = X.LOUNGE_X
    def f(sc):
        q = lambda a, b, c, e: X.quad(sc, "tone", a, b, c, e)       # noqa: E731
        y = N - d                                                    # street wall, around the glass
        for a, b, z0, z1 in ((E, lx0, z, TOP), (lx1, W, z, TOP), (lx0, lx1, z, G0), (lx0, lx1, G0 + 36, TOP)):
            q([a, y, z0], [b, y, z0], [b, y, z1], [a, y, z1])
        if under(Sth) > z:                                           # rear wall
            q([E, Sth + d, z], [W, Sth + d, z], [W, Sth + d, under(Sth)], [E, Sth + d, under(Sth)])
        for x in (E - d, W + d):                                     # end walls, up to the slope
            q([x, N, z], [x, Sth, z], [x, Sth, max(z, under(Sth))], [x, N, under(N)])
        sc.mat["tone"] = {"color": colour}
    return f


VARIANTS = {   # key -> (title, [steps])
    "recessed": ("Recessed windows only (no band)", [A.recessed]),
    "band-9-dark": ("Dark band at the porch ceiling line (9')", [A.recessed, band(108, 116, DARK)]),
    "mid": ("One band centred between window heads and clerestory", [A.recessed, band(*centred(MID), GREY)]),
    "mid-wrap": ("The centred band, wrapped around both ends (main plan)", [A.recessed, band_wrap(*centred(MID), GREY)]),
    "mid-all": ("The centred band, all the way round (rear too)",
                [A.recessed, band_wrap(*centred(MID), GREY, rear=True)]),
    "mid-dark": ("The centred band in dark metal", [A.recessed, band(*centred(MID), DARK)]),
    "thirds": ("Two bands, the wall above the windows in thirds",
               [A.recessed] + [band(*centred(HEAD + (G0 - HEAD) * k / 3), GREY) for k in (1, 2)]),
    "edges-dark": ("Band filling the 9'-11' course (between the edge lines), dark, 6\" proud",
                   [A.recessed, band(108, X.PLATE, DARK)]),
    "edges-wood": ("The same 9'-11' band in wood-look, 6\" proud", [A.recessed, band(108, X.PLATE, WOOD)]),
    "tone-dark": ("Two-tone: dark stucco above the 9' line, all round", [A.recessed, tone(108, 0x7C8187)]),
    "tone-wood": ("Two-tone: wood-look above the 9' line, all round", [A.recessed, tone(108, WOOD)]),
    "tone-mid": ("Two-tone dark, split midway between windows and clerestory", [A.recessed, tone(MID, 0x7C8187)]),
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
        for view, (cam, tgt) in VIEWS.items():
            X.screenshot(out_dir / "house.html", OUT / f"band-{key}-{view}.png", cam, tgt)
    for view in VIEWS:
        fig, axs = plt.subplots(6, 2, figsize=(16, 23.4 if view == "street" else 29.4))
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
