# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: a shallow built-in storage run along the lobby (the bedroom end of the hall).

  - Full-height cabinets, 10" deep, on the hall's south side from the cased opening to the primary
    bedroom door (along the walk-in closet wall): a hall linen closet plus board games, books and cleaning
    supplies, doors below and open shelves above.
  - The hall stays 3'-2" clear in front of it (code minimum 3'-0"), and the attic hatch stays clear of it.

Writes renders/experiments/hall-storage.png (with the current plan, hall-storage-current.png, to compare)
and a 3D model with a view down the hall. Not part of the regular build.

    uv run scripts/experiment_hall_storage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
DEPTH = 10.0                                    # cabinet depth (the attic hatch stays clear)
RUN = (S.HALL_ARCH + S.INT / 2 + 4.0, 1066.0)   # from just past the cased opening to the primary door
_build = S.build


def build():
    sh = _build()
    y1 = S.face("south hall wall", -1)
    x0, x1 = RUN
    sh.rect(x0, y1 - DEPTH, x1, y1, "A-EQPM")
    sh.text("HALL LINEN / STORAGE CABINETS", (x0 + x1) / 2, y1 - DEPTH / 2, 2.4)
    return sh


def render(png, sh):
    S.render(sh.doc, png, 640.0, 330.0, S.W + 30, 540.0, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "hall-storage"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"down-the-hall": ((870, 420, 63.5), (1110, 440, 50))}
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
    render(OUT / "hall-storage-current.png", _build())
    S.build = build
    render(OUT / "hall-storage.png", S.build())
    model()


if __name__ == "__main__":
    main()
