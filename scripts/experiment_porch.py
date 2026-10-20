# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: an extended porch that qualifies under Table 22.140.520-D (8' x 5', ceiling no more than 12'
above its floor), so the parking needs no 5' setback from the house front, only to sit behind the front door.

  - The porch grows 1' toward the street (a covered porch may project up to 5' into the front yard,
    §22.110.090.D.2) and 8" east into the carport's walkway: 8'-0" x 5'-0". The front door stays where it is.
  - A slim flat metal canopy at the porch ceiling's height (9') covers the new front foot.
  - The carport's walkway shrinks to 4' (to the front door's line): carport 18' x 22', the fence and gate 1'
    nearer the street, and the dining slider back to 6' with the full 2'-9" of wall at the corner.

Writes renders/experiments/porch/: plan.png, a 3D model (house.html) and street views. Not part of the
regular build.

    uv run scripts/experiment_porch.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402
import exterior as X  # noqa: E402
import make_3d as M  # noqa: E402

OUT = S.RENDERS / "experiments" / "porch"
CHROME = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
FWD, EAST = 12.0, 8.0                       # porch grows 1' toward the street and 8" east
P0, P1 = S.E - EAST, S.N - FWD              # porch's new outer corner
CANOPY_Z = M.CEIL                           # canopy underside at the porch ceiling (9')
_build = S.build


def plan():
    S.CARPORT_WALK = S.PORCH_Y - S.N                          # walkway to the front door's line: 4'
    S.CARPORT = (S.CARPORT[0], S.N, S.E, S.N + S.CARPORT_WALK + S.STALL_D)
    S.OPENINGS[:] = [("east", 514.0, 586.0, "slider") if o[0] == "east" and o[3] == "slider" else o
                     for o in S.OPENINGS]


def build():
    sh = _build()
    for e in list(sh.msp.query("LWPOLYLINE[layer=='L-SITE']")):             # the old porch step
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        if abs(min(xs) - (S.E + 4)) < 0.5 and abs(min(ys) - (S.N - 24)) < 0.5:
            sh.msp.delete_entity(e)
    sh.rect(P0, P1, S.PORCH_X, S.N, "L-SITE")                                # porch floor, 1' forward
    sh.rect(P0, S.N, S.E, S.PORCH_Y, "L-SITE")                               # and 8" into the walkway
    sh.rect(P0 + 4, P1 - 24, S.PORCH_X - 4, P1, "L-SITE")                    # step, in front of it
    sh.msp.add_lwpolyline([(P0, P1), (S.PORCH_X, P1), (S.PORCH_X, S.N), (P0, S.N)], close=True,
                          dxfattribs={"layer": "A-CANP", "linetype": "DASHED"})
    sh.text("CANOPY ABOVE (9')", (P0 + S.PORCH_X) / 2, P1 + 5, 2.4, "A-CANP")
    sh.text("8'-0\" x 5'-0\"", (P0 + S.PORCH_X) / 2, S.N + 12, 3.0)
    return sh


def model(out):
    S.build = build
    try:
        sc = M.build_schematic()
    finally:
        S.build = _build
    sc.polys["concrete"].append([[[P0, P1 - 24], [S.PORCH_X, P1 - 24], [S.PORCH_X, S.PORCH_Y], [P0, S.PORCH_Y]],
                                 0.0, 3.5])
    X.chosen_exterior(sc)
    sc.boxes["canopy"].append([P0, P1, S.PORCH_X, S.N, CANOPY_Z, CANOPY_Z + 3])
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True, "roof_options": {}, "roof_flat": []})
    return out / "house.html"


def views(html):
    if not CHROME.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    for name, ((cx, cy, cz), (tx, ty, tz)) in {"entry": ((260, -160, 64), (430, 300, 70)),
                                               "east": ((-200, -150, 80), (500, 350, 110))}.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            ";orbit.enabled = false; groups.labels.visible = false;"
            "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
            "camera.fov = 60; camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
        subprocess.run([str(CHROME), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(html.parent)}\\{name}.png",
                        "file:///" + win(tmp).replace("\\", "/") + "#roof"], capture_output=True)
        tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan()
    S.render(build().doc, OUT / "plan.png", S.LOT_X0 - 20, S.N - 120, S.face("lounge|gym", -1) + 40, S.S + 140,
             width_in=12, dpi=200)
    views(model(OUT))


if __name__ == "__main__":
    main()
