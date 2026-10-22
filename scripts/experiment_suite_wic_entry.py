# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the no-tub, wider walk-in closet suite, with the bath reached through the closet.

  - As experiment_suite_wide_wic.py (the closet 7'-0" deep with a 3' aisle, the bath about 4'-10" deep with a
    curbless shower at the plumbing-wall end), but the bedroom's bath door goes: the closet opening moves to
    the middle of its bedroom-side end, straight into the aisle, and the bath is entered from the closet by a
    door at the bedroom end of the closet | bath wall, just inside the closet door.
  - Doors: the closet door (32") swings into the closet, hinged on the hall side, and opens into the
    door bay; the bath door (32") swings into the bath, hinged at the bedroom end, and opens
    flat against the bath's end wall, clear of the vanity.
  - Closet: the hall-side hanging stops 3' short of the bedroom wall, where 12"-deep shelves make a bay the
    open closet door rests in (a door stop holds it at 90 degrees, clear of the shelves and the clothes; a
    mirror can go on the door's inside face); the bath-side run stops at the bath door. About 18'-5" of rod.
    Corner shelves and drawer stack at the far end, as now.
  - Bath: the WC and the vanity side by side on the rear wall (the vanity under the high window, mirror below
    the 6' sill), a walkway along the closet wall from the door to the shower's walk-in entry at that wall. A 6'-0"
    shower with two heads on the closet wall, 36" apart (a station each, spraying toward the rear wall), each
    with its own valve; the niche between them; a 16"-deep solid bench along the rear wall (a foam bench kit or block,
    wrapped in the shower membrane).
  - The bedroom has the hall door, the closet door and the nook. The closet door sits near the bed's
    centre line, so the bedroom TV goes off-centre on the wall beside it.

Writes renders/experiments/suite-wic-entry.png and a 3D model with views into the closet and the bath. Not
part of the regular build.

    uv run scripts/experiment_suite_wic_entry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
WIC_D = 84.0                                    # closet depth: 24" hanging + 36" aisle + 24" hanging
SHOWER_W = 72.0                                 # shower width along the bath, from the plumbing wall
DOOR_BAY = 36.0                                 # closet: shallow shelves where the closet door opens
BENCH_D = 16.0                                  # shower bench depth (rear wall)
BATH_DOOR = (1024.0, 1056.0)                    # 32" door, closet -> bath: swings in, opens flat on the bath's end wall


def plan():
    y = S.face("south hall wall", +1) + WIC_D + S.WET / 2
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = (w[0], w[1], y, *w[3:])
    mid = S.face("south hall wall", +1) + WIC_D / 2                       # closet opening centred on the aisle
    S.OPENINGS[:] = [o for o in S.OPENINGS if o[0] != "suite|primary"]
    S.OPENINGS += [("suite|primary", mid - 16, mid + 16, "door", "a", -1),   # closet: swings in, opens into the door bay
                   ("bath|wic", *BATH_DOOR, "door", "b", +1)]


def primary_bath(sh):
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + SHOWER_W
    S.wet_zone(sh, m0, top, gx, S.S_IN)
    for hx in (m0 + 14, m0 + 50):                                          # two heads on the closet wall, 36"
        S.shower_head(sh, hx, top, +1)                                     # apart: a station each, spraying
    sh.rect(m0 + 23, top - 3.5, m0 + 41, top, "A-EQPM")                    # toward the rear wall; niche between
    sh.text("NICHE", m0 + 32, top + 4, 2.0)
    sh.rect(m0, S.S_IN - BENCH_D, gx, S.S_IN, "A-EQPM")                     # solid bench along the rear wall (foam
    sh.text("BENCH (SOLID)", (m0 + gx) / 2, S.S_IN - BENCH_D / 2, 2.2)     # or block, membrane-wrapped), under the window
    sh.text("CURBLESS SHOWER", (m0 + gx) / 2, (top + S.S_IN - BENCH_D) / 2, 2.6)
    S.glass(sh, (gx, S.S_IN), (gx, top + 30))                              # fixed panel from the rear wall;
    S.drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - BENCH_D - 3))                   # walk-in by the closet wall
    wx = gx + 2.25                                                         # rear wall: WC by the glass, then
    S.wc(sh, wx, S.S_IN - 28, wx + 30, S.S_IN)                             # the vanity (15"+ from the WC centre)
    S.vanity(sh, wx + 33, S.S_IN - 22, wx + 93, S.S_IN, "DOUBLE VANITY 60")
    sh.text("HIGH WINDOW", 911.0, S.S_IN - 4, 2.0)
    sh.text("HIGH WINDOW ABOVE", 999.0, S.S_IN - 4, 1.6)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + BATH_DOOR[0]) / 2, cy=top + 14, h=2.6)


def wic(sh):
    x0, x1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    y0, y1 = S.face("south hall wall", +1), S.face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hang(x0 + 24, x1 - DOOR_BAY, y0, +1)                                   # hall side, up to the door bay:
    sh.rect(x1 - DOOR_BAY, y0, x1, y0 + 12, fu)                            # 12" shelves the open closet door
    sh.text("SHELVES", x1 - DOOR_BAY / 2, y0 + 6, 2.0)                     # rests clear of (door stop at 90 deg)
    sh.text("DOOR STOP", x1 - DOOR_BAY / 2, y0 + 17, 1.6)
    hang(x0 + 24, BATH_DOOR[0] - 3, y1, -1)                                # bath side: to the bath door
    for ya, yb in ((y0, y0 + 24), (y1 - 24, y1)):                          # corner shelves either side of
        sh.rect(x0, ya, x0 + 24, yb, fu)                                   # a drawer stack, as now
        sh.text("SHELVES", x0 + 12, (ya + yb) / 2, 2.2)
    sh.rect(x0, y0 + 24, x0 + 20, y1 - 24, fu)
    sh.text("DRAWERS", x0 + 10, (y0 + y1) / 2, 2.2, rot=90)
    S.room_label(sh, "WIC", x0, y0, x1, y1, cx=990.0, h=5.0)
    bx, w0 = S.face("suite|primary", +1), (y0 + y1) / 2 + 16 + 3           # bedroom TV: off-centre, on the
    ty = (w0 + S.S_IN) / 2                                                 # wall beside the closet opening
    sh.rect(bx, ty - 33.5, bx + 3, ty + 33.5, fu); sh.text('TV 77" (OFF-CENTRE)', bx + 6, ty, 2.2, rot=90)


def render(png, sh):
    S.render(sh.doc, png, S.face("pantry|laundry", -1) - 20, S.face("south hall wall", -1) - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-wic-entry"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-bedroom": ((1190, 503, 63.5), (950, 503, 50)), "overhead": ((1000, 700, 330), (980, 520, 0))}
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
    render(OUT / "suite-wic-entry.png", S.build())
    model()


if __name__ == "__main__":
    main()
