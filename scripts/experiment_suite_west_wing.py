# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the primary suite as a north-south wing across the west end; the office moves to the rear.

  - The bedroom hall ends at a suite door in line with the guest wall. Behind it, the suite's entry (where
    the reading nook is now) leads to the bedroom (south, the same quiet rear corner and window) and to the
    walk-in closet and bath (north, where the office is now). The bedroom has one door, from the entry.
  - Walk-in closet: about 7' deep, hanging on both long walls; entered from the suite entry, with the bath
    door straight across its aisle. Bath along the street wall: double vanity and WC on the street wall
    (a high window over the vanity), a shower at the west end with its head on the closet (plumbing) wall.
  - The office takes the rear room where the primary bath and closet are now, its door off the hall, with a
    standard rear window.
  - Loses the reading nook and the office's street window (the bath gets a high one instead); the primary
    bath moves away from the plumbing core.

Writes renders/experiments/suite-west-wing.png (with the current plan, suite-west-wing-current.png, to
compare) and a 3D model with views. Not part of the regular build.

    uv run scripts/experiment_suite_west_wing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from ezdxf import bbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
SUITE_X = 1062.0                                # hall end / guest | suite line (centreline)
BATH_D = 61.0                                   # bath depth from the street wall
BATH_WALL = S.N_IN + BATH_D + S.WET / 2         # bath | closet wall centreline (plumbing wall)
DOOR_X = (1104.0, 1134.0)                       # closet door from the entry, and the bath door across the aisle
_build = S.build


def plan():
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "hall end":
            ws[i] = ("hall end", "y", SUITE_X, 403.2, S.HALL_S, S.INT)
        elif w[0] == "south hall wall":
            ws[i] = (w[0], w[1], w[2], w[3], S.W_IN, w[5])
        elif w[0] == "bath|wic":
            ws[i] = ("bath|wic", "x", BATH_WALL, SUITE_X, S.W_IN, S.WET)
    drop = {("north", 1101.6), ("west", 289.6), ("west", 415.45), ("south", S.SHOWER_WIN[0]), ("south", 978.0),
            ("bedroom hall wall", 1067.0)}
    S.OPENINGS[:] = [o for o in S.OPENINGS if (o[0], o[1]) not in drop and o[0] != "suite|primary"]
    S.OPENINGS += [
        ("north", 1073.25, 1115.25, "window", 72.0, 96.0),       # bath: high window over the vanity
        ("south", 936.75, 1008.75, "window"),                    # office: 6' rear window
        ("south hall wall", 1022.0, 1054.0, "door", "b", +1),    # office, off the hall
        ("hall end", 413.0, 445.0, "door", "a", +1),             # suite door
        ("bedroom hall wall", *DOOR_X, "door", "a", -1),         # closet, from the suite entry
        ("bath|wic", *DOOR_X, "door", "a", -1),                  # bath, straight across the closet aisle
    ]
    S.HALL_TUBE = SUITE_X - S.INT / 2 - 32.0                    # hall skylight near the new hall end
    S.primary_bath = S.wic = lambda sh: None


def _clear(sh, x0, y0, x1, y1):
    keep = {"A-WALL", "A-WALL-PATT", "A-DOOR", "A-GLAZ", "A-ANNO-DIMS"}
    for e in list(sh.msp):
        if e.dxf.layer in keep:
            continue
        b = bbox.extents([e])
        if b.has_data and x0 <= b.extmin.x and b.extmax.x <= x1 and y0 <= b.extmin.y and b.extmax.y <= y1:
            sh.msp.delete_entity(e)


def build():
    sh = _build()
    eq, fu = "A-EQPM", "A-FURN"
    _clear(sh, 883.0, S.HALL_S, SUITE_X, S.S + 1)                        # the old bath and closet
    _clear(sh, SUITE_X, S.N - 1, S.W + 1, S.HALL_S + 2.5)                     # the office and the reading nook
    sh.heads[:] = [h for h in sh.heads if not (883.0 < h[0] < S.W and S.HALL_S < h[1])]
    for t in sh.msp.query("TEXT"):                                        # lobby label clear of the hatch
        if t.dxf.text == "LOBBY":
            for k in ("insert", "align_point"):
                if t.dxf.hasattr(k):
                    v = t.dxf.get(k)
                    t.dxf.set(k, (931.0 + (v[0] - t.dxf.align_point[0] if t.dxf.hasattr("align_point") else 0), v[1]))
    xi0, xi1 = S.face("guest|office", +1), S.W_IN
    # office (rear)
    o0, o1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    oy0 = S.face("south hall wall", +1)
    sh.rect(o0, S.S_IN - 30, o0 + 60, S.S_IN, fu); sh.text("DESK", o0 + 30, S.S_IN - 15, 3.0)
    sh.rect(o0, oy0, 1012.0, oy0 + 24, fu); sh.line((o0, oy0 + 12), (1012.0, oy0 + 12), fu)
    sh.text("CL", (o0 + 1012.0) / 2, oy0 + 18, 4.0)
    S.room_label(sh, "OFFICE", o0, oy0, o1, S.S_IN, cy=(oy0 + S.S_IN) / 2 + 10)
    # suite entry (where the nook was)
    ey0, ey1 = S.face("bedroom hall wall", +1), S.face("south hall wall", -1)
    sh.rect(xi1 - 24, ey0, xi1, ey1, fu); sh.text("LINEN", xi1 - 12, (ey0 + ey1) / 2, 2.6, rot=90)
    S.room_label(sh, "SUITE ENTRY", xi0, ey0, xi1 - 24, ey1, cx=1160.0, h=2.6)
    # walk-in closet
    wy0, wy1 = S.face("bath|wic", +1), S.face("bedroom hall wall", -1)
    d0, d1 = DOOR_X
    for a, b in ((xi0, d0 - 4), (d1 + 4, xi1)):                          # hanging on both long walls, clear
        for y, d in ((wy0, +1), (wy1, -1)):                              # of the two doors
            sh.rect(a, min(y, y + 24 * d), b, max(y, y + 24 * d), fu)
            sh.line((a, y + 12 * d), (b, y + 12 * d), fu)
            sh.text("HANG", (a + b) / 2, y + 18 * d, 2.6)
    sh.rect(xi1 - 20, wy0 + 24, xi1, wy1 - 24, fu); sh.text("DRAWERS", xi1 - 10, (wy0 + wy1) / 2, 2.0, rot=90)
    S.room_label(sh, "WIC", xi0, wy0, xi1, wy1, cx=1165.0, h=3.0)
    # bath
    by0, by1 = S.N_IN, S.face("bath|wic", -1)
    S.vanity(sh, xi0, by0, xi0 + 60, by0 + 22, "DOUBLE VANITY 60")
    S.wc(sh, xi0 + 62, by0, xi0 + 92, by0 + 28)
    gx = xi0 + 93.75                                                      # shower at the west end
    S.wet_zone(sh, gx, by0, xi1, by1)
    S.glass(sh, (gx, by0), (gx, by1 - 30))                                # entry by the closet wall
    S.shower_head(sh, (gx + xi1) / 2 + 6, by1, -1)                        # head on the plumbing wall
    sh.text("SHOWER", (gx + xi1) / 2, (by0 + by1) / 2 - 6, 2.6)
    S.room_label(sh, "PRIMARY BATH", xi0, by0, gx, by1, cx=1110.0, cy=by1 - 12, h=2.4)
    return sh


def render(png, sh):
    S.render(sh.doc, png, 860.0, S.N - 40, S.W + 40, S.S + 40, width_in=12, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    for k in ("wall", "closet"):                                          # no reading nook soffit / cabinets
        sc.boxes[k] = [b for b in sc.boxes[k] if b[4] != S.NOOK_CEIL]
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-west-wing"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"overhead": ((1000, 700, 360), (1060, 430, 0)), "from-hall": ((960, 430, 63.5), (1200, 430, 50))}
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
    render(OUT / "suite-west-wing-current.png", _build())
    plan()
    S.build = build
    render(OUT / "suite-west-wing.png", S.build())
    model()


if __name__ == "__main__":
    main()
