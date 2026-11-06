# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the suite's door in the hall's end wall, opening into the reading nook.

  - A 3'-0" x 8'-0" door centred in the hall's end wall, swinging into the nook, hinged on the office side and
    folding back against the nook's north wall. The bedroom's hall wall is solid; the dressing room's door stays.
  - The nook loses its lowered ceiling and the cabinets above: the bedroom's 9' ceiling runs through it, so the
    door is the normal height.
  - The bookshelves on the office wall start past the open door (about 3'-4" in), so they run about 4'-10".
  - The end wall goes back 5" east (the nook about 8'-2"); the bedroom's switches on the nook side of the end
    wall, on the door's latch side.

Writes renders/experiments/nook-entry.png and a 3D model with views. Not part of the regular build.

    uv run scripts/experiment_nook_entry.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
HALL_END = 1110.5                               # the hall's end wall, 5" back east
DOOR = (413.45, 449.45)                         # 36", centred in the hall's width
SHELF_START = 40.0                              # bookshelves start this far into the nook, past the open door


def plan():
    S.HALL_END = HALL_END
    for i, w in enumerate(S.WALLS):
        if w[0] == "hall end":
            S.WALLS[i] = (w[0], w[1], HALL_END, w[3], w[4], w[5])
        if w[0] == "south hall wall":
            S.WALLS[i] = (w[0], w[1], w[2], w[3], HALL_END + S.INT / 2, w[5])
    S.OPENINGS[:] = [o for o in S.OPENINGS if not (o[0] == "south hall wall" and o[1] == 1074.0)]
    S.OPENINGS.append(("hall end", *DOOR, "door", "a", +1))


def nook(sh):
    """No lowered ceiling or cabinets above; the bookshelves past the door; the switches moved."""
    n0, ny = HALL_END + S.INT / 2, S.face("bedroom hall wall", +1)
    for e in list(sh.msp.query("TEXT")):
        t, x, y = e.dxf.text, e.dxf.insert.x, e.dxf.insert.y
        if t.startswith("CABINETS ABOVE") or t == "BOOKSHELVES":
            sh.msp.delete_entity(e)
        elif t == "S" and abs(x - (S.face("suite|primary", +1) + 4.9)) < 6 and abs(y - (S.face("south hall wall", +1) + 4)) < 3:
            sh.msp.delete_entity(e)                                     # the old corner stub's switches
    for e in list(sh.msp.query("LINE")):
        if e.dxf.layer == "A-CLNG" and e.dxf.start.x >= n0 - 1 and ny - 5 <= e.dxf.start.y <= S.face("south hall wall", +1) + 6:
            sh.msp.delete_entity(e)
    sh.rect(n0 + SHELF_START, ny, S.W_IN, ny + S.NOOK_SHELF_D, "A-FURN")
    sh.text("BOOKSHELVES", (n0 + SHELF_START + S.W_IN) / 2, ny + S.NOOK_SHELF_D / 2, 2.4)
    sh.text("S", n0 + 4, DOOR[1] + 6, 2.4)                              # bedroom, the door's latch side, nook face


def render(png, sh):
    S.render(sh.doc, png, S.face("bath|wic", -1) - 20, S.HALL_N - 40, S.W + 30, S.S + 30, width_in=12, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    n0, ny = HALL_END + S.INT / 2, S.face("bedroom hall wall", +1)
    for k in ("wall", "closet"):                                        # lowered ceiling, cabinets, old shelves out
        sc.boxes[k] = [b for b in sc.boxes[k] if not (b[0] >= n0 - 8 and b[2] >= S.W_IN - 1 and b[1] >= ny - 1
                                                      and b[3] <= S.face("south hall wall", +1) + 6 and
                                                      (b[4] >= S.NOOK_CEIL - 1 or k == "closet"))]
    sc.boxes["closet"].append([n0 + SHELF_START, ny, S.W_IN, ny + S.NOOK_SHELF_D, 0, 96])
    m = S.face("lounge|gym", -1)
    sc.boxes["wall"].append([m, S.N_IN, S.W_IN, S.S_IN, 108, 109])      # the wing's flat ceiling
    out = OUT / "nook-entry"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    yc = sum(DOOR) / 2
    shots = {"down-the-hall": ((960, yc, 62), (1200, yc, 58)), "from-bed": ((1160, 540, 56), (1125, 420, 56)),
             "overhead": ((1140, 640, 300), (1130, 470, 0))}
    for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;gridGroup.visible=false;"
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
    nook(sh)
    render(OUT / "nook-entry.png", sh)
    model()


if __name__ == "__main__":
    main()
