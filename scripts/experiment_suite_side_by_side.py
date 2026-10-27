# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the primary bath and walk-in closet side by side instead of front to back.

  - The suite block between the bedroom and the laundry/common bath is split east-west: the bath on the east
    part, against the existing plumbing wall, from the hall to the rear wall, about 6'-2" x 12'-8"; the closet
    on the west part, next to the bedroom, about 8'-0" x 12'-8", instead of two strips front to back. No hall
    closet: its corner is the bath's.
  - One cased opening from the bedroom into the closet (a dressing room); the bath is reached straight across
    the closet, along the hall wall, by a 30" door in line with it, swinging into the bath and resting flat on
    the hall wall clear of the vanity. The bedroom loses one door.
  - Bath, no tub: a curbless walk-in shower across the rear wall (a fixed head on the plumbing wall and a slide-
    bar handheld on the closet wall facing it, by the open end; a niche in the closet wall), the 60" double
    vanity on the plumbing wall facing the door, and the WC on the plumbing wall between the vanity and the
    glass. No window (exhaust fan). The house's tub is the guest ensuite's.
  - The closet opening is in the hall corner, so the bedroom's TV wall (the rest of that wall) stays centred on
    the bed. Closet: the walkway along the hall wall, hanging down both long walls (about 18'-2" of rod),
    drawers and shelves under the rear high window, and room to dress in the middle (about 4' between the
    hanging).

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
SPLIT = 962.0                                  # bath | closet wall centreline: a 6'-2" bath, the rest (about 8') to
                                               # the closet
ENTRY = (463.0, 495.0)                         # 32" cased opening in the hall corner, bedroom -> closet
BATH_DOOR = (463.0, 493.0)                     # 30" door, closet -> bath: in line with the entry, a straight path
                                               # along the hall wall; swings into the bath, flat on the hall wall
SHOWER_D = 54.0                                # walk-in shower depth from the rear wall


def plan():
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = ("bath|wic", "y", SPLIT, 457.0, S.S_IN, S.INT)
    ws[:] = [w for w in ws if not w[0].startswith("hall closet")]           # no hall closet: its corner is the bath's
    S.OPENINGS[:] = [o for o in S.OPENINGS if not (o[0] == "suite|primary" and o[3] == "door")
                     and not (o[0] == "south hall wall" and o[1] == S.HALL_CL_DOOR[0])]
    S.OPENINGS += [("suite|primary", *ENTRY, "cased"), ("bath|wic", *BATH_DOOR, "door", "a", -1)]


def primary_bath(sh):
    m0, b1 = S.face("utility|bath", +1), S.face("bath|wic", -1)
    y0 = S.face("south hall wall", +1)
    gy = S.S_IN - SHOWER_D
    S.wet_zone(sh, m0, gy, b1, S.S_IN)
    hy = (gy + S.S_IN) / 2
    for x, d in ((m0, 1.0), (b1, -1.0)):                                   # fixed head on the plumbing wall, a slide-
        sh.circle((x + d * 4, hy), 2.5, "A-EQPM"); sh.heads.append((x, hy, d, 0.0))   # bar handheld facing it
    sh.text("HAND", b1 - 8, hy - 9, 1.4)
    sh.rect(b1, S.S_IN - 22, b1 + 3.5, S.S_IN - 6, "A-EQPM")                # niche in the closet wall
    sh.text("NICHE", b1 - 7, S.S_IN - 14, 2.0, rot=90)
    sh.text("CURBLESS SHOWER", (m0 + b1) / 2, hy, 2.6)
    S.glass(sh, (m0, gy), (b1 - 30, gy))                                   # glass, open at the door end
    S.drain(sh, (m0 + 3, gy + 3), (b1 - 3, gy + 3))                         # linear drain along the glass line
    S.vanity(sh, m0, y0, m0 + 22, y0 + 60, "DOUBLE VANITY 60", rot=90)     # plumbing wall, facing the door
    wy = (y0 + 60 + gy) / 2
    S.wc(sh, m0, wy - 15, m0 + 28, wy + 15)                                # plumbing wall, between vanity and glass
    S.room_label(sh, "PRIMARY BATH", m0, y0, b1, S.S_IN, cx=(m0 + 22 + b1) / 2, cy=wy - 22, h=2.4)


def wic(sh):
    x0, x1 = S.face("bath|wic", +1), S.face("suite|primary", -1)
    y0, y1 = S.face("south hall wall", +1), S.S_IN
    fu = "A-FURN"
    for a, b in ((x0, x0 + 24), (x1 - 24, x1)):                            # hanging down both long walls, past
        h0 = ENTRY[1] + 6                                                  # the walkway along the hall wall
        sh.rect(a, h0, b, y1, fu)
        sh.line(((a + b) / 2, h0), ((a + b) / 2, y1), fu)
        sh.text("HANG", (a + b) / 2, (h0 + y1) / 2, 3.0, rot=90)
    sh.rect(x0 + 24, y1 - 24, x1 - 24, y1, fu); sh.text("DRAWERS + SHELVES", (x0 + x1) / 2, y1 - 12, 2.0)
    sh.text("HIGH WINDOW ABOVE", 999.0, S.S_IN - 4, 1.8)
    bx, by = S.face("suite|primary", +1), (y0 + y1) / 2                   # bedroom TV, centred on the bed
    sh.rect(bx, by - 33.5, bx + 3, by + 33.5, fu); sh.text('TV 77"', bx + 6, by + 24, 2.6, rot=90)
    S.room_label(sh, "WIC / DRESSING", x0, y0, x1, y1, cx=(x0 + x1) / 2, cy=(ENTRY[1] + y1) / 2 - 10, h=3.6)


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
