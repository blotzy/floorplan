# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Experiment: exterior styles on the schematic's 3D model (roof form, eaves, colours).
The shingle set is Class A asphalt shingle at 2:12, the code minimum for shingles (double
underlayment below 4:12); butterfly roofs and anything under 2:12 are out for shingles.

  mcm-shed        Midcentury modern: single 2:12 slope, high at the street with clerestory
                  glass, falling to the rear (the big rear plane faces SSW: ideal for solar).
  mcm-shed-vault  The same shed with only the lounge vaulted (clerestory over the lounge);
                  flat 10' ceilings and a sealed attic elsewhere. Writes a cross-section.
  mcm-gable       Midcentury modern (Eichler-like): 2:12 gable, deep eaves, glazed gable
                  ends, dark siding with warm wood-look soffits.
  ranch-hip       California ranch: 4:12 hip roof, 24" eaves, light walls.
  ranch-gable     Ranch: 4:12 gable, board-and-batten colours.

Colours stand in for fire-zone materials (stucco, fiber cement, metal; wood looks are
wood-look products).

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
    """Front door with one horizontal glass lite near its top (echoes the shared ensuite's high window)."""
    x0, x1 = next(o for o in S.OPENINGS if o[0] == "porch front" and o[3] == "door")[1:3]
    sc.boxes["door"].append([x0, S.PORCH_Y + 2, x1, S.PORCH_Y + 5, 0, 96])
    c = (x0 + x1) / 2
    sc.boxes["glass"].append([c - 12, S.PORCH_Y + 1.8, c + 12, S.PORCH_Y + 5.2, 78, 90])  # 24" x 12" lite


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
EAVE = 30.0                               # main plan: eaves may project at most 2'-6" into a required yard
                                          # (22.110.090.A); the front, rear and west walls sit on their setback lines


def slab_roof(sc, ov, under, splits=(), ends="exterior", north="exterior", south="exterior", seams=False):
    """Midcentury roof as a thin slab whose underside height is under(y) (linear between the
    split lines), with sloped soffits, fascia all round, and the walls rising to meet it
    (clerestory glass where the side is "glass")."""
    X0, X1, Y0, Y1 = E - ov, W + ov, N - ov, Sth + ov
    ys = [Y0, *splits, Y1]
    for ya, yb in zip(ys, ys[1:]):
        for dz, mat in ((THK, "roofing"), (0.0, "soffit")):
            quad(sc, mat, [X0, ya, under(ya) + dz], [X1, ya, under(ya) + dz], [X1, yb, under(yb) + dz],
                 [X0, yb, under(yb) + dz])
        if seams:                                               # standing seams every 18", down the slope
            za, zb = under(ya) + THK + 0.6, under(yb) + THK + 0.6
            x = X0 + 9
            while x < X1:
                quad(sc, "seam", [x, ya, za], [x + 1.2, ya, za], [x + 1.2, yb, zb], [x, yb, zb])
                x += 18
        for x in (X0, X1):                                      # rake fascia on the ends
            quad(sc, "fascia", [x, ya, under(ya)], [x, yb, under(yb)], [x, yb, under(yb) + THK], [x, ya, under(ya) + THK])
    for y in (Y0, Y1):                                          # eave fascia on the long sides
        quad(sc, "fascia", [X0, y, under(y)], [X1, y, under(y)], [X1, y, under(y) + THK], [X0, y, under(y) + THK])
    for y, mat in ((N, north), (Sth, south)):                   # long walls up to the underside
        z = under(y)
        if z > PLATE + 0.5:
            x0 = S.PORCH_X if y == N else E                     # over the porch it's a beam, not glass
            segs = mat if isinstance(mat, list) else [(x0, W, mat)]   # [(x from, x to, material)]
            for a, b, m in segs:
                if m:                                           # None: the caller draws that stretch
                    quad(sc, m, [a, y, PLATE], [b, y, PLATE], [b, y, z], [a, y, z])
            if y == N:
                quad(sc, "exterior", [E, y, PLATE], [x0, y, PLATE], [x0, y, z], [E, y, z])
    wall_ys = [N, *splits, Sth]
    for x in (E, W):                                            # end walls follow the slab
        for ya, yb in zip(wall_ys, wall_ys[1:]):
            quad(sc, ends, [x, ya, PLATE], [x, yb, PLATE], [x, yb, max(PLATE, under(yb))], [x, ya, max(PLATE, under(ya))])


YM = (N + Sth) / 2


def shed(sc, pitch, ov, seams=False, clerestory=True, heel=0.0):
    """Low at the rear wall, rising to the street, with a clerestory along the front (or a
    solid street wall: flat 10' ceilings and a sealed attic throughout). heel raises the
    whole roof (walls rise to meet it all round) so the low side of the attic has headroom."""
    slab_roof(sc, ov, lambda y: PLATE + heel + (Sth - y) * pitch, north="glass" if clerestory else "exterior",
              seams=seams)


def butterfly(sc, pitch, ov, seams=False):
    """Valley down the middle (underside at the plate), rising to both long eaves."""
    slab_roof(sc, ov, lambda y: PLATE + abs(y - YM) * pitch, splits=(YM,), north="glass", south="glass", seams=seams)


LOUNGE_X = (S.face("foyer wall", +1), S.face("lounge|gym", -1))
LOUNGE_Y = (S.N_IN, S.face("south hall wall", -1))          # street wall to the lobby edge
JOISTS = 10.0                                               # ceiling framing above the 10' ceiling


def shed_vault_under(pitch):
    return lambda y: PLATE + (Sth - y) * pitch


def shed_vault(sc, pitch, ov, seams=False, band=None):
    """Shed roof; only the lounge is vaulted (clerestory along its stretch of the street wall);
    flat 10' ceilings and a sealed attic everywhere else. band: clerestory glass height in inches,
    centred in the wall above the plate (stucco above and below); None glazes the full height."""
    under = shed_vault_under(pitch)
    x0, x1 = LOUNGE_X
    slab_roof(sc, ov, under, north=[(S.PORCH_X, x0, "exterior"), (x0, x1, None if band else "glass"),
                                    (x1, W, "exterior")], seams=seams)
    if band:
        top = under(N)
        g0 = PLATE + (top - PLATE - band) / 2
        for z0, z1, m in ((PLATE, g0, "exterior"), (g0, g0 + band, "glass"), (g0 + band, top, "exterior")):
            quad(sc, m, [x0, N, z0], [x1, N, z0], [x1, N, z1], [x0, N, z1])
    y0, y1 = LOUNGE_Y
    quad(sc, "wall", [x0, y0, under(y0) - 1], [x1, y0, under(y0) - 1], [x1, y1, under(y1) - 1],
         [x0, y1, under(y1) - 1])                                                     # vault (just under the slab)
    quad(sc, "wall", [x0, y1, M.CEIL], [x1, y1, M.CEIL], [x1, y1, under(y1)], [x0, y1, under(y1)])      # step down
    for x in (x0, x1):                                      # side walls of the vault
        quad(sc, "wall", [x, y0, M.CEIL], [x, y1, M.CEIL], [x, y1, under(y1)], [x, y0, under(y0)])


def clerestory(sc, x0, x1, top, pieces):
    """Street wall over the lounge (x0..x1, from the plate up to `top`), glazed where `pieces`
    [(from, to, height), ...] say: each piece centred vertically in the wall, stucco elsewhere."""
    xs = sorted({x0, x1, *[p for a, b, _ in pieces for p in (a, b)]})
    for a, b in zip(xs, xs[1:]):
        hit = next((h for pa, pb, h in pieces if pa <= a and b <= pb), None)
        if hit is None:
            quad(sc, "exterior", [a, N, PLATE], [b, N, PLATE], [b, N, top], [a, N, top])
            continue
        g0 = PLATE + (top - PLATE - hit) / 2
        for z0, z1, m in ((PLATE, g0, "exterior"), (g0, g0 + hit, "glass"), (g0 + hit, top, "exterior")):
            quad(sc, m, [a, N, z0], [b, N, z0], [b, N, z1], [a, N, z1])


def great_room_vault(to_outside=False):
    """Plan outline (shapely) of the vaulted great room: lounge, foyer, dining and kitchen. With
    to_outside, it runs on through the exterior walls to the house's outer faces."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    lx0, lx1 = LOUNGE_X
    yf, fy = S.FOYER_WALL_END, S.PORCH_Y + S.EXT
    kx = S.face("kitchen|pantry", -1)
    e, n, s_ = (S.E, S.N, S.S) if to_outside else (S.E_IN, S.N_IN, S.S_IN)
    fy = S.PORCH_Y if to_outside else fy
    return unary_union([box(lx0, n, lx1, yf), box(e, fy, lx0, yf), box(e, yf, kx, s_)])


def shed_vault_great(sc, pitch, ov, seams=False, band=None, pieces=None):
    """shed_vault, but the whole great room (lounge, dining, kitchen) is vaulted under one continuous
    sloped ceiling, from the clerestory down to the rear wall: no step where the lounge meets the
    dining, and the foyer opens up to it too (the foyer/TV wall runs full height). Everything west of
    the kitchen keeps flat 10' ceilings under the attic."""
    under = shed_vault_under(pitch)
    lx0, lx1 = LOUNGE_X
    if band and not pieces:
        pieces = [(lx0, lx1, band)]
    slab_roof(sc, ov, under, north=[(S.PORCH_X, lx0, "exterior"), (lx0, lx1, None if pieces else "glass"),
                                    (lx1, W, "exterior")], seams=seams)
    if pieces:
        clerestory(sc, lx0, lx1, under(N), pieces)
    yf = S.FOYER_WALL_END                                   # foyer's open (south) edge
    kx = S.face("kitchen|pantry", -1)
    E_in = S.E_IN
    fy = S.PORCH_Y + S.EXT                                  # foyer's front wall (behind the porch)
    for x0, x1, y0, y1 in ((lx0, lx1, S.N_IN, yf), (E_in, lx0, fy, yf),      # lounge; foyer;
                           (E_in, kx, yf, S.S_IN)):                           # dining + kitchen
        quad(sc, "wall", [x0, y0, under(y0) - 1], [x1, y0, under(y0) - 1], [x1, y1, under(y1) - 1],
             [x0, y1, under(y1) - 1])                       # just under the slab, so it doesn't flicker
    C = M.CEIL
    # Walls that rise to the vault: the porch's side wall (lounge corner), the gym and kitchen walls,
    # and the foyer/TV wall (both faces), so the foyer is a tall space of its own beside the lounge.
    tv0, tv1 = S.face("foyer wall", -1), S.face("foyer wall", +1)
    for x, y0, y1 in ((lx0, S.N_IN, S.PORCH_Y), (lx1, S.N_IN, yf), (kx, yf, S.S_IN),
                      (tv0, fy, yf), (tv1, S.PORCH_Y, yf)):
        quad(sc, "wall", [x, y0, C], [x, y1, C], [x, y1, under(y1)], [x, y0, under(y0)])
    quad(sc, "wall", [tv0, yf, C], [tv1, yf, C], [tv1, yf, under(yf)], [tv0, yf, under(yf)])   # its end
    quad(sc, "wall", [E_in, fy, C], [lx0, fy, C], [lx0, fy, under(fy)], [E_in, fy, under(fy)])  # over the door
    quad(sc, "wall", [kx, yf, C], [lx1, yf, C], [lx1, yf, under(yf)], [kx, yf, under(yf)])  # jog at the hall


def section(pitch, path, roofing="shingles"):
    """Cross-sections (street on the left): through the lounge, and through the bedroom wing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    under = shed_vault_under(pitch)
    ov = 36
    fig, axes = plt.subplots(2, 1, figsize=(12, 8.5))
    for ax, (title, vault) in zip(axes, (("Through the lounge (vaulted)", True),
                                          ("Through the bedroom wing (flat 10' ceiling, attic above)", False))):
        ys = [N - ov, Sth + ov]
        ax.fill_between(ys, [under(y) for y in ys], [under(y) + THK for y in ys], color="#4a4e54")   # roof slab
        for y0 in (N, Sth - 9):
            ax.add_patch(plt.Rectangle((y0, 0), 9, under(y0 + (9 if y0 == N else 0)), color="#bbb"))  # walls
        ax.plot([N, Sth], [0, 0], color="k", lw=2)
        ceil_lo = LOUNGE_Y[1] if vault else N + 9
        if vault:
            ys_v = [N + 9, LOUNGE_Y[1]]
            ax.plot(ys_v, [under(y) for y in ys_v], color="#c0392b", lw=2.5, label="vaulted lounge ceiling")
            ax.plot([LOUNGE_Y[1]] * 2, [M.CEIL, under(LOUNGE_Y[1])], color="#c0392b", lw=2.5)
            ax.fill_between([N + 0.5, N + 8.5], [PLATE + 4] * 2, [under(N) - 4] * 2, color="#9cc8e8", label="clerestory")
            ax.annotate(f"{under(N + 9) / 12:.0f}' high at the street wall", (N + 12, under(N + 9) - 18), fontsize=9)
        ax.plot([ceil_lo, Sth - 9], [M.CEIL] * 2, color="#555", lw=2.5, label="flat 10' ceiling")
        att = [y for y in range(int(ceil_lo), int(Sth - 9) + 1, 2)]
        ax.fill_between(att, [M.CEIL + JOISTS] * len(att), [under(y) for y in att], color="#f3d9a6", alpha=.8,
                        label="sealed attic")
        for y in (ceil_lo + 20, (ceil_lo + Sth) / 2, Sth - 40):
            h = under(y) - M.CEIL - JOISTS
            if h > 6:
                ax.annotate(f"{h / 12:.1f}' clear", (y, M.CEIL + JOISTS + h / 2), ha="center", fontsize=9)
        ax.set_title(title); ax.set_aspect("equal"); ax.set_xlim(N - 60, Sth + 60); ax.set_ylim(-10, under(N - ov) + 30)
        ax.set_xlabel("street  ←      (inches)      →  rear yard"); ax.legend(loc="upper right", fontsize=8)
    fig.suptitle(f"MCM shed, {pitch * 12:g}:12 {roofing}, lounge-only vault", fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=100); plt.close(fig)


def low_gable(sc, pitch, ov, seams=False, glazed_ends=True):
    """Shallow gable, ridge along the house; glazed gable ends unless glazed_ends is False."""
    half = (Sth - N) / 2
    slab_roof(sc, ov, lambda y: PLATE + (half - abs(y - YM)) * pitch, splits=(YM,),
              ends="glass" if glazed_ends else "exterior", seams=seams)


WOOD, BLACK, WHITE = 0xB07A4F, 0x2B2D30, 0xF1EDE4
STYLES = {
    "mcm-shed": (lambda sc: shed(sc, 2 / 12, 36),
                 {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3C3F44, "door": 0xD9792B}),
    "mcm-gable": (lambda sc: low_gable(sc, 2 / 12, 36),
                  {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3C3F44, "door": 0xD9792B}),
    "mcm-shed-vault": (lambda sc: shed_vault(sc, 2 / 12, 36),
                       {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3C3F44, "door": 0xD9792B}),
    "ranch-hip": (lambda sc: hip(sc, 4 / 12, 24),
                  {"exterior": WHITE, "soffit": WHITE, "fascia": WHITE, "roofing": 0x6B6E72, "door": 0x2D3E5C}),
    "ranch-gable": (lambda sc: gable(sc, 4 / 12, 24, 12),
                    {"exterior": 0xB9C2B0, "soffit": 0xF4F2EC, "fascia": 0xF4F2EC, "roofing": 0x45484C, "door": 0x222222}),
}
PORCH_DOOR = next(o for o in S.OPENINGS if o[0] == "porch front" and o[3] == "door")[1:3]
PORCH_WIN = next(o for o in S.OPENINGS if o[0] == "porch side" and o[3] == "window")[1:3]


def porch_feature(sc):
    """Wood-look cladding (fiber cement or porcelain wood-grain) on the porch's two back walls,
    around the front door and the reeded side window, wrapping onto the porch ceiling."""
    px, py = S.PORCH_X, S.PORCH_Y
    y = py - 0.4                                         # just proud of the front wall
    d0, d1 = PORCH_DOOR
    for a, b, z0, z1 in ((E, d0, 0, 120), (d1, px, 0, 120), (d0, d1, 96, 120)):
        sc.quad("feature", (a, y), (b, y), z0, z1)
    x = px - 0.4                                         # side wall, around the reeded window
    w0, w1 = PORCH_WIN
    for a, b, z0, z1 in ((N, w0, 0, 120), (w1, py, 0, 120), (w0, w1, 0, 30), (w0, w1, 96, 120)):
        sc.quad("feature", (x, a), (x, b), z0, z1)
    sc.boxes["feature"].append([E + 6, N, px, py, M.CEIL - 1.5, M.CEIL - 0.5])   # porch ceiling
    sc.mat["feature"] = {"color": 0xA8754B}


def porch_breeze(sc):
    """Breeze-block screen (12" concrete blocks, open centres) along the full street-side seat wall."""
    x0, y0, x1, y1 = S.ENTRY_WALLS[0]
    z0, rows, t = S.ENTRY_WALL_H, 4, 2.0
    n = int((x1 - x0) // 12)
    xs = x1 - n * 12
    for i in range(n):
        for j in range(rows):
            a, c = xs + i * 12, z0 + j * 12
            for bx0, bx1, bz0, bz1 in ((a, a + 12, c, c + t), (a, a + 12, c + 12 - t, c + 12),
                                       (a, a + t, c, c + 12), (a + 12 - t, a + 12, c, c + 12)):
                sc.boxes["breeze"].append([bx0, y0, bx1, y1, bz0, bz1])
    sc.mat["breeze"] = {"color": 0xECE7DD}


def chosen_exterior(sc, porch=True):
    """The main plan's exterior: MCM shingle shed (2:12, 2'-6" eaves) with a 3' clerestory band over the
    lounge and the foyer, lounge, dining and kitchen under one sloped ceiling; stucco walls,
    dark shingles and fascia, accent front door; porch with a wood-look feature wall. make_3d.py
    adds this to the main model."""
    band(sc, "exterior", WALL_TOP, PLATE)
    shed_vault_great(sc, 2 / 12, EAVE, band=36.0)
    front_door(sc)
    sc.mat = {k: {"color": v} for k, v in STYLES["mcm-gable"][1].items()}
    sc.mat["seam"] = {"color": 0x2A2D31}
    if porch:
        porch_feature(sc)


def roof_options():
    """Alternative roofs for the main model's Roof selector: {label: tris} (the main plan's shingle
    shed with a 3' clerestory band is the model's own roof)."""
    out = {}
    sc = M.Scene()
    band(sc, "exterior", WALL_TOP, PLATE)
    low_gable(sc, 2 / 12, EAVE, glazed_ends=False)
    out["MCM gable 2:12, flat 9' ceilings"] = dict(sc.tris)
    for label, seams, glass_h in (
            ("MCM shingle shed 2:12, full-height clerestory, great room vaulted", False, None),
            ("MCM metal shed 2:12, 3' clerestory band, great room vaulted", True, 36.0),
            ("MCM metal shed 2:12, full-height clerestory, great room vaulted", True, None)):
        sc = M.Scene()
        band(sc, "exterior", WALL_TOP, PLATE)
        shed_vault_great(sc, 2 / 12, EAVE, seams=seams, band=glass_h)
        out[label] = dict(sc.tris)
    for label, seams in (("MCM shingle shed 2:12, no clerestory, flat 9' ceilings", False),
                         ("MCM metal shed 2:12, no clerestory, flat 9' ceilings", True)):
        sc = M.Scene()
        band(sc, "exterior", WALL_TOP, PLATE)
        shed(sc, 2 / 12, EAVE, seams=seams, clerestory=False)
        out[label] = dict(sc.tris)
    return out


METAL = {   # the original, lower midcentury slopes, with roofing that suits them
    "metal-mcm-shed": (lambda sc: shed(sc, 1.5 / 12, 36, seams=True),
                       {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3F4347,
                        "seam": 0x2A2D31, "door": 0xD9792B}),
    "metal-mcm-shed-solid": (lambda sc: shed(sc, 1.5 / 12, 36, seams=True, clerestory=False),
                             {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3F4347,
                              "seam": 0x2A2D31, "door": 0xD9792B}),
    "metal-mcm-shed-heel": (lambda sc: shed(sc, 1.5 / 12, 36, seams=True, clerestory=False, heel=24.0),
                            {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3F4347,
                             "seam": 0x2A2D31, "door": 0xD9792B}),
    "metal-mcm-shed-vault": (lambda sc: shed_vault(sc, 2 / 12, 36, seams=True),
                             {"exterior": 0xEFE9DF, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3F4347,
                              "seam": 0x2A2D31, "door": 0xD9792B}),
    "metal-mcm-butterfly": (lambda sc: butterfly(sc, 2 / 12, 30),
                            {"exterior": 0xE9E4DA, "soffit": WOOD, "fascia": WHITE, "roofing": 0xD5D8DA,
                             "door": 0x2B8C8C}),
    "metal-mcm-gable": (lambda sc: low_gable(sc, 2 / 12, 36, seams=True),
                        {"exterior": 0x4F5358, "soffit": WOOD, "fascia": BLACK, "roofing": 0x3F4347,
                         "seam": 0x2A2D31, "door": 0xE8B33C}),
}
METAL_LABELS = {"metal-mcm-shed": "MCM shed, 1.5:12 standing-seam metal (clerestory to the street)",
                "metal-mcm-shed-solid": "MCM shed, 1.5:12 standing-seam metal, no clerestory (attic throughout)",
                "metal-mcm-shed-heel": "MCM shed, 1.5:12 standing-seam metal, no clerestory, raised 2' (raised heel: attic headroom at the rear too)",
                "metal-mcm-shed-vault": "MCM shed, 2:12 standing-seam metal: only the lounge vaulted, attic elsewhere",
                "metal-mcm-butterfly": "MCM butterfly, 2:12 single-ply membrane (clerestories both sides)",
                "metal-mcm-gable": "MCM gable, 2:12 standing-seam metal (Eichler-like, glazed gable ends)"}
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


LABELS = {"mcm-shed": "MCM shed, 2:12 shingles (clerestory to the street, solar plane to the rear)",
          "mcm-gable": "MCM gable, 2:12 shingles (Eichler-like, glazed gable ends)",
          "mcm-shed-vault": "MCM shed, 2:12 shingles: only the lounge vaulted, attic elsewhere",
          "ranch-hip": "Ranch, 4:12 hip, shingles", "ranch-gable": "Ranch, 4:12 gable, shingles, board-and-batten colours"}


def contact_sheet(view: str, styles: dict, labels: dict, name: str):
    """All styles' renders for one view, stacked with labels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pngs = [(k, OUT / f"exterior-{k}-{view}.png") for k in styles]
    pngs = [(k, p) for k, p in pngs if p.exists()]
    if not pngs:
        return
    fig, axes = plt.subplots(len(pngs), 1, figsize=(10, 5.9 * len(pngs)))
    for ax, (k, p) in zip(axes, pngs):
        ax.imshow(plt.imread(p)); ax.set_title(labels[k], fontsize=13); ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / f"{name}-{view}.png", dpi=80)
    plt.close(fig)


SETS = {   # name -> (styles, labels, comparison sheet, lounge-vault section)
    "shingles": (STYLES, LABELS, "exterior-compare", (2 / 12, "exterior-mcm-shed-vault-section.png", "shingles")),
    "metal": (METAL, METAL_LABELS, "exterior-metal-compare",
              (2 / 12, "exterior-metal-mcm-shed-vault-section.png", "standing-seam metal")),
}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(SETS), help="build just one set")
    args = ap.parse_args()
    for set_name, (styles, labels, sheet, (pitch, sec_png, roofing)) in SETS.items():
        if args.only and set_name != args.only:
            continue
        for key, (roof, colours) in styles.items():
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
            contact_sheet(view, styles, labels, sheet)
        section(pitch, OUT / sec_png, roofing)


if __name__ == "__main__":
    main()
