# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the current primary suite (walk-in closet along the hall, bath along the rear wall) without the
tub, the bath made shallower and the walk-in closet wider.

  - The bath | closet wall moves toward the rear wall: the closet is 7'-0" deep, enough for hanging on both
    long walls with a 3' aisle between them (the current 5'-10" leaves about 22"). Same hanging, corner shelves
    and drawer stack as the current closet, same door from the bedroom.
  - The bath is about 4'-10" deep. No tub: a 5'-0" curbless shower at the plumbing-wall end (heads on the
    plumbing wall and the closet wall, a niche in the closet wall, a fixed glass panel with a walk-in opening
    by the rear wall), then the WC and the 60" double vanity on the closet wall, as now. Door from the bedroom
    at the rear-wall end, as now. The house's tub is the guest ensuite's.

Writes renders/experiments/suite-wide-wic.png and a 3D model with views into the closet and the bath. Not part
of the regular build.

    uv run scripts/experiment_suite_wide_wic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments"
WIC_D = 84.0                                    # closet depth: 24" hanging + 36" aisle + 24" hanging
SHOWER_W = 60.0                                 # shower width along the bath, from the plumbing wall


def plan():
    y = S.face("south hall wall", +1) + WIC_D + S.WET / 2
    ws = S.WALLS
    for i, w in enumerate(ws):
        if w[0] == "bath|wic":
            ws[i] = (w[0], w[1], y, *w[3:])


def primary_bath(sh):
    m0, m1 = S.face("utility|bath", +1), S.face("suite|primary", -1)
    top = S.face("bath|wic", +1)
    gx = m0 + SHOWER_W
    S.wet_zone(sh, m0, top, gx, S.S_IN)
    hy = (top + S.S_IN) / 2
    sh.circle((m0 + 4, hy), 2.5, "A-EQPM"); sh.heads.append((m0, hy, 1.0, 0.0))   # head on the plumbing wall
    S.shower_head(sh, m0 + 42, top, +1)                                    # and one on the closet wall
    sh.rect(m0 + 8, top - 3.5, m0 + 26, top, "A-EQPM")                     # niche in the closet wall
    sh.text("NICHE", m0 + 17, top + 4, 2.0)
    sh.text("CURBLESS SHOWER", (m0 + gx) / 2, hy + 6, 2.6)
    S.glass(sh, (gx, top), (gx, S.S_IN - 30))                              # fixed panel, walk-in by the rear wall
    S.drain(sh, (gx - 3, top + 3), (gx - 3, S.S_IN - 3))
    S.wc(sh, gx + 2.25, top, gx + 32.25, top + 28)                         # closet wall: 17.25" to the glass
    S.vanity(sh, m1 - 60, top, m1, top + 22, "DOUBLE VANITY 60")
    for hx in (911.0, 999.0):
        sh.text("HIGH WINDOW", hx, S.S_IN - 4, 2.0)
    S.room_label(sh, "PRIMARY BATH", m0, top, m1, S.S_IN, cx=(gx + 32 + m1 - 60) / 2, cy=top + 30, h=2.8)


def render(png, sh):
    S.render(sh.doc, png, S.face("pantry|laundry", -1) - 20, S.face("south hall wall", -1) - 40, S.W + 40,
             S.S + 40, width_in=14, dpi=200)


def model():
    import exterior as X
    import make_3d as M
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / "suite-wide-wic"
    M.write_model(sc, out, {**sc.meta, "roof_hidden": True})
    html = out / "house.html"
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if chrome.exists():
        hook = "if (location.hash === '#touchwalk') startTouchWalk();"
        win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
        shots = {"from-bedroom": ((1190, 520, 63.5), (1000, 545, 50)), "overhead": ((1000, 700, 330), (980, 520, 0))}
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
    plan()
    S.primary_bath = primary_bath
    render(OUT / "suite-wide-wic.png", S.build())
    model()


if __name__ == "__main__":
    main()
