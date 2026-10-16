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
    if S.face("bedroom hall wall", +1) < y < S.face("south hall wall", -1) and x > S.face("lounge|gym", +1):
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
    ws = [(o[0], o[1], o[2], *(o[4:6] if len(o) > 4 else (30.0, 96.0)), "window")
          for o in S.OPENINGS if o[3] in ("window", "transom")]
    lx0, lx1 = X.LOUNGE_X                                                 # clerestory, above the lounge window
    ws.append(("north", lx0, lx1, X.CLERESTORY_SILL, X.CLERESTORY_SILL + 36.0, "clerestory"))
    return ws


def window_type(rm, w, h, sill, kind):
    """(operation, notes) for the schedule: notes only where something is required."""
    if kind == "clerestory":
        return "Fixed (mulled units)", "Clerestory"
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
    if rm == "LOBBY":
        return "Fixed transom", ""
    if "ENSUITE" in rm:
        return "Awning", "Obscure glass"
    return "Awning", ""


CASEWORK_WORDS = {"HANG", "SHELVES", "SHELVES ABOVE", "SHELVES TO 6'", "DRAWERS", "LINEN", "BENCH", "BEV",
                  "TALL STORAGE", "TRASH", "ON PEDESTAL", "HIGH WINDOW", "FOLDING COUNTER", "CEILING AIRER",
                  "LEDGE", "CURBLESS"}
KEEP_OUTSIDE = {"CARPORT", "18' x 18'", "CONDENSER", "PORCH", "WOOD-LOOK FEATURE WALL"}


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
               if e.dxf.text in ("CL", "CLOSET")]
    for e in list(sh.msp):
        lay, kind = e.dxf.layer, e.dxftype()
        txt = e.dxf.text if kind == "TEXT" else None
        bb = bbox.extents([e])
        geo = box(bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y) if bb.has_data else None
        gone = (id(e) in drop or lay in ("A-ANNO-DIMS", "L-PLNT", "A-FENC", "C-PROP")
                or (lay == "A-FURN" and not (geo and any(geo.buffer(1).contains(Point(p)) for p in closets)))
                or (txt in CASEWORK_WORDS) or (txt and "FENCE" in txt) or (lay == "A-CLNG" and txt == "CEILING AIRER"))
        if (not gone and lay == "A-WALL" and geo is not None and geo.area > 0
                and geo.intersection(house).area < 0.5 * geo.area and not geo.within(carport)):
            gone = True                                                # the entry court's seat wall
        if not gone and geo is not None and not geo.intersects(house) and txt not in KEEP_OUTSIDE:
            gone = not (geo.within(carport) or lay == "A-EQPM" or (lay == "L-SITE" and geo.within(carport)))
        if lay == "L-SITE" and not (geo and geo.within(carport)):
            gone = True
        if gone:
            sh.msp.delete_entity(e)
    for e in list(sh.msp.query("LWPOLYLINE[layer=='A-CLNG']")):    # the airer's dashed outline
        bb = bbox.extents([e])
        if bb.size.y > 50 and bb.size.x < 30:
            sh.msp.delete_entity(e)
    return sh


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
    dsched, placed = [], []
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
        while any((pt[0] - q[0]) ** 2 + (pt[1] - q[1]) ** 2 < 18 ** 2 for q in placed):   # clear of other tags
            pt = (pt[0] + 20, pt[1]) if along_x else (pt[0], pt[1] + 20)
        placed.append(pt)
        ax.add_patch(Circle(pt, 8, fc="white", ec=INK, lw=0.8, zorder=5))
        ax.text(*pt, str(i), fontsize=6.5, ha="center", va="center", zorder=6)
        w = 36.0 if o[0] == "porch front" else o[2] - o[1]    # front door 3'-0" in its opening
        ext = o[0] in S.EXT_WALLS
        if o[3] == "slider":
            h, typ = 96.0, "Sliding glass door"
        elif o[0] == "west":
            h, typ = 84.0, "Hinged"
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
        if o[0] == "west":
            notes.append("solid slab, no glass; fixed transom above")
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
            out = outward(wall)
            inside = minus if out > 0 else plus
            outside = plus if out > 0 else minus
            rm = room_at(rms, *inside) if kind != "clerestory" else "LOUNGE"
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
    alarm(955, hall_y + 15, "SD/\nCO")           # one, mid-lobby: within 21' of every bedroom door
    ax.text(990 + 27, hall_y + 15, "AIR HANDLER ABOVE (SEALED ATTIC)", fontsize=5,
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
        "10. Attic access: 22\" x 54\" pull-down ladder in the hall,\n   30\" min headroom above (CRC R807.1).\n"
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
    lg.text(7, 1.5, "Overhead: band, canopy, attic hatch, skylight", fontsize=8, va="center")

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
        floor_plan(pdf)
    print("  ", (OUT / "architectural-set.pdf").relative_to(S.ROOT))


if __name__ == "__main__":
    main()
