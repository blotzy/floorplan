# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the reading nook takes part of the office closet, behind its low bookshelves.

The wall between the nook and the office closet steps toward the street along the bookshelves' run (from just
past the suite door's swing to the west wall, about 4'-10"), under a header at 7'-0". The closet's east end
(behind the door's swing) stays a 2'-deep hanging closet for the office.

  - shelves: a 12" recess; the bookshelves move into the wall, flush, to the header. The office keeps a
    12"-deep shelf closet behind them.
  - alcove: the full 2' depth; a built-in window seat (drawers under) beside the nook window, shelves above.
    The office closet is the 3'-2" at its east end only.

Writes renders/experiments/nook-alcove.png (plan: current, shelves, alcove), and a 3D model and views for each
option to renders/experiments/nook-alcove/<option>/. Not part of the regular build.

    uv run scripts/experiment_nook_alcove.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
WALLS0 = list(S.WALLS)
BUILD0 = S.build
HALL_N_FACE = S.HALL_N - S.INT / 2                    # the office side of the hall wall (the closet's back)
NOOK_FACE = S.HALL_N + S.INT / 2                      # the nook side
A = S.HALL_END + S.INT / 2 + S.NOOK_SHELF_START       # where the bookshelves start, clear of the door's swing
XR = A - S.INT / 2                                    # centreline of the recess's east return
CL0 = 1103.0 + 12.0                                   # the office closet's east end (as built in schematic.py)
DEPTH = {"shelves": 12.0, "alcove": 24.0}
HEADER = 84.0
SHOTS = {"from-bedroom": ((1135, 540, 63.5), (1195, 395, 38))}


def set_walls(opt):
    S.WALLS[:] = WALLS0
    if opt == "current":
        return
    c = NOOK_FACE - DEPTH[opt] - S.INT / 2            # recessed wall's centreline
    S.WALLS[:] = [w for w in WALLS0 if w[0] != "bedroom hall wall"] + [
        ("bedroom hall wall", "x", S.HALL_N, 671.75, XR, S.INT),
        ("nook recess", "x", c, XR, S.W_IN, S.INT),
        ("nook return", "y", XR, c - S.INT / 2, NOOK_FACE, S.INT)]


def edit(sh, opt):
    if opt == "current":
        return sh
    msp = sh.msp
    zone = lambda x, y: 1110 <= x <= S.W_IN + 1 and HALL_N_FACE - 25 <= y <= NOOK_FACE + 13  # noqa: E731
    for q in ("LWPOLYLINE[layer=='A-FURN']", "LINE[layer=='A-FURN']"):
        for e in list(msp.query(q)):
            pts = [(p[0], p[1]) for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else \
                [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            if all(zone(*p) for p in pts):
                msp.delete_entity(e)
    for e in list(msp.query("TEXT[layer=='A-ANNO-TEXT']")):
        if e.dxf.text in ("CL", "LOW BOOKSHELVES") and zone(e.dxf.insert.x, e.dxf.insert.y):
            msp.delete_entity(e)
    fu, d = "A-FURN", DEPTH[opt]
    back = NOOK_FACE - d                                                      # the recess's back (nook side)
    sh.rect(CL0, HALL_N_FACE - 24, XR - S.INT / 2, HALL_N_FACE, fu)           # office: hanging at the east end
    sh.line((CL0, HALL_N_FACE - 12), (XR - S.INT / 2, HALL_N_FACE - 12), fu)
    sh.text("CL", (CL0 + XR - S.INT / 2) / 2, HALL_N_FACE - 18, 3.0)
    if opt == "shelves":
        sh.rect(XR + S.INT / 2, HALL_N_FACE - 24, S.W_IN, back - S.INT, fu)   # office: a 12" shelf closet
        sh.text("CL", (XR + S.W_IN) / 2, HALL_N_FACE - 18, 3.0)
        sh.rect(A, back, S.W_IN, NOOK_FACE, fu)
        sh.text("SHELVES", (A + S.W_IN) / 2, back + 6, 2.2)
    else:
        sh.rect(A, back, S.W_IN, back + 20.0, fu)
        sh.text("BENCH SEAT", (A + S.W_IN) / 2, back + 10, 2.4)
        sh.text("SHELVES ABOVE", (A + S.W_IN) / 2, NOOK_FACE + 4, 1.8)        # outside the seat (3D height)
    return sh


def build(opt):
    set_walls(opt)
    return edit(BUILD0(), opt)


def plan():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    import zoning_set as Z
    tmp = OUT / "nook-alcove"
    tmp.mkdir(parents=True, exist_ok=True)
    win = (1040.0, 250.0, 1225.0, 520.0)
    titles = {"current": "Current: low bookshelves; office closet 8'-0\"",
              "shelves": "Recessed shelves (12\"); office: 3'-2\" hanging + 12\" shelves",
              "alcove": "Window-seat alcove (2'), shelves above; office: 3'-2\" closet"}
    fig, axs = plt.subplots(1, 3, figsize=(16, 8.4))
    for ax, (opt, t) in zip(axs, titles.items()):
        p = tmp / f"_plan-{opt}.png"
        S.render(build(opt).doc, p, *win, width_in=5, dpi=200)
        ax.imshow(mpimg.imread(p)); ax.set_title(t, fontsize=10, loc="left"); ax.axis("off")
        p.unlink()
    set_walls("current")
    fig.tight_layout()
    Z.save_png(fig, OUT / "nook-alcove.png", dpi=110)
    plt.close(fig)


def model(opt):
    import exterior as X
    import make_3d as M
    S.build = lambda: build(opt)
    try:
        sc = M.build_schematic()
    finally:
        S.build = BUILD0
        set_walls("current")
    if opt != "current":
        sc.boxes["wall"].append([A, HALL_N_FACE, S.W_IN, NOOK_FACE, HEADER, M.CEIL])   # header over the recess
        if opt == "alcove":
            back = NOOK_FACE - DEPTH[opt]
            sc.boxes["closet"].append([A, back, S.W_IN, back + 11.0, 48.0, HEADER])     # shelves above the seat
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "nook-alcove" / opt
    M.write_model(sc, out, sc.meta)
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    html = out / "house.html"
    for name, ((cx, cy, cz), (tx, ty, tz)) in SHOTS.items():
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
    for o in ("current", "shelves", "alcove"):
        model(o)
