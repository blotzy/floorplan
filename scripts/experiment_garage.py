# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the carport enclosed as a two-car garage.

  - The carport's front 4' stays an open covered walkway to the porch; the garage starts at the front door's
    line (parking no closer to the street than the front door, as now), with a 16' x 7' sectional door.
  - 6" stud walls (stucco outside, Type X gypsum inside) on the east and rear; the east wall stays on the
    carport's line (the east side yard). The rear wall goes about 1' further south so the garage is 18' deep
    inside (about 17'-6" wide).
  - Roof: a 2:12 gable in the house's dark shingles (the wing's pitch), its ridge east-west like the wing's
    gable, over the garage and the covered walkway; eaves at 9' to the street and the courtyard, a stucco gable
    end on the east, the west end against the house. Its ridge is about 11'-6", some 2' below the wing's.
  - A 3'-0" door from the garage into the courtyard in the rear wall (clear of the dining slider's landing), in place of the 14'
    courtyard gate; the courtyard fence meets the garage's east wall. The bins stay in the strip east of it.

Writes renders/experiments/garage.png (plan) and a 3D model with views to renders/experiments/garage/.
Not part of the regular build.

    uv run scripts/experiment_garage.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
T = 6.0                                           # garage wall
CX0, CY0, CX1, CY1 = S.CARPORT
FRONT = S.PORCH_Y                                 # the garage's front wall: the front door's line
BACK = FRONT + T + 216.0                          # inside face of the rear wall: 18' deep inside
DOOR = (CX0 + T + 9.0, CX0 + T + 9.0 + 192.0)     # 16' door, piers each side
MAN = (CX1 - 96.0, CX1 - 60.0)                    # 3' door to the courtyard, clear of the slider's landing
PITCH, EAVE_Z, THK = 2 / 12, 108.0, 6.0
RX0, RY0, RX1, _ = S.CARPORT_ROOF
RY1 = BACK + T + 6.0                              # the roof: 6" past the rear wall
RYM = (RY0 + RY1) / 2                             # its ridge
FY = BACK + T / 2                                 # the courtyard fence meets the garage's rear wall line
WALLS = [(CX0, FRONT, CX0 + T, BACK + T),                      # east
         (CX0 + T, BACK, MAN[0], BACK + T), (MAN[1], BACK, CX1, BACK + T),   # rear, either side of the door
         (CX0 + T, FRONT, DOOR[0], FRONT + T), (DOOR[1], FRONT, CX1, FRONT + T)]   # front piers


def garage(sh):
    msp = sh.msp
    drop_text = {"CARPORT", S.carport_size(), "2 SPACES, 8'-6\" x 18'-0\"", "6' FENCE",
                 f"{S.fmt(S.GATE_L)} GATE, OPENS FLAT AGAINST THE HOUSE"}
    for e in list(msp.query("TEXT")):
        if e.dxf.text in drop_text:
            msp.delete_entity(e)
    for e in list(msp.query("LWPOLYLINE[layer=='L-SITE']")):       # the two stalls and the carport's outline
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        if CX0 - 1 <= min(xs) and max(xs) <= CX1 + 1 and FRONT - 1 <= min(ys) and max(ys) <= CY1 + 1:
            msp.delete_entity(e)
        elif abs(min(xs) - CX0) < 1 and abs(min(ys) - CY0) < 1 and abs(max(ys) - CY1) < 1:
            msp.delete_entity(e)
    for e in list(msp.query("LWPOLYLINE[layer=='A-WALL']")):      # the carport's rear post (inside the wall now)
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        if abs(min(xs) - CX0) < 1 and abs(min(ys) - (CY1 - 6)) < 1:
            msp.delete_entity(e)
    fy = CY1 + 3
    for e in list(msp.query("LINE ARC[layer=='A-FENC']")):   # courtyard fence and gate
        if e.dxftype() == "ARC" or abs(e.dxf.start.y - fy) < 1:
            msp.delete_entity(e)
    for x0, y0, x1, y1 in WALLS:
        h = msp.add_hatch(color=8, dxfattribs={"layer": "A-WALL-PATT"})
        h.paths.add_polyline_path([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], is_closed=True)
        sh.rect(x0, y0, x1, y1, "A-WALL")
    sh.line((DOOR[0], FRONT + T / 2), (DOOR[1], FRONT + T / 2), "A-DOOR")
    sh.text("16'-0\" x 7'-0\" GARAGE DOOR", (DOOR[0] + DOOR[1]) / 2, FRONT + 14, 4.0)
    a, b = MAN                                                        # courtyard door, swinging out, hinged at
    sh.line((b, BACK + T), (b, BACK + T + 36), "A-DOOR")              # the house end
    sh.msp.add_arc((b, BACK + T), 36.0, 90.0, 180.0, dxfattribs={"layer": "A-DOOR"})
    sh.text("GARAGE", (CX0 + CX1) / 2, (FRONT + BACK) / 2 + 14, 10.0, "A-AREA-IDEN")
    sh.text(f"{S.fmt(CX1 - CX0 - T)} x {S.fmt(BACK - FRONT - T)} CLEAR", (CX0 + CX1) / 2,
            (FRONT + BACK) / 2, 6.5, "A-AREA-IDEN")
    sh.text("2 CARS; EV CHARGER", (CX0 + CX1) / 2, (FRONT + BACK) / 2 - 14, 5.0, "A-AREA-IDEN")
    for e in list(msp.query("TEXT")):
        if e.dxf.text == "CARPORT ROOF ABOVE (9')":
            msp.delete_entity(e)
    for e in list(msp.query("LWPOLYLINE[layer=='A-CANP']")):        # the carport roof's outline
        xs = [q[0] for q in e.get_points()]
        if abs(min(xs) - RX0) < 1:
            msp.delete_entity(e)
    msp.add_lwpolyline([(RX0, RY0), (RX1, RY0), (RX1, RY1), (RX0, RY1)], close=True,
                       dxfattribs={"layer": "A-CANP", "linetype": "DASHED"})
    msp.add_line((RX0, RYM), (RX1, RYM), dxfattribs={"layer": "A-CANP", "linetype": "DASHED"})
    sh.text("2:12 GABLE ROOF ABOVE, RIDGE", (RX0 + RX1) / 2, RYM + 5, 3.0, "A-CANP")
    sh.line((S.LOT_X0, FY), (CX0, FY), "A-FENC")
    sh.text("6' FENCE", (S.LOT_X0 + CX0) / 2, FY + 10, 4.0)
    return sh


def plan():
    sh = garage(S.build())
    S.render(sh.doc, OUT / "garage.png", S.LOT_X0 - 20, -60, S.E + 420, S.LOT_D + 20, width_in=12, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    build = S.build
    S.build = lambda: garage(build())
    sc = M.build_schematic()
    S.build = build
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    for x0, y0, x1, y1 in WALLS:
        sc.boxes["exterior"].append([x0, y0, x1, y1, 0, 108])
    sc.boxes["exterior"].append([DOOR[0], FRONT, DOOR[1], FRONT + T, 84, 108])   # header over the door
    sc.boxes["exterior"].append([MAN[0], BACK, MAN[1], BACK + T, 80, 108])
    sc.boxes["gdoor"].append([DOOR[0], FRONT + 2, DOOR[1], FRONT + 4, 0, 84])
    sc.boxes["gdoor"].append([MAN[0], BACK + 2, MAN[1], BACK + 4, 0, 80])
    sc.mat["gdoor"] = {"color": 0x2B2D30}
    sc.boxes["roof"] = [b for b in sc.boxes["roof"] if b[4] != 108]   # the flat carport roof comes off
    top = lambda x, y: EAVE_Z + THK + ((RY1 - RY0) / 2 - abs(y - RYM)) * PITCH   # noqa: E731
    for a, b in ((RY0, RYM), (RYM, RY1)):
        X.sloped_slab(sc, "roofing", RX0, a, RX1, b, top, THK)
    gx = CX0                                                         # the east gable end, on the east wall
    sc.tris["exterior"].append([[gx, RY0 + 12, EAVE_Z], [gx, RY1 - 6, EAVE_Z], [gx, RYM, top(gx, RYM) - THK]])
    for p in sc.boxes["post"]:                                       # the walkway's post up to the eave
        if abs(p[0] - CX0) < 1 and p[5] == 108:
            p[5] = EAVE_Z
    out = OUT / "garage"
    M.write_model(sc, out, sc.meta)
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    html = out / "house.html"
    shots = {"driveway": ((250, -200, 62), (260, 400, 60)),
             "east": ((-200, -150, 80), (500, 350, 110)), "courtyard": ((120, 700, 62), (300, 450, 60))}
    for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;gridGroup.visible=false;"
            "scene.traverse(o=>{if(o.isSprite||o.type==='ArrowHelper')o.visible=false;});"
            "document.getElementById('ui').style.display='none';document.getElementById('help').style.display='none';"
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
