# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: two matching round arches in the bedroom hall, plain drywall, no trim.

  - One where the hall meets the great room (the hall's mouth, on the lounge | gym wall line), one replacing the
    square dropped header partway down the hall (in line with the guest ensuite | guest wall).
  - Each a half-circle across the hall's 3'-8": springing at 7'-0", peaking 2" under the 9' ceiling.

Writes a 3D model with views (from the lounge down the hall, and back from the primary bedroom door) to
renders/experiments/hall-arches/. Not part of the regular build.

    uv run scripts/experiment_hall_arches.py
"""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments" / "hall-arches"
CEIL = 108.0
GAP = 2.0                                       # arch peak below the ceiling


def arch(sc, x0, x1, y0, y1, n=36):
    """Drywall infill above a half-circle arch spanning y0..y1, between wall faces x0 and x1 (triangles, so the
    curve renders smooth; they show with the roof, #roof)."""
    r, yc = (y1 - y0) / 2, (y0 + y1) / 2
    zs = CEIL - GAP - r
    pts = [(yc - r * math.cos(math.pi * i / n), zs + r * math.sin(math.pi * i / n)) for i in range(n + 1)]
    for x in (x0, x1):                                          # both faces: strips from the curve to the ceiling
        for (ya, za), (yb, zb) in zip(pts, pts[1:]):
            sc.tris["wall"] += [[[x, ya, za], [x, yb, zb], [x, yb, CEIL]], [[x, ya, za], [x, yb, CEIL], [x, ya, CEIL]]]
    for (ya, za), (yb, zb) in zip(pts, pts[1:]):                # the curved soffit
        sc.tris["wall"] += [[[x0, ya, za], [x1, ya, za], [x1, yb, zb]], [[x0, ya, za], [x1, yb, zb], [x0, yb, zb]]]


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    y0, y1 = S.face("bedroom hall wall", +1), S.face("south hall wall", -1)
    a0, a1 = S.face("hall threshold", -1), S.face("hall threshold", +1)
    sc.boxes["wall"] = [b for b in sc.boxes["wall"]                 # the square dropped header comes out
                        if not (abs(b[0] - a0) < 0.5 and abs(b[2] - a1) < 0.5 and b[4] == S.ARCH_HEAD)]
    arch(sc, a0, a1, y0, y1)
    m = S.face("lounge|gym", -1)
    arch(sc, m, m + S.INT, y0, y1)                                  # the hall's mouth
    sc.boxes["wall"].append([m, S.N_IN, S.W_IN, S.S_IN, CEIL, CEIL + 1])   # the wing's flat ceiling (the roof's off)
    M.write_model(sc, OUT, {**sc.meta, "roof_hidden": True})
    html = OUT / "house.html"
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    yc = (y0 + y1) / 2
    shots = {"from-lounge": ((560, yc + 6, 62), (1110, yc, 70)), "from-primary-door": ((1090, yc, 62), (600, yc, 70))}
    for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
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
                        f"--screenshot={win(OUT)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/") + "#roof"],
                       capture_output=True)
        tmp.unlink()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    model()
