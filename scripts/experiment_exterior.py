# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: exterior styles on the schematic's 3D model (roof form, eaves, colours).

  mcm-shed       Midcentury modern: single low slope, high at the street with clerestory
                 glass, falling to the rear (the big rear plane faces SSW: ideal for solar).
  mcm-butterfly  Midcentury modern: two planes sloping to a central valley, clerestories
                 on both long walls.
  mcm-gable      Midcentury modern (Eichler-like): shallow 2:12 gable, deep eaves, glazed
                 gable ends, dark siding with warm wood-look soffits.
  ranch-hip      California ranch: 4:12 hip roof, 24" eaves, light walls.
  ranch-gable    Ranch: 4:12 gable, board-and-batten colours.

Colours stand in for fire-zone materials (stucco, fiber cement, metal; wood looks are
wood-look products). Low slopes (MCM) need standing-seam metal or membrane, not shingles.

Writes renders/experiments/exterior-<style>/house.html (walkable, Roof toggle) and
renders/experiments/exterior-<style>-{street,aerial}.png when a Chrome is found.

    uv run scripts/experiment_exterior.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

E, W, N, Sth = S.E, S.W, S.N, S.S
WALL_TOP = M.CEIL                         # exterior walls in the model stop at the ceiling
PLATE = 132.0                             # top plate / underside of roof framing (11')
FASCIA = 8.0
OUT = S.RENDERS / "experiments"


def quad(sc, mat, a, b, c, d):
    sc.tris[mat] += [[a, b, c], [a, c, d]]


def band(sc, mat, z0, z1):
    """Wall band around the house rectangle (from the model's wall top up to the plate)."""
    for (x0, y0), (x1, y1) in (((E, N), (W, N)), ((W, N), (W, Sth)), ((W, Sth), (E, Sth)), ((E, Sth), (E, N))):
        quad(sc, mat, [x0, y0, z0], [x1, y1, z0], [x1, y1, z1], [x0, y0, z1])


def eaves(sc, ov_x, ov_y):
    """Soffits (flat, at the plate) and fascia around the eave rectangle; returns it."""
    X0, X1, Y0, Y1 = E - ov_x, W + ov_x, N - ov_y, Sth + ov_y
    z, zf = PLATE, PLATE + FASCIA
    for inner, outer in ((((E, N), (W, N)), ((X0, Y0), (X1, Y0))), (((W, N), (W, Sth)), ((X1, Y0), (X1, Y1))),
                         (((W, Sth), (E, Sth)), ((X1, Y1), (X0, Y1))), (((E, Sth), (E, N)), ((X0, Y1), (X0, Y0)))):
        (a, b), (c, d) = inner, outer
        quad(sc, "soffit", [*a, z], [*b, z], [*d, z], [*c, z])
        quad(sc, "fascia", [*c, z], [*d, z], [*d, zf], [*c, zf])
    return X0, X1, Y0, Y1, zf


def front_door(sc):
    sc.boxes["door"].append([380.0, S.PORCH_Y + 2, 418.0, S.PORCH_Y + 5, 0, 96])


# ---- roof forms -----------------------------------------------------------------------
def hip(sc, pitch, ov):
    X0, X1, Y0, Y1, ze = eaves(sc, ov, ov)
    half = (Y1 - Y0) / 2; ym = (Y0 + Y1) / 2; zr = ze + half * pitch
    a, b = [X0 + half, ym, zr], [X1 - half, ym, zr]
    quad(sc, "roofing", [X0, Y0, ze], [X1, Y0, ze], b, a)
    quad(sc, "roofing", [X0, Y1, ze], [X1, Y1, ze], b, a)
    sc.tris["roofing"] += [[[X0, Y0, ze], [X0, Y1, ze], a], [[X1, Y0, ze], [X1, Y1, ze], b]]


def gable(sc, pitch, ov, rake, glazed_ends=False):
    X0, X1, Y0, Y1, ze = eaves(sc, rake, ov)
    ym = (Y0 + Y1) / 2; zr = ze + (Y1 - Y0) / 2 * pitch
    for yy in (Y0, Y1):
        quad(sc, "roofing", [X0, yy, ze], [X1, yy, ze], [X1, ym, zr], [X0, ym, zr])
    zw = ze + (N - Y0) * pitch                       # roof underside height over the long walls
    for x in (E, W):                                  # gable ends
        quad(sc, "exterior", [x, N, PLATE], [x, Sth, PLATE], [x, Sth, zw], [x, N, zw])
        sc.tris["glass" if glazed_ends else "exterior"].append([[x, N, zw], [x, Sth, zw], [x, ym, zr - 4]])


THK = 10.0                                # MCM roof slab: roofing on top, sloped soffit underneath


def slab_roof(sc, ov, under, splits=(), ends="exterior", north="exterior", south="exterior"):
    """Midcentury roof as a thin slab whose underside height is under(y) (linear between the
    split lines), with sloped soffits, fascia all round, and the walls rising to meet it
    (clerestory glass where the side is "glass")."""
    X0, X1, Y0, Y1 = E - ov, W + ov, N - ov, Sth + ov
    ys = [Y0, *splits, Y1]
    for ya, yb in zip(ys, ys[1:]):
        for dz, mat in ((THK, "roofing"), (0.0, "soffit")):
            quad(sc, mat, [X0, ya, under(ya) + dz], [X1, ya, under(ya) + dz], [X1, yb, under(yb) + dz],
                 [X0, yb, under(yb) + dz])
        for x in (X0, X1):                                      # rake fascia on the ends
            quad(sc, "fascia", [x, ya, under(ya)], [x, yb, under(yb)], [x, yb, under(yb) + THK], [x, ya, under(ya) + THK])
    for y in (Y0, Y1):                                          # eave fascia on the long sides
        quad(sc, "fascia", [X0, y, under(y)], [X1, y, under(y)], [X1, y, under(y) + THK], [X0, y, under(y) + THK])
    for y, mat in ((N, north), (Sth, south)):                   # long walls up to the underside
        z = under(y)
        if z > PLATE + 0.5:
            x0 = S.PORCH_X if y == N else E                     # over the porch it's a beam, not glass
            quad(sc, mat, [x0, y, PLATE], [W, y, PLATE], [W, y, z], [x0, y, z])
            if y == N:
                quad(sc, "exterior", [E, y, PLATE], [x0, y, PLATE], [x0, y, z], [E, y, z])
    wall_ys = [N, *splits, Sth]
    for x in (E, W):                                            # end walls follow the slab
        for ya, yb in zip(wall_ys, wall_ys[1:]):
            quad(sc, ends, [x, ya, PLATE], [x, yb, PLATE], [x, yb, max(PLATE, under(yb))], [x, ya, max(PLATE, under(ya))])


YM = (N + Sth) / 2


def butterfly(sc, pitch, ov):
    """Valley down the middle (underside at the plate), rising to both long eaves."""
    slab_roof(sc, ov, lambda y: PLATE + abs(y - YM) * pitch, splits=(YM,), north="glass", south="glass")


def shed(sc, pitch, ov):
    """Low at the rear wall, rising to the street with a clerestory along the front."""
    slab_roof(sc, ov, lambda y: PLATE + (Sth - y) * pitch, north="glass")


def low_gable(sc, pitch, ov):
    """Shallow gable, ridge along the house, glazed gable ends."""
    half = (Sth - N) / 2
    slab_roof(sc, ov, lambda y: PLATE + (half - abs(y - YM)) * pitch, splits=(YM,), ends="glass")


WOOD, BLACK, WHITE = 0xB07A4F, 0x2B2D30, 0xF1EDE4
STYLES = {
    "mcm-shed": (lambda sc: shed(sc, 1.5 / 12, 36),
                 {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x4A4E54, "door": 0xD9792B}),
    "mcm-butterfly": (lambda sc: butterfly(sc, 2 / 12, 30),
                      {"exterior": 0xE9E4DA, "soffit": WOOD, "fascia": WHITE, "roofing": 0xB9BDC2, "door": 0x2B8C8C}),
    "mcm-gable": (lambda sc: low_gable(sc, 2 / 12, 36),
                  {"exterior": 0x4F5358, "soffit": WOOD, "fascia": BLACK, "roofing": 0x55595F, "door": 0xE8B33C}),
    "ranch-hip": (lambda sc: hip(sc, 4 / 12, 24),
                  {"exterior": WHITE, "soffit": WHITE, "fascia": WHITE, "roofing": 0x6B6E72, "door": 0x2D3E5C}),
    "ranch-gable": (lambda sc: gable(sc, 4 / 12, 24, 12),
                    {"exterior": 0xB9C2B0, "soffit": 0xF4F2EC, "fascia": 0xF4F2EC, "roofing": 0x45484C, "door": 0x222222}),
}
VIEWS = {   # camera position and target in plan inches (x west, y south, z up)
    "street": ((230, -330, 64), (760, 330, 80)),
    "aerial": ((120, -380, 430), (780, 420, 40)),
}
CHROME = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")


def screenshot(html: Path, png: Path, cam, target):
    """Render a view with headless Chrome (WSL path conventions); skipped if no Chrome."""
    if not CHROME.exists():
        return
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    (cx, cy, cz), (tx, ty, tz) = cam, target
    src = html.read_text().replace(hook, hook + (
        "\norbit.enabled = false; groups.labels.visible = false;"
        "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
        f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);"))
    tmp = html.with_name("_view.html")
    tmp.write_text(src)
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()
    subprocess.run([str(CHROME), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                    "--window-size=1400,800", "--virtual-time-budget=15000", f"--screenshot={win(png)}",
                    "file:///" + win(tmp).replace("\\", "/")], capture_output=True)
    tmp.unlink()


LABELS = {"mcm-shed": "MCM shed (clerestory to the street, solar plane to the rear)",
          "mcm-butterfly": "MCM butterfly (clerestories both sides)",
          "mcm-gable": "MCM low gable (Eichler-like, glazed gable ends)",
          "ranch-hip": "Ranch, 4:12 hip", "ranch-gable": "Ranch, 4:12 gable, board-and-batten colours"}


def contact_sheet(view: str):
    """All styles' renders for one view, stacked with labels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pngs = [(k, OUT / f"exterior-{k}-{view}.png") for k in STYLES]
    pngs = [(k, p) for k, p in pngs if p.exists()]
    if not pngs:
        return
    fig, axes = plt.subplots(len(pngs), 1, figsize=(10, 5.9 * len(pngs)))
    for ax, (k, p) in zip(axes, pngs):
        ax.imshow(plt.imread(p)); ax.set_title(LABELS[k], fontsize=13); ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / f"exterior-compare-{view}.png", dpi=80)
    plt.close(fig)


def main():
    for key, (roof, colours) in STYLES.items():
        sc = M.build_schematic()
        band(sc, "exterior", WALL_TOP, PLATE)
        roof(sc)
        front_door(sc)
        sc.mat = {k: {"color": v} for k, v in colours.items()}
        out_dir = OUT / f"exterior-{key}"
        M.write_model(sc, out_dir, sc.meta)
        for view, (cam, target) in VIEWS.items():
            screenshot(out_dir / "house.html", OUT / f"exterior-{key}-{view}.png", cam, target)
        print("styled", key)
    for view in VIEWS:
        contact_sheet(view)


if __name__ == "__main__":
    main()
