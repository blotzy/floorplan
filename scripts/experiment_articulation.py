# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: street-facade articulation without changing the roof (County building articulation,
Table 22.140.520-C): street windows recessed 6" ("recessed windows, 6 inches deep for over 50% of
the facade window area") plus metal canopies 3' deep over the street windows ("weather protection
or shading device over windows, 3 feet deep for 50% of the windows"), in different styles and
heights. Each canopy runs 1' past its window and no farther (22.110.090.B), so they stay separate.

  plan       before: no recess, no canopies (reference)
  recessed   recessed windows only
  flat-8     thin flat plate just above the 8' window heads
  flat-9     thin flat plate at 9', in line with the porch ceiling
  hood-9     at 9', with a deep front fascia and side cheeks (a boxed hood)
  louver-9   at 9', open aluminium louver blades between two outriggers
  tilt-9     at 9', a thin plate rising toward its outer edge
  all-9      flat-9, plus a short canopy over the shared ensuite's small high window (all five)

All but plan and recessed: recessed windows + canopies over the lounge, gym, guest and office
windows (four of the five street windows). Writes renders/experiments/canopy-<option>/house.html,
canopy-<option>-{street,front,close}.png and canopy-compare-{street,front,close}.png.

    uv run scripts/experiment_articulation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

N = S.N
OUT = S.RENDERS / "experiments"
DEPTH, RUN = 36.0, 12.0                    # canopy depth off the wall; run past each side of the window
WINS = [(o[1], o[2], *(o[4:6] if len(o) > 4 else (30.0, 96.0)))
        for o in S.OPENINGS if o[0] == "north" and o[3] == "window"]      # (x0, x1, sill, head)
BIG = [w for w in WINS if w[2] < 60]                                        # not the ensuite's high window
VIEWS = {"street": X.VIEWS["street"], "front": ((800, -300, 70), (800, 300, 100)),
         "close": ((560, -110, 62), (900, 250, 100))}
DARK = 0x2B2D30


def recessed(sc):
    """Glass 6" behind the stucco face (the openings' jambs are already drawn)."""
    yc = N + S.EXT / 2
    for q in sc.quads["glass"]:
        if abs(q[1] - yc) < 0.01 and abs(q[3] - yc) < 0.01 and q[4] < 100:
            q[1] = q[3] = N + 6.0


def flat(z, wins=BIG):
    def f(sc):
        for x0, x1, _, head in wins:
            zb = max(z, head + 2)
            sc.boxes["canopy"].append([x0 - RUN, N - DEPTH, x1 + RUN, N, zb, zb + 3])
    return f


def hood(z):
    def f(sc):
        for x0, x1, _, _ in BIG:
            a, b = x0 - RUN, x1 + RUN
            sc.boxes["canopy"].append([a, N - DEPTH, b, N, z + 6, z + 8])           # top plate
            sc.boxes["canopy"].append([a, N - DEPTH, b, N - DEPTH + 2, z, z + 8])   # front fascia
            for x in (a, b - 2):                                                     # side cheeks
                sc.boxes["canopy"].append([x, N - DEPTH, x + 2, N, z, z + 8])
    return f


def louver(z):
    def f(sc):
        for x0, x1, _, _ in BIG:
            a, b = x0 - RUN, x1 + RUN
            for x in (a, b - 2):                                                     # outriggers
                sc.boxes["canopy"].append([x, N - DEPTH, x + 2, N, z, z + 5])
            sc.boxes["canopy"].append([a, N - DEPTH, b, N - DEPTH + 2, z, z + 5])   # front rail
            y = N - 6
            while y > N - DEPTH + 2:                                                 # blades every 5"
                sc.boxes["canopy"].append([a + 2, y - 2.5, b - 2, y, z + 1.5, z + 2.5])
                y -= 5
    return f


def tilt(z, rise=6.0):
    def f(sc):
        for x0, x1, _, _ in BIG:
            a, b = x0 - RUN, x1 + RUN
            y0, y1 = N, N - DEPTH
            for dz in (0.0, 2.0):                                                    # underside, top
                X.quad(sc, "canopy", [a, y0, z + dz], [b, y0, z + dz], [b, y1, z + rise + dz], [a, y1, z + rise + dz])
            X.quad(sc, "canopy", [a, y1, z + rise], [b, y1, z + rise], [b, y1, z + rise + 2], [a, y1, z + rise + 2])
            for x in (a, b):
                X.quad(sc, "canopy", [x, y0, z], [x, y1, z + rise], [x, y1, z + rise + 2], [x, y0, z + 2])
    return f


VARIANTS = {   # key -> (title, [steps])
    "plan": ("Before: no recess, no canopies", []),
    "recessed": ("Street windows recessed 6\" (no canopies)", [recessed]),
    "flat-8": ("Recessed + thin flat canopies just above the 8' window heads ", [recessed, flat(98.0)]),
    "flat-9": ("Recessed + thin flat canopies at 9' (porch ceiling line)", [recessed, flat(108.0)]),
    "hood-9": ("Recessed + boxed hoods at 9' (front fascia, side cheeks)", [recessed, hood(104.0)]),
    "louver-9": ("Recessed + open louvered sunshades at 9'", [recessed, louver(106.0)]),
    "tilt-9": ("Recessed + thin canopies at 9', rising toward the edge", [recessed, tilt(106.0)]),
    "all-9": ("Recessed + flat canopies at 9' over all five street windows", [recessed, flat(108.0, WINS)]),
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
        sc.mat["canopy"] = {"color": DARK}
        out_dir = OUT / f"canopy-{key}"
        M.write_model(sc, out_dir, sc.meta)
        for view, (cam, tgt) in VIEWS.items():
            X.screenshot(out_dir / "house.html", OUT / f"canopy-{key}-{view}.png", cam, tgt)
    for view in VIEWS:
        fig, axs = plt.subplots(4, 2, figsize=(16, 15.6 if view == "street" else 19.6))
        for ax, (key, (title, _)) in zip(axs.flat, VARIANTS.items()):
            png = OUT / f"canopy-{key}-{view}.png"
            if png.exists():
                im = plt.imread(png)
                h, w = im.shape[:2]
                ax.imshow(im[int(h * .12):int(h * .75), int(w * .08):int(w * .95)] if view == "street" else im)
            ax.set_title(f"{key}: {title}", fontsize=11); ax.axis("off")
        fig.tight_layout()
        try:
            fig.savefig(OUT / f"canopy-compare-{view}.png", dpi=90)
        except OSError:                    # locked by a Windows image viewer
            import time
            fig.savefig(OUT / f"canopy-compare-{view}-{time.strftime('%H%M%S')}.png", dpi=90)
        plt.close(fig)
        print("  ", (OUT / f"canopy-compare-{view}.png").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
