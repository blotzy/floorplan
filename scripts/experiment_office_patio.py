# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: office-end (hall ends at the office, primary entered through a foyer off the walk-in
closet), plus a covered patio cut into the house's northwest corner, the office opening onto it.

  - The patio runs the office's full width, from the guest room's wall to the west end, at the porch's
    depth (4'-0"), under the main roof, with a corner post and a wood-look ceiling like the porch's.
    The guest room's west wall becomes an exterior wall along the patio.
  - The office's 6' street window goes; a pair of 6'-0" French doors (out-swinging), centred on the
    office, opens onto the patio. The office bed moves south, clear of the patio.

Writes renders/experiments/office-patio.png and a 3D model, renders/experiments/office-patio/house.html,
with eye-level views. Not part of the regular build.

    uv run scripts/experiment_office_patio.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402
import experiment_office_end as O  # noqa: E402

OUT = S.RENDERS / "experiments"
PATIO_D = S.PORCH_Y - S.N                                 # the porch's depth: 4'-0"
PX, PY = S.face("guest|office", -1) + S.EXT, S.N + PATIO_D   # notch is PX..W by N..PY: the guest room keeps
                                                          # its size, its west wall now exterior
DOORS = (1101.6, 1173.6)                                  # 6'-0" pair, centred on the office (as its window was)
BED_Y = 368.0                                             # office bed, moved south of the notch
_build = S.build


def plan():
    O.plan()
    S.EXT_WALLS["north"] = ("x", S.N, +1, S.PORCH_X, PX)
    S.EXT_WALLS["patio front"] = ("x", PY, +1, PX - S.EXT, S.W)
    S.EXT_WALLS["patio side"] = ("y", PX, -1, S.N, PY + S.EXT)
    S.EXT_WALLS["west"] = ("y", S.W, -1, PY, S.S)
    ops = S.OPENINGS
    ops[:] = [o for o in ops if not (o[0] == "north" and o[1] == 1101.6)]       # office street window
    m = sum(DOORS) / 2
    ops += [("patio front", DOORS[0], m, "door", "a", -1),                      # French doors, out-swinging
            ("patio front", m, DOORS[1], "door", "b", -1)]


def build():
    patched, S.build = S.build, _build                        # O.build calls S.build: the real one
    real_label = S.room_label

    def label(sh, name, *a, **k):
        if name == "OFFICE":                                  # beside the bed, clear of the notch
            k.update(cx=(S.face("guest|office", +1) + S.W_IN - 83) / 2, cy=330.0)
            a = (a[0], PY + S.EXT, *a[2:])                    # clear size: from the patio wall
        real_label(sh, name, *a, **k)

    S.room_label = label
    try:
        sh = O.build()
    finally:
        S.build, S.room_label = patched, real_label
    fu = "A-FURN"
    box = (1100.0, 255.0, S.W_IN + 1, 375.0)                  # the office bed: redrawn clear of the notch
    for e in list(sh.msp):
        if e.dxf.layer != fu or e.dxftype() != "LWPOLYLINE":
            continue
        pts = [tuple(p)[:2] for p in e.get_points()]
        if all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in pts):
            sh.msp.delete_entity(e)
    m = sh.mark()
    hx, hb, ft = S.W_IN, S.W_IN - 3, S.W_IN - 83              # 60" x 80" bed, head on the west wall
    y0, y1 = BED_Y - 30, BED_Y + 30
    sh.rect(hb, y0, hx, y1, fu)
    sh.rect(ft, y0, hb, y1, fu)
    sh.rect(hb - 16, y0 + 3, hb - 2, BED_Y - 2, fu); sh.rect(hb - 16, BED_Y + 2, hb - 2, y1 - 3, fu)
    for ny in (y0 - 18, y1):
        sh.rect(hx - 16, ny, hx, ny + 18, fu)
    sh.movable_since(m)
    sh.rect(S.W - 6, S.N, S.W, S.N + 6, "A-WALL")             # patio corner post
    sh.text("PATIO", (PX + S.W) / 2 - 4, S.N + 8, 5.0, "A-AREA-IDEN")
    return sh


def model():
    import exterior as X
    import make_3d as M
    S.build = build                                           # the 3D model reads the plan through it
    try:
        sc = M.build_schematic()
    finally:
        S.build = _build
    E_, W_, N_, S_ = S.E, S.W, S.N, S.S
    px, py = S.PORCH_X, S.PORCH_Y
    fp = [[E_, py], [px, py], [px, N_], [PX, N_], [PX, PY], [W_, PY], [W_, S_], [E_, S_]]
    sc.polys["slab"][0][0] = fp
    sc.polys["ceiling"][0][0] = fp
    sc.meta["grid"] = M.floor_grid(fp, (S.E_IN, S.N_IN))
    sc.polys["concrete"].append([[[PX, N_], [W_, N_], [W_, PY], [PX, PY]], 0.0, 3.0])   # patio slab
    sc.boxes["post"].append([W_ - 6, N_, W_, N_ + 6, 0, M.CEIL])                          # corner post
    on_patio = lambda q: (abs(q[1] - PY) < 0.1 and abs(q[3] - PY) < 0.1 and PX - 0.1 <= min(q[0], q[2])) or \
        (abs(q[0] - PX) < 0.1 and abs(q[2] - PX) < 0.1 and max(q[1], q[3]) <= PY + 0.1)    # noqa: E731
    keep = []
    for q in sc.quads["wall"]:                                 # the notch's outer faces are stucco
        (sc.quads["exterior"] if on_patio(q) else keep).append(q)
    sc.quads["wall"] = keep
    y0, y1 = PY + 4, PY + 6                                   # French door leaves: dark frames, full glass
    for a, b in ((DOORS[0], sum(DOORS) / 2), (sum(DOORS) / 2, DOORS[1])):
        sc.boxes["frame"] += [[a, y0, a + 3, y1, 0, 96], [b - 3, y0, b, y1, 0, 96],
                              [a + 3, y0, b - 3, y1, 93, 96], [a + 3, y0, b - 3, y1, 0, 8]]
        sc.quads["glass"].append([a + 3, PY + 5, b - 3, PY + 5, 8, 93])
    X.chosen_exterior(sc)
    sc.mat["frame"] = {"color": 0x2B2D30}
    sc.boxes["feature"].append([PX, N_, W_ - 6, PY, M.CEIL - 1.5, M.CEIL - 0.5])          # patio ceiling
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    opts = X.roof_options()
    out = OUT / "office-patio"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True, "roof_options": opts,
                            "roof_flat": [i + 1 for i, k in enumerate(opts) if "flat" in k]})
    return out / "house.html"


def views(html):
    """Stills from the 3D model: the patio from the street, and the office looking out to it."""
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    shots = {"street-view": ((1330, -150, 66), (1100, 300, 70), "#roof"),
             "office-view": ((1110, 435, 62), (1137, 250, 55), "")}
    for name, ((cx, cy, cz), (tx, ty, tz), hsh) in shots.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "\norbit.enabled = false; groups.labels.visible = false;"
            "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
            "camera.fov = 70; camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(html.parent)}\\{name}.png",
                        "file:///" + win(tmp).replace("\\", "/") + hsh], capture_output=True)
        tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS), dict(S.EXT_WALLS), S.wic)
    plan()
    S.wic = O.wic
    S.render(build().doc, OUT / "office-patio.png", S.face("lounge|gym", -1) - 20, S.N - 70, S.W + 40,
             S.S + 40, width_in=14, dpi=200)
    views(model())
    S.WALLS, S.OPENINGS, S.EXT_WALLS, S.wic = base


if __name__ == "__main__":
    main()
