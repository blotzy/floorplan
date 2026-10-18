# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: end the bedroom hall just past the office door, with the primary bedroom door in the
end wall.

  - The west exterior door and its transom go; a new wall closes the hall just past the office door,
    and the primary bedroom door sits in it, on axis with the hall.
  - The primary bedroom takes the last stretch of the hall as an entry nook along its north side
    (room for a dresser past the open door); the bed stays out of view from the hall.
  - The office (door, closet) and the walk-in closet stay as they are.
  - Halfway down the hall, just past the common bath, a cased opening with a dropped header
    (7'-6" under the 9' ceiling) marks the start of the bedroom end: no door.

Writes renders/experiments/primary-end.png and a 3D model, renders/experiments/primary-end/house.html
(open in a browser; walk mode). Not part of the regular build (the current plan for
comparison is renders/experiments/office-end-current.png).

    uv run scripts/experiment_primary_end.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
END = 1110.5                              # hall end wall centreline: just past the office door's jamb
ARCH = 892.0                              # threshold wall centreline: between the common bath and guest doors
ARCH_OPEN = (413.2, 449.2)                # 3'-0" cased opening, centred in the hall (~8" stubs each side)
ARCH_HEAD = 90.0                          # dropped header: 7'-6"


def plan():
    ws, ops = S.WALLS, S.OPENINGS
    for i, w in enumerate(ws):
        if w[0] == "south hall wall":                      # stops at the new end wall
            ws[i] = (*w[:4], END + S.INT / 2, w[5])
    ws.append(("hall end", "y", END, 403.2, 459.2, S.INT))
    ws.append(("hall threshold", "y", ARCH, 403.2, 459.2, S.INT))
    drop = {("west", 414.7), ("south hall wall", 1070.0)}
    ops[:] = [o for o in ops if (o[0], o[1]) not in drop]
    ops.append(("hall end", 411.0, 447.0, "door", "a", +1))   # primary, at the end of the hall:
                                                              # opens flat against the office wall
    ops.append(("hall threshold", *ARCH_OPEN, "cased"))


_build = S.build


def build():
    sh = _build()
    hall_n = S.face("bedroom hall wall", +1)
    m = sh.mark()
    d0 = END + S.INT / 2 + 40                                   # dresser on the office wall, past
    sh.rect(d0, hall_n, S.W_IN, hall_n + 20, "A-FURN")          # the open door
    sh.text("DRESSER", (d0 + S.W_IN) / 2, hall_n + 10, 3.5)
    sh.movable_since(m)
    t = S.INT / 2                                               # dropped header over the cased opening
    for x in (ARCH - t, ARCH + t):
        sh.msp.add_line((x, ARCH_OPEN[0]), (x, ARCH_OPEN[1]),
                        dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    sh.text("HEADER AT 7'-6\"", ARCH + 22, (ARCH_OPEN[0] + ARCH_OPEN[1]) / 2, 2.4, "A-CLNG", rot=90)
    return sh


def views(html):
    """Eye-level stills from the 3D model: down the hall, and into the primary's entry nook."""
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    for name, ((cx, cy, cz), (tx, ty, tz)) in {"hall-view": ((690, 430, 62), (1200, 430, 58)),
                                               "nook-view": ((1100, 560, 62), (1211, 420, 50))}.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "\norbit.enabled = false; groups.labels.visible = false;"
            "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
            "camera.fov = 70; camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(html.parent)}\\{name}.png",
                        "file:///" + win(tmp).replace("\\", "/")], capture_output=True)
        tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = (copy.deepcopy(S.WALLS), copy.deepcopy(S.OPENINGS))
    plan()
    S.render(build().doc, OUT / "primary-end.png", S.face("lounge|gym", -1) - 20, S.N - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)
    import exterior as X
    import make_3d as M
    S.build = build                                            # the 3D model reads the plan through it
    try:
        sc = M.build_schematic()
    finally:
        S.build = _build
    t = S.INT / 2
    sc.boxes["wall"].append([ARCH - t, ARCH_OPEN[0], ARCH + t, ARCH_OPEN[1], ARCH_HEAD, M.CEIL])
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    opts = X.roof_options()
    M.write_model(sc, OUT / "primary-end", {**sc.meta, "roof_hidden": True, "roof_options": opts,
                                            "roof_flat": [i + 1 for i, k in enumerate(opts) if "flat" in k]})
    views(OUT / "primary-end" / "house.html")
    S.WALLS, S.OPENINGS = base


if __name__ == "__main__":
    main()
