# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the lounge clerestory as three separate windows instead of one 18' band.

  - Three 4'-0" x 3'-0" windows over the lounge, 3'-0" of stucco between them, spanning the same 18' as the
    band and centred on it (36 sq ft of glass instead of 54).
  - Separate punched windows could be recessed like the street windows below them (the band is flush), and
    the stucco piers between them stiffen the tall street wall.

Writes renders/experiments/clerestory-three/ (a 3D model, a front view and a view up from the lounge, and the
same two views of the current plan, *-current.png, to compare). Not part of the regular build.

    uv run scripts/experiment_clerestory_three.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments" / "clerestory-three"
UNIT, PIER = 48.0, 36.0                          # each window's width, and the stucco between them


def main():
    import exterior as X
    import make_3d as M
    band = X.clerestory

    def three(sc, x0, x1, top, pieces):
        out = []
        for a, b, h in pieces:
            if b - a > 3 * UNIT:                                          # the band: split into three
                mid, step = (a + b) / 2, UNIT + PIER
                out += [(mid + k * step - UNIT / 2, mid + k * step + UNIT / 2, h) for k in (-1, 0, 1)]
            else:
                out.append((a, b, h))
        band(sc, x0, x1, top, out)

    X.clerestory = three
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    OUT.mkdir(parents=True, exist_ok=True)
    M.write_model(sc, OUT, sc.meta)
    html = OUT / "house.html"
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    shots = {"front": ((600, -620, 66), (600, 300, 115), "#roof", ""),
             "from-lounge": ((600, 420, 63.5), (560, 240, 150), "#roof", "groups.labels.visible = false;")}
    current = S.RENDERS / "3d" / "house.html"                             # the same views of the current plan
    jobs = [(html, name, v) for name, v in shots.items()] + [(current, name + "-current", v) for name, v in shots.items()]
    for src, name, ((cx, cy, cz), (tx, ty, tz), hsh, extra) in jobs:
        tmp = src.with_name(f"_{name}.html")
        tmp.write_text(src.read_text().replace(hook, hook + (
            ";orbit.enabled = false;" + extra +
            "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
            f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(OUT)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/") + hsh],
                       capture_output=True)
        tmp.unlink()


if __name__ == "__main__":
    main()
