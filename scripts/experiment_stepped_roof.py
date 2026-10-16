# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a stepped shed. The great room (foyer, lounge, dining, kitchen: everything east of the
lounge/gym and kitchen/pantry wall line) gets its own shed roof, raised above the bedroom wing's, so
the street facade has a roof height change (County building articulation, Table 22.140.520-C:
"variation in roof height, 4 feet high along at least 20% of facade length"). Both roofs keep the
2:12 slope and 3' eaves; the step is a stucco wall rising above the low roof.

  plan        main plan: one roof plane over the whole house
  step4       great room roof raised 4', clerestory glass still a 3' band
  step4-g4    raised 4', clerestory glass 4' tall (more glass: over the energy-code budget)
  step5       raised 5', 3' band

Writes renders/experiments/stepped-<option>/house.html, stepped-<option>-{street,aerial}.png and
stepped-compare-{street,aerial}.png.

    uv run scripts/experiment_stepped_roof.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

E, W, N, Sth = S.E, S.W, S.N, S.S
OUT = S.RENDERS / "experiments"
PITCH, OV = 2 / 12, X.EAVE
XS = 674.0                          # the step: lounge/gym and kitchen/pantry walls (one line)
quad = X.quad
VARIANTS = {   # key -> (title, rise, clerestory glass height)
    "plan": ("Main plan: one roof plane (roof height variation 0%)", 0.0, 36.0),
    "step4": ("Great room raised 4', 3' clerestory band", 48.0, 36.0),
    "step4-g4": ("Great room raised 4', 4' clerestory glass", 48.0, 48.0),
    "step5": ("Great room raised 5', 3' clerestory band", 60.0, 36.0),
}


def slab(sc, x0, x1, under):
    """Roof slab between x0 and x1 (eave overhangs front and rear), fascia all round."""
    Y0, Y1 = N - OV, Sth + OV
    for dz, mat in ((X.THK, "roofing"), (0.0, "soffit")):
        quad(sc, mat, [x0, Y0, under(Y0) + dz], [x1, Y0, under(Y0) + dz], [x1, Y1, under(Y1) + dz],
             [x0, Y1, under(Y1) + dz])
    for x in (x0, x1):
        quad(sc, "fascia", [x, Y0, under(Y0)], [x, Y1, under(Y1)], [x, Y1, under(Y1) + X.THK], [x, Y0, under(Y0) + X.THK])
    for y in (Y0, Y1):
        quad(sc, "fascia", [x0, y, under(y)], [x1, y, under(y)], [x1, y, under(y) + X.THK], [x0, y, under(y) + X.THK])


def stepped(sc, rise, glass):
    lo = X.shed_vault_under(PITCH)
    hi = lambda y: lo(y) + rise                                          # noqa: E731
    P = X.PLATE
    lx0, lx1 = X.LOUNGE_X
    slab(sc, XS, W + OV, lo)                                             # bedroom wing + utility block
    slab(sc, E - OV, XS + (6.0 if rise else 0.0), hi)                    # great room, lapping the step
    # walls up to the roof undersides
    quad(sc, "exterior", [E, N, P], [lx0, N, P], [lx0, N, hi(N)], [E, N, hi(N)])          # porch beam + corner
    X.clerestory(sc, lx0, lx1, hi(N), [(lx0, lx1, glass)])
    quad(sc, "exterior", [lx1, N, P], [XS, N, P], [XS, N, hi(N)], [lx1, N, hi(N)])
    quad(sc, "exterior", [XS, N, P], [W, N, P], [W, N, lo(N)], [XS, N, lo(N)])
    for a, b, f in ((E, XS, hi), (XS, W, lo)):                                                  # rear wall
        quad(sc, "exterior", [a, Sth, P], [b, Sth, P], [b, Sth, f(Sth)], [a, Sth, f(Sth)])
    for x, f in ((E, hi), (W, lo)):                                                             # end walls
        quad(sc, "exterior", [x, N, P], [x, Sth, P], [x, Sth, f(Sth)], [x, N, f(N)])
    if rise:                                                             # the step: stucco above the low roof
        quad(sc, "exterior", [XS, N, lo(N)], [XS, Sth, lo(Sth)], [XS, Sth, hi(Sth)], [XS, N, hi(N)])
    # interior: the vault follows the high roof (as in experiment_exterior.shed_vault_great)
    yf, kx, E_in = S.FOYER_WALL_END, S.face("kitchen|pantry", -1), S.E_IN
    fy, C = S.PORCH_Y + S.EXT, M.CEIL
    for x0, x1, y0, y1 in ((lx0, lx1, S.N_IN, yf), (E_in, lx0, fy, yf), (E_in, kx, yf, S.S_IN)):
        quad(sc, "wall", [x0, y0, hi(y0) - 1], [x1, y0, hi(y0) - 1], [x1, y1, hi(y1) - 1], [x0, y1, hi(y1) - 1])
    tv0, tv1 = S.face("foyer wall", -1), S.face("foyer wall", +1)
    for x, y0, y1 in ((lx0, S.N_IN, S.PORCH_Y), (lx1, S.N_IN, yf), (kx, yf, S.S_IN),
                      (tv0, fy, yf), (tv1, S.PORCH_Y, yf)):
        quad(sc, "wall", [x, y0, C], [x, y1, C], [x, y1, hi(y1)], [x, y0, hi(y0)])
    quad(sc, "wall", [tv0, yf, C], [tv1, yf, C], [tv1, yf, hi(yf)], [tv0, yf, hi(yf)])
    quad(sc, "wall", [E_in, fy, C], [lx0, fy, C], [lx0, fy, hi(fy)], [E_in, fy, hi(fy)])
    quad(sc, "wall", [kx, yf, C], [lx1, yf, C], [lx1, yf, hi(yf)], [kx, yf, hi(yf)])
    return hi(N - OV) + X.THK                                            # top of roof (street fascia)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    share = (XS - E) / (W - E)
    tops = {}
    for key, (_, rise, glass) in VARIANTS.items():
        sc = M.build_schematic()
        X.band(sc, "exterior", X.WALL_TOP, X.PLATE)
        tops[key] = stepped(sc, rise, glass)
        X.front_door(sc)
        sc.mat = {k: {"color": v} for k, v in X.STYLES["mcm-gable"][1].items()}
        X.porch_feature(sc)
        out_dir = OUT / f"stepped-{key}"
        M.write_model(sc, out_dir, sc.meta)
        for view, (cam, tgt) in X.VIEWS.items():
            X.screenshot(out_dir / "house.html", OUT / f"stepped-{key}-{view}.png", cam, tgt)
    for view in X.VIEWS:
        fig, axs = plt.subplots(2, 2, figsize=(16, 9.6))
        for ax, (key, (title, rise, _)) in zip(axs.flat, VARIANTS.items()):
            png = OUT / f"stepped-{key}-{view}.png"
            if png.exists():
                ax.imshow(plt.imread(png))
            ft, inch = divmod(round(tops[key]), 12)
            extra = f"  ·  step along {share:.0%} of the street facade" if rise else ""
            ax.set_title(f"{key}: {title}\ntop of roof ~{ft}'-{inch}\" above floor{extra}", fontsize=10)
            ax.axis("off")
        fig.tight_layout()
        try:
            fig.savefig(OUT / f"stepped-compare-{view}.png", dpi=90)
        except OSError:                    # locked by a Windows image viewer
            import time
            fig.savefig(OUT / f"stepped-compare-{view}-{time.strftime('%H%M%S')}.png", dpi=90)
        plt.close(fig)
        print("  ", (OUT / f"stepped-compare-{view}.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
