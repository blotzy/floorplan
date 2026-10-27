# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: from suite-wic-entry, a small foyer at the suite's entry, off the hall, leading to the
primary bedroom, the walk-in closet and the bath.

  - The foyer (about 3'-6" x 7'-0") takes the bedroom end of the walk-in closet, right off the hall. The
    suite's door moves from the bedroom's corner to the hall wall, opening into the foyer (hinged on the
    closet side, so it rests clear of the bedroom opening).
  - From the foyer: the bedroom through a cased opening at the hall end of its west side (so the bedroom's
    east wall stays whole for the TV, centred on the bed); the walk-in closet through a door on
    its east side (swinging into the closet); the bath through a door on its south side (swinging into the bath,
    opening flat on its end wall). The bedroom has no doors of its own besides the opening.
  - The walk-in closet is shorter (about 10'-7"), both sides hanging to the foyer wall; the corner shelves and
    drawers at the far end, as now. The hall closet stays in its corner.
  - The bath as in suite-wic-entry: a 6'-0" curbless shower at the plumbing-wall end (a fixed head and a
    slide-bar handheld on the closet wall, valves by the walk-in entry there, a solid bench along the rear wall),
    the WC and the double vanity side by side on the rear wall under the high window, the walkway along the
    closet wall.

Writes renders/experiments/suite-foyer.png and a 3D model with views. Not part of the regular build.

    uv run scripts/experiment_suite_foyer.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
WIC_D = 84.0                                    # closet depth: 24" hanging + 36" aisle + 24" hanging
SHOWER_W = 72.0                                 # shower width along the bath, from the plumbing wall
BENCH_D = 16.0                                  # shower bench depth (rear wall)
FOYER_X = 1015.5                                # closet | foyer wall (centreline): the foyer 3'-6" wide
HALL_DOOR = (1027.0, 1057.0)                    # hall -> foyer, 30" (the suite's door), hinged on the closet side
WIC_DOOR = (488.0, 518.0)                       # foyer -> closet, 30", on the aisle, past the open suite door
BATH_DOOR = (1026.0, 1056.0)                    # foyer -> bath, 30"
OPENING = (461.0, 493.0)                        # foyer -> bedroom, cased, 32", at the hall end (TV wall clear)


def plan():
    y = S.face("south hall wall", +1) + WIC_D + S.INT / 2                  # closet | bath wall: 2x4 (the shower
    ws = S.WALLS                                                           # heads and valves in it)
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = (w[0], w[1], y, w[3], w[4], S.INT)
    ws.append(("wic|foyer", "y", FOYER_X, S.HALL_S, y, S.INT))
    S.OPENINGS[:] = [o for o in S.OPENINGS if o[0] != "suite|primary"
                     and not (o[0] == "south hall wall" and o[1] == 1070.0)]
    S.OPENINGS += [("south hall wall", *HALL_DOOR, "door", "a", +1),       # the suite's door, into the foyer
                   ("suite|primary", *OPENING, "cased"),                   # foyer -> bedroom
                   ("wic|foyer", *WIC_DOOR, "door", "a", -1),              # foyer -> closet: swings into the closet
                   ("bath|wic", *BATH_DOOR, "door", "b", +1)]              # foyer -> bath: swings in, flat on its end


def primary_bath(sh):
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + SHOWER_W
    S.wet_zone(sh, m0, top, gx, S.S_IN)
    S.shower_head(sh, m0 + 26, top, +1)                                    # fixed head, spraying toward the rear wall
    S.shower_head(sh, gx - 16, top, +1)                                    # handheld on a slide bar, by the valves
    sh.rect(gx - 17, top, gx - 15, top + 1.5, "A-EQPM")
    sh.text("HAND", gx - 16, top + 14, 1.4)
    sh.text("VALVES", gx - 5, top + 9, 1.8, rot=90)
    sh.rect(m0 + 33, top - 3.5, m0 + 51, top, "A-EQPM")                    # niche between them
    sh.text("NICHE", m0 + 42, top + 4, 1.6)
    sh.rect(m0, S.S_IN - BENCH_D, gx, S.S_IN, "A-EQPM")                     # solid bench along the rear wall
    sh.text("BENCH (SOLID)", (m0 + gx) / 2, S.S_IN - BENCH_D / 2, 2.2)
    sh.text("CURBLESS SHOWER", (m0 + gx) / 2, (top + S.S_IN - BENCH_D) / 2, 2.6)
    S.glass(sh, (gx, S.S_IN), (gx, top + 30))                              # walk-in by the closet wall
    S.drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - BENCH_D - 3))
    wx = gx + 2.25                                                         # rear wall: WC by the glass, then
    S.wc(sh, wx, S.S_IN - 28, wx + 30, S.S_IN)                             # the vanity under the high window
    S.vanity(sh, wx + 33, S.S_IN - 22, wx + 93, S.S_IN, "DOUBLE VANITY 60")
    sh.text("HIGH WINDOW ABOVE", wx + 63, S.S_IN - 26, 1.6)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + BATH_DOOR[0]) / 2, cy=top + 14, h=2.6)


def wic(sh):
    x0, x1 = S.face("utility|bath", +1), S.face("wic|foyer", -1)
    y0, y1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hx, cy = S.face("hall closet|wic end", +1), S.face("hall closet|wic", +1)
    hang(hx, x1, y0, +1)                                                   # both sides to the foyer wall
    hang(x0 + 24, x1, y1, -1)
    sh.rect(x0, y1 - 24, x0 + 24, y1, fu); sh.text("SHELVES", x0 + 12, y1 - 12, 2.2)
    sh.rect(x0, cy, x0 + 20, y1 - 24, fu)
    sh.text("DRAWERS", x0 + 10, (cy + y1 - 24) / 2, 2.2, rot=90)
    c1, cb = S.face("hall closet|wic end", -1), S.face("hall closet|wic", -1)
    sh.rect(x0, cb - 14, c1, cb, fu); sh.text("SHELVES", (x0 + c1) / 2, cb - 7, 1.8)
    sh.text("HALL CLOSET", (x0 + c1) / 2, cb - 18, 1.6)
    S.room_label(sh, "WIC", x0, y0, x1, y1, cx=965.0, h=5.0)
    f0, f1 = S.face("wic|foyer", +1), S.face("suite|primary", -1)
    S.room_label(sh, "FOYER", f0, y0, f1, y1, h=2.4)
    bx, bc = S.face("suite|primary", +1), (y0 + S.S_IN) / 2               # bedroom TV: centred on the bed, on the
    sh.rect(bx, bc - 33.5, bx + 3, bc + 33.5, fu)                          # east wall past the foyer opening
    sh.text('TV 77"', bx + 6, bc, 2.2, rot=90)


def render(png, sh):
    S.render(sh.doc, png, S.face("pantry|laundry", -1) - 20, S.face("south hall wall", -1) - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-foyer"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-hall": ((1040, 425, 63.5), (1040, 560, 45)), "overhead": ((1000, 700, 330), (980, 520, 0))}
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
    render(OUT / "suite-foyer.png", S.build())
    model()


if __name__ == "__main__":
    main()
