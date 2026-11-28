# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the gym opened to the lounge as a flex room (den / play / second guest room).

  - A 6'-0" opening in the lounge | gym wall, centred on the wall, with bi-parting pocket doors (two 3'-0" leaves,
    8'-0" tall like the other doors) sliding into the wall either side. Open, the room extends the lounge behind
    the sectional; closed, it's a bedroom again (the hall door stays).
  - The pockets fill nearly the whole wall, so nothing can go in it: the rear surround speakers move to the lounge
    ceiling near the wall (angled in-ceiling), and the lounge light switches at the hall corner move to the end
    of the kitchen | pantry wall, just past the hall mouth.
  - The room: a sleeper sofa on the ensuite wall in place of the bed; the bike and bench stored in the closet.

Writes renders/experiments/gym-open.png (plan, current vs open), a 3D model and views to
renders/experiments/gym-open/. Not part of the regular build.

    uv run scripts/experiment_gym_open.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
W0, W1 = S.N_IN, S.face("bedroom hall wall", -1)        # the wall's clear run, street face to hall face
MID = (W0 + W1) / 2
OPEN = (MID - 36.0, MID + 36.0)                          # 6'-0" opening; 3'-0" pockets either side
GX0, GX1 = S.face("lounge|gym", +1), S.face("gym|ensuite", -1)
CLOSET_Y = W1 - 24.0
SOFA = (GX1 - 36.0, MID - 42.0, GX1, MID + 42.0)
SHOTS = {"from-lounge": ((470, 300, 63.5), (800, 320, 50), "from the lounge, through the opening"),
         "from-gym": ((775, 290, 63.5), (440, 320, 60), "from the gym, back toward the TV")}

OPENINGS = [*S.OPENINGS,
            ("lounge|gym", OPEN[0], MID, "pocket", "a", +1),
            ("lounge|gym", MID, OPEN[1], "pocket", "b", +1)]


def gym_open(sh):
    msp = sh.msp
    inside = lambda x0, y0, x1, y1: GX0 - 1 <= x0 and x1 <= GX1 + 1 and W0 - 1 <= y0 and y1 <= CLOSET_Y - 1  # noqa: E731
    for e in list(msp.query("LWPOLYLINE[layer=='A-FURN']")):        # the bed and nightstands
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        if inside(min(xs), min(ys), max(xs), max(ys)):
            msp.delete_entity(e)
    sx = S.face("lounge|gym", -1) - 4
    for e in list(msp.query("TEXT")):
        x, y = e.dxf.insert.x, e.dxf.insert.y
        if e.dxf.text == "S" and abs(x - sx) < 3 and abs(y - (S.HALL_N - 12)) < 3:   # switches off the pocket wall
            msp.delete_entity(e)
        elif e.dxf.text == "CL" and GX0 < x < GX1 and y > CLOSET_Y - 20:
            e.dxf.text = "CL (BIKE, BENCH)"
    sh.text("S", sx, S.HALL_S + S.INT / 2 + 6, 2.4)
    sh.rect(*SOFA, "A-FURN")
    sh.text("SLEEPER SOFA", (SOFA[0] + SOFA[2]) / 2, MID, 3.0, rot=90)
    sh.text("6'-0\" OPENING, BI-PARTING POCKET DOORS", S.face("lounge|gym", -1) - 10, MID, 2.4, rot=90)
    sh.text("REAR SURROUNDS IN CEILING", S.face("lounge|gym", -1) - 22, MID, 2.4, rot=90)
    return sh


def plan():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    import zoning_set as Z
    tmp = OUT / "gym-open"
    tmp.mkdir(parents=True, exist_ok=True)
    win = (380, 220, 880, 470)
    S.render(S.build().doc, tmp / "_plan-current.png", *win, width_in=7, dpi=200)
    S.OPENINGS[:] = OPENINGS
    S.render(gym_open(S.build()).doc, tmp / "_plan-open.png", *win, width_in=7, dpi=200)
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.4))
    for ax, (f, t) in zip(axs, (("current", "Current: gym behind a solid wall"),
                                ("open", "Gym opened to the lounge: 6' bi-parting pocket doors"))):
        p = tmp / f"_plan-{f}.png"
        ax.imshow(mpimg.imread(p)); ax.set_title(t, fontsize=10, loc="left"); ax.axis("off")
        p.unlink()
    fig.tight_layout()
    Z.save_png(fig, OUT / "gym-open.png", dpi=110)
    plt.close(fig)


def model():
    import exterior as X
    import make_3d as M
    S.OPENINGS[:] = OPENINGS
    build = S.build
    S.build = lambda: gym_open(build())
    sc = M.build_schematic()
    S.build = build
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "gym-open"
    M.write_model(sc, out, sc.meta)
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    html = out / "house.html"
    for name, ((cx, cy, cz), (tx, ty, tz), _) in SHOTS.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;gridGroup.visible=false;"
            "scene.traverse(o=>{if(o.isSprite||o.type==='ArrowHelper')o.visible=false;});"
            "document.getElementById('ui').style.display='none';document.getElementById('help').style.display='none';"
            "camera.fov=70;camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN,{cz}*IN,{-cy}*IN);orbit.target.set({tx}*IN,{tz}*IN,{-ty}*IN);"
            f"camera.lookAt({tx}*IN,{tz}*IN,{-ty}*IN);}},50);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/") + "#roof"],
                       capture_output=True)
        tmp.unlink()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    plan()
    model()
