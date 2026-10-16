# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: street-facade articulation without changing the roof (County building articulation,
Table 22.140.520-C: at least one strategy plus one per 30 linear feet of street facade).

  plan       main plan as drawn
  canopies   flat metal eyebrow canopies, 3' deep, over the lounge, gym, guest and office windows
             (each canopy runs 1' past its window: 22.110.090.B), "weather protection or shading
             device over windows, 3 feet deep for 50% of the windows"
  recessed   street windows set 6" back from the stucco face, "recessed windows, 6 inches deep for
             over 50% of the facade window area"
  textured   dark fiber-cement board-and-batten on the bedroom wing's street wall, wrapping 4' around
             the west corner, "textured materials with relief"
  surrounds  projected window surrounds, 6" wide and 4" proud, around every street window
             (reviewed by hand: the County's tool doesn't assess it)
  combo      canopies + recessed + textured

Writes renders/experiments/artic-<option>/house.html, artic-<option>-{street,front}.png and
artic-compare-{street,front}.png.

    uv run scripts/experiment_articulation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

E, W, N = S.E, S.W, S.N
OUT = S.RENDERS / "experiments"
UNDER = X.shed_vault_under(2 / 12)
WINS = [(o[1], o[2], *(o[4:6] if len(o) > 4 else (30.0, 96.0)))
        for o in S.OPENINGS if o[0] == "north" and o[3] == "window"]      # (x0, x1, sill, head)
CANOPIED = [w for w in WINS if w[2] < 60]                                   # not the ensuite's high window
WING = S.face("lounge|gym", +1) - 2.25                                      # bedroom wing: wall line to the west end
VIEWS = {"street": X.VIEWS["street"], "front": ((800, -300, 70), (800, 300, 100))}


def canopies(sc):
    for x0, x1, _, head in CANOPIED:
        sc.boxes["canopy"].append([x0 - 12, N - 36, x1 + 12, N, head + 2, head + 5])
    sc.mat["canopy"] = {"color": 0x2B2D30}


def recessed(sc):
    """Glass from the wall's centre to 6" behind the stucco face (the openings' jambs are already drawn)."""
    yc = N + S.EXT / 2
    for q in sc.quads["glass"]:
        if abs(q[1] - yc) < 0.01 and abs(q[3] - yc) < 0.01 and q[4] < 100:
            q[1] = q[3] = N + 6.0


def textured(sc):
    """Board-and-batten panels (just proud of the stucco) on the wing's street wall and 4' around the corner."""
    y, top = N - 0.6, UNDER(N)
    xs = [WING]
    for x0, x1, _, _ in WINS:
        if x0 > WING:
            xs += [x0, x1]
    xs.append(W)
    for a, b in zip(xs[::2], xs[1::2]):                                      # full height between windows
        sc.boxes["cladding"].append([a, y, b, N, 0, top])
    for x0, x1, sill, head in WINS:
        if x0 > WING:
            sc.boxes["cladding"].append([x0, y, x1, N, 0, sill])
            sc.boxes["cladding"].append([x0, y, x1, N, head, top])
    sc.boxes["cladding"].append([W, N, W + 0.6, N + 48, 0, UNDER(N + 48)])  # wrap the west corner
    x = WING + 8
    while x < W:                                                             # battens every 16"
        z_gaps = [(0, top)]
        for x0, x1, sill, head in WINS:
            if x0 <= x <= x1:
                z_gaps = [(0, sill), (head, top)]
        for z0, z1 in z_gaps:
            sc.boxes["batten"].append([x, N - 1.5, x + 1.5, N - 0.6, z0, z1])
        x += 16
    for yb in range(int(N) + 8, int(N) + 48, 16):
        sc.boxes["batten"].append([W + 0.6, yb, W + 1.5, yb + 1.5, 0, UNDER(yb)])
    sc.mat["cladding"] = {"color": 0x646A70}
    sc.mat["batten"] = {"color": 0x565C62}


def surrounds(sc):
    for x0, x1, sill, head in WINS:
        y0 = N - 4
        for b in ((x0 - 6, x1 + 6, head, head + 6), (x0 - 6, x1 + 6, sill - 6, sill),
                  (x0 - 6, x0, sill, head), (x1, x1 + 6, sill, head)):
            sc.boxes["surround"].append([b[0], y0, b[1], N, max(0.0, b[2]), b[3]])
    sc.mat["surround"] = {"color": 0x2B2D30}


VARIANTS = {   # key -> (title, [steps])
    "plan": ("Main plan as drawn", []),
    "canopies": ("Metal eyebrow canopies, 3' deep, over 4 of the 5 street windows", [canopies]),
    "recessed": ("Street windows recessed 6\"", [recessed]),
    "textured": ("Fiber-cement board-and-batten on the bedroom wing", [textured]),
    "surrounds": ("Projected window surrounds, 6\" x 4\" (manual review)", [surrounds]),
    "combo": ("Canopies + recessed windows + board-and-batten", [canopies, recessed, textured]),
}


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for key, (_, steps) in VARIANTS.items():
        sc = M.build_schematic()
        X.chosen_exterior(sc)
        for step in steps:
            step(sc)
        out_dir = OUT / f"artic-{key}"
        M.write_model(sc, out_dir, sc.meta)
        for view, (cam, tgt) in VIEWS.items():
            X.screenshot(out_dir / "house.html", OUT / f"artic-{key}-{view}.png", cam, tgt)
    for view in VIEWS:
        fig, axs = plt.subplots(3, 2, figsize=(16, 14.4))
        for ax, (key, (title, _)) in zip(axs.flat, VARIANTS.items()):
            png = OUT / f"artic-{key}-{view}.png"
            if png.exists():
                ax.imshow(plt.imread(png))
            ax.set_title(f"{key}: {title}", fontsize=11); ax.axis("off")
        fig.tight_layout()
        try:
            fig.savefig(OUT / f"artic-compare-{view}.png", dpi=90)
        except OSError:                    # locked by a Windows image viewer
            import time
            fig.savefig(OUT / f"artic-compare-{view}-{time.strftime('%H%M%S')}.png", dpi=90)
        plt.close(fig)
        print("  ", (OUT / f"artic-compare-{view}.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
