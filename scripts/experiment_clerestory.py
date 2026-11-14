# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the lounge clerestory as three stock 5'-6" x 3'-0" units (16'-6" of glass) instead of three
6'-0" units (18'-0"), still centred over the lounge: about 10" of wall at each end instead of about 1 1/4",
room for the king and jack studs (or a post), the drywall returns and the trim where the TV wall and the
gym wall meet the street wall.

Writes 3D models and views (current vs 5'-6": inside the lounge toward each end of the band, and from across
the street) to renders/experiments/clerestory/, and a side-by-side comparison
renders/experiments/clerestory.png. Not part of the regular build.

    uv run scripts/experiment_clerestory.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments" / "clerestory"
UNIT = 66.0
SHOTS = {"tv-wall-end": ((600, 420, 63.5), (470, 252, 165), "lounge, toward the TV-wall end"),
         "gym-wall-end": ((520, 420, 63.5), (660, 252, 165), "lounge, toward the gym-wall end"),
         "street": ((560, -200, 62), (560, 250, 150), "from across the street")}


def model(key):
    import exterior as X
    import make_3d as M
    saved = X.CLERESTORY_UNIT, X.CLERESTORY_X, X.shed_gable.__defaults__
    if key == "stock":
        X.CLERESTORY_UNIT = UNIT
        X.CLERESTORY_X = tuple(sum(X.LOUNGE_X) / 2 + d * X.CLERESTORY_UNITS * UNIT / 2 for d in (-1, 1))
        xs, _, seams, band = X.shed_gable.__defaults__
        X.shed_gable.__defaults__ = (xs, X.CLERESTORY_X, seams, band)
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    X.CLERESTORY_UNIT, X.CLERESTORY_X, X.shed_gable.__defaults__ = saved
    out = OUT / key
    M.write_model(sc, out, sc.meta)
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    html = out / "house.html"
    for name, ((cx, cy, cz), (tx, ty, tz), _) in SHOTS.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;gridGroup.visible=false;"
            "scene.traverse(o=>{if(o.isSprite||o.type==='ArrowHelper')o.visible=false;});"
            "document.getElementById('ui').style.display='none';document.getElementById('help').style.display='none';"
            "camera.fov=70;camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN,{cz}*IN,{-cy}*IN);orbit.target.set({tx}*IN,{tz}*IN,{-ty}*IN);"
            f"camera.lookAt({tx}*IN,{tz}*IN,{-ty}*IN);}},50);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/") + "#roof"],
                       capture_output=True)
        tmp.unlink()


def compare():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    import zoning_set as Z
    rows = (("current", "Current: 3 x 6'-0\" (about 1 1/4\" of wall each end)"),
            ("stock", "3 x 5'-6\" stock (about 10\" of wall each end)"))
    fig, axs = plt.subplots(2, len(SHOTS), figsize=(5 * len(SHOTS), 7.2))
    for (key, title), row in zip(rows, axs):
        for ax, (name, (_, _, label)) in zip(row, SHOTS.items()):
            p = OUT / key / f"{name}.png"
            if p.exists():
                ax.imshow(mpimg.imread(p))
            ax.set_title(f"{title}\n{label}" if ax is row[0] else f"\n{label}", fontsize=9, loc="left")
            ax.axis("off")
    fig.tight_layout()
    Z.save_png(fig, OUT.parent / "clerestory.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for k in ("current", "stock"):
        model(k)
    compare()
