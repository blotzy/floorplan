# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the no-tub, wider walk-in closet suite with a 6' double shower, keeping both doors from the
bedroom.

  - As experiment_suite_wide_wic.py: the closet 7'-0" deep (hanging on both long walls, a 3' aisle, corner
    shelves and drawer stack), its door from the bedroom by the hall wall; the bath about 4'-10" deep, its door
    from the bedroom at the rear-wall end. Both doors 30".
  - Shower: 6'-0" curbless at the plumbing-wall end, the walk-in entry by the rear wall. Two heads on the rear
    wall 36" apart (a station each, spraying toward the closet wall), each with its own valve, the valves by the
    entry so the water can be started from outside the spray; a full-width solid bench (foam kit or block,
    membrane-wrapped) along the closet wall facing them, the niche above it. The shower's high window is a
    strip above the heads (sill 7', head 8'); plumbing in the rear (outside) wall stays on the warm side of the
    insulation. The WC and the 60" double vanity on the closet wall, as now; the bath door opens flat against the rear
    wall.

Writes renders/experiments/suite-double-shower.png and a 3D model with views into the closet and the bath. Not
part of the regular build.

    uv run scripts/experiment_suite_double_shower.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
WIC_D = 84.0                                    # closet depth: 24" hanging + 36" aisle + 24" hanging
SHOWER_W = 72.0                                 # shower width along the bath, from the plumbing wall
BENCH_D = 16.0                                  # shower bench depth (closet wall)
ENTRY_W = 30.0                                  # walk-in shower entry, by the rear wall
WIN_SILL = 84.0                                 # shower window sill: 7', above the heads (head height stays 8')


def plan():
    y = S.face("south hall wall", +1) + WIC_D + S.WET / 2
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = (w[0], w[1], y, *w[3:])
    for i, o in enumerate(S.OPENINGS):
        if o[:4] == ("south", 890.0, 932.0, "window"):                     # shower window: a strip above the heads
            S.OPENINGS[i] = (*o[:4], WIN_SILL, o[5])
    for i, o in enumerate(S.OPENINGS):                                    # both bedroom doors 30"
        if o[0] == "suite|primary" and o[3] == "door":
            S.OPENINGS[i] = (o[0], o[1], o[1] + 30, *o[3:]) if o[4] == "a" else (o[0], o[2] - 30, *o[2:])


def primary_bath(sh):
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + SHOWER_W
    S.wet_zone(sh, m0, top, gx, S.S_IN)
    for hx in (m0 + 18, m0 + 54):                                          # two heads on the rear wall, 36" apart,
        S.shower_head(sh, hx, S.S_IN, -1)                                  # spraying toward the closet wall; the
    sh.text("VALVES", gx - 7, S.S_IN - 9, 1.8, rot=90)                     # valves by the entry, reachable from it
    sh.rect(m0, top, gx, top + BENCH_D, "A-EQPM")                          # solid bench along the closet wall,
    sh.text("BENCH (SOLID)", (m0 + gx) / 2, top + BENCH_D / 2, 2.2)        # full width, facing the heads
    sh.rect(m0 + 27, top - 3.5, m0 + 45, top, "A-EQPM")                    # niche above the bench
    sh.text("NICHE ABOVE", m0 + 36, top + BENCH_D + 3, 1.8)
    sh.text("CURBLESS SHOWER", (m0 + gx) / 2, top + BENCH_D + 9, 2.6)
    S.glass(sh, (gx, top), (gx, S.S_IN - ENTRY_W))                         # fixed panel from the closet wall;
    S.drain(sh, (gx - 3, top + BENCH_D + 3), (gx - 3, S.S_IN - 3))                   # walk-in by the rear wall
    S.wc(sh, gx + 2.25, top, gx + 32.25, top + 28)                         # closet wall: 17.25" to the glass
    S.vanity(sh, m1 - 60, top, m1, top + 22, "DOUBLE VANITY 60")           # 22.5" from the WC centre
    sh.text("HIGH WINDOW ABOVE, SILL 7'", (m0 + gx) / 2, S.S_IN - 16, 1.6)
    sh.text("HIGH WINDOW", 999.0, S.S_IN - 4, 2.0)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + m1) / 2, cy=S.S_IN - 14, h=2.6)


def render(png, sh):
    S.render(sh.doc, png, S.face("pantry|laundry", -1) - 20, S.face("south hall wall", -1) - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-double-shower"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-bedroom": ((1190, 520, 63.5), (1000, 545, 50)), "overhead": ((1000, 700, 330), (980, 520, 0)),
                 "in-bath": ((1045, 592, 63.5), (900, 575, 40))}
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
    S.primary_bath = primary_bath
    render(OUT / "suite-double-shower.png", S.build())
    model()


if __name__ == "__main__":
    main()
