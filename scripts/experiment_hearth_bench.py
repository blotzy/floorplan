# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a hearth bench on the lounge TV wall (the lounge side of the foyer wall).

  - A floating bench 16" deep and 18" high runs the TV wall, from just past the reeded porch-side
    window to the walkway between the foyer and the bedroom hall.
  - A linear electric fireplace (60") is set into the bench's face, centred under the TV, so the flames
    sit low and the 90" TV stays at seated-viewing height just above the bench.
  - The wall above is a wood-slat feature wall up to the sloped ceiling.

Writes renders/experiments/hearth-bench.png and a 3D model, renders/experiments/hearth-bench/house.html,
with eye-level views. Not part of the regular build.

    uv run scripts/experiment_hearth_bench.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
DEPTH, HEIGHT = 16.0, 18.0                    # bench
BENCH_Y = (284.0, 398.0)                      # past the reeded window, short of the walkway
FIRE_W = 60.0                                 # linear electric fireplace, set into the bench face
SEAT_CY = (305.0 + 396.0) / 2                 # the TV's centre line (as in the plan)
_build = S.build


def build():
    sh = _build()
    x0 = S.face("foyer wall", +1)
    fu = "A-FURN"
    m = sh.mark()
    for e in list(sh.msp.query("TEXT")):                     # the TV label goes after the bench's, so the
        if e.dxf.text.startswith("TV"):                       # 3D model reads the bench as a bench
            sh.msp.delete_entity(e)
    sh.rect(x0, BENCH_Y[0], x0 + DEPTH, BENCH_Y[1], fu)
    sh.text("BENCH", x0 + DEPTH / 2, BENCH_Y[0] + 7, 2.5)
    sh.text('TV 90"', x0 + 8, SEAT_CY, 4.0, rot=90)
    sh.rect(x0 + DEPTH - 3, SEAT_CY - FIRE_W / 2, x0 + DEPTH, SEAT_CY + FIRE_W / 2, "A-EQPM")
    sh.text("ELEC. FIREPLACE", x0 + DEPTH + 7, SEAT_CY, 3.0, rot=90)
    sh.movable_since(m)
    return sh


def model():
    import exterior as X
    import make_3d as M
    S.build = build
    try:
        sc = M.build_schematic()
    finally:
        S.build = _build
    x0 = S.face("foyer wall", +1)
    under = X.shed_vault_under(2 / 12)                       # the great room's sloped ceiling
    for b in sc.boxes["fixture"]:                            # the TV moves out in front of the slats
        if abs(b[0] - x0) < 1 and b[3] - b[1] > 70 and b[4] > 20:
            b[0], b[2], b[4], b[5] = x0 + 1.5, x0 + 4.5, 26.0, 70.0
    y = BENCH_Y[0]
    while y + 1.5 <= BENCH_Y[1]:                             # wood slats, 1-1/2" every 3", to the ceiling
        sc.boxes["feature"].append([x0, y, x0 + 1.25, y + 1.5, HEIGHT, under(y + 1.5) - 1])
        y += 3.0
    fx = x0 + DEPTH
    sc.boxes["frame"].append([fx - 4, SEAT_CY - FIRE_W / 2 - 1, fx + 0.2, SEAT_CY + FIRE_W / 2 + 1, 4, 14])
    sc.boxes["flame"].append([fx - 0.5, SEAT_CY - FIRE_W / 2 + 2, fx + 0.3, SEAT_CY + FIRE_W / 2 - 2, 6, 12])
    X.chosen_exterior(sc)
    sc.mat["frame"] = {"color": 0x2B2D30}
    sc.mat["flame"] = {"color": 0xFF8A2A, "emissive": 0xC0501A}
    sc.mat["feature"] = {"color": 0xA8754B}
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "hearth-bench"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    return out / "house.html"


def views(html):
    """Stills: from the couch toward the TV wall, and the lounge from the dining room."""
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    shots = {"couch-view": ((610, 345, 42), (453, 345, 50)),
             "lounge-view": ((640, 470, 62), (453, 320, 70))}
    for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "\norbit.enabled = false; groups.labels.visible = false; groups.furn.visible = true; groups.ceil.visible = true;"
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
    S.render(build().doc, OUT / "hearth-bench.png", S.E - 40, S.N - 40, S.face("lounge|gym", -1) + 30, 480.0,
             width_in=12, dpi=200)
    views(model())


if __name__ == "__main__":
    main()
