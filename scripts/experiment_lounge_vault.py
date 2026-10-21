# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: vault only the lounge side of the great room.

  - Outside nothing changes: the same split roof, shed and clerestory.
  - Inside, the lounge and foyer keep the sloped ceiling up to the clerestory; the dining room and kitchen
    get a flat 9' ceiling under the shed (an attic space above it, about 2' deep at the rear wall and about
    4' where it meets the lounge, for ducts, the range hood duct and recessed lights).
  - The step between them is a drywall face across the great room on the foyer-wall / bedroom-hall line.

Writes a 3D model, renders/experiments/lounge-vault/house.html, with eye-level views. The floor plan doesn't
change. Not part of the regular build.

    uv run scripts/experiment_lounge_vault.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments" / "lounge-vault"


def model():
    import exterior as X
    import make_3d as M
    from shapely.geometry import box
    from shapely.ops import unary_union
    real = X.great_room_inside
    yf, kx, C = S.FOYER_WALL_END, S.face("kitchen|pantry", -1), M.CEIL

    def inside(sc, under, *a, **k):
        real(sc, under, *a, **k)
        dining = lambda t: all(p[1] >= yf - 0.1 and S.E_IN - 0.1 <= p[0] <= kx + 0.1 and p[2] > C + 0.5   # noqa: E731
                               for p in t)                    # the sloped ceiling over the dining and kitchen
        sc.tris["wall"] = [t for t in sc.tris["wall"] if not dining(t)]
        X.quad(sc, "wall", [S.E_IN, yf, C - 1], [kx, yf, C - 1], [kx, S.S_IN, C - 1], [S.E_IN, S.S_IN, C - 1])
        X.quad(sc, "wall", [S.E_IN, yf, C - 1], [kx, yf, C - 1], [kx, yf, under(yf) - 1],   # the step, up
               [S.E_IN, yf, under(yf) - 1])                                                # to the slope

    X.great_room_inside = inside
    try:
        sc = M.build_schematic()
        X.chosen_exterior(sc)
    finally:
        X.great_room_inside = real
    lx0, lx1 = X.LOUNGE_X                                     # flat ceilings everywhere but the lounge and foyer
    M.add_vault_ceiling(sc, unary_union([box(lx0, S.N, lx1, yf), box(S.E, S.PORCH_Y, lx0, yf)]))
    M.write_model(sc, OUT, {**sc.meta, "roof_hidden": True})
    return OUT / "house.html"


def views(html):
    """Stills: from the lounge toward the kitchen, and from the dining table toward the lounge."""
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    shots = {"lounge-to-kitchen": ((640, 270, 63.5), (470, 560, 80)),
             "dining-to-lounge": ((420, 600, 46), (600, 280, 100))}
    for name, ((cx, cy, cz), (tx, ty, tz)) in shots.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "\norbit.enabled = false; groups.labels.visible = false; groups.ceil.visible = true;"
            "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
            "camera.fov = 75; camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(html.parent)}\\{name}.png",
                        "file:///" + win(tmp).replace("\\", "/") + "#roof"], capture_output=True)   # the vault
        tmp.unlink()


if __name__ == "__main__":
    views(model())
