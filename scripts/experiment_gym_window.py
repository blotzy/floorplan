# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: two ways to keep the shed's west edge off the gym's street window (in the main plan the edge
lands partway along it).

  gym-window       the gym window slides about 2'-10" toward the lounge, ending about 1'-5" short of the
                   shed's edge; the roof is unchanged.
  shed-to-ensuite  the shed runs on to the gym|ensuite wall, so its edge lands on a wall line and the whole
                   gym window sits under it; the clerestory stays where it is (no longer centred in the shed).

For each: the street elevation, a 3D model (renders/experiments/<name>/house.html) and street views.
Not part of the regular build.

    uv run scripts/experiment_gym_window.py
"""
from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402
import exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import zoning_set as Z  # noqa: E402

OUT = S.RENDERS / "experiments"
GYM_WINDOW = (680.0, 752.0)                # 6' window, 4" off the gym's east wall
CHROME = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")


def slide_window():
    S.OPENINGS[:] = [("north", *GYM_WINDOW, "window") if o[0] == "north" and o[1] == 714.0 else o
                     for o in S.OPENINGS]


def extend_shed():
    X.SPLIT_WIDE_X = (S.E, S.wall_info("gym|ensuite")[1])
    X.WING_X = X.SPLIT_WIDE_X[1]


def elevation_png(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 4.2))
    ax = fig.add_axes([0.01, 0.02, 0.98, 0.9])
    Z.elevation(ax, "north")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def model(out):
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True, "roof_options": {}, "roof_flat": []})
    return out / "house.html"


def views(html):
    if not CHROME.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    for name, ((cx, cy, cz), (tx, ty, tz)) in {"street": ((1350, -260, 70), (700, 330, 110)),
                                               "front": ((760, -420, 66), (760, 300, 110))}.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            ";orbit.enabled = false; groups.labels.visible = false;"
            "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
            "camera.fov = 60; camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
        subprocess.run([str(CHROME), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(html.parent)}\\{name}.png",
                        "file:///" + win(tmp).replace("\\", "/") + "#roof"], capture_output=True)
        tmp.unlink()


def main():
    base = (copy.deepcopy(S.OPENINGS), X.SPLIT_WIDE_X, X.WING_X)
    for name, change in (("gym-window", slide_window), ("shed-to-ensuite", extend_shed)):
        change()
        out = OUT / name
        out.mkdir(parents=True, exist_ok=True)
        elevation_png(out / "street-elevation.png")
        views(model(out))
        S.OPENINGS[:], X.SPLIT_WIDE_X, X.WING_X = copy.deepcopy(base[0]), base[1], base[2]


if __name__ == "__main__":
    main()
