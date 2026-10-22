# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a built-in banquette under the dining window instead of a table with chairs all round.

  - A built-in bench along the south wall under the 12' window (its 18" sill is seat height), deep drawers
    in its base, a back cushion against the window wall.
  - An 84" x 36" table pulled up to it, overlapping the seat front; three chairs on the open side and one at
    each end (about 8 seated; an extendable table takes more at holidays).
  - The table and chairs sit about 3' further south than now, leaving an open strip of floor between the
    dining area and the lounge (a reading chair, plants, a play or project area).

Writes renders/experiments/dining-banquette.png (with the current plan, dining-banquette-current.png, to
compare) and a 3D model with a view of the dining area. Not part of the regular build.

    uv run scripts/experiment_dining_banquette.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
BENCH = (380.0, 532.0)                          # banquette: under the window (384-528) plus 4" each side
BENCH_D = 22.0                                  # seat plus back cushion
TABLE = (84.0, 36.0)                            # table length x depth
_build = S.build


def _in_dining(e):
    """The current dining table and chairs (A-FURN, between the east wall and the stools)."""
    if e.dxf.layer != "A-FURN":
        return False
    if e.dxftype() == "CIRCLE":
        c = e.dxf.center
        return S.E_IN < c.x < 530.0 and S.KITCHEN_ROW < c.y < S.S_IN
    if e.dxftype() == "LWPOLYLINE":
        xs = [p[0] for p in e.get_points("xy")]
        ys = [p[1] for p in e.get_points("xy")]
        return S.E_IN < min(xs) and max(xs) < 530.0 and S.KITCHEN_ROW < min(ys) and max(ys) < S.S_IN
    return False


def build():
    sh = _build()
    for e in [e for e in sh.msp if _in_dining(e)]:
        sh.msp.delete_entity(e)
    fu = "A-FURN"
    b0, b1 = BENCH
    by = S.S_IN - BENCH_D
    sh.rect(b0, by, b1, S.S_IN, fu)                                       # built-in banquette
    sh.text("BANQUETTE BENCH, DRAWERS BELOW", (b0 + b1) / 2, by + 9, 2.6)
    cx = (b0 + b1) / 2
    tl, td = TABLE
    ty1 = by + 4                                                          # table overlaps the seat front 4"
    ty0 = ty1 - td
    sh.rect(cx - tl / 2, ty0, cx + tl / 2, ty1, fu)
    for dx in (-28, 0, 28):                                               # three chairs on the open side
        sh.circle((cx + dx, ty0 - 10), 7, fu)
    for x in (cx - tl / 2 - 10, cx + tl / 2 + 10):                        # and one at each end
        sh.circle((x, (ty0 + ty1) / 2), 7, fu)
    ly = (S.KITCHEN_ROW + ty0 - 17) / 2                                   # room label moves off the banquette,
    for t in sh.msp.query("TEXT"):                                        # into the open floor
        if t.dxf.text == "DINING" or (t.dxf.text.startswith("15'") and "x 12'" in t.dxf.text):
            for k in ("insert", "align_point"):
                if t.dxf.hasattr(k):
                    v = t.dxf.get(k)
                    t.dxf.set(k, (v[0], v[1] - (592.0 - ly) - 6))
    sh.text("OPEN FLOOR (FLEX)", cx, ly + 12, 3.0)
    return sh


def render(png, sh):
    S.render(sh.doc, png, S.E - 40, 380.0, S.face("kitchen|pantry", -1) + 20, S.S + 40, width_in=12, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "dining-banquette"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-lounge": ((455, 445, 63.5), (455, 610, 30)), "overhead": ((450, 380, 330), (455, 540, 0))}
        for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
            tmp = html.with_name(f"_{name}.html")
            tmp.write_text(html.read_text().replace(hook, hook + (
                "\norbit.enabled = false; groups.labels.visible = false;"
                "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
                "camera.fov = 70; camera.updateProjectionMatrix();"
                f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
            subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                            "--window-size=1400,900", "--virtual-time-budget=15000",
                            f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/")],
                           capture_output=True)
            tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render(OUT / "dining-banquette-current.png", _build())
    S.build = build
    render(OUT / "dining-banquette.png", S.build())
    model()


if __name__ == "__main__":
    main()
