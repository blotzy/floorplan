# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a flat 9' ceiling over the foyer.

  - The foyer (front door to the end of the foyer wall) gets a flat ceiling at 9', the porch soffit's height,
    instead of rising into the great room's vault: a low entry that opens into the tall great room past the
    end of the foyer wall (a drywall header steps up from 9' to the vault there).
  - The foyer wall still runs full height on the lounge (TV) side; on the foyer side the closets stop at 9'.

Writes a 3D model and views (current vs flat ceiling: from the front door, looking up, and back from the
dining room) to renders/experiments/foyer-ceiling/, and a side-by-side comparison
renders/experiments/foyer-ceiling.png. Not part of the regular build.

    uv run scripts/experiment_foyer_ceiling.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments" / "foyer-ceiling"
SHOTS = {"from-door": ((405, 304, 63.5), (420, 600, 75), "from the front door"),
         "looking-up": ((405, 304, 63.5), (420, 420, 160), "looking up from the door"),
         "from-dining": ((430, 560, 63.5), (405, 300, 90), "back toward the foyer from the dining room")}


def model(key):
    import exterior as X
    import make_3d as M
    orig = X.great_room_inside
    if key == "flat":
        fx = S.wall_info("foyer wall")[1]
        X.great_room_inside = lambda sc, under, ceil=None, xs=(), ys=(), foyer=None: orig(
            sc, under, ceil, xs, ys, foyer=(fx, M.CEIL))
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    X.great_room_inside = orig
    if key == "flat":                                                # the foyer's closets stop at the 9' ceiling
        x0, x1 = S.E_IN, S.face("foyer wall", -1)
        y0, y1 = S.PORCH_Y + S.EXT, S.FOYER_WALL_END
        for boxes in sc.boxes.values():
            for b in boxes:
                if x0 - 1 <= b[0] and b[2] <= x1 + 1 and y0 - 1 <= b[1] and b[3] <= y1 + 1 and b[5] > M.CEIL:
                    b[5] = M.CEIL
    out = OUT / key
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
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
    rows = (("current", "Current: foyer open to the vault"), ("flat", "Flat 9' foyer ceiling"))
    fig, axs = plt.subplots(2, len(SHOTS), figsize=(5 * len(SHOTS), 7.2))
    for (key, title), row in zip(rows, axs):
        for ax, (name, (_, _, label)) in zip(row, SHOTS.items()):
            p = OUT / key / f"{name}.png"
            if p.exists():
                ax.imshow(mpimg.imread(p))
            ax.set_title(f"{title}: {label}" if ax is row[0] else label, fontsize=9, loc="left")
            ax.axis("off")
    fig.tight_layout()
    Z.save_png(fig, OUT.parent / "foyer-ceiling.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for k in ("current", "flat"):
        model(k)
    compare()
