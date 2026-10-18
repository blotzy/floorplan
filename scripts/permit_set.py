# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Architectural permit set (draft), 24" x 36" sheets drawn to scale, from the schematic and the main
plan's exterior. Sheets follow LA County Building and Safety's Eaton & Palisades Fire Rebuild minimum
residential submittal list (architectural plans: site plan, floor plan with door and window schedules,
smoke and CO alarms, heating appliances and water heater; roof plan; elevations; sections).

  A-2  Floor plan, door and window schedules, alarms, equipment

Writes renders/permit/architectural-set.pdf and a PNG of each sheet.

    uv run scripts/permit_set.py
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exterior as X  # noqa: E402
import schematic as S  # noqa: E402
import zoning_set as Z  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle  # noqa: E402
from shapely.geometry import Point, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

OUT = S.RENDERS / "permit"
W_IN, H_IN = 36.0, 24.0                         # ARCH D sheet, landscape
INK, RED = "#111", "#b03a2e"
ftin = Z.ftin
DOOR_H = 96.0                                   # interior and front doors: 8' (headers at 8')


# ---- sheet, title block, scaled drawing areas -------------------------------------------------
def sheet(num, title):
    fig = plt.figure(figsize=(W_IN, H_IN))
    fig.add_artist(Rectangle((0.5 / W_IN, 0.5 / H_IN), (W_IN - 1) / W_IN, (H_IN - 1) / H_IN,
                             transform=fig.transFigure, fill=False, lw=2, ec=INK))
    tb = 32.8 / W_IN                                                     # title block strip on the right
    fig.add_artist(plt.Line2D([tb, tb], [0.5 / H_IN, 23.5 / H_IN], transform=fig.transFigure, lw=1.5, color=INK))
    t = lambda y, s, **k: fig.text(tb + 0.12 / W_IN, y / H_IN, s, va="top", **k)   # noqa: E731
    t(23.3, "ACOSTA RESIDENCE", fontsize=16, weight="bold")
    t(22.85, "Single-family residence\nfire rebuild (Eaton Fire)", fontsize=10)
    t(22.0, "220 Laurel Dr\nAltadena, CA 91001\nAPN 5832-003-027", fontsize=10)
    t(20.9, "Zone R-1 · Altadena CSD\nVery High Fire Hazard\nSeverity Zone", fontsize=9)
    t(19.6, "Owner: Richard Acosta", fontsize=9)
    t(19.15, "Prepared by: ______________", fontsize=9)
    t(18.7, "Structural: by engineer\n(separate sheets)", fontsize=9)
    t(17.6, "DRAFT FOR REVIEW\nnot for construction", fontsize=10, color=RED, weight="bold")
    t(16.6, f"Date: {Z.DATE}\nRevisions:", fontsize=9)
    t(6.2, "\u00a9 2026 Richard Acosta.\nAll rights reserved.\nThese drawings are for\n220 Laurel Dr only. Not to\nbe copied, adapted, sold\nor built from on any\nother site.", fontsize=8.5)
    t(3.4, title, fontsize=13, weight="bold", wrap=True)
    t(1.9, num, fontsize=40, weight="bold")
    return fig


def scaled_axes(fig, left_in, bottom_in, x0, y0, x1, y1, scale=0.25):
    """Axes showing plan inches x0..x1, y0..y1 at `scale` paper inches per foot (1/4" = 1'-0" default)."""
    w, h = (x1 - x0) / 12 * scale, (y1 - y0) / 12 * scale
    ax = fig.add_axes([left_in / W_IN, bottom_in / H_IN, w / W_IN, h / H_IN])
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")
    return ax


def dim_string(ax, pts, at, horiz=True, fs=7, color=INK):
    """Chain of dimensions through the points `pts` (x's for a horizontal string at y=`at`, or y's)."""
    pts = sorted(set(round(p, 2) for p in pts))
    a0, a1 = pts[0], pts[-1]
    if horiz:
        ax.plot([a0, a1], [at, at], color=color, lw=0.6)
    else:
        ax.plot([at, at], [a0, a1], color=color, lw=0.6)
    for p in pts:                                                        # architectural ticks
        if horiz:
            ax.plot([p - 3, p + 3], [at - 3, at + 3], color=color, lw=1.0)
        else:
            ax.plot([at - 3, at + 3], [p - 3, p + 3], color=color, lw=1.0)
    for a, b in zip(pts, pts[1:]):
        if b - a < 6:
            continue
        m = (a + b) / 2
        if horiz:
            ax.text(m, at + 3, ftin(b - a), fontsize=fs, ha="center", va="bottom", color=color)
        else:
            ax.text(at - 3, m, ftin(b - a), fontsize=fs, ha="right", va="center", rotation=90, color=color)


def table(fig, left_in, top_in, title, cols, widths, rows, fs=7.5, row_h=0.24):
    """A schedule: column headings and rows of text, ruled, top-left at (left_in, top_in)."""
    x = [left_in]
    for w in widths:
        x.append(x[-1] + w)
    fig.text(left_in / W_IN, (top_in + 0.1) / H_IN, title, fontsize=10, weight="bold")
    y = top_in
    for i, r in enumerate([cols] + rows):
        lines = max(str(c).count("\n") + 1 for c in r)
        h = row_h * lines
        for j, c in enumerate(r):
            fig.text((x[j] + 0.05) / W_IN, (y - 0.05) / H_IN, str(c), fontsize=fs, va="top",
                     weight="bold" if i == 0 else "normal")
        y -= h
        fig.add_artist(plt.Line2D([x[0] / W_IN, x[-1] / W_IN], [y / H_IN] * 2, transform=fig.transFigure,
                                  lw=1.0 if i == 0 else 0.4, color=INK))
    for xx in x:
        fig.add_artist(plt.Line2D([xx / W_IN] * 2, [top_in / H_IN, y / H_IN], transform=fig.transFigure,
                                  lw=0.4, color=INK))
    fig.add_artist(plt.Line2D([x[0] / W_IN, x[-1] / W_IN], [top_in / H_IN] * 2, transform=fig.transFigure,
                              lw=1.0, color=INK))
    return y


# ---- rooms, openings ---------------------------------------------------------------------------
def rooms(sh):
    """[(name, polygon)]: the spaces between walls, named by the plan's room labels inside them."""
    solids = unary_union([S.ext_rect(ax, f, d, a, b) for ax, f, d, a, b in S.EXT_WALLS.values()]
                         + [S.wall_rect(ax, c, a, b, t) for _, ax, c, a, b, t in S.WALLS])
    spaces = box(S.E, S.N, S.W, S.S).difference(solids)
    labels = [(e.dxf.text, e.dxf.insert.x, e.dxf.insert.y) for e in sh.msp.query("TEXT[layer=='A-AREA-IDEN']")
              if not any(ch.isdigit() for ch in e.dxf.text)]
    out = []
    for poly in getattr(spaces, "geoms", [spaces]):
        names = [(n, x, y) for n, x, y in labels if poly.contains(Point(x, y))]
        out.append((names, poly))
    return out


def room_at(rms, x, y):
    if S.face("bedroom hall wall", +1) < y < S.face("south hall wall", -1) and \
            S.face("lounge|gym", +1) < x < S.face("hall end", -1):
        return "LOBBY"                                   # the hall runs on from the lounge: one open space
    for names, poly in rms:
        if poly.contains(Point(x, y)):
            if not names:
                return "EXTERIOR"
            return min(names, key=lambda n: (n[1] - x) ** 2 + (n[2] - y) ** 2)[0]
    return "EXTERIOR"


def sides(o):
    """Points 20" either side of an opening's centre: (minus side, plus side) along the wall normal."""
    axis, c, t = S.wall_info(o[0])
    m = (o[1] + o[2]) / 2
    if axis == "x":
        return (m, c - t / 2 - 20), (m, c + t / 2 + 20)
    return (c - t / 2 - 20, m), (c + t / 2 + 20, m)


def outward(name):
    """+1/-1: the outside of an exterior wall along its normal (+y for x walls, +x for y walls)."""
    return -S.EXT_WALLS[name][2]


def doors():
    return [o for o in S.OPENINGS if o[3] in ("door", "slider", "bifold", "pocket")]


def windows():
    ws = [(o[0], o[1], o[2], *(o[4:6] if len(o) > 4 else (30.0, 96.0)),
           "window" if o[0] in S.EXT_WALLS else "interior")
          for o in S.OPENINGS if o[3] in ("window", "transom")]
    lx0, lx1 = X.CLERESTORY_X                                             # clerestory, above the lounge window
    ws.append(("north", lx0, lx1, X.CLERESTORY_SILL, X.CLERESTORY_SILL + 36.0, "clerestory"))
    return ws


def window_type(rm, w, h, sill, kind):
    """(operation, notes) for the schedule: notes only where something is required."""
    if kind == "clerestory":
        return f"Fixed, {X.CLERESTORY_UNITS} units mulled", "Clerestory"
    if kind == "interior":
        return "Fixed transom", "Interior, over the door; reeded glass"
    if rm in ("GYM", "GUEST", "OFFICE", "PRIMARY") and sill <= 44:
        return "Horizontal slider", "Emergency escape (note 6)"
    if rm == "LOUNGE":
        return "Fixed center, slider each end", ""
    if rm == "DINING":
        return "Fixed, two units mulled", ""
    if rm == "KITCHEN":
        return "Horizontal slider", ""
    if rm in ("PORCH", "FOYER"):
        return "Fixed, reeded glass", "Tempered (CRC R308.4.2)"
    if "ENSUITE" in rm:
        return "Awning", "Obscure glass"
    return "Awning", ""


CASEWORK_WORDS = {"HANG", "SHELVES", "SHELVES ABOVE", "SHELVES TO 6'", "DRAWERS", "BENCH", "BEV",
                  "TALL STORAGE", "TRASH", "ON PEDESTAL", "HIGH WINDOW", "FOLDING COUNTER",
                  "LEDGE", "CURBLESS"}
KEEP_OUTSIDE = {"CARPORT", "18' x 20'", "CONDENSER", "PORCH", "WOOD-LOOK FEATURE WALL"}


def build_doc():
    """The schematic for the permit plans: no loose furniture or built-in casework (shelves, rods,
    drawers, benches: they can change without a revision), no site work; walls, doors, windows,
    plumbing fixtures, appliances, equipment, closets and the carport stay."""
    from ezdxf import bbox
    sh = S.build()
    drop = set(id(e) for e in sh.movable)
    house = box(S.E - 2, S.N - 2, S.W + 2, S.S + 2)
    carport = box(*S.CARPORT).buffer(8)
    closets = [(e.dxf.insert.x, e.dxf.insert.y) for e in sh.msp.query("TEXT")
               if e.dxf.text in ("CL", "CLOSET", "LINEN CLOSET")]
    for e in list(sh.msp):
        lay, kind = e.dxf.layer, e.dxftype()
        txt = e.dxf.text if kind == "TEXT" else None
        bb = bbox.extents([e])
        geo = box(bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y) if bb.has_data else None
        gone = (id(e) in drop or lay in ("A-ANNO-DIMS", "L-PLNT", "A-FENC", "C-PROP")
                or (lay == "A-FURN" and not (geo and any(geo.buffer(1).contains(Point(p)) for p in closets)))
                or (txt in CASEWORK_WORDS) or (txt and "FENCE" in txt))
        if (not gone and lay == "A-WALL" and geo is not None and geo.area > 0
                and geo.intersection(house).area < 0.5 * geo.area and not geo.within(carport)):
            gone = True                                                # the entry court's seat wall
        if not gone and geo is not None and not geo.intersects(house) and txt not in KEEP_OUTSIDE:
            gone = not (geo.within(carport) or lay == "A-EQPM" or (lay == "L-SITE" and geo.within(carport)))
        if lay == "L-SITE" and not (geo and geo.within(carport)):
            gone = True
        if gone:
            sh.msp.delete_entity(e)
    return sh


# ---- survey surface, grades ---------------------------------------------------------------------
_SURF = {}


def survey():
    """(ground shots [(x, y, z)], smooth surface z(x, y) in feet, utilities {label: (x, y)}) from the
    topographic survey, in plan inches."""
    if _SURF:
        return _SURF["shots"], _SURF["z"], _SURF["utils"]
    import re
    import ezdxf
    import matplotlib.tri as mtri
    import numpy as np
    import survey_overlay as O
    msp = ezdxf.readfile(O.SURVEY).modelspace()
    to_lot, _, _ = O.lot_transform(msp)
    shots = []
    for m in msp.query("MTEXT"):
        if "pts label" not in m.dxf.layer:
            continue
        hit = re.search(r"\b(FG|CONC|FS|EP)\s+(14\d\d\.\d\d)", m.plain_text())
        if hit:
            x, y = to_lot(m.dxf.insert.x, m.dxf.insert.y)
            if -200 < y < S.LOT_D + 60 and -80 < x < S.LOT_W + 100:
                shots.append((x, y, float(hit.group(2))))
    xs, ys, zs = (np.array(v) for v in zip(*shots))
    tri = mtri.Triangulation(xs, ys)
    t = tri.triangles
    edge = np.max([np.hypot(xs[t[:, i]] - xs[t[:, (i + 1) % 3]], ys[t[:, i]] - ys[t[:, (i + 1) % 3]])
                   for i in range(3)], axis=0)
    tri.set_mask(edge > 360)
    interp = mtri.CubicTriInterpolator(tri, zs, kind="geom")
    lin = mtri.LinearTriInterpolator(mtri.Triangulation(xs, ys), zs)

    def z(x, y):
        v = interp(x, y)
        return float(lin(x, y)) if np.ma.is_masked(v) else float(v)
    names = {"WM": "WATER METER", "SSCO": "SEWER CLEANOUT", "PP": "POWER POLE"}
    utils = {names[t.dxf.text.strip()]: to_lot(t.dxf.insert.x, t.dxf.insert.y)
             for t in msp.query("TEXT") if t.dxf.text.strip() in names}
    walls = []                                                           # existing walls and the chimney
    for e in msp:
        lay = e.dxf.layer
        if ("sw wall" in lay or "sw chimney" in lay) and "hatch" not in lay and e.dxftype() in ("LINE", "LWPOLYLINE"):
            pts = ([to_lot(e.dxf.start.x, e.dxf.start.y), to_lot(e.dxf.end.x, e.dxf.end.y)] if e.dxftype() == "LINE"
                   else [to_lot(q[0], q[1]) for q in e.get_points("xy")])
            kind = "chimney" if "chimney" in lay else ("line" if max(q[0] for q in pts) < 20 else "old")
            walls.append((kind, pts))
    _SURF.update(shots=shots, z=z, utils=utils, grid=(xs, ys, zs, interp), walls=walls)
    return shots, z, utils


def ff_elev():
    """Assumed finished floor elevation (ft): 6" above the highest existing grade at the house walls."""
    _, z, _ = survey()
    pts = [(x, y) for x in range(int(S.E), int(S.W) + 1, 24) for y in (S.N, S.S)]
    pts += [(x, y) for y in range(int(S.N), int(S.S) + 1, 24) for x in (S.E, S.W)]
    return round(max(z(x, y) for x, y in pts) + 0.5, 1)


def contours(ax, x0, y0, x1, y1, color="#9a7b4f"):
    import numpy as np
    survey()
    xs, ys, zs, interp = _SURF["grid"]
    gx, gy = np.meshgrid(np.arange(max(x0, xs.min()), min(x1, xs.max()), 12.0),
                         np.arange(max(y0, ys.min()), min(y1, ys.max()), 12.0))
    gz = interp(gx, gy)
    lo, hi = int(np.floor(zs.min())), int(np.ceil(zs.max()))
    cs = ax.contour(gx, gy, gz, levels=range(lo, hi + 1), colors=color,
                    linewidths=[1.3 if lv % 5 == 0 else 0.7 for lv in range(lo, hi + 1)], linestyles="--")
    ax.clabel(cs, levels=[lv for lv in range(lo, hi + 1)], fmt=lambda v: f"{v:.0f}", fontsize=5, inline=True)


# ---- A-1 site plan ---------------------------------------------------------------------------
def site_plan(pdf):
    from matplotlib.patches import FancyArrow
    fig = sheet("A-1", "SITE PLAN\n& PROJECT DATA")
    x0, y0, x1, y1 = S.LOT_X0 - 60, -230, S.LOT_X0 + S.LOT_W + 70, S.LOT_D + 60
    ax = scaled_axes(fig, 0.9, 3.4, x0, y0, x1, y1, scale=3 / 16)
    contours(ax, x0, y0, x1, y1)
    L = S.LOT_X0, 0, S.LOT_X0 + S.LOT_W, S.LOT_D
    ax.add_patch(Rectangle((L[0], L[1]), L[2] - L[0], L[3] - L[1], fill=False, ec=INK, lw=1.6, ls="-."))
    # setback lines
    sb = dict(fill=False, ec=RED, lw=0.7, ls=":")
    ax.add_patch(Rectangle((L[0] + Z.SIDE_REQ, Z.REAR_REQ * 0 + 240.0), L[2] - L[0] - 2 * Z.SIDE_REQ,
                           L[3] - Z.REAR_REQ - 240.0, **sb))
    ax.text(L[0] + Z.SIDE_REQ + 6, 246, "SETBACK LINES", fontsize=5.5, color=RED, va="bottom")
    # house, porch, carport, eaves
    ax.add_patch(MPoly(Z.FOOT, closed=True, fc="#cfcfcf", ec=INK, lw=1.4, hatch="////"))
    ax.text((S.E + S.W) / 2, (S.N + S.S) / 2, "NEW 1-STORY RESIDENCE\n" + f"{Z.HOUSE:,.0f} SQ FT\n"
            f"FF {ff_elev():.1f}' (ASSUMED, PER CIVIL)", ha="center", va="center", fontsize=8, weight="bold",
            bbox=dict(fc="white", ec="none", pad=1.5))
    ax.add_patch(Rectangle((S.E - X.EAVE, S.N - X.EAVE), S.W - S.E + 2 * X.EAVE, S.S - S.N + 2 * X.EAVE,
                           fill=False, ec=INK, lw=0.6, ls="--"))
    cx0, cy0, cx1, cy1 = S.CARPORT
    ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0, fc="#eeeeee", ec=INK, lw=1.0, ls="--"))
    ax.text((cx0 + cx1) / 2, (cy0 + cy1) / 2, f"OPEN CARPORT\n{Z.CARPORT:,.0f} SQ FT\n2 SPACES", ha="center",
            va="center", fontsize=6.5)
    ax.text((S.E + S.PORCH_X) / 2, (S.N + S.PORCH_Y) / 2, "PORCH", ha="center", va="center", fontsize=5.5)
    # hardscape
    ax.add_patch(MPoly(S.driveway_outline(), closed=True, fc="#f3f3f3", ec=INK, lw=0.8))
    ax.text((S.DRIVE_IN[0] + S.DRIVE_IN[1]) / 2, 120, "NEW DRIVEWAY", ha="center", fontsize=6.5)
    e0, e1, e2, e3 = S.ENTRY_COURT
    ax.add_patch(Rectangle((e0, e1), e2 - e0, e3 - e1, fc="#f3f3f3", ec=INK, lw=0.6))
    for b in S.ENTRY_WALLS:
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc="#999", ec=INK, lw=0.5))
    ax.text((e0 + e2) / 2, (e1 + e3) / 2, "ENTRY COURT\n24\" SEAT WALL", ha="center", va="center", fontsize=5)
    ax.plot([L[0], L[2]], [S.EDGE_OF_PAVEMENT] * 2, color=INK, lw=0.8)
    ax.text((L[0] + L[2]) / 2, -200, "LAUREL DRIVE (50' R/W)", ha="center", fontsize=10, weight="bold")
    ax.text(L[0] + 20, S.EDGE_OF_PAVEMENT + 5, "EDGE OF PAVEMENT", fontsize=5)
    # trees and utilities
    trees = [(x, y, "EXIST. OLIVE (REMAIN)") for x, y in S.EXIST_TREES] + [
        (*S.PRIVACY_TREE, "NEW TREE"), (*S.SIDE_TREE, "NEW TREE"), (107.0, 158.0, "EXIST. TREE (ARBORIST)"),
        (322.0, -114.0, "EXIST. STREET TREE")]
    for x, y, lab in trees:
        ax.add_patch(Circle((x, y), 30, fill=False, ec="#2e7d32", lw=0.8))
        ax.add_patch(Circle((x, y), 3, fc="#2e7d32", ec="none"))
        ax.text(x, y - 38, lab, fontsize=4.5, ha="center", va="top", color="#2e7d32")
    _, z, utils = survey()
    for kind, pts in _SURF["walls"]:                                     # existing walls and chimney
        c, ls = ("#b03a2e", "--") if kind != "line" else ("#555", "-")
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=c, lw=1.4 if kind == "line" else 1.1, ls=ls)
    ax.text(150, 690, "EXIST. RETAINING WALL\nAND CHIMNEY (DASHED)\nTO BE REMOVED", fontsize=5.5, color="#b03a2e",
            va="center")
    ax.text(S.LOT_X0 + 10, 300, "EXIST. RETAINING WALL AT THE\nEAST LINE (NEIGHBOR'S GRADE):\nTO REMAIN, NO EXCAVATION\n"
            "AT ITS BASE", fontsize=5, color="#555", va="center", rotation=90)
    for lab, (x, y) in utils.items():
        ax.add_patch(Rectangle((x - 5, y - 5), 10, 10, fc="white", ec="#1f5e9e", lw=0.8))
        ax.text(x + 9, y, lab, fontsize=5, color="#1f5e9e", va="center")
    ax.text(S.W + 12, S.N + 8, "ELECTRIC SERVICE\n(METER-MAIN, PER SCE)", fontsize=5, color="#1f5e9e", va="bottom")
    hx = sum(next(w[3:5] for w in S.WALLS if w[0] == "bath|storage")) / 2
    ax.add_patch(Rectangle((hx - 21, S.S + 10), 42, 20, fc="white", ec=INK, lw=0.6))
    ax.text(hx, S.S + 34, "HEAT PUMP\nOUTDOOR UNIT", fontsize=4.5, ha="center", va="bottom")
    # existing grade at the corners, drainage away from the house
    for x, y in ((S.E, S.N), (S.W, S.N), (S.W, S.S), (S.E, S.S), (S.PORCH_X, S.N)):
        ax.text(x, y, f"  {z(x, y):.1f}", fontsize=5, color="#9a7b4f", ha="left", va="center")
    arr = dict(width=1.2, head_width=9, head_length=12, color="#1f5e9e", length_includes_head=True)
    for (ax_, ay), (dx, dy) in [((700, S.N - 10), (0, -60)), ((1000, S.N - 10), (0, -60)),
                                ((700, S.S + 45), (0, 50)), ((1000, S.S + 45), (0, 50)),
                                ((S.W + 10, 330), (60, 0)), ((S.W + 10, 540), (60, 0)),
                                ((S.E - 10, 560), (-50, 0))]:
        ax.add_artist(FancyArrow(ax_, ay, dx, dy, **arr))
    ax.text(1180, S.S + 120, "DRAINAGE: finished grade slopes away from\nthe house (5% for 10' or 2% at paving,\n"
            "CRC R401.3); site drainage per civil.", fontsize=5.5, color="#1f5e9e", va="top")
    # dimensions
    Z.dim(ax, (950, 0), (950, S.N), f"{ftin(S.N)}\n(20'-0\" req.)", fs=6.5, rot=90)
    Z.dim(ax, (950, S.S), (950, S.LOT_D), f"{ftin(S.LOT_D - S.S)} ({ftin(Z.REAR_REQ)} req.)", fs=6.5, rot=90)
    Z.dim(ax, (S.W, 430), (L[2], 430), f"{ftin(L[2] - S.W)}\n({ftin(Z.SIDE_REQ)} req.)", fs=6.5, rot=90)
    Z.dim(ax, (L[0], 485), (cx0, 485), f"{ftin(cx0 - L[0])}\n({ftin(Z.SIDE_REQ)} req.)", fs=6.5)
    dim_string(ax, [L[0], L[2]], L[3] + 25, fs=7)
    dim_string(ax, [0, L[3]], L[2] + 35, horiz=False, fs=7)
    ax.text(L[0] + 10, L[3] - 14, "PROPERTY LINE (S67°36'30\"E 113.00')", fontsize=5)
    ax.text((L[0] + L[2]) / 2, y0 + 8, "SITE PLAN   3/16\" = 1'-0\"", fontsize=12, weight="bold", ha="center")
    ax.annotate("", (S.W + 40, 120), (S.W + 40, 190), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(S.W + 48, 155, "PLAN NORTH", fontsize=6, va="center")
    import math
    az = math.radians(S.PLAN_NORTH_AZ)
    tx, ty = 1290, 100                                   # true north: plan north is ~22° east of true
    ax.annotate("", (tx - 55 * math.sin(az), ty - 55 * math.cos(az)), (tx, ty),
                arrowprops=dict(arrowstyle="-|>", lw=1.2, color=INK))
    ax.text(tx + 6, ty + 8, "TRUE N", fontsize=6)

    # project data and general notes (right column)
    rows = [("PROJECT DATA", ""), ("Scope", "New 1-story single-family residence\nwith attached open carport; Eaton Fire\n"
            "rebuild (non-like-for-like). Demolish\nremaining retaining wall and chimney."),
            ("Address / APN", "220 Laurel Dr, Altadena CA 91001\nAPN 5832-003-027"),
            ("Zoning", "R-1-7500 · Altadena CSD"), ("Fire zone", "Very High Fire Hazard Severity Zone"),
            ("Occupancy", "R-3 (dwelling), U (carport)"), ("Construction type", "V-B, fully sprinklered (NFPA 13D)"),
            ("Codes", "2022 California Residential, Building,\nElectrical, Mechanical, Plumbing, Energy\n"
             "and Green Building Codes (fire rebuild,\nEO N-29-25), as amended by LA County\nTitle 26"),
            ("Lot", f"{Z.LOT_W_FT:.2f}' x {Z.LOT_D_FT:.2f}' = {Z.LOT_AREA:,.0f} sq ft"),
            ("Floor area", f"{Z.HOUSE:,.0f} sq ft (to outside of walls)"),
            ("Porch / carport", f"{Z.PORCH:,.0f} / {Z.CARPORT:,.0f} sq ft"),
            ("Lot coverage", f"{Z.COVER:,.0f} sq ft ({Z.COVER / Z.LOT_AREA:.1%}); limit {Z.LIMIT:,.0f}"),
            ("Height", f"1 story, ~{ftin(Z.TOP)} above finished floor"),
            ("Bedrooms / baths", "4 / 3"), ("Parking", "2 covered (carport)")]
    y = 22.9
    for k, v in rows:
        fig.text(25.9 / W_IN, y / H_IN, k, fontsize=8, weight="bold" if not v else "normal", va="top")
        fig.text(28.3 / W_IN, y / H_IN, v, fontsize=8, va="top")
        y -= 0.22 * max(1, v.count("\n") + 1) + 0.08
    notes = ("SITE NOTES\n"
             "1. Lot lines, existing trees, utilities, spot\n   elevations and 1' contours (dashed) from\n"
             "   the owner's topographic survey.\n"
             "2. Finished floor elevation, grading and drainage\n   per civil (separate sheets).\n"
             "3. Eaves (dashed) 2'-6\" all round (LACC 22.110.090).\n"
             "4. Existing street and parkway trees protected\n   during construction (root zones).\n"
             "5. 5' noncombustible zone around the house.\n"
             "6. Water, sewer and SCE service per the utilities;\n   no gas service (all-electric).\n"
             "7. Demolition: remove the remaining retaining wall and\n   chimney from the burned house (dashed red); asbestos\n"
             "   survey first if required (SCAQMD Rule 1403); fill\n   and grade per civil.\n"
             "8. The retaining wall along the east line holds the\n   neighbor's higher grade: protect it in place.")
    fig.text(25.9 / W_IN, (y - 0.3) / H_IN, notes, fontsize=8, va="top", linespacing=1.35)
    pdf.savefig(fig); fig.savefig(OUT / "A-1-site-plan.png", dpi=80); plt.close(fig)


# ---- A-3 roof plan ---------------------------------------------------------------------------
def text_at(sh, label):
    for e in sh.msp.query("TEXT"):
        if e.dxf.text == label:
            return e.dxf.insert.x, e.dxf.insert.y
    return None


def roof_plan(pdf):
    fig = sheet("A-3", "ROOF PLAN")
    OV, cx0, cy0, cx1, cy1 = X.EAVE, *S.CARPORT
    x0, y0, x1, y1 = cx0 - 40, S.N - OV - 110, S.W + OV + 150, S.S + OV + 130
    ax = scaled_axes(fig, 1.2, 6.5, x0, y0, x1, y1)
    X0, X1, Y0, Y1 = S.E - OV, S.W + OV, S.N - OV, S.S + OV
    ax.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fc="#e6e6e6", ec=INK, lw=1.6))
    ax.add_patch(MPoly(Z.FOOT, closed=True, fill=False, ec="#777", ls="--", lw=0.8))
    ax.add_patch(Rectangle((cx0 - 6, cy0 - 6), cx1 - cx0 + 6, cy1 - cy0 + 12, fc="#f4f4f4", ec=INK, lw=1.0))
    wx, ry = X.WING_X, X.RIDGE_Y
    ax.plot([wx, wx], [Y0, Y1], color=INK, lw=1.2)                         # shed / gable line
    ax.plot([wx, X1], [ry, ry], color=INK, lw=1.8)                         # the wing's ridge
    ax.text(X1 - 8, ry - 6, "RIDGE", fontsize=7, ha="right")
    ax.text(wx + 6, Y0 + 30, "SHED WALL ABOVE THE GABLE:\nstep + kick-out flashing", fontsize=5.5)
    for xx in (470, 680):                                              # shed: down toward the rear
        ax.annotate("", (xx, Y1 - 30), (xx, Y0 + 40), arrowprops=dict(arrowstyle="->", lw=1.4))
        ax.text(xx + 8, (Y0 + Y1) / 2, "2:12\nDN", fontsize=8, va="center")
    for xx in (960, 1170):                                             # gable: down each way from the ridge
        ax.annotate("", (xx, Y1 - 30), (xx, ry + 12), arrowprops=dict(arrowstyle="->", lw=1.4))
        ax.annotate("", (xx, Y0 + 30), (xx, ry - 12), arrowprops=dict(arrowstyle="->", lw=1.4))
        ax.text(xx + 8, (ry + Y1) / 2 + 40, "2:12\nDN", fontsize=8, va="center")
        ax.text(xx + 8, (Y0 + ry) / 2, "2:12\nDN", fontsize=8, va="center")
    ax.annotate("", (cx0 + 10, (cy0 + cy1) / 2), (cx1 - 20, (cy0 + cy1) / 2), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text((cx0 + cx1) / 2, (cy0 + cy1) / 2 + 14, "CARPORT ROOF\n1/2\":12 DN, away from house\nstanding-seam metal, double-lock",
            ha="center", fontsize=6.5)
    ax.plot([X0, X1], [Y1 + 4, Y1 + 4], color=INK, lw=2.5)                 # rear gutter
    for gx in (X0 + 14, (X0 + X1) / 2, X1 - 14):
        ax.add_patch(Circle((gx, Y1 + 4), 6, fc="white", ec=INK, lw=1.0))
    ax.text(X1 - 14, Y1 + 18, "GUTTER ALONG THE REAR EAVE, 3 DOWNSPOUTS (O) TO SITE DRAINAGE (CIVIL)",
            fontsize=6.5, ha="right", va="bottom")
    ax.plot([wx, X1], [Y0 - 4, Y0 - 4], color=INK, lw=2.5)                 # the wing's street gutter
    for gx in (wx + 14, X1 - 14):
        ax.add_patch(Circle((gx, Y0 - 4), 6, fc="white", ec=INK, lw=1.0))
    ax.text(X1 - 14, Y0 - 16, "GUTTER ALONG THE WING'S STREET EAVE, 2 DOWNSPOUTS", fontsize=6.5, ha="right")
    ax.plot([cx0 - 8, cx0 - 8], [cy0 - 6, cy1 + 6], color=INK, lw=2.0)
    ax.text(cx0 - 14, (cy0 + cy1) / 2, "GUTTER", fontsize=5.5, rotation=90, ha="right", va="center")
    sh = S.build()
    sk = text_at(sh, "SKYLIGHT")                                        # straight up from the common bath ceiling
    hs = text_at(sh, '14" SKYLIGHT')                                    # the hall's: its dome just off the ridge
    hs = hs and (hs[0], X.RIDGE_Y + 24)
    for lab, note, p in (("SKYLIGHT", "10\" TUBULAR SKYLIGHT + FAN (CLASS A),\nstraight up from the bath; VTR-2 just downslope", sk),
                         ("RANGE", "RANGE HOOD CAP, EMBER-RESISTANT DAMPER:\nshortest run; set the PV layout around it", text_at(sh, "RANGE")),
                         ("HALL", "14\" TUBULAR SKYLIGHT (CLASS A) from the hall ceiling,\ndome 2' downslope of the ridge "
                          "(short offset);\nset the PV layout around it", hs)):
        if p:
            ax.add_patch(Circle(p, 7, fc="white", ec=INK, lw=0.9))
            below = lab == "SKYLIGHT"                                    # its vent label sits above it
            ax.text(p[0] + 10, p[1] - 10 if below else p[1] + 10, note, fontsize=5.5, va="top" if below else "bottom")
    # plumbing vents through the roof: grouped in a strip along the high (street) edge, outside the PV area
    ax.add_patch(MPoly(pv_area(), closed=True, fill=False, ec="#1f5e9e", lw=1.0, ls="--"))
    ax.text(X0 + 48, Y1 - 50, "POTENTIAL SOLAR PV AREA (dashed): the south-facing planes, clear of the shed's high-edge\n"
            "setback, the ridge setback and the 36\" pathways at both ends (CRC R324.6); final layout per the solar design",
            fontsize=6.5, color="#1f5e9e")
    vtrs = [(860.0, S.N + 10, "VTR-1: guest ensuite (its own vent, on the\nwing's street-facing slope, outside the PV area)", "bottom"),
            (868.0, 544.0, "VTR-2 (3\" main vent), just downslope of the skylight: kitchen sink\n(up beside the window, into the pantry wall, then the\n"
                              "pantry attic), common bath, laundry and primary bath", "bottom")]
    for vx, vy, lab, va in vtrs:
        ax.add_patch(Circle((vx, vy), 6, fc="white", ec=INK, lw=1.2, zorder=5))
        ax.plot([vx - 6, vx + 6], [vy] * 2, color=INK, lw=0.8, zorder=6)
        ax.text(vx + 10, vy + (4 if va == "bottom" else -8), lab, fontsize=5.5, va=va)
    ax.text(X1 - 40, S.N + 4, "PLUMBING VENTS (APPROX., FINAL PER PLUMBER): each\n6\" min. above the roof and 10' from or 3' above\n"
            "openable windows and air intakes", fontsize=5.5,
            ha="right", va="bottom")
    ax.text((X0 + wx) / 2, Y0 + 8, f"SHED'S HIGH EDGE AT THE STREET: TOP ~{ftin(Z.TOP)} ABOVE FINISHED FLOOR",
            fontsize=7, ha="center")
    ax.text((wx + X1) / 2, ry - 30, f"GABLE RIDGE: TOP ~{ftin(Z.RIDGE_TOP)}", fontsize=7, ha="center")
    ax.text((X0 + X1) / 2, Y1 - 24, f"LOW EDGE AT THE REAR: TOP OF ROOF ~{ftin(Z.REAR_TOP)} ABOVE FINISHED FLOOR",
            fontsize=7, ha="center")
    dim_string(ax, [X0, S.E, S.W, X1], Y0 - 30)
    dim_string(ax, [Y0, S.N, S.S, Y1], X1 + 40, horiz=False)
    ax.text((X0 + X1) / 2, y0 + 8, "ROOF PLAN   1/4\" = 1'-0\"", fontsize=12, weight="bold", ha="center")
    ax.text(X0, Y0 - 70, "STREET (PLAN NORTH)", fontsize=8, weight="bold")
    notes = ("ROOF NOTES\n"
             "1. Main roof at 2:12: a shed from the porch into the bedroom wing,\n"
             "   high at the street, and a gable over the rest of the wing.\n"
             "   Class A asphalt shingles (fiberglass), dark, wind-rated\n"
             "   (ASTM D7158 Class H / D3161 Class F), over two layers of\n"
             "   underlayment as required at 2:12 (CRC R905.2); self-adhered\n"
             "   underlayment at the eaves and along the shed / gable junction.\n"
             "2. Sealed (unvented) attic, CRC R806.5: insulation at the roof deck;\n"
             "   NO attic or eave vents.\n"
             "3. Eaves 2'-6\" all round, enclosed; dark metal fascia and drip edge.\n"
             "   See A-6 for fire-zone details (CRC R337).\n"
             "4. Gutters with noncombustible gutter guards (CRC R337.5.4);\n"
             "   downspouts to the site drainage system per civil.\n"
             "5. Roof framing, sheathing and connections per structural.\n"
             "6. Roof penetrations flashed per the shingle maker. Two plumbing\n"
             "   vents (VTR): the guest ensuite's on the wing's street slope; the\n"
             "   rest combined into one beside the common bath skylight, so\n"
             "   the panel layout works around one cluster. Bath and laundry\n"
             "   fans exit through walls where possible. The range hood cap\n"
             "   and the hall's 14\" skylight are the other penetrations in\n"
             "   the PV area.\n"
             "7. Carport: attached open carport, its own roof at 1/2\":12 in\n"
             "   double-lock standing seam (Class A assembly, uplift-rated),\n"
             "   gutter on its east edge.\n"
             "8. Future solar: layout by the solar provider, on rails over\n"
             "   flashed attachments into the framing (per the solar design).\n"
             "   Its conduit enters through the roof into the attic and\n"
             "   runs inside to the panel: none on the roof surface or\n"
             "   the exterior walls.\n"
             "9. Wind: severe downslope winds from the north / northeast\n"
             "   strike the shed's high street edge. Wind-rated shingles with\n"
             "   the maker's high-wind nailing, sealed starter strips at eaves\n"
             "   and rakes; eave and carport tie-downs per structural.")
    fig.text(27.0 / W_IN, 22.9 / H_IN, notes, fontsize=8.5, va="top", linespacing=1.35)
    pdf.savefig(fig); fig.savefig(OUT / "A-3-roof-plan.png", dpi=80); plt.close(fig)


# ---- A-4 elevations ------------------------------------------------------------------------
MATERIALS = ("EXTERIOR MATERIALS\n"
             "1. Walls: 3-coat stucco, light color (noncombustible).\n"
             "2. Roof: asphalt shingles, dark, Class A (A-3); carport\n"
             "   roof standing-seam metal.\n"
             "3. Fascia, drip edge and canopies: dark metal.\n"
             "4. Porch walls and ceiling: wood-look fiber cement or\n"
             "   porcelain (noncombustible / ignition-resistant).\n"
             "5. Windows: dual-pane, one pane tempered (CRC R337.8);\n"
             "   street windows recessed 6\". See A-2 schedule.\n"
             "6. Eave soffits enclosed, no vents (A-6).\n"
             "7. Existing grade (dashed) is approximate, from the\n"
             "   survey with an assumed finished floor; finished\n"
             "   grades and floor elevation per civil.")


def grade_line(ax, side, ff):
    _, z, _ = survey()
    import numpy as np
    if side in ("north", "south"):
        y = S.N - 12 if side == "north" else S.S + 12
        us = np.arange(S.E - 60, S.W + 61, 12)
        h = (lambda u: u) if side == "north" else (lambda u: -u)
        pts = [(h(u), (z(u, y) - ff) * 12) for u in us]
    else:
        x = S.E - 12 if side == "east" else S.W + 12
        us = np.arange(S.N - 60, S.S + 61, 12)
        h = (lambda u: u) if side == "west" else (lambda u: -u)
        pts = [(h(u), (z(x, u) - ff) * 12) for u in us]
    pts.sort()
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#9a7b4f", lw=1.0, ls="--")
    lo = min(p[1] for p in pts)
    ax.text(pts[0][0], pts[0][1] + 4, "EXIST. GRADE (APPROX.)", fontsize=5.5, color="#9a7b4f", va="bottom")
    return lo


def elevations(pdf):
    fig = sheet("A-4", "EXTERIOR\nELEVATIONS")
    ff = ff_elev()
    tmp = plt.figure()
    lims = {}
    for side in ("north", "south", "east", "west"):
        a = tmp.add_subplot()
        Z.elevation(a, side)
        lims[side] = (a.get_xlim(), a.get_ylim())
        a.remove()
    plt.close(tmp)
    slots = {"north": (0.9, 17.6), "south": (0.9, 11.4), "east": (0.9, 4.2), "west": (13.4, 4.2)}
    for side, (lx, by) in slots.items():
        (a0, a1), (b0, b1) = lims[side]
        b0 = -70.0
        ax = scaled_axes(fig, lx, by, a0, b0, a1, b1, scale=3 / 16)
        Z.elevation(ax, side)
        ax.set_ylim(b0, b1)
        grade_line(ax, side, ff)
    fig.text(26.0 / W_IN, 22.9 / H_IN, MATERIALS, fontsize=8.5, va="top", linespacing=1.35)
    fig.text(26.0 / W_IN, 18.6 / H_IN, f"Heights are above finished floor (0'-0\").\nAssumed finished floor: {ff:.1f}' "
             "(6\" above the\nhighest existing grade at the walls).\nScale: 3/16\" = 1'-0\"", fontsize=8.5, va="top")
    pdf.savefig(fig); fig.savefig(OUT / "A-4-elevations.png", dpi=80); plt.close(fig)


# ---- A-5 sections --------------------------------------------------------------------------
ASSEMBLIES = ("ASSEMBLIES (insulation values per the Title 24 report)\n"
              "R1 ROOF: Class A asphalt shingles on two layers of\n"
              "   underlayment (2:12),\n"
              "   roof sheathing, framing per structural; spray foam at the\n"
              "   underside of the deck (unvented, CRC R806.5); ignition\n"
              "   barrier / thermal barrier where the attic is used.\n"
              "R2 VAULT: as R1, gypsum board on the framing (no attic).\n"
              "C1 CEILING (9'-0\"): 5/8\" gypsum board; sealed attic above.\n"
              "W1 EXTERIOR WALL: 7/8\" 3-coat stucco, weather barrier,\n"
              "   1\" rigid insulation, sheathing, 2x6 studs with cavity\n"
              "   insulation, 1/2\" gypsum board.\n"
              "W2 INTERIOR WALL: 2x4 (plumbing walls 2x6), gypsum both\n"
              "   sides; sound insulation at bedrooms, baths, laundry.\n"
              "F1 FLOOR: concrete slab on grade over vapor retarder and\n"
              "   capillary break (CALGreen 4.505.2); foundation, slab\n"
              "   and footings per structural; floor level per civil.")


def section_cut(ax, cut, at, ff):
    """Section through the house: cut 'x' (plan x = at, looking east-west across y) or 'y'."""
    roof = X.roof_under(2 / 12)
    THK, OV, P, C = X.THK, X.EAVE, X.PLATE, M_CEIL
    if cut == "x":
        a, b = S.N, S.S
        und = lambda u: roof(at, u)                                     # noqa: E731
        brk = X.RIDGE_Y
    else:
        a, b = S.E, S.W
        und = lambda u: roof(u, at)                                     # noqa: E731
        brk = X.WING_X
    us = [a - OV, brk, b + OV]
    ax.fill_between(us, [und(u) for u in us], [und(u) + THK for u in us], color="#555")       # roof
    for w0, w1 in ((a, a + S.EXT), (b - S.EXT, b)):                                         # exterior walls
        top = und(w0 if w0 == a else w1)
        ax.add_patch(Rectangle((w0, 0), S.EXT, top, fc="#bbb", ec=INK, lw=0.8))
    ax.add_patch(Rectangle((a - 12, -16), b - a + 24, 16, fc="#ddd", ec=INK, lw=0.8))        # slab + footings
    for f in (a, b - 12):
        ax.add_patch(Rectangle((f - 6, -40), 24, 24, fc="#ddd", ec=INK, lw=0.6, ls="--"))
    ax.text((a + b) / 2, -10, "SLAB ON GRADE (F1); FOUNDATION PER STRUCTURAL", fontsize=5.5, ha="center", va="center")
    vault = X.great_room_vault(to_outside=False)
    from shapely.geometry import Point as P_
    us_in = [u for u in range(int(a + S.EXT) + 3, int(b - S.EXT) - 2, 6)]
    def vaulted(u):
        pt = P_(at, u) if cut == "x" else P_(u, at)
        return vault.contains(pt)
    segs, cur = [], None
    for u in us_in:
        v = vaulted(u)
        if cur is None or cur[0] != v:
            cur = [v, u, u]; segs.append(cur)
        cur[2] = u
    for v, s0, s1 in segs:
        if v:
            ax.plot([s0, s1], [und(s0) - 1, und(s1) - 1], color=RED, lw=1.5)
            ax.text((s0 + s1) / 2, und((s0 + s1) / 2) - 14, "VAULTED CEILING (R2)", fontsize=5.5, ha="center",
                    color=RED, va="top")
        else:
            ax.plot([s0, s1], [C, C], color=INK, lw=1.5)
            att = [(u, und(u)) for u in range(int(s0), int(s1) + 1, 6)]
            ax.fill_between([p[0] for p in att], [C + 10] * len(att), [p[1] for p in att], color="#f3d9a6", alpha=.7)
            ax.text((s0 + s1) / 2, C + 14, "SEALED ATTIC", fontsize=5.5, ha="center", va="bottom")
            ax.text((s0 + s1) / 2, C - 6, "9'-0\" CLG (C1)", fontsize=5.5, ha="center", va="top")
    # interior walls cut by the section, and the glass in the exterior walls at the cut
    for name, axis, c, w0, w1, t in S.WALLS:
        if (axis == "x") == (cut == "x") and min(w0, w1) <= at <= max(w0, w1):
            v = vaulted(c + t)
            ax.add_patch(Rectangle((c - t / 2, 0), t, (und(c) - 1) if v else C, fc="#bbb", ec=INK, lw=0.6))
    walls = ("north", "south") if cut == "x" else ("east", "west")
    for o in S.OPENINGS:
        if o[0] in walls and o[1] <= at <= o[2] and o[3] in ("window", "slider", "door", "transom"):
            if o[3] in ("window", "transom"):
                sill, head = (o[4], o[5]) if len(o) > 4 else (30.0, 96.0)
            else:
                sill, head = 0.0, 96.0
            u0 = a if o[0] in ("north", "east") else b - S.EXT
            ax.add_patch(Rectangle((u0, sill), S.EXT, head - sill, fc="#bfe3f2", ec=INK, lw=0.6))
    lx0, lx1 = X.CLERESTORY_X
    if cut == "x" and lx0 <= at <= lx1:
        ax.add_patch(Rectangle((a, X.CLERESTORY_SILL), S.EXT, 36, fc="#bfe3f2", ec=INK, lw=0.6))
        ax.text(a + S.EXT + 4, X.CLERESTORY_SILL + 18, "CLERESTORY", fontsize=5.5, va="center")
    ax.plot([a - OV - 40, b + OV + 40], [0, 0], color=INK, lw=1.2)
    ax.text(b + OV + 45, 0, "FIN. FLOOR 0'-0\"", fontsize=6, va="center")
    ax.text(b + OV + 45, P, f"PLATE {ftin(P)}", fontsize=6, va="center")
    if cut == "x":
        ax.text(a - OV - 40, und(a) + THK + 8, "STREET", fontsize=7, weight="bold")
        ax.text(b + OV - 60, und(b) + THK + 8, "REAR", fontsize=7, weight="bold")
    _, z, _ = survey()
    gu = list(range(int(a - OV - 40), int(b + OV + 41), 12))
    gz = [(z(at, u) if cut == "x" else z(u, at)) - ff for u in gu]
    ax.plot(gu, [g * 12 for g in gz], color="#9a7b4f", lw=1.0, ls="--")
    ax.text(gu[0], gz[0] * 12 + 4, "EXIST. GRADE (APPROX.)", fontsize=5.5, color="#9a7b4f", va="bottom")
    for tag, (u, zz) in {"R1": ((a + b) / 2 + 40, und((a + b) / 2 + 40) + THK + 6),
                         "W1": (a - 26, 50), "F1": ((a + b) / 2 - 120, -26)}.items():
        ax.text(u, zz, tag, fontsize=7, weight="bold", ha="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=INK, lw=0.6))


M_CEIL = 108.0


def sections(pdf):
    fig = sheet("A-5", "BUILDING\nSECTIONS")
    ff = ff_elev()
    top = X.shed_vault_under(2 / 12)(S.N - X.EAVE) + X.THK + 30
    cuts = [("A", "x", 600.0, "SECTION A: THROUGH THE LOUNGE AND KITCHEN (VAULTED)", (0.9, 16.4)),
            ("B", "x", 960.0, "SECTION B: THROUGH THE GUEST ROOM, LOBBY AND WALK-IN CLOSET (GABLE)", (13.6, 16.4)),
            ("C", "y", 432.0, "SECTION C: ALONG THE LOBBY, LOOKING SOUTH", (0.9, 4.0))]
    for tag, cut, at, title, (lx, by) in cuts:
        a, b = (S.N, S.S) if cut == "x" else (S.E, S.W)
        ax = scaled_axes(fig, lx, by, a - X.EAVE - 50, -90, b + X.EAVE + 140, top)
        section_cut(ax, cut, at, ff)
        ax.text(a - X.EAVE - 40, -80, title + "   1/4\" = 1'-0\"", fontsize=9, weight="bold")
    fig.text(27.0 / W_IN, 22.9 / H_IN, ASSEMBLIES, fontsize=8.5, va="top", linespacing=1.35)
    fig.text(27.0 / W_IN, 15.0 / H_IN, "Section cuts: A at the lounge / kitchen, B at the guest room,\n"
             "C along the lobby (see A-2). Heights above finished floor;\nexisting grade approximate (survey, assumed "
             f"floor {ff:.1f}').", fontsize=8.5, va="top")
    pdf.savefig(fig); fig.savefig(OUT / "A-5-sections.png", dpi=80); plt.close(fig)


# ---- A-6 fire-zone details -------------------------------------------------------------------
R337 = [
    ("R337.5", "Roof", "Class A asphalt shingles; eave and rake edges, ridge cap and the shed / gable junction\n"
                       "closed and sealed so embers can't get under them. Carport: standing seam, Class A."),
    ("R337.5.4", "Gutters", "Noncombustible gutter guards on all gutters."),
    ("R337.6", "Vents", "No attic or eave vents (sealed attic). Exhaust and hood terminations: listed\n"
                        "ember-resistant vents (ASTM E2886) or noncombustible 1/16\"-1/8\" mesh with dampers."),
    ("R337.7", "Exterior walls", "3-coat stucco (noncombustible). Porch cladding: noncombustible or\n"
                                 "ignition-resistant wood-look (fiber cement / porcelain)."),
    ("R337.7.5", "Eaves, soffits", "Enclosed soffits, noncombustible or ignition-resistant (fiber cement or metal);\n"
                                    "fascia dark metal. Porch ceiling the same."),
    ("R337.8.2", "Glazing", "Dual-pane, at least one tempered pane, all windows, doors, skylight, clerestory."),
    ("R337.8.3", "Exterior doors", "Noncombustible, ignition-resistant, or solid core at least 1-3/8\" thick."),
    ("R337.9", "Decks", "None. At-grade concrete landing and entry court only."),
    ("R337.10", "Carport, fences", "Carport roof Class A; framing within 5' of the house noncombustible\n"
                                    "or ignition-resistant. Fences and gates within 5' of the house noncombustible."),
    ("--", "Zone 0 (0-5')", "Noncombustible ground cover (gravel, pavers, concrete) within 5' of the house;\n"
                             "no bark mulch or plants against the walls."),
]


def detail_box(fig, left, bottom, w, h, title):
    ax = fig.add_axes([left / W_IN, bottom / H_IN, w / W_IN, h / H_IN])
    ax.set_xlim(0, w * 12); ax.set_ylim(0, h * 12); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((0.5, 0.5), w * 12 - 1, h * 12 - 1, fill=False, ec=INK, lw=0.8))
    ax.text(4, 4, title, fontsize=8, weight="bold")
    return ax


def details(pdf):
    fig = sheet("A-6", "FIRE-ZONE\nDETAILS\n(CRC R337)")
    # 1. enclosed eave at the street wall (schematic, not to scale)
    ax = detail_box(fig, 0.9, 13.0, 7.5, 9.8, "1  ENCLOSED EAVE (NO VENTS)   NTS")
    ax.add_patch(Rectangle((60, 6), 9, 82, fc="#ccc", ec=INK))                       # wall up to the soffit
    ax.add_patch(MPoly([(10, 82), (69, 92), (69, 100), (10, 90)], closed=True, fc="#666", ec=INK))   # roof slab
    ax.add_patch(MPoly([(10, 82), (60, 90.5), (60, 88), (14, 80.5)], closed=True, fc="#e8d5b5", ec=INK))  # soffit
    ax.add_patch(Rectangle((8, 78), 4, 13, fc="#222", ec=INK))                        # fascia
    for txt, (x, y) in {"Class A asphalt shingles on\ntwo layers of underlayment": (30, 104),
                        "Dark metal fascia\n+ drip edge": (2, 64), "Enclosed soffit, fiber cement\nor metal: NO VENTS": (14, 70),
                        "Stucco to the soffit,\nsealed at the joint": (72, 70), "Spray foam at the deck\n(sealed attic)": (72, 92)}.items():
        ax.text(x, y, txt, fontsize=7, va="top")
    # 2. wall base
    ax = detail_box(fig, 9.0, 13.0, 7.5, 9.8, "2  WALL BASE / WEEP SCREED   NTS")
    ax.add_patch(Rectangle((40, 30), 9, 70, fc="#ccc", ec=INK))
    ax.add_patch(Rectangle((10, 10), 70, 18, fc="#ddd", ec=INK))
    ax.plot([0, 40], [26, 26], color="#9a7b4f", lw=1.5)
    ax.plot([49, 90], [28, 28], color="#777", lw=3)
    for txt, (x, y) in {"Stucco on weather barrier": (52, 80), "Weep screed 4\" min. above earth,\n2\" min. above paving (CRC R703.7.2.1)": (52, 46),
                        "Gravel / pavers: noncombustible\n0-5' from the house": (2, 22), "Slab and footing\nper structural": (12, 18)}.items():
        ax.text(x, y, txt, fontsize=7, va="top")
    # 3. gutter
    ax = detail_box(fig, 17.1, 13.0, 7.5, 9.8, "3  REAR GUTTER   NTS")
    ax.add_patch(MPoly([(10, 70), (70, 80), (70, 86), (10, 76)], closed=True, fc="#666", ec=INK))
    ax.add_patch(Rectangle((60, 20), 9, 58, fc="#ccc", ec=INK))
    ax.add_patch(MPoly([(0, 60), (14, 60), (14, 72), (0, 72)], closed=True, fill=False, ec=INK, lw=1.4))
    ax.plot([0, 14], [74, 74], color=INK, lw=1, ls=":")
    for txt, (x, y) in {"Noncombustible gutter guard\n(CRC R337.5.4)": (2, 96), "Metal gutter + drip edge": (16, 62),
                        "Downspout to site drainage\n(per civil)": (2, 50)}.items():
        ax.text(x, y, txt, fontsize=7, va="top")
    # 4. exhaust terminations: roof cap (range hood, interior bath) and wall cap (rooms on an exterior wall)
    ax = detail_box(fig, 25.2, 13.0, 7.3, 9.8, "4  EXHAUST TERMINATIONS   NTS")
    ax.text(4, 112, "4a ROOF CAP: range hood; fans in rooms\nwith no exterior wall (common bath)", fontsize=7, va="top")
    ax.add_patch(MPoly([(4, 66), (84, 80), (84, 86), (4, 72)], closed=True, fc="#666", ec=INK))     # roof slab
    ax.add_patch(Rectangle((40, 40), 6, 44, fc="white", ec=INK, zorder=3))                          # duct through
    ax.add_patch(MPoly([(33, 84), (53, 84), (53, 91), (33, 91)], closed=True, fc="#999", ec=INK, zorder=4))  # cap
    ax.add_patch(MPoly([(34, 77.5), (52, 80.6), (52, 82), (34, 79)], closed=True, fc="#222", ec=INK, zorder=4))  # flashing
    ax.text(55, 92, "Listed ember-resistant roof cap\nwith back-draft damper\n(ASTM E2886)", fontsize=6.5, va="bottom")
    ax.annotate("Flashing", (36, 78.5), (8, 96), fontsize=6.5, arrowprops=dict(arrowstyle="-", lw=0.6))
    ax.text(48, 46, "Duct up from the\nhood or fan", fontsize=6.5, va="center")
    ax.plot([2, 86], [36, 36], color=INK, lw=0.5, ls=":")
    ax.text(4, 33, "4b WALL CAP: bath and laundry fans\non an exterior wall (no roof penetration)", fontsize=7, va="top")
    ax.add_patch(Rectangle((50, 4), 9, 20, fc="#ccc", ec=INK))                                        # wall (section)
    ax.add_patch(Rectangle((22, 12), 30, 5, fc="white", ec=INK))                                      # duct
    ax.add_patch(Rectangle((59, 9), 6, 11, fc="#999", ec=INK))                                        # cap
    ax.text(67, 14, "Ember-resistant wall cap\nwith damper", fontsize=6.5, va="center")
    ax.text(22, 21, "Duct from the fan", fontsize=6.5, va="bottom")
    table(fig, 0.9, 11.9, "WILDLAND-URBAN INTERFACE REQUIREMENTS (VERY HIGH FIRE HAZARD SEVERITY ZONE)",
          ("CRC", "ITEM", "THIS PROJECT"), (1.0, 1.6, 9.5), [(a, b, c) for a, b, c in R337], fs=7.5)
    pdf.savefig(fig); fig.savefig(OUT / "A-6-fire-details.png", dpi=80); plt.close(fig)


def cover_view():
    """A clean exterior view of the 3D model (no controls), for the cover; skipped without Chrome."""
    import subprocess
    chrome = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")
    html, png = S.RENDERS / "3d" / "house.html", OUT / "cover-3d.png"
    if not chrome.exists() or not html.exists():
        return png if png.exists() else None
    hook = "if (location.hash === '#touchwalk') startTouchWalk();"
    (cx, cy, cz), (tx, ty, tz) = (230, -330, 64), (760, 330, 80)
    src = html.read_text().replace(hook, hook + (
        "\norbit.enabled = false; groups.labels.visible = false;"
        "document.getElementById('ui').style.display='none'; document.getElementById('help').style.display='none';"
        f"camera.position.set({cx}*IN, {cz}*IN, {-cy}*IN); camera.lookAt({tx}*IN, {tz}*IN, {-ty}*IN);"))
    tmp = html.with_name("_cover.html")
    tmp.write_text(src)
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    subprocess.run([str(chrome), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                    "--window-size=1600,900", "--virtual-time-budget=15000", f"--screenshot={win(png)}",
                    "file:///" + win(tmp).replace("\\", "/") + "#roof"], capture_output=True)
    tmp.unlink()
    return png if png.exists() else None


# ---- A-7 attic and loads plan ---------------------------------------------------------------
RING_GAP = 20.0                                       # gym rings: 20" apart, side by side across the swing


def loads():
    """Where the special loads sit (plan inches): ring points, storage strip, air handler platform, PV."""
    gx0, gx1 = S.face("lounge|gym", +1), S.face("gym|ensuite", -1)
    gy0, gy1 = S.N_IN, S.face("bedroom hall wall", -1)
    cx, cy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
    rings = [(cx - RING_GAP / 2, cy), (cx + RING_GAP / 2, cy)]
    ahu = (S.HATCH_X - 15, 360.0, S.HATCH_X + 60, gy1)  # platform over the guest room, beside the hatch, near
                                                        # the gable's ridge (the wing's tallest attic)
    store = (gx0, S.N_IN + 24.0, gx1, gy1)              # over the gym, under the shed's tall attic
    return dict(gym=(gx0, gy0, gx1, gy1), rings=rings, ahu=ahu, store=store, pv=pv_area())


def pv_area():
    """Outline of the potential PV area (plan inches): the south-facing planes, clear of the shed's high-edge
    setback, the ridge setback and the pathways at both ends."""
    X0, X1, Y1 = S.E - X.EAVE + 36, S.W + X.EAVE - 36, S.S + X.EAVE
    return [(X0, S.N + 24), (X.WING_X, S.N + 24), (X.WING_X, X.RIDGE_Y + 18), (X1, X.RIDGE_Y + 18), (X1, Y1), (X0, Y1)]


def loads_plan(pdf):
    fig = sheet("A-7", "ATTIC AND\nSTRUCTURAL\nLOADS PLAN")
    sh = build_doc()
    x0, y0, x1, y1 = S.CARPORT[0] - 20, S.N - 120, S.W + 125, S.S + 110
    ax = scaled_axes(fig, 0.9, 9.6, x0, y0, x1, y1)
    Z.draw_dxf(ax, sh.doc, x0, y0, x1, y1)
    for art in ax.lines + ax.collections + ax.patches + ax.texts:      # plan as a faint background
        try:
            art.set_alpha(0.25)
        except Exception:
            pass
    L = loads()
    sx0, sy0, sx1, sy1 = L["store"]
    ax.add_patch(Rectangle((sx0, sy0), sx1 - sx0, sy1 - sy0, fc="#f3d9a6", ec="#b07a2a", lw=1.2, alpha=0.6, hatch="..",
                           zorder=4))
    ax.text((sx0 + sx1) / 2, S.N - 30, "ATTIC STORAGE (hatched): 20 PSF LIVE LOAD, PLYWOOD DECKED\n"
            f"(over the gym, under the shed: {ftin(sy0 - S.N_IN)} off the street wall to the hall wall)", fontsize=7,
            ha="center", zorder=6, bbox=dict(fc="white", ec="none", alpha=0.8))
    a0, b0, a1, b1 = L["ahu"]
    ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, fc="#cfe0f3", ec="#1f5e9e", lw=1.4, zorder=5))
    ax.text((a0 + a1) / 2, (b0 + b1) / 2, "AIR HANDLER\nON PLATFORM\n~250 LB", fontsize=6, ha="center", va="center",
            zorder=6)
    hx0, hy = S.HATCH_X, (S.face("bedroom hall wall", +1) + S.face("south hall wall", -1)) / 2
    ax.plot([S.face("lounge|gym", +1), S.W_IN], [hy, hy], color="#8e44ad", lw=1.4, ls=(0, (8, 4)), zorder=5)
    ax.text(S.face("lounge|gym", +1) + 6, hy + 4, "HALL CENTRELINE: KEEP CLEAR FOR RECESSED LIGHTS (note 7)",
            fontsize=6, color="#8e44ad", va="bottom", zorder=6)
    ax.add_patch(Rectangle((hx0, hy - 12.75), 54, 25.5, fill=False, ec=INK, lw=1.2, ls="--", zorder=5))
    ax.text(hx0 + 27, hy - 16, "ATTIC HATCH", fontsize=6, ha="center", va="top", zorder=6)
    ax.add_patch(Circle((S.HALL_TUBE, hy), 8, fill=False, ec=INK, lw=1.2, ls="--", zorder=5))
    ax.text(S.HALL_TUBE, hy - 12, "14\" SKYLIGHT TUBE\n(insulated, through the attic)", fontsize=5.5, ha="center",
            va="top", zorder=6, bbox=dict(fc="white", ec="none", alpha=0.8))
    for rx, ry in L["rings"]:
        ax.add_patch(Circle((rx, ry), 5, fc=RED, ec=INK, lw=0.8, zorder=7))
    (r0x, r0y), (r1x, r1y) = L["rings"]
    gx0, gy0, gx1, gy1 = L["gym"]
    ax.text((r0x + r1x) / 2, r0y - 12, "2 GYM RING POINTS\n500 LB EACH (CONCENTRATED)", fontsize=6.5, ha="center",
            va="top", color=RED, zorder=7)
    dim_string(ax, [gx0, r0x, r1x, gx1], gy0 + 16, color=RED, fs=6)
    dim_string(ax, [gy0, r0y, gy1], gx0 + 16, horiz=False, color=RED, fs=6)
    pv = L["pv"]
    ax.add_patch(MPoly(pv, closed=True, fill=False, ec="#2e7d32", lw=1.2, ls="-.", zorder=4))
    ax.text(pv[0][0] + 8, pv[-1][1] - 10, "FUTURE SOLAR PV AREA ON THE ROOF (dash-dot): allow ~3-4 PSF dead load", fontsize=6.5,
            color="#2e7d32", va="top", zorder=6)
    mx = [o for o in S.OPENINGS if o[0] == "pantry|laundry" and o[3] == "bifold"]
    ax.text(712, 585, "HEAT PUMP WATER\nHEATER, 80 GAL\n(~900 LB FULL, ON SLAB)", fontsize=5.5, ha="center", va="center",
            zorder=6, bbox=dict(fc="white", ec="none", alpha=0.8))
    ax.text((S.E + S.W) / 2, y0 + 8, "ATTIC AND LOADS PLAN   1/4\" = 1'-0\"", fontsize=12, weight="bold", ha="center")
    notes = ("LOAD NOTES (for the structural engineer and truss designer)\n"
             "1. Gym ring points: two eye bolts 20\" apart at the gym's centre,\n"
             "   rings swinging along the room's long (street-to-hall) direction.\n"
             "   500 lb concentrated at each, dynamic: blocking across several\n"
             "   trusses or joists with framing connectors; through-bolted forged\n"
             "   eye bolts with plate washers.\n"
             "2. Attic storage: 20 psf live load on the decked area shown\n"
             "   (hatched), over the gym, where the shed roof gives\n"
             "   the attic its height; light storage only. The rest of the\n"
             "   wing's attic, under the gable, is tallest along the ridge.\n"
             "3. Air handler: on a platform beside the attic hatch, near the\n"
             "   ridge, with a 30\" walkway, light and outlet (mechanical code).\n"
             "4. Future solar: on the roof plane, clear of the fire setbacks\n"
             "   (A-3); include its dead load in the roof design.\n"
             "5. Heat pump water heater: on the slab in the mechanical closet.\n"
             "6. Vaulted great room: no attic and no loads above the ceiling.\n"
             "7. Bedroom hall ceiling: keep the hall's centreline free of\n"
             "   blocking, strongbacks, ducts and pipes, so recessed lights\n"
             "   fit between the trusses along it (clear of the hatch, smoke\n"
             "   alarm and return grille). Run the duct trunk to one side.\n"
             "   The 14\" skylight tube takes the last spot, near the hall's end.")
    fig.text(27.0 / W_IN, 22.9 / H_IN, notes, fontsize=8.5, va="top", linespacing=1.35)
    pdf.savefig(fig); fig.savefig(OUT / "A-7-attic-loads.png", dpi=80); plt.close(fig)


# ---- A-0 cover -------------------------------------------------------------------------------
def cover(pdf):
    fig = sheet("A-0", "COVER SHEET,\nCODE ANALYSIS")
    fig.text(0.9 / W_IN, 22.6 / H_IN, "ACOSTA RESIDENCE", fontsize=34, weight="bold", va="top")
    fig.text(0.9 / W_IN, 21.5 / H_IN, "New single-family residence, Eaton Fire rebuild  ·  220 Laurel Dr, Altadena CA 91001",
             fontsize=14, va="top")
    img = cover_view()
    if img:
        a = fig.add_axes([0.9 / W_IN, 9.6 / H_IN, 15.5 / W_IN, 10.8 / H_IN]); a.axis("off")
        a.imshow(plt.imread(img)); a.set_title("3D massing, from the street (for reference)", fontsize=8, loc="left")
    sheets = [("A-0", "Cover sheet, code analysis"), ("A-1", "Site plan, project data"),
              ("A-2", "Floor plan, door and window schedules"), ("A-3", "Roof plan"), ("A-4", "Exterior elevations"),
              ("A-5", "Building sections"), ("A-6", "Fire-zone details (CRC R337)"),
              ("A-7", "Attic and structural loads plan"),
              ("S-", "Structural (by the structural engineer)"), ("C-", "Grading and drainage (by the civil engineer)"),
              ("T-24", "Energy compliance (CF1R) and solar PV (by the energy consultant)"),
              ("CALGreen", "Green building checklist")]
    y = table(fig, 17.3, 20.3, "SHEET INDEX", ("SHEET", "TITLE"), (1.2, 6.8), sheets, fs=8)
    deferred = [("1", "Fire sprinkler plans and calculations (NFPA 13D), before the final foundation inspection"),
                ("2", "Roof truss drawings and calculations (truss manufacturer), reviewed by the engineer of record"),
                ("3", "Solar PV plans, if not in the energy package")]
    y = table(fig, 17.3, y - 0.5, "DEFERRED SUBMITTALS", ("#", "ITEM"), (0.5, 7.5), deferred, fs=8)
    code = [("Codes", "2022 California Residential, Building, Electrical, Mechanical, Plumbing,\nEnergy, Fire and "
                      "Green Building Standards Codes, as allowed for fire rebuilds by Executive\nOrder N-29-25; "
                      "LA County Title 26 amendments"),
            ("Occupancy", "R-3 single-family dwelling; U open carport (attached)"),
            ("Construction", "Type V-B; automatic fire sprinklers throughout (NFPA 13D)"),
            ("Stories / height", f"1 story; ~{ftin(Z.TOP)} above finished floor (30' limit, Altadena CSD)"),
            ("Areas", f"Dwelling {Z.HOUSE:,.0f} sq ft · porch {Z.PORCH:,.0f} · carport {Z.CARPORT:,.0f} sq ft"),
            ("Lot / coverage", f"{Z.LOT_AREA:,.0f} sq ft · {Z.COVER:,.0f} sq ft ({Z.COVER / Z.LOT_AREA:.1%})"),
            ("Zoning", "R-1-7500 · Altadena CSD · Disaster Recovery Permit (non-like-for-like)"),
            ("Fire zone", "VHFHSZ: wildland-urban interface construction, CRC R337 (A-6)"),
            ("Energy", "All-electric; Title 24 Part 6 compliance by the energy consultant"),
            ("Green building", "CALGreen mandatory measures (checklist)")]
    y = table(fig, 17.3, y - 0.5, "CODE ANALYSIS", ("ITEM", "PROJECT"), (1.6, 6.4), code, fs=8)
    scope = ("SCOPE OF WORK\n"
             "New one-story, all-electric single-family residence (4 bedrooms, 3 baths) with an attached open\n"
             "carport, replacing the house destroyed in the Eaton Fire. Demolition of the remaining retaining\n"
             "wall and chimney, grading and drainage per civil, new driveway, utilities (water, sewer, electric;\n"
             "no gas). Fire sprinklers throughout.")
    fig.text(0.9 / W_IN, 8.9 / H_IN, scope, fontsize=9, va="top", linespacing=1.4)
    team = ("PROJECT TEAM\n"
            "Owner: Richard Acosta\n"
            "Plans prepared by: ______________________\n"
            "Structural engineer: ______________________\n"
            "Civil engineer: ______________________\n"
            "Energy consultant: ______________________\n"
            "Fire sprinkler designer: ______________________")
    fig.text(0.9 / W_IN, 6.2 / H_IN, team, fontsize=9, va="top", linespacing=1.5)
    gen = ("GENERAL NOTES\n"
           "1. Work shall comply with the codes listed and the conditions of approval.\n"
           "2. Do not scale drawings; dimensions govern. Verify on site.\n"
           "3. Structural, civil and energy documents govern their own scope.\n"
           "4. Special inspections and structural observation per the structural engineer.\n"
           "5. Smoke and CO alarms per A-2; fire sprinklers per the deferred submittal.")
    fig.text(9.0 / W_IN, 6.2 / H_IN, gen, fontsize=9, va="top", linespacing=1.5)
    pdf.savefig(fig); fig.savefig(OUT / "A-0-cover.png", dpi=80); plt.close(fig)


# ---- A-2 floor plan --------------------------------------------------------------------------
def floor_plan(pdf):
    fig = sheet("A-2", "FLOOR PLAN,\nDOOR & WINDOW\nSCHEDULES")
    sh = build_doc()
    rms = rooms(sh)
    x0, y0, x1, y1 = S.CARPORT[0] - 20, S.N - 150, S.W + 125, S.S + 130
    ax = scaled_axes(fig, 0.9, 9.6, x0, y0, x1, y1)
    Z.draw_dxf(ax, sh.doc, x0, y0, x1, y1)

    # dimension strings: openings, walls, overall (north and south); walls and overall (west, east)
    n_walls = [S.E, S.PORCH_X, 674.0, 826.0, 897.5, 1062.0, S.W]
    s_walls = [S.E, 674.0, 750.0, S.face("laundry|bath", -1) + S.WET / 2, 884.5, 1062.0, S.W]
    n_open = [v for o in S.OPENINGS if o[0] == "north" for v in o[1:3]]
    s_open = [v for o in S.OPENINGS if o[0] == "south" for v in o[1:3]]
    dim_string(ax, [S.PORCH_X, S.W] + n_open, S.N - 50)
    dim_string(ax, n_walls, S.N - 80)
    dim_string(ax, [S.E, S.W], S.N - 110)
    dim_string(ax, [S.E, S.W] + s_open, S.S + 50)
    dim_string(ax, s_walls, S.S + 80)
    dim_string(ax, [S.E, S.W], S.S + 110)
    dim_string(ax, [S.N, 403.2, 459.2, S.S], S.W + 50, horiz=False)
    dim_string(ax, [S.N, S.S], S.W + 85, horiz=False)
    ew = [v for o in S.OPENINGS if o[0] == "east" for v in o[1:3]]
    dim_string(ax, [S.PORCH_Y, S.S] + ew, S.E - 30, horiz=False)

    # door tags (circles) on the side the door doesn't swing to; window tags (hexagons) outside
    dsched = []
    placed = [(S.HALL_TUBE, (S.face("bedroom hall wall", +1) + S.face("south hall wall", -1)) / 2)]   # keep tags off the hall skylight
    for i, o in enumerate(doors(), 1):
        minus, plus = sides(o)
        a, b = room_at(rms, *minus), room_at(rms, *plus)
        if o[0] in S.EXT_WALLS:
            pt = plus if outward(o[0]) > 0 else minus
            pt = (pt[0] + (pt[0] - (o[1] + o[2]) / 2 if S.wall_info(o[0])[0] == "y" else 0) * 0, pt[1])
        else:
            swing = o[5] if len(o) > 5 else 1
            pt = minus if swing > 0 else plus
        along_x = S.wall_info(o[0])[0] == "x"
        other = plus if pt == minus else minus           # clear of other tags: this side, then the other side
        tries = [pt, other] + [(pt[0] + d, pt[1]) if along_x else (pt[0], pt[1] + d)   # then 20" steps either way
                               for n in range(1, 8) for d in (20 * n, -20 * n)]
        pt = next(p for p in tries if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= 18 ** 2 for q in placed))
        placed.append(pt)
        ax.add_patch(Circle(pt, 8, fc="white", ec=INK, lw=0.8, zorder=5))
        ax.text(*pt, str(i), fontsize=6.5, ha="center", va="center", zorder=6)
        w = 36.0 if o[0] == "porch front" else o[2] - o[1]    # front door 3'-0" in its opening
        ext = o[0] in S.EXT_WALLS
        if o[3] == "slider":
            h, typ = 96.0, "Sliding glass door"
        elif o[3] == "bifold":
            h, typ = DOOR_H, "Bifold, louvered"
        elif o[3] == "pocket":
            h, typ = DOOR_H, "Pocket"
        else:
            h, typ = DOOR_H, "Hinged"
        names = " / ".join(dict.fromkeys(n for n in (a, b) if n != "EXTERIOR")) or "-"
        if ext:
            names += " (exterior)"
        notes = []
        if o[3] == "slider":
            notes.append("Dual-pane tempered glazing (CRC R308.4.1, R337.8.2); weatherstripped")
        elif ext:
            notes.append("Solid core 1-3/8\"+ or noncombustible (CRC R337.8.3); weatherstripped")
            if o[0] == "porch front":
                notes.append("glass lite, if any, dual-pane tempered")
        if "MECH" in names:
            notes.append("louvered (water heater air)")
        dsched.append((str(i), names, f"{ftin(w)} x {ftin(h)}", typ, textwrap.fill("; ".join(notes), 95)))

    groups = {}
    for wall, a, b, sill, head, kind in windows():
        key = (round(b - a, 1), round(head - sill, 1), round(sill, 1), kind)
        groups.setdefault(key, []).append((wall, a, b, sill, head, kind))
    letters = iter("ABCDEFGHJKLMNP")
    wsched = []
    for key, items in groups.items():
        L = next(letters)
        rms_here = []
        for wall, a, b, sill, head, kind in items:
            o = (wall, a, b)
            minus, plus = sides(o)
            out = outward(wall) if wall in S.EXT_WALLS else 1
            inside = minus if out > 0 else plus
            outside = plus if out > 0 else minus
            rm = room_at(rms, *inside) if kind != "clerestory" else "LOUNGE"
            if kind == "interior":
                rm = f"{room_at(rms, *minus)} / {room_at(rms, *plus)}"
            rms_here.append(rm)
            if kind == "clerestory":
                outside = ((a + b) / 2 + 40, outside[1])
            elif any(d[0] == wall and d[1] < b and a < d[2] for d in doors()):   # transom over a door:
                along = 30.0                                                     # beside the door's tag
                outside = (outside[0], outside[1] + along) if S.wall_info(wall)[0] == "y" else (outside[0] + along, outside[1])
            pts = [(outside[0] + 9 * dx, outside[1] + 9 * dy) for dx, dy in
                   ((1, 0), (0.5, 0.87), (-0.5, 0.87), (-1, 0), (-0.5, -0.87), (0.5, -0.87))]
            ax.add_patch(MPoly(pts, closed=True, fc="white", ec=INK, lw=0.8, zorder=5))
            ax.text(*outside, L, fontsize=6.5, ha="center", va="center", zorder=6)
        w, h, sill, kind = key
        op, note = window_type(rms_here[0], w, h, sill, kind)
        where = ", ".join(dict.fromkeys(r.title() for r in rms_here))
        wsched.append((L, str(len(items)), where, f"{ftin(w)} x {ftin(h)}", ftin(sill), op, note))

    # smoke (SD) and combination smoke / carbon monoxide (SD/CO) alarms
    def alarm(x, y, lab):
        ax.add_patch(Circle((x, y), 7, fc="white", ec=RED, lw=1.0, zorder=5))
        ax.text(x, y, lab, fontsize=4.5, ha="center", va="center", color=RED, zorder=6)
    hall_y = (S.face("bedroom hall wall", +1) + S.face("south hall wall", -1)) / 2
    for nm, (x, y) in {"GYM": (760, 330), "GUEST": (980, 330), "OFFICE": (1140, 330), "PRIMARY": (1140, 540)}.items():
        alarm(x, y, "SD")
    alarm(S.HATCH_X - 24, hall_y + 15, "SD/\nCO")           # one, mid-lobby: within 21' of every bedroom door
    ax.text(S.HATCH_X + 27, hall_y + 15, "AIR HANDLER ABOVE (SEALED ATTIC)", fontsize=5,
            ha="center", va="bottom", color=INK)
    for x, y in ((560, 360), (430, 560), (610, 470)):
        pass
    ax.text(585, 445, "VAULTED CEILING\n(FOYER, LOUNGE, DINING, KITCHEN)", fontsize=6, ha="center", color="#555")
    ax.text((S.E + S.W) / 2, y0 + 6, "FLOOR PLAN   1/4\" = 1'-0\"", fontsize=12, weight="bold", ha="center")
    ax.annotate("", (S.W + 40, S.N - 110), (S.W + 40, S.N - 60), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(S.W + 48, S.N - 85, "PLAN\nNORTH\n(STREET)", fontsize=7, va="center")

    # notes and legend (right of the plan)
    notes = (
        "GENERAL NOTES\n"
        "1. Dimensions are to wall centrelines; exterior walls to\n   the outside face of framing + finish (9\" walls).\n"
        "2. Walls: exterior 2x6 with 1\" rigid insulation and stucco;\n   interior 2x4; plumbing walls 2x6.\n"
        "3. Ceilings 9'-0\" unless noted. The foyer, lounge, dining\n   and kitchen are vaulted under the roof (see sections).\n"
        "4. Doors 8'-0\" high unless noted; interior doors solid\n   core. Exterior doors and glazing per CRC R337 (VHFHSZ).\n"
        "5. All exterior glazing dual-pane with at least one tempered\n   pane (CRC R337.8.2.1). Fully tempered where noted\n   (CRC R308.4).\n"
        "6. Bedroom windows meet emergency escape: 5.7 sq ft net\n   clear, 20\" min width, 24\" min height, sill 44\" max\n   (CRC R310).\n"
        "7. Smoke alarms: hard-wired, interconnected, battery\n   backup, at least 3' from bathroom doors (CRC R314).\n   Combination smoke / CO alarms outside the sleeping areas.\n"
        "8. All-electric: heat pump HVAC (air handler in the sealed\n   attic; outdoor unit at the rear wall), heat pump water\n   heater (HPWH) in the mechanical closet. Whole-house\n   ventilation by a continuous exhaust fan.\n"
        "9. Fire sprinklers throughout (NFPA 13D); plans by the\n   sprinkler designer (deferred submittal).\n"
        "10. Attic access in the hall: 22\" x 54\" insulated, gasketed\n   access panel (passes the air handler), 30\" min headroom\n   above (CRC R807.1).\n"
        "11. Furniture not shown; closets, cabinets and fixtures\n   shown for reference.\n")
    fig.text(27.0 / W_IN, 22.9 / H_IN, notes, fontsize=8.5, va="top", linespacing=1.35)
    lg = fig.add_axes([27.0 / W_IN, 6.9 / H_IN, 5.5 / W_IN, 2.4 / H_IN]); lg.axis("off")
    lg.set_xlim(0, 55); lg.set_ylim(0, 24)
    lg.text(0, 23, "LEGEND", fontsize=9, weight="bold", va="top")
    lg.add_patch(Circle((3, 16), 1.6, fc="white", ec=INK)); lg.text(3, 16, "1", fontsize=6, ha="center", va="center")
    lg.text(7, 16, "Door tag (see door schedule)", fontsize=8, va="center")
    hx = [(3 + 1.8 * dx, 11 + 1.8 * dy) for dx, dy in ((1, 0), (0.5, .87), (-.5, .87), (-1, 0), (-.5, -.87), (.5, -.87))]
    lg.add_patch(MPoly(hx, closed=True, fc="white", ec=INK)); lg.text(3, 11, "A", fontsize=6, ha="center", va="center")
    lg.text(7, 11, "Window tag (see window schedule)", fontsize=8, va="center")
    lg.add_patch(Circle((3, 6), 1.6, fc="white", ec=RED)); lg.text(3, 6, "SD", fontsize=4.5, ha="center", va="center", color=RED)
    lg.text(7, 6, "Smoke alarm (SD), smoke / CO alarm (SD/CO)", fontsize=8, va="center")
    lg.plot([0.5, 5.5], [1.5, 1.5], ls="--", color=INK, lw=0.8)
    lg.text(7, 1.5, "Overhead: canopy, attic hatch, skylight", fontsize=8, va="center")

    # schedules (below the plan)
    table(fig, 0.9, 9.0, "DOOR SCHEDULE", ("TAG", "LOCATION", "SIZE (W x H)", "TYPE", "NOTES"),
          (0.45, 2.6, 1.15, 1.6, 6.2), dsched, fs=7)
    table(fig, 13.4, 9.0, "WINDOW SCHEDULE", ("TAG", "QTY", "LOCATION", "SIZE (W x H)", "SILL", "OPERATION", "NOTES"),
          (0.45, 0.45, 2.3, 1.15, 0.6, 2.0, 4.2), wsched, fs=7)
    pdf.savefig(fig)
    fig.savefig(OUT / "A-2-floor-plan.png", dpi=80)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUT / "architectural-set.pdf") as pdf:
        cover(pdf)
        site_plan(pdf)
        floor_plan(pdf)
        roof_plan(pdf)
        elevations(pdf)
        sections(pdf)
        details(pdf)
        loads_plan(pdf)
    print("  ", (OUT / "architectural-set.pdf").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
