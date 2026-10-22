# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the primary bath and walk-in closet side by side instead of front to back.

  - The suite block between the bedroom and the laundry/common bath is split east-west: the bath on the east
    half, against the existing plumbing wall, from the hall to the rear wall; the closet on the west half,
    next to the bedroom. Both rooms are about 7' x 12'-5" instead of two 6'-wide strips.
  - One cased opening from the bedroom into the closet (a dressing room); the bath is reached through the
    closet by a pocket door. The bedroom loses one door.
  - Bath: a wet room across the rear wall (the back-to-wall tub under the high window, a curbless shower in
    front of it, the heads on the plumbing wall), the WC on the plumbing wall and a 60" double vanity on the
    hall wall. Closet: shelves along the hall wall, hanging down both long walls, shelves under the rear high
    window.

Writes renders/experiments/suite-side-by-side.png (with the current plan, suite-side-by-side-current.png, to
compare) and a 3D model with a view from the bedroom. Not part of the regular build.

    uv run scripts/experiment_suite_side_by_side.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
SPLIT = 973.0                                  # bath | closet wall centreline (east half / west half)
ENTRY = (485.0, 521.0)                         # 36" cased opening, bedroom -> closet
BATH_DOOR = (492.0, 522.0)                     # 30" pocket door, closet -> bath
WET_Y = 528.0                                  # the wet room's north edge (tub + shower to the rear wall)


def plan():
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = ("bath|wic", "y", SPLIT, 457.0, S.S_IN, S.INT)
    S.OPENINGS[:] = [o for o in S.OPENINGS if not (o[0] == "suite|primary" and o[3] == "door")]
    S.OPENINGS += [("suite|primary", *ENTRY, "cased"), ("bath|wic", *BATH_DOOR, "pocket", "a")]


def primary_bath(sh):
    m0, b1 = S.face("utility|bath", +1), S.face("bath|wic", -1)
    y0 = S.face("south hall wall", +1)
    S.wet_zone(sh, m0, WET_Y, b1, S.S_IN)
    tx = (m0 + b1) / 2 - S.TUB_L / 2                                       # tub centred under the high window
    S.tub(sh, tx, S.S_IN - S.TUB_W, tx + S.TUB_L, S.S_IN, "67x32 TUB")
    hy = (WET_Y + S.S_IN - S.TUB_W) / 2
    sh.circle((m0 + 4, hy), 2.5, "A-EQPM"); sh.heads.append((m0, hy, 1.0, 0.0))   # head on the plumbing wall
    sh.text("CURBLESS", (m0 + b1) / 2, hy, 3.0)
    S.glass(sh, (m0, WET_Y), (b1 - 30, WET_Y))                             # glass, with the way in by the door
    S.drain(sh, (m0 + 3, WET_Y + 3), (b1 - 3, WET_Y + 3))
    S.wc(sh, m0, 494.0, m0 + 28, 524.0)                                    # plumbing wall
    S.vanity(sh, b1 - 60, y0, b1, y0 + 22, "DOUBLE VANITY 60")             # hall wall
    sh.text("HIGH WINDOW", 911.0, S.S_IN - 4, 2.0)
    S.room_label(sh, "PRIMARY BATH", m0, y0, b1, S.S_IN, cx=(m0 + b1) / 2 + 8, cy=505.0, h=3.2)


def wic(sh):
    x0, x1 = S.face("bath|wic", +1), S.face("suite|primary", -1)
    y0, y1 = S.face("south hall wall", +1), S.S_IN
    fu = "A-FURN"
    sh.rect(x0, y0, x1, y0 + 18, fu); sh.text("SHELVES", (x0 + x1) / 2, y0 + 9, 2.4)
    for a, b in ((x0, x0 + 24), (x1 - 24, x1)):                            # hanging down both long walls
        sh.rect(a, WET_Y, b, y1, fu)
        sh.line(((a + b) / 2, WET_Y), ((a + b) / 2, y1), fu)
        sh.text("HANG", (a + b) / 2, (WET_Y + y1) / 2, 3.0, rot=90)
    sh.rect(x0 + 24, y1 - 16, x1 - 24, y1, fu); sh.text("SHELVES", (x0 + x1) / 2, y1 - 8, 2.0)
    sh.text("HIGH WINDOW", 999.0, S.S_IN - 20, 2.0)
    S.room_label(sh, "WIC / DRESSING", x0, y0, x1, y1, cx=(x0 + x1) / 2, cy=(WET_Y + y1) / 2 - 10, h=3.6)


def render(png, sh):
    S.render(sh.doc, png, S.face("pantry|laundry", -1) - 20, S.face("south hall wall", -1) - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-side-by-side"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-bedroom": ((1190, 520, 63.5), (1000, 545, 50)), "overhead": ((1000, 700, 330), (980, 520, 0))}
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
    render(OUT / "suite-side-by-side-current.png", S.build())
    plan()
    S.primary_bath, S.wic = primary_bath, wic
    render(OUT / "suite-side-by-side.png", S.build())
    model()


if __name__ == "__main__":
    main()
