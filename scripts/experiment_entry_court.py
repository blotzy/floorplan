# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: the entry court's seat wall, seen from the lounge window.

  - current: the street run plus a return to the house just short of the lounge window.
  - mid-return: the return centred between the porch notch and the lounge window.
  - mid-return-long: the same, with the street run extended east to 6" short of the driveway edge (no gap at the
    front corner; the court opens only on its driveway side).
  - porch-return: the return moved east to land just past the porch notch (the court narrows to the porch's line),
    clear of the lounge window.
  - no-return: the street run only, a freestanding seat wall open at its west end.
  - no-court: no court or wall; a 3' paver landing in front of the porch step, the house numbers on the house
    front between the porch and the lounge window.

Writes a 3D model per option and views (standing at the lounge window, and from the street) to
renders/experiments/entry-court/, plus a side-by-side comparison. Not part of the regular build.

    uv run scripts/experiment_entry_court.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

OUT = S.RENDERS / "experiments" / "entry-court"
Y0, T = 156.0, 8.0                                         # the street run's face and the 8" block
RET = S.PORCH_X + T                                        # porch-return: the return's west face
MID = (S.PORCH_X + 502.4) / 2 + T / 2                       # mid-return: the return's west face (window at 502.4)

OPTIONS = {
    "current": ("Current: return beside the lounge window", S.ENTRY_COURT, S.ENTRY_WALLS),
    "mid-return": ("Return halfway between the porch and the window", (S.E, Y0, MID, S.N),
                   [(S.E + 36.0, Y0, MID, Y0 + T), (MID - T, Y0 + T, MID, S.N)]),
    "mid-return-long": ("Return halfway, front run to 6\" short of the driveway", (S.E, Y0, MID, S.N),
                        [(S.E + 6.0, Y0, MID, Y0 + T), (MID - T, Y0 + T, MID, S.N)]),
    "porch-return": ("Return moved to the porch line", (S.E, Y0, RET, S.N),
                     [(S.E + 36.0, Y0, RET, Y0 + T), (S.PORCH_X, Y0 + T, RET, S.N)]),
    "no-return": ("No return: freestanding seat wall", S.ENTRY_COURT, [S.ENTRY_WALLS[0]]),
    "no-court": ("No court: landing at the porch step", None, []),
}
OX, OY = S.PORCH_OUT
LANDING = (OX, OY - 24 - 36, S.PORCH_X, OY - 24)           # pavers in front of the porch step
NUMBERS = (S.PORCH_X + 14, S.N - 0.5, S.PORCH_X + 32, S.N, 60, 66)


def no_court(sc):
    """Take the court, its walls and the wall's house numbers out; add the landing."""
    court, walls = OPTIONS["current"][1], OPTIONS["current"][2]
    rect = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]  # noqa: E731
    sc.polys["pavers"] = [q for q in sc.polys["pavers"] if q[0] != rect(*court)]
    sc.boxes["concrete"] = [b for b in sc.boxes["concrete"] if b[:4] not in [list(w) for w in walls]]
    w0 = walls[0]
    sc.boxes["post"] = [b for b in sc.boxes["post"] if b[:2] != [w0[2] - 30, w0[1] - 0.5]]
    sc.polys["pavers"].append([rect(*LANDING), 0.0, 2.0])
    sc.boxes["post"].append(list(NUMBERS))
SHOTS = {"lounge": ((570, 290, 62), (440, 140, 26)), "street": ((580, 20, 62), (400, 260, 30))}


def model(key):
    import exterior as X
    import make_3d as M
    _, court, walls = OPTIONS[key]
    S.ENTRY_COURT, S.ENTRY_WALLS = (court, walls) if court else OPTIONS["current"][1:]
    sc = M.build_schematic()
    X.chosen_exterior(sc)
    if not court:
        no_court(sc)
    M.add_vault_ceiling(sc, X.great_room_vault(to_outside=True))
    out = OUT / key
    out.mkdir(parents=True, exist_ok=True)
    M.write_model(sc, out, sc.meta)
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        return
    html, hook = out / "house.html", "if (location.hash === '#touchwalk') startTouchWalk();"
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    for name, ((cx, cy, cz), (tx, ty, tz)) in SHOTS.items():
        tmp = html.with_name(f"_{name}.html")
        tmp.write_text(html.read_text().replace(hook, hook + (
            "setTimeout(()=>{orbit.enabled=false;groups.labels.visible=false;gridGroup.visible=false;"
            "scene.traverse(o=>{if(o.isSprite||o.type==='ArrowHelper')o.visible=false;});"
            "document.getElementById('ui').style.display='none';document.getElementById('help').style.display='none';"
            "camera.fov=65;camera.updateProjectionMatrix();"
            f"camera.position.set({cx}*IN,{cz}*IN,{-cy}*IN);orbit.target.set({tx}*IN,{tz}*IN,{-ty}*IN);"
            f"camera.lookAt({tx}*IN,{tz}*IN,{-ty}*IN);}},50);")))
        subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--window-size=1400,900", "--virtual-time-budget=15000",
                        f"--screenshot={win(out)}\\{name}.png", "file:///" + win(tmp).replace("\\", "/") + "#roof"],
                       capture_output=True)
        tmp.unlink()


def plan(ax, key):
    """Plan sketch of the house front, porch, lounge window and seat wall (right = west, street at the bottom)."""
    from matplotlib.patches import Rectangle
    _, court, walls = OPTIONS[key]
    if court:
        ax.add_patch(Rectangle((court[0], court[1]), court[2] - court[0], court[3] - court[1], fc="#e9e4da", ec="none"))
    else:
        x0, y0, x1, y1 = LANDING
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#e9e4da", ec="none"))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, "landing", ha="center", va="center", fontsize=7)
    ax.fill([S.E, S.PORCH_X, S.PORCH_X, 700, 700, S.E], [S.PORCH_Y, S.PORCH_Y, S.N, S.N, 320, 320], c="#cfc9bf")
    ax.plot([S.E, S.E, S.PORCH_X, S.PORCH_X, 700], [320, S.PORCH_Y, S.PORCH_Y, S.N, S.N], c="k", lw=1.5)
    ax.plot([502.4, 622.4], [S.N, S.N], c="#3a7bd5", lw=4)
    ax.plot([OX, OX, S.PORCH_X, S.PORCH_X], [S.N, OY, OY, S.N], c="#888", lw=0.8)          # porch floor's front
    ax.plot([OX, OX, S.PORCH_X, S.PORCH_X], [OY, OY - 24, OY - 24, OY], c="#888", lw=0.8)  # step
    ax.text(562.4, S.N + 14, "lounge\nwindow", ha="center", va="top", fontsize=7)
    ax.text((S.E + S.PORCH_X) / 2, (S.N + S.PORCH_Y) / 2, "porch", ha="center", va="center", fontsize=7)
    for x0, y0, x1, y1 in walls:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#555", ec="none"))
    ax.annotate("", xy=(440, 140), xytext=(570, 290), arrowprops=dict(arrowstyle="->", color="#c33", lw=1))
    ax.set_xlim(330, 700); ax.set_ylim(100, 330); ax.set_aspect("equal"); ax.axis("off")


def compare():
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(OPTIONS), 3, figsize=(15, 3.4 * len(OPTIONS)),
                            gridspec_kw={"width_ratios": [0.8, 1, 1]})
    for row, key in zip(axs, OPTIONS):
        plan(row[0], key)
        row[0].set_title(OPTIONS[key][0], fontsize=10, loc="left")
        for ax, name, label in ((row[1], "lounge", "standing at the lounge window"), (row[2], "street", "from the street")):
            p = OUT / key / f"{name}.png"
            if p.exists():
                ax.imshow(mpimg.imread(p))
            ax.set_title(label, fontsize=9); ax.axis("off")
    fig.tight_layout()
    import zoning_set as Z
    Z.save_png(fig, OUT.parent / "entry-court.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    for key in OPTIONS:
        model(key)
    compare()
