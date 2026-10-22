# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a hall closet in the walk-in closet's hall-side corner, by the cased opening.

  - The hall's cased opening (and its dropped header) moves about 14" east, in line with the walk-in closet's
    end wall, just past the common bath door, so its wall stub lands at the closet's corner.
  - A hall closet about 2'-3" wide x 2' deep in that corner, opening onto the hall right past the stub through
    24" doors (bifold here) 7'-6" tall, their heads in line with the dropped header: linens and towels, or
    the vacuum and cleaning supplies.
  - The walk-in closet loses that corner's shelf unit and about 7" of the hall-side hanging (its drawer
    stack gets a little narrower); its 3' aisle and the hall's 4' width are unchanged.

Writes renders/experiments/hall-closet.png (with the current plan, hall-closet-current.png, to compare)
and a 3D model with a view down the hall. Not part of the regular build.

    uv run scripts/experiment_hall_closet.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
ARCH = 883.5                                    # cased opening moved 14" east, in line with the closet's end wall
DOOR = (ARCH + S.INT / 2 + 1.5, ARCH + S.INT / 2 + 25.5)   # 24" hall closet doors, right past its stub
CL_W, CL_D = DOOR[1] + 1.5 - (ARCH + S.INT / 2), 24.0       # hall closet: as wide as its doors, 2' deep
_build, _wic = S.build, S.wic


def plan():
    for i, w in enumerate(S.WALLS):
        if w[0] == "hall threshold":
            S.WALLS[i] = (w[0], w[1], ARCH, *w[3:])
    x0 = S.face("utility|bath", +1)
    y0 = S.face("south hall wall", +1)
    S.WALLS.append(("hall closet|wic", "x", y0 + CL_D + S.INT / 2, 883.5, x0 + CL_W + S.INT, S.INT))
    S.WALLS.append(("hall closet|wic end", "y", x0 + CL_W + S.INT / 2, S.HALL_S, y0 + CL_D + S.INT, S.INT))
    S.OPENINGS.append(("south hall wall", *DOOR, "bifold", "a", +1))


def wic(sh):
    """As the main plan's, less the hall-side corner: hanging starts past the hall closet."""
    x0, x1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    y0, y1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    cy = S.face("hall closet|wic", +1)
    hx = S.face("hall closet|wic end", +1)
    fu = "A-FURN"

    def hang(a, b, y, d):
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hang(hx, 1023.0, y0, +1)                                   # hall side: from the hall closet to the landing
    hang(x0 + 24, x1, y1, -1)                                  # bath side, as now
    sh.rect(x0, y1 - 24, x0 + 24, y1, fu); sh.text("SHELVES", x0 + 12, y1 - 12, 2.2)
    sh.rect(x0, cy, x0 + 20, y1 - 24, fu)
    sh.text("DRAWERS", x0 + 10, (cy + y1 - 24) / 2, 2.2, rot=90)
    S.room_label(sh, "WIC", x0, y0, x1, y1, cx=1000.0, h=5.0)
    c0, c1 = x0, S.face("hall closet|wic end", -1)            # the hall closet
    cb = S.face("hall closet|wic", -1)                         # its back wall's hall-closet face
    sh.rect(c0, cb - 14, c1, cb, fu); sh.text("SHELVES", (c0 + c1) / 2, cb - 7, 1.8)
    sh.text("HALL CLOSET", (c0 + c1) / 2, cb - 18, 1.6)


def render(png, sh):
    S.render(sh.doc, png, 760.0, 330.0, S.W + 30, S.S + 30, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "hall-closet"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"down-the-hall": ((800, 415, 63.5), (1000, 455, 45))}
        for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
            tmp = html.with_name(f"_{name}.html")
            tmp.write_text(html.read_text().replace(hook, hook + (
                "\norbit.enabled = false; groups.labels.visible = false;"
                "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
                "camera.fov = 70; camera.updateProjectionMatrix();"
                f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
            subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                            "--window-size=1400,900", "--virtual-time-budget=15000",
                            f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/")],
                           capture_output=True)
            tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render(OUT / "hall-closet-current.png", _build())
    plan()
    S.wic = wic
    render(OUT / "hall-closet.png", S.build())
    model()


if __name__ == "__main__":
    main()
