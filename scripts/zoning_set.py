# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Preliminary zoning check set (owner-prepared, not for construction), from the schematic and the
main plan's exterior: site plan with setbacks and project data, floor plan with areas, roof plan,
and four elevations with heights.

Writes renders/zoning/zoning-check-set.pdf (11x17 sheets) and a PNG of each sheet.

    uv run scripts/zoning_set.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exterior as X  # noqa: E402
import make_3d as M  # noqa: E402
import schematic as S  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Polygon as MPoly, Rectangle  # noqa: E402

OUT = S.RENDERS / "zoning"
DATE = "October 15, 2026"
PROJECT = "Single-family residence rebuild (Eaton Fire), 220 Laurel Dr, Altadena CA 91001"
APN = "APN 5832-003-027"
OWNER = "Owner: Richard Acosta"
PITCH = 2 / 12
UNDER = X.shed_vault_under(PITCH)              # underside of the shed's framing at plan y
GABLE = X.gable_under(PITCH)                   # and of the bedroom wing's gable (west of X.WING_X)
THK, OV = X.THK, X.EAVE                        # roof framing depth, eave overhang
INK, SOFT = "#222", "#888"


def save_png(fig, path, dpi):
    """Save a sheet image; if Windows has the file open (locked), write a timestamped copy beside it."""
    try:
        fig.savefig(path, dpi=dpi)
    except OSError:
        import time
        alt = path.with_name(f"{path.stem}-{time.strftime('%H%M%S')}{path.suffix}")
        fig.savefig(alt, dpi=dpi)
        print("   locked:", path.name, "-> wrote", alt.name)


def ftin(v):
    """Inches -> 12'-3 1/4" style."""
    neg, v = v < 0, abs(v)
    q = round(v * 8) / 8
    ft, inch = divmod(q, 12)
    whole, frac = int(inch), inch - int(inch)
    f = {0.125: "⅛", 0.25: "¼", 0.375: "⅜", 0.5: "½", 0.625: "⅝", 0.75: "¾", 0.875: "⅞"}.get(round(frac, 3), "")
    return f"{'-' if neg else ''}{int(ft)}'-{whole}{f}\""


# ---- numbers ------------------------------------------------------------------------------
LOT_W_FT, LOT_D_FT = S.LOT_W / 12, S.LOT_D / 12
LOT_AREA = LOT_W_FT * LOT_D_FT
FOOT = [(S.E, S.PORCH_Y), (S.PORCH_X, S.PORCH_Y), (S.PORCH_X, S.N), (S.W, S.N), (S.W, S.S), (S.E, S.S)]


def poly_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


HOUSE = poly_area(FOOT) / 144
PORCH = ((S.PORCH_X - S.E) * (S.PORCH_Y - S.N) + (S.PORCH_X - S.PORCH_OUT[0]) * S.PORCH_FWD) / 144   # the strip in
                                                 # the carport's walkway is counted with the carport
cx0, cy0, cx1, cy1 = S.CARPORT
CARPORT = (cx1 - cx0) * (cy1 - cy0) / 144
COVER = HOUSE + PORCH + CARPORT
LIMIT = LOT_AREA / 4 + 1000                      # Altadena CSD: 1/4 net lot area + 1,000 sq ft
SIDE_REQ = 0.10 * LOT_W_FT * 12
REAR_REQ = 0.20 * S.LOT_D                         # shallow lot (< 75' deep): 20% of depth, §22.110.080.D
SETBACKS = [   # (label, required, provided) in inches
    ("Front (street)", 240.0, S.N),
    ("Rear (§22.110.080.D)", REAR_REQ, S.LOT_D - S.S),
    ("Side, west", SIDE_REQ, S.LOT_X0 + S.LOT_W - S.W),
    ("Side, east (carport)", SIDE_REQ, cx0 - S.LOT_X0),
]
TOP = UNDER(S.N - OV) + THK                      # highest point: roof top at the street fascia
REAR_TOP = UNDER(S.S + OV) + THK
RIDGE_TOP = GABLE(X.RIDGE_Y) + THK               # the wing's ridge
WING_EAVE_TOP = GABLE(S.N - OV) + THK            # the wing's street eave


def glass_total():
    tot = 0.0
    for o in S.OPENINGS:
        if o[0] in S.EXT_WALLS and o[3] in ("window", "slider", "transom"):
            h = 96.0 if o[3] == "slider" else (o[5] - o[4] if len(o) > 4 else 66.0)
            tot += (o[2] - o[1]) * h / 144
    lx0, lx1 = X.CLERESTORY_X
    return tot + (lx1 - lx0) * 36 / 144


# ---- sheet frame ----------------------------------------------------------------------------
def sheet(num, title):
    fig = plt.figure(figsize=(17, 11))
    fig.add_artist(Rectangle((0.01, 0.015), 0.98, 0.97, transform=fig.transFigure, fill=False, lw=1.2))
    fig.add_artist(Rectangle((0.01, 0.015), 0.98, 0.07, transform=fig.transFigure, fill=False, lw=1.0))
    fig.text(0.02, 0.06, PROJECT, fontsize=11, weight="bold")
    fig.text(0.02, 0.035, f"{APN}   ·   Zone R-1, Altadena Community Standards District   ·   {OWNER}", fontsize=9)
    fig.text(0.47, 0.019, S.NOTICE, fontsize=7, color="#555")
    fig.text(0.47, 0.06, "PRELIMINARY ZONING CHECK SET — OWNER-PREPARED, NOT FOR CONSTRUCTION",
             fontsize=8.5, color="#a33")
    fig.text(0.47, 0.035, f"{DATE}  ·  Dimensions in feet-inches  ·  Plan north = street side", fontsize=8.5)
    fig.text(0.975, 0.045, f"{num}", fontsize=22, weight="bold", ha="right", va="center")
    fig.text(0.925, 0.045, title, fontsize=11, ha="right", va="center")
    return fig


def clean_plan_doc(furniture=False):
    """The schematic's DXF without furniture, fixtures and fixture labels inside the house."""
    sh = S.build()
    drop = {"A-CLNG", "A-FENC"} | ({"A-FURN", "A-EQPM"} if not furniture else set())   # fences and gates: later
    for e in list(sh.msp):
        lay = e.dxf.layer
        if lay in drop or (e.dxftype() == "TEXT" and ("FENCE" in e.dxf.text or e.dxf.text.startswith("\u00a9"))):
            sh.msp.delete_entity(e)
        elif lay == "A-ANNO-TEXT" and e.dxftype() == "TEXT":
            p = e.dxf.insert
            if S.E < p.x < S.W and S.N < p.y < S.S:
                sh.msp.delete_entity(e)
    return sh


def draw_dxf(ax, doc, x0, y0, x1, y1):
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK,
                        lineweight_scaling=1.0)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace(), finalize=False)
    ax.set_aspect("equal", adjustable="box"); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")


def dim(ax, a, b, text, off=(0, 0), color="#c0392b", fs=8.5, rot=0):
    (ax0, ay0), (bx0, by0) = a, b
    ax.annotate("", (ax0, ay0), (bx0, by0), arrowprops=dict(arrowstyle="<->", color=color, lw=0.9))
    ax.text((ax0 + bx0) / 2 + off[0], (ay0 + by0) / 2 + off[1], text, color=color, fontsize=fs,
            ha="center", va="center", rotation=rot, bbox=dict(fc="white", ec="none", pad=0.6))


# ---- Z-1 site plan ----------------------------------------------------------------------------
def site_plan(pdf):
    fig = sheet("Z-1", "Site plan & project data")
    ax = fig.add_axes([0.02, 0.1, 0.66, 0.86])
    sh = clean_plan_doc()
    draw_dxf(ax, sh.doc, S.LOT_X0 - 40, -200, S.LOT_X0 + S.LOT_W + 60, S.LOT_D + 60)
    xm = 950.0                                                     # dimension column in front of the bedrooms
    dim(ax, (xm, 0), (xm, S.N), f"FRONT {ftin(S.N)}\n(20'-0\" req.)", rot=90)
    ax.annotate("", (xm, S.S), (xm, S.LOT_D), arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=0.9))
    ax.text(xm + 12, (S.S + S.LOT_D) / 2, f"REAR {ftin(S.LOT_D - S.S)}\n({ftin(REAR_REQ)} req., note 2)",
            color="#c0392b", fontsize=8.5, ha="left", va="center")       # beside the arrows: the yard is shallow
    yw = 430.0
    dim(ax, (S.W, yw), (S.LOT_X0 + S.LOT_W, yw), f"{ftin(S.LOT_X0 + S.LOT_W - S.W)}\n({ftin(SIDE_REQ)} req.)", rot=90)
    dim(ax, (S.LOT_X0, 485), (cx0, 485), f"{ftin(cx0 - S.LOT_X0)}\n({ftin(SIDE_REQ)} req.)", off=(0, 0))
    ax.text((S.E + S.W) / 2, -120, "LAUREL DRIVE (50' R/W)", fontsize=10, ha="center", weight="bold")
    ax.text(S.LOT_X0 + S.LOT_W / 2, S.LOT_D + 40,
            "Front-yard walls: entry seat wall 24\" (under the 42\" limit).",
            fontsize=7.5, ha="center", color="#555")
    # data table
    tx = fig.add_axes([0.70, 0.1, 0.28, 0.86]); tx.axis("off")
    rows = [
        ("PROJECT DATA", ""),
        ("Scope", "Non-like-for-like rebuild, 1-story SFR\n+ attached carport (Eaton Fire)"),
        ("Zone / overlay", "R-1 · Altadena CSD · VHFHSZ"),
        ("Lot", f"{LOT_W_FT:.2f}' x {LOT_D_FT:.2f}' = {LOT_AREA:,.0f} sq ft"),
        ("Floor area (to outside of walls)", f"{HOUSE:,.0f} sq ft"),
        ("Covered porch", f"{PORCH:,.0f} sq ft"),
        ("Carport (attached, open)", f"{CARPORT:,.0f} sq ft"),
        ("Lot coverage", f"{COVER:,.0f} sq ft ({COVER / LOT_AREA:.1%})"),
        ("CSD limit (¼ lot + 1,000)", f"{LIMIT:,.0f} sq ft (coverage and floor area)"),
        ("Stories / max height", f"1 story · ~{ftin(TOP)} above finished floor\n(top of roof at the street eave)"),
        ("Bedrooms / baths", "4 / 3"),
        ("Parking", f"2 covered, 8'-6\" x 18'-0\" each, behind the front\ndoor; the carport's front "
                    f"{ftin(S.CARPORT_WALK)} is a covered\nwalkway, not parking (8' x 5' covered porch)"),
        ("", ""),
        ("SETBACKS", "required  ·  provided"),
    ] + [(n, f"{ftin(r)}  ·  {ftin(p)}") for n, r, p in SETBACKS] + [
        ("", ""),
        ("Glazing (Title 24 check)", f"~{glass_total():,.0f} sq ft (~{glass_total() / HOUSE:.1%} of floor)"),
    ]
    y = 0.98
    for k, v in rows:
        bold = v == "" or k in ("PROJECT DATA", "SETBACKS")
        tx.text(0.0, y, k, fontsize=9, weight="bold" if bold else "normal", va="top", transform=tx.transAxes)
        tx.text(1.0, y, v, fontsize=9, ha="right", va="top", transform=tx.transAxes)
        y -= 0.036 if "\n" not in v else 0.058
    notes = ("NOTES\n"
             "1. Setbacks measured to the outside face of exterior walls (eaves excluded).\n"
             "2. Side setback taken as 10% of lot width. Rear yard on a shallow lot (§22.110.080.D):\n"
             f"   the lot is {LOT_D_FT:.2f}' deep (under 75'), so the rear yard is 20% of the average\n"
             f"   depth, {ftin(REAR_REQ)}. Please confirm it applies under the Altadena CSD.\n"
             "3. Heights are above finished floor; the lot falls ~4' across the footprint, so\n"
             "   height above grade depends on the foundation design (to be set with the civil).\n"
             "4. Lot lines, lot dimensions and existing trees are from the owner's topographic\n"
             "   survey (available on request).\n"
             f"5. Eaves {ftin(OV)} all round: the most an eave may project into a required yard\n"
             "   (§22.110.090.A); more than 2'-6\" from every lot line, no supports in the yards.\n"
             f"6. Rear window canopies {ftin(S.CANOPY_D)} deep (§22.110.090.B: up to 5' into the rear yard):\n"
             "   over the windows only, 1' past each side, no supports in the yard.\n"
             f"7. Covered entry porch 8'-0\" x 5'-0\" (Table 22.140.520-D), {ftin(S.PORCH_FWD)} into the front yard under a\n"
             "   9' canopy (§22.110.090.D.2 allows 5'); parking sits behind the front door.")
    tx.text(0.0, y - 0.01, notes, fontsize=6.9, va="top", transform=tx.transAxes, linespacing=1.25)
    pdf.savefig(fig); save_png(fig, OUT / "Z-1-site-plan.png", dpi=110); plt.close(fig)


# ---- Z-2 floor plan ---------------------------------------------------------------------------------
def floor_plan(pdf):
    fig = sheet("Z-2", "Floor plan & areas")
    ax = fig.add_axes([0.02, 0.1, 0.96, 0.86])
    sh = clean_plan_doc()
    draw_dxf(ax, sh.doc, S.CARPORT[0] - 40, S.N - 90, S.W + 60, S.S + 70)
    dim(ax, (S.E, S.S + 40), (S.W, S.S + 40), ftin(S.W - S.E))
    dim(ax, (cx0, S.N - 40), (cx1, S.N - 40), ftin(cx1 - cx0) + " carport")
    ax.text((S.E + S.W) / 2, S.N - 70,
            f"Floor area {HOUSE:,.0f} sq ft (to outside of walls)  ·  covered porch {PORCH:,.0f} sq ft  ·  "
            f"carport {CARPORT:,.0f} sq ft  ·  room sizes are clear dimensions", fontsize=9, ha="center")
    pdf.savefig(fig); save_png(fig, OUT / "Z-2-floor-plan.png", dpi=110); plt.close(fig)


# ---- Z-3 roof plan --------------------------------------------------------------------------------
def roof_plan(pdf):
    fig = sheet("Z-3", "Roof plan")
    ax = fig.add_axes([0.04, 0.12, 0.92, 0.82])
    X0, X1, Y0, Y1 = S.E - OV, S.W + OV, S.N - OV, S.S + OV
    ax.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fc="#e9e9e9", ec=INK, lw=1.4))
    ax.add_patch(MPoly(FOOT, closed=True, fill=False, ec=SOFT, ls="--", lw=0.8))
    ax.add_patch(Rectangle((cx0 - 6, cy0 - 6), cx1 - cx0 + 6, cy1 - cy0 + 12, fc="#f6f6f6", ec=INK, lw=1.0))
    wx, ry = X.WING_X, X.RIDGE_Y
    ax.plot([wx, wx], [Y0, Y1], color=INK, lw=1.0)                       # shed / gable line
    ax.plot([wx, X1], [ry, ry], color=INK, lw=1.4)                       # the wing's ridge
    for xx in (420, 700):                                                # shed: down to the rear
        ax.annotate("", (xx, Y1 - 20), (xx, Y0 + 40), arrowprops=dict(arrowstyle="->", lw=1.2))
    for xx in (930, 1150):                                               # gable: down each way from the ridge
        ax.annotate("", (xx, Y1 - 20), (xx, ry + 10), arrowprops=dict(arrowstyle="->", lw=1.2))
        ax.annotate("", (xx, Y0 + 20), (xx, ry - 10), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text((X0 + wx) / 2, (Y0 + Y1) / 2 - 40, "SHED 2:12, DOWN TOWARD THE REAR\n"
            f"high edge at the street (top ~{ftin(TOP)}),\nlow edge at the rear (top ~{ftin(REAR_TOP)})",
            ha="center", va="center", fontsize=8.5, bbox=dict(fc="white", ec="none"))
    ax.text((wx + X1) / 2, ry - 60, f"GABLE 2:12, RIDGE ~{ftin(RIDGE_TOP)}", ha="center", va="center", fontsize=8.5,
            bbox=dict(fc="white", ec="none"))
    ax.text((X0 + X1) / 2, Y1 + 50, "Class A asphalt shingles · heights above finished floor · "
            f"{ftin(OV)} eaves all round (max. 2'-6\" into a required yard, §22.110.090.A) · "
            "gutter along the rear edge (none on the wing's street eave)", ha="center", fontsize=8.5)
    ax.annotate("", (cx0 + 10, (cy0 + cy1) / 2), (cx1 - 20, (cy0 + cy1) / 2), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text((cx0 + cx1) / 2, (cy0 + cy1) / 2 + 22, "CARPORT ROOF\n½\":12, slopes away from house\nstanding-seam metal\n"
            "gutter on east edge", ha="center", fontsize=7.5)
    ax.text(X0, Y0 - 25, "STREET (PLAN NORTH)", fontsize=9, weight="bold")
    dim(ax, (X0, Y1 + 25), (X1, Y1 + 25), ftin(X1 - X0) + " to fascia")
    dim(ax, (X1 + 30, Y0), (X1 + 30, Y1), ftin(Y1 - Y0) + " to fascia", rot=90)
    ax.set_aspect("equal"); ax.set_xlim(cx0 - 60, X1 + 80); ax.set_ylim(Y0 - 60, Y1 + 80); ax.axis("off")
    pdf.savefig(fig); save_png(fig, OUT / "Z-3-roof-plan.png", dpi=110); plt.close(fig)


# ---- Z-4 elevations -------------------------------------------------------------------------------
def openings_on(wall):
    for o in S.OPENINGS:
        if o[0] != wall:
            continue
        k = o[3]
        if k == "window":
            z0, z1 = (o[4], o[5]) if len(o) > 4 else (M.SILL, M.HEAD)
        elif k == "transom":
            z0, z1 = o[4], o[5]
        elif k == "slider":
            z0, z1 = 0, M.HEAD
        elif k == "door":
            z0, z1 = 0, (84.0 if any(p[0] == wall and p[3] == "transom" for p in S.OPENINGS) else M.HEAD)
        else:
            continue
        yield o[1], o[2], z0, z1, k


WOOD = "#b07a4f"
PORCH_CEIL = M.CEIL                                    # the porch's own ceiling, 9'-0"


def elevation(ax, side):
    """side: north | south | east | west. Horizontal axis runs left-to-right as seen from outside."""
    flip = side in ("south", "east")
    h = (lambda u: -u) if flip else (lambda u: u)
    if side in ("north", "south"):
        a, b = S.E, S.W
        wall_top = UNDER(S.N) if side == "north" else UNDER(S.S)
        za = UNDER(S.N - OV) if side == "north" else UNDER(S.S + OV)
        if side == "north":                                        # shed block, then the wing's gable beside it
            wx = X.WING_X
            ax.add_patch(Rectangle((h(a), 0), wx - a, wall_top, fc="#efe9df", ec=INK, lw=1.2))
            ax.add_patch(Rectangle((h(wx), 0), b - wx, X.PLATE, fc="#efe9df", ec=INK, lw=1.2))
            ax.add_patch(Rectangle((h(wx), GABLE(S.N - OV)), b + OV - wx, RIDGE_TOP - GABLE(S.N - OV),
                                   fc="#55595e", ec=INK, lw=0.8))        # the gable's street slope, seen face-on
            ax.add_patch(Rectangle((h(wx), GABLE(S.N - OV)), b + OV - wx, THK, fc="#3c3f44", ec=INK))
            ax.add_patch(Rectangle((h(a - OV), za), wx - a + OV, THK, fc="#3c3f44", ec=INK))
        else:                                                      # rear: one plane, shed and gable alike
            ax.add_patch(Rectangle((min(h(a), h(b)), 0), b - a, wall_top, fc="#efe9df", ec=INK, lw=1.2))
            ax.add_patch(Rectangle((min(h(a - OV), h(b + OV)), za), b - a + 2 * OV, THK, fc="#3c3f44", ec=INK))
        if side == "north":
            ax.add_patch(Rectangle((h(a), 0), S.PORCH_X - a, PORCH_CEIL, fc=WOOD, ec=INK, lw=0.8))   # porch: its
            ax.add_patch(Rectangle((h(a), 0), 6, PORCH_CEIL, fc=INK))       # wood-look back wall under its own
            ox = S.PORCH_OUT[0]
            ax.add_patch(Rectangle((h(ox), PORCH_CEIL), S.PORCH_X - ox, 3, fc=INK))   # canopy over its front
            ax.annotate("Porch: wood-look walls and ceiling,\nits own 9'-0\" ceiling", (h(a) + 17, PORCH_CEIL - 30),
                        (h(a) - 140, PORCH_CEIL + 45), fontsize=6.5, ha="center",
                        arrowprops=dict(arrowstyle="-", lw=0.6))
            for x0, x1, z0, z1, k in openings_on("porch front"):
                ax.add_patch(Rectangle((h(x0), z0), x1 - x0, z1 - z0, fc="#d9792b" if k == "door" else "#bfe3f2",
                                       ec=INK, lw=0.8))
            lx0, lx1 = X.CLERESTORY_X
            g0 = X.PLATE + (wall_top - X.PLATE - 36) / 2
            ax.add_patch(Rectangle((h(lx0), g0), lx1 - lx0, 36, fc="#bfe3f2", ec=INK, lw=0.8))   # clerestory
            for k in range(1, X.CLERESTORY_UNITS):                                            # mullions
                mx = lx0 + k * X.CLERESTORY_UNIT
                ax.plot([h(mx), h(mx)], [g0, g0 + 36], color=INK, lw=0.6)
            ax.add_patch(Rectangle((h(cx0), 0), 6, 108, fc=INK)); ax.add_patch(Rectangle((h(cx0 - 6), 108), cx1 - cx0 + 6, 4, fc=INK))
        else:
            ax.add_patch(Rectangle((h(cx1), 108), cx1 - cx0 + 6, 4, fc=INK))
            ax.add_patch(Rectangle((h(cx0) - 6, 0), 6, 108, fc=INK))
        for x0, x1, z0, z1, k in openings_on(side):
            ax.add_patch(Rectangle((min(h(x0), h(x1)), z0), x1 - x0, z1 - z0, fc="#bfe3f2", ec=INK, lw=0.8))
        for _, x0, x1 in S.canopies(side):                         # window canopies
            ax.add_patch(Rectangle((min(h(x0), h(x1)), S.CANOPY_Z), x1 - x0, 3, fc=INK))
        if side == "north":
            xm = (1101.6 + 1173.6) / 2                             # the office window
            ax.annotate(f"windows recessed {S.WINDOW_RECESS:.0f}\" (typ.)", (h(xm), 96.0), (h(xm) + 70, 110.0),
                        fontsize=6.5, ha="center", arrowprops=dict(arrowstyle="-", lw=0.6))
        lo, hi = min(h(a - OV), h(b + OV)), max(h(a - OV), h(b + OV))
    else:
        a, b = S.N, S.S
        hy = (lambda y: y) if side == "west" else (lambda y: -y)
        pts = [(hy(a), 0), (hy(a), UNDER(a)), (hy(b), UNDER(b)), (hy(b), 0)]
        roof = [(hy(a - OV), UNDER(a - OV)), (hy(b + OV), UNDER(b + OV)), (hy(b + OV), UNDER(b + OV) + THK),
                (hy(a - OV), UNDER(a - OV) + THK)]
        if side == "west":                                         # the shed beyond, then the gable end
            ax.add_patch(MPoly(pts, closed=True, fc="#e2dccf", ec=INK, lw=0.8))
            ax.add_patch(MPoly(roof, closed=True, fc="#5a5e63", ec=INK, lw=0.8))
            ry = X.RIDGE_Y
            ax.add_patch(MPoly([(hy(a), 0), (hy(a), GABLE(a)), (hy(ry), GABLE(ry)), (hy(b), GABLE(b)), (hy(b), 0)],
                               closed=True, fc="#efe9df", ec=INK, lw=1.2))
            for e in (a - OV, b + OV):
                ax.add_patch(MPoly([(hy(e), GABLE(e)), (hy(ry), GABLE(ry)), (hy(ry), GABLE(ry) + THK),
                                    (hy(e), GABLE(e) + THK)], closed=True, fc="#3c3f44", ec=INK))
        else:
            ax.add_patch(MPoly(pts, closed=True, fc="#efe9df", ec=INK, lw=1.2))
            ax.add_patch(MPoly(roof, closed=True, fc="#3c3f44", ec=INK))
        for x0, x1, z0, z1, k in openings_on(side):
            ax.add_patch(Rectangle((min(hy(x0), hy(x1)), z0), x1 - x0, z1 - z0, fc="#bfe3f2", ec=INK, lw=0.8))
        if side == "east":                                         # into the porch: wood-look side wall,
            ax.add_patch(Rectangle((min(hy(S.N), hy(S.PORCH_Y)), 0), S.PORCH_Y - S.N, PORCH_CEIL,   # reeded window
                                   fc=WOOD, ec=INK, lw=0.8))
            for y0, y1, z0, z1, k in openings_on("porch side"):
                ax.add_patch(Rectangle((min(hy(y0), hy(y1)), z0), y1 - y0, z1 - z0, fc="#bfe3f2", ec=INK, lw=0.8))
            ax.add_patch(Rectangle((min(hy(S.N), hy(S.N + 6)), 0), 6, PORCH_CEIL, fc=INK))      # porch corner post
            ax.add_patch(Rectangle((min(hy(S.PORCH_OUT[1]), hy(S.N)), PORCH_CEIL), S.PORCH_FWD, 3, fc=INK))   # canopy
        ax.add_patch(Rectangle((min(hy(b), hy(b + S.CANOPY_D)), S.CANOPY_Z), S.CANOPY_D, 3, fc=INK))   # rear canopy, end-on
        if side == "east":                                         # carport in front: posts + roof
            for yy in (cy0, cy1 - 6):
                ax.add_patch(Rectangle((min(hy(yy), hy(yy + 6)), 0), 6, 108, fc=INK))
            ax.add_patch(Rectangle((min(hy(cy0 - 6), hy(cy1 + 6)), 108), cy1 - cy0 + 12, 4, fc=INK))
        lo, hi = min(hy(a - OV), hy(b + OV)), max(hy(a - OV), hy(b + OV))
    if side in ("north", "south"):
        lo = min(lo, h(cx0) - 20, h(cx1) - 20) if side == "north" else lo
        hi = max(hi, h(cx0) + 20) if side == "south" else hi
    ax.plot([lo - 40, hi + 40], [0, 0], color=INK, lw=1.5)
    marks = [(0, "Finished floor 0'-0\""), (M.HEAD, "Window/door heads 8'-0\"")]
    if side in ("north", "east"):
        marks += [(PORCH_CEIL, f"Porch ceiling {ftin(PORCH_CEIL)}")]
    if side == "north":
        marks += [(UNDER(S.N), f"Top of street wall {ftin(UNDER(S.N))}"), (TOP, f"Top of roof {ftin(TOP)} (highest point)"),
                  (RIDGE_TOP, f"Bedroom wing ridge {ftin(RIDGE_TOP)}")]
    elif side == "west":
        marks += [(REAR_TOP, f"Roof, rear eave {ftin(REAR_TOP)}"), (RIDGE_TOP, f"Gable ridge {ftin(RIDGE_TOP)}"),
                  (TOP, f"Shed beyond, street eave {ftin(TOP)}")]
    elif side == "south":
        marks += [(REAR_TOP, f"Top of roof at rear eave {ftin(REAR_TOP)} (wall plate 11'-0\")")]
    else:
        marks += [(REAR_TOP, f"Roof, rear eave {ftin(REAR_TOP)}"),
                  (TOP, f"Roof, street eave {ftin(TOP)}")]
    for z, lab in marks:
        ax.plot([hi + 20, hi + 60], [z, z], color="#c0392b", lw=0.8)
        ax.text(hi + 65, z, lab, fontsize=6.5, va="center", color="#c0392b")
    top = TOP
    names = {"north": "NORTH (STREET) ELEVATION", "south": "SOUTH (REAR) ELEVATION",
             "east": "EAST (CARPORT) ELEVATION", "west": "WEST ELEVATION"}
    ax.set_title(names[side], fontsize=10, weight="bold", loc="left")
    ax.set_aspect("equal"); ax.set_xlim(lo - 60, hi + 260); ax.set_ylim(-20, top + 30); ax.axis("off")


def elevations(pdf):
    fig = sheet("Z-4", "Elevations")
    for i, side in enumerate(("north", "south")):
        elevation(fig.add_axes([0.02, 0.645 - i * 0.265, 0.96, 0.255]), side)
    for i, side in enumerate(("east", "west")):
        elevation(fig.add_axes([0.02 + i * 0.49, 0.1, 0.47, 0.26]), side)
    fig.text(0.02, 0.972, "Heights above finished floor. The lot falls ~4' across the footprint (survey); grade lines "
             "and height above grade to follow the foundation/grading design.", fontsize=8.5, color="#555")
    fig.text(0.02, 0.962, "Street facade articulation (§22.140.520, Table 22.140.520-C): recessed windows: all street "
             f"windows set {S.WINDOW_RECESS:.0f}\" behind the stucco face.\n"
             "Rear: metal canopies over the kitchen and primary bedroom windows.", fontsize=8.5, color="#555", va="top")
    pdf.savefig(fig); save_png(fig, OUT / "Z-4-elevations.png", dpi=110); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUT / "zoning-check-set.pdf") as pdf:
        site_plan(pdf)
        floor_plan(pdf)
        roof_plan(pdf)
        elevations(pdf)
    print("  ", (OUT / "zoning-check-set.pdf").relative_to(S.ROOT))
    print(f"   floor {HOUSE:.0f}  coverage {COVER:.0f} ({COVER / LOT_AREA:.1%})  limit {LIMIT:.0f}  top {ftin(TOP)}")


if __name__ == "__main__":
    main()
