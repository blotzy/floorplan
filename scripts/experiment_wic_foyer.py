# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the dressing room as the suite's foyer. The hall door opens into the dressing room; the bedroom
and the bath both open off it.

  - The suite's 3'-0" hall door moves from the bedroom's corner into the dressing room's hall wall, swinging in
    and folding flat against the hall wall toward the bath, with about 21" of wall left on its latch side for the
    dressing room's switches.
  - The bedroom's door stays in its opening at the hall corner (2'-8") but swings into the bedroom, folding back
    against the bedroom's now-solid hall wall; the bedroom's switches on that wall just past it, on the bed side.
  - No door from the hall into the bedroom, so the hall ends just past the office door: its end wall goes back
    5" east and the reading nook gets that 5" back (about 8'-2").

Writes renders/experiments/wic-foyer.png and a 3D model with views. Not part of the regular build.

    uv run scripts/experiment_wic_foyer.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
HALL_DOOR = (1002.25, 1038.25)                  # hall -> dressing room, 36", hinged on the bath side
HALL_END = 1110.5                               # the hall's end wall, 5" back east


def plan():
    S.HALL_END = HALL_END
    for i, w in enumerate(S.WALLS):
        if w[0] == "hall end":
            S.WALLS[i] = (w[0], w[1], HALL_END, w[3], w[4], w[5])
        if w[0] == "south hall wall":
            S.WALLS[i] = (w[0], w[1], w[2], w[3], HALL_END + S.INT / 2, w[5])
    S.OPENINGS[:] = [o for o in S.OPENINGS if not (o[0] == "south hall wall" and o[1] == 1074.0)
                     and o[0] != "suite|primary"]
    S.OPENINGS += [("south hall wall", *HALL_DOOR, "door", "a", +1),   # the suite's door, into the dressing room
                   ("suite|primary", *S.SUITE_ENTRY, "door", "a", +1)]  # dressing room -> bedroom, swinging into it


def switches(sh):
    """The switch marks that move: the bedroom's corner stub and the dressing room's, by the old opening."""
    hs = S.face("south hall wall", +1) + 4
    bx = S.face("suite|primary", +1)
    for e in list(sh.msp.query("TEXT")):
        if e.dxf.text == "S":
            x, y = e.dxf.insert.x, e.dxf.insert.y
            if abs(x - (bx + 4)) < 8 and (abs(y - 502.0) < 8 or abs(y - hs) < 8):
                sh.msp.delete_entity(e)
    sh.text("S", HALL_DOOR[1] + 6, hs, 2.4)                             # dressing room, latch side of the hall door
    sh.text("S", bx + 38, hs, 2.4)                                      # bedroom, past its door, on the bed side


def render(png, sh):
    S.render(sh.doc, png, S.face("utility|bath", +1) - 20, S.HALL_N - 40, S.W + 30, S.S + 30, width_in=12, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "wic-foyer"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    shots = {"from-hall": ((1020, 432, 62), (1020, 560, 45)), "overhead": ((1040, 700, 330), (1040, 500, 0))}
    for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;"
            "document.getElementById('ui').style.display='none';document.getElementById('help').style.display='none';"
            "camera.fov=70;camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN,{cz}*IN,{-cy}*IN);orbit.target.set({tx}*IN,{tz}*IN,{-ty}*IN);"
            f"camera.lookAt({tx}*IN,{tz}*IN,{-ty}*IN);}},50);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/")],
                       capture_output=True)
        tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan()
    sh = S.build()
    switches(sh)
    render(OUT / "wic-foyer.png", sh)
    model()


if __name__ == "__main__":
    main()
