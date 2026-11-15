# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a banquette under the dining window, and a built-in on the east wall.

  - A built-in bench along the dining window (the rear wall), about the window's length, 22" deep at seat
    height, with drawers or lift-up storage in the seat.
  - The table turns to run along it (84" x 36"), pushed up to the bench: the bench seats one side, three chairs
    the other, one at the east end (8 at a squeeze; 4 every day). It stays 3' clear of the slider.
  - A 5' built-in (16" deep, drawers and cabinets at counter height, shelves or art above) on the east wall, the
    first thing you face coming out of the foyer: drop zone, bar, the good dishes.
  - The floor between the foyer and the table stays open: the arrival space.

Writes renders/experiments/banquette.png (plan, current vs banquette), a 3D model and views to
renders/experiments/banquette/. Not part of the regular build.

    uv run scripts/experiment_banquette.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
D0, D1 = S.E_IN, 546.9                            # dining room: east wall to the peninsula's stool face
Y0, Y1 = S.KITCHEN_ROW, S.S_IN
BENCH = (382.0, Y1 - 22.0, 530.0, Y1)             # along the dining window (384-528)
TABLE = (418.0, Y1 - 22.0 - 36.0 + 3.0, 502.0, Y1 - 22.0 + 3.0)   # 3" over the bench's seat
CHAIRS = [(432.0, TABLE[1] - 11.0), (460.0, TABLE[1] - 11.0), (488.0, TABLE[1] - 11.0),
          (TABLE[0] - 10.0, (TABLE[1] + TABLE[3]) / 2)]
BUILTIN = (S.E_IN, 432.0, S.E_IN + 16.0, 492.0)
SHOTS = {"from-foyer": ((405, 385, 63.5), (470, 590, 45), "coming out of the foyer"),
         "from-kitchen": ((575, 500, 63.5), (420, 600, 35), "from the kitchen aisle end"),
         "from-slider": ((385, 560, 63.5), (520, 430, 50), "from the slider, back toward the lounge")}


def banquette(sh):
    msp = sh.msp
    inside = lambda x0, y0, x1, y1: D0 - 1 <= x0 and x1 <= D1 - 4 and Y0 - 1 <= y0 and y1 <= Y1 + 1  # noqa: E731
    for e in list(msp.query("LWPOLYLINE[layer=='A-FURN']")):        # the old table
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        if inside(min(xs), min(ys), max(xs), max(ys)):
            msp.delete_entity(e)
    for e in list(msp.query("CIRCLE[layer=='A-FURN']")):            # and its chairs (not the stools)
        x, y, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
        if r < 7.2 and inside(x, y, x, y):
            msp.delete_entity(e)
    for e in msp.query("TEXT[layer=='A-AREA-IDEN']"):                # the room label moves into the open floor
        x, y = e.dxf.insert.x, e.dxf.insert.y
        if D0 <= x <= D1 and y > TABLE[1] - 20:
            e.dxf.insert = (x, y - 92.0)
            if e.dxf.hasattr("align_point"):
                e.dxf.align_point = (e.dxf.align_point.x, e.dxf.align_point.y - 92.0)
    sh.rect(*BENCH, "A-FURN"); sh.text("BANQUETTE BENCH", (BENCH[0] + BENCH[2]) / 2, (BENCH[1] + BENCH[3]) / 2, 3.5)
    sh.rect(*TABLE, "A-FURN")
    for c in CHAIRS:
        sh.circle(c, 7, "A-FURN")
    sh.rect(*BUILTIN, "A-FURN"); sh.text("BUILT-IN DRAWERS", BUILTIN[0] + 8, (BUILTIN[1] + BUILTIN[3]) / 2, 2.6, rot=90)
    return sh


def plan():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    import zoning_set as Z
    tmp = OUT / "banquette"
    tmp.mkdir(parents=True, exist_ok=True)
    win = (S.E - 30, S.FOYER_WALL_END - 120, 700, S.S + 30)
    S.render(S.build().doc, tmp / "_plan-current.png", *win, width_in=7, dpi=200)
    S.render(banquette(S.build()).doc, tmp / "_plan-banquette.png", *win, width_in=7, dpi=200)
    fig, axs = plt.subplots(1, 2, figsize=(14, 7.6))
    for ax, (f, t) in zip(axs, (("current", "Current: table in the middle of the room"),
                                ("banquette", "Banquette under the window, built-in on the east wall"))):
        p = tmp / f"_plan-{f}.png"
        ax.imshow(mpimg.imread(p)); ax.set_title(t, fontsize=10, loc="left"); ax.axis("off")
        p.unlink()
    fig.tight_layout()
    Z.save_png(fig, OUT / "banquette.png", dpi=110)
    plt.close(fig)


def model():
    import exterior as X
    import make_3d as M
    build = S.build
    S.build = lambda: banquette(build())
    sc = M.build_schematic()
    S.build = build
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "banquette"
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
