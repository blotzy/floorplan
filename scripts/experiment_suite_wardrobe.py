# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: no walk-in closet; a wardrobe wall for the primary bedroom, a bigger primary bath and a hall
storage closet.

  - The walk-in closet goes. A 24"-deep built-in wardrobe with sliding doors runs along the bedroom's east
    wall, set into the suite block (the bedroom keeps its size); its sliding doors stay clear of the bedroom
    door's swing.
  - The bath takes most of the block: the same wet room (back-to-wall tub and curbless shower on the plumbing
    wall), with the double vanity on the storage-closet wall and the WC on the wardrobe wall. Door from the bedroom at the rear-wall end, as
    now.
  - A 3'-deep storage closet along the hall, with bifold doors off the hall (linen, bulk storage).
  - The bedroom has one door (the bath's) besides its own and the wardrobe's sliding doors.

Writes renders/experiments/suite-wardrobe.png and a 3D model with a view from the bedroom. Not part of the
regular build.

    uv run scripts/experiment_suite_wardrobe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
WARD_D = 24.0                                   # wardrobe depth
WARD_END = 566.0                                # the wardrobe runs from the hall wall to here; the bath door beyond
STORE_WALL = 497.0                              # hall storage closet | bath wall (centreline)


def plan():
    xw = 1062.0 - S.INT / 2 - WARD_D - S.INT / 2          # bath | wardrobe wall centreline
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = ("bath|wic", "x", STORE_WALL, 884.5, xw + S.INT / 2, S.INT)   # storage closet | bath
        elif w[0] == "suite|primary":
            ws[i] = ("suite|primary", "y", 1062.0, WARD_END, S.S_IN, S.INT)        # only beside the bath door
    ws.append(("bath|wardrobe", "y", xw, 457.0, WARD_END + S.INT / 2, S.INT))
    S.OPENINGS[:] = [o for o in S.OPENINGS if not (o[0] == "suite|primary" and o[1] == 463.0)]
    S.OPENINGS.append(("south hall wall", 898.0, 1022.0, "bifold", "a", +1))       # hall storage closet


def primary_bath(sh):
    m0, m1 = S.face("utility|bath", +1), S.face("bath|wardrobe", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + 80.0
    tz = (top + S.S_IN - S.TUB_L) / 2
    S.wet_zone(sh, m0, top, gx, S.S_IN)
    S.tub(sh, m0, tz, m0 + S.TUB_W, tz + S.TUB_L, "67x32 TUB")
    sx = (m0 + S.TUB_W + gx) / 2
    sh.text("CURBLESS", sx, (top + S.S_IN) / 2, 3.5, rot=90)
    S.shower_head(sh, sx, S.S_IN, -1)
    S.shower_head(sh, sx, top, +1)
    S.glass(sh, (gx, top), (gx, S.S_IN - 30))
    S.drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - 3))
    S.vanity(sh, m1 - 60, top, m1, top + 22, "DOUBLE VANITY 60")           # north (storage-closet) wall
    S.wc(sh, m1 - 28, top + 31, m1, top + 61)                                 # wardrobe wall, clear of the door
    for hx in (911.0, 999.0):
        sh.text("HIGH WINDOW", hx, S.S_IN - 4, 2.0)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + m1) / 2, cy=575.0, h=3.2)


def wic(sh):
    fu = "A-FURN"
    x0, x1 = S.face("bath|wardrobe", +1), 1062.0 + S.INT / 2           # wardrobe, open to the bedroom
    y0 = S.face("south hall wall", +1)
    sh.rect(x0, y0, x1, WARD_END - S.INT / 2, fu)
    sh.line(((x0 + x1) / 2, y0), ((x0 + x1) / 2, WARD_END - S.INT / 2), fu)
    sh.text("WARDROBE CLOSET, SLIDING DOORS", (x0 + x1) / 2, (y0 + WARD_END) / 2, 2.6, rot=90)
    s0, s1 = S.face("utility|bath", +1), S.face("bath|wardrobe", -1)    # hall storage closet
    sy0, sy1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    sh.rect(s0, sy0, s1, sy0 + 24, fu); sh.text("SHELVES", (s0 + s1) / 2, sy0 + 12, 2.6)
    S.room_label(sh, "HALL STORAGE", s0, sy0, s1, sy1, cy=sy1 - 4, h=2.6)


def render(png, sh):
    S.render(sh.doc, png, S.face("pantry|laundry", -1) - 20, S.face("south hall wall", -1) - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-wardrobe"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-bedroom": ((1190, 600, 63.5), (1040, 480, 50)), "overhead": ((1000, 700, 330), (980, 520, 0))}
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
    plan()
    S.primary_bath, S.wic = primary_bath, wic
    render(OUT / "suite-wardrobe.png", S.build())
    model()


if __name__ == "__main__":
    main()
