# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a second dropped header in the bedroom hall, where it meets the great room, matching the one past
the linen closet (a 3'-0" cased opening under a 7'-6" header), so the long view down the hall reads as segments.

Writes renders/experiments/hall-header.png and 3D views from the lounge, with and without the header, to
renders/experiments/hall-header/. Not part of the regular build.

    uv run scripts/experiment_hall_header.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
MOUTH = 674.0                                   # in line with the lounge | gym and kitchen | pantry walls


def plan():
    S.WALLS.append(("hall mouth", "y", MOUTH, S.HALL_N, S.HALL_S, S.INT))
    S.OPENINGS.append(("hall mouth", 413.2, 449.2, "cased", 0.0, S.ARCH_HEAD))


def model(name):
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    sc.boxes["wall"].append([S.face("lounge|gym", +1), S.N_IN, S.W_IN, S.S_IN, 108, 109])   # the wing's flat ceiling
    out = OUT / "hall-header"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    yc = (S.face("bedroom hall wall", +1) + S.face("south hall wall", -1)) / 2
    (cx, cy, cz), (tx, ty, tz) = (560, yc + 6, 62), (1200, yc, 66)
    tmp = html.with_name("_shot.html")
    tmp.write_text(html.read_text().replace(hook, hook + (
        "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;gridGroup.visible=false;"
        "document.getElementById('ui').style.display='none';document.getElementById('help').style.display='none';"
        "camera.fov=60;camera.updateProjectionMatrix();"
        f"camera.position.set({cx}*IN,{cz}*IN,{-cy}*IN);orbit.target.set({tx}*IN,{tz}*IN,{-ty}*IN);"
        f"camera.lookAt({tx}*IN,{tz}*IN,{-ty}*IN);}},50);")))
    subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                    "--window-size=1400,900", "--virtual-time-budget=15000",
                    f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/") + "#roof"],
                   capture_output=True)
    tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hall-header").mkdir(exist_ok=True)
    model("from-lounge-current")
    plan()
    sh = S.build()
    S.render(sh.doc, OUT / "hall-header.png", 640.0, S.HALL_N - 60, 1225.0, S.HALL_S + 60, width_in=14, dpi=180)
    model("from-lounge-with-header")


if __name__ == "__main__":
    main()
