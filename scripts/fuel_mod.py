# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2", "numpy"]
# ///
"""Fuel modification plan (LA County Fire, Fuel Modification Unit) for the Very High Fire Hazard Severity
Zone: one 24" x 36" sheet, FM-1, drawn to scale, with the building footprint, the ember-resistant zone and
Zone 1 (A), the proposed planting by scientific name, existing vegetation, irrigation and the County's plan
notes. Writes renders/fuelmod/FM-1-fuel-modification-plan.png and fuel-modification-plan.pdf.

    uv run scripts/fuel_mod.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle  # noqa: E402
from shapely.geometry import Polygon as MPolygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402
import exterior as X  # noqa: E402
import permit_set as P  # noqa: E402
import zoning_set as Z  # noqa: E402

OUT = S.RENDERS / "fuelmod"
INK, GREEN, LAWN, GC = "#222", "#2e7d32", "#cfe8c4", "#e4f1dc"
EMBER = 60.0                                    # ember-resistant zone: 5' beyond any roof edge or projection
ZONE1 = 360.0                                   # Zone 1 (A): 30'
L = (S.LOT_X0, 0.0, S.LOT_X0 + S.LOT_W, S.LOT_D)
LOT = box(*L)
FY = S.CARPORT[3] + 3                           # courtyard fence line


def roofs():
    """Roof edges (plan): the house with its eaves, the porch canopy, and the carport roof."""
    house = box(S.E - X.EAVE, S.N - X.EAVE, S.W + X.EAVE, S.S + X.EAVE_REAR)
    ox, oy = S.PORCH_OUT
    canopy = box(ox, oy, S.PORCH_X, S.N)
    cx0, cy0, cx1, cy1 = S.CARPORT
    carport = box(*S.CARPORT_ROOF)
    return unary_union([house, canopy, carport])


# Proposed planting: (key, botanical, common, County zone / min. distance, size at maturity, qty, size, notes)
PLANTS = [
    ("T1", "Heteromeles arbutifolia", "Toyon", "A / 15'", "10'-15' h x 10'-15' w", "1", "15 gal",
     "Privacy tree, tree form; canopy clear of the roof"),
    ("T2", "Cercis occidentalis", "Western redbud", "A / 10'", "10'-18' h x 10'-15' w", "1", "15 gal",
     "Deciduous; canopy clear of the roof"),
    ("S1", "Salvia greggii", "Autumn sage", "A / 10'", "2'-3' h x 3' w", "8", "5 gal",
     "Accents only, 10'+ from the house, widely spaced"),
    ("S2", "Iris douglasiana", "Pacific coast iris", "A", "1'-2' h x 2' w", "12", "1 gal", "Front beds"),
    ("G1", "Dymondia margaretae / Achillea tomentosa", "Dymondia / woolly yarrow", "A", "under 6\" h",
     "per area", "flats @ 12\" o.c.", "Front, side and rear ground cover"),
    ("G2", "Festuca arundinacea (dwarf) with Trifolium repens", "Tall fescue lawn with microclover", "A",
     "mowed, 3\"-4\"", "per area", "sod / seed", "Courtyard lawn, irrigated and mowed"),
    ("P1", "Heuchera spp. / Cyrtomium falcatum", "Coral bells / holly fern", "A", "1'-2' h", "per area", "1 gal",
     "Raised planters along the rear fence"),
]
EXISTING = [
    ("Olea europaea (3)", "Olive, mature", "Public parkway, outside the property", "Existing to remain"),
    ("Unidentified", "Lot tree (dead)", "On the lot, beside the carport", "Remove"),
    ("Olea europaea", "Olive", "Public parkway, in the driveway", "Remove (County permit)"),
    ("Ficus sp.", "Ficus", "Public parkway, ~13'-6\" east of the olive", "Remove (County permit)"),
]


def plan(ax):
    ex = roofs()
    cx0, cy0, cx1, cy1 = S.CARPORT                                          # includes the ground under the
    built = unary_union([MPolygon(Z.FOOT), box(cx0, cy0, cx1, cy1), box(*S.ENTRY_COURT)])   # eaves
    ember = ex.buffer(EMBER, join_style=2).difference(built).intersection(LOT)
    zone1 = ex.buffer(ZONE1, join_style=2).intersection(LOT)
    ax.add_patch(Rectangle((L[0], L[1]), L[2] - L[0], L[3] - L[1], fc="none", ec=INK, lw=1.6, ls="-."))
    # planting areas (drawn first, under the zones' outlines)
    gc = [box(S.E, 0, L[2], S.N - X.EAVE - EMBER),                       # front yard
          box(S.W + X.EAVE + EMBER, 0, L[2], L[3]),                      # west side yard strip
          box(S.E, S.S + X.EAVE_REAR + EMBER, L[2], L[3]),                    # rear yard strip
          box(S.LOT_X0 + 198, S.S + X.EAVE_REAR + EMBER, S.E, L[3] - 42),     # courtyard edge
          box(L[0], 0, S.CARPORT[0] - 6 - EMBER, FY),                    # east strip beside the carport
          box(L[0], 0, S.CARPORT[0], S.N - EMBER),                       # front corner east of the drive
          box(S.LOT_X0 + 18 + 180, FY + 61, S.E - X.EAVE - EMBER, L[3] - 42)]   # courtyard, beside the lawn
    gcu = unary_union(gc).difference(ember).difference(box(*S.ENTRY_COURT)).intersection(LOT)
    for g in getattr(gcu, "geoms", [gcu]):
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc=GC, ec=GREEN, lw=0.5))
    lawn = (S.LOT_X0 + 18, FY + 61, S.LOT_X0 + 18 + 180, L[3] - 42)
    ax.add_patch(Rectangle(lawn[:2], lawn[2] - lawn[0], lawn[3] - lawn[1], fc=LAWN, ec=GREEN, lw=0.6))
    ax.text((lawn[0] + lawn[2]) / 2, (lawn[1] + lawn[3]) / 2, "G2\nLAWN", ha="center", va="center", fontsize=6)
    pl = (S.LOT_X0 + 6, L[3] - 42, S.E, L[3] - 6)
    ax.add_patch(Rectangle(pl[:2], pl[2] - pl[0], pl[3] - pl[1], fc=GC, ec=GREEN, lw=0.6, hatch=".."))
    ax.text((pl[0] + pl[2]) / 2, (pl[1] + pl[3]) / 2, "P1  RAISED PLANTERS", ha="center", va="center", fontsize=5.5)
    # zones
    for g in getattr(ember, "geoms", [ember]):
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc="#f1e3d3", ec="#b07a2a", lw=0.8, hatch="xx",
                           alpha=0.9))
        for hole in g.interiors:
            ax.add_patch(MPoly(list(hole.coords), closed=True, fc="white", ec="#b07a2a", lw=0.5))
    ax.add_patch(MPoly(list(zone1.exterior.coords), closed=True, fill=False, ec="#c0392b", lw=1.6, ls="--"))
    # structures and hardscape
    ax.add_patch(MPoly(Z.FOOT, closed=True, fc="#cfcfcf", ec=INK, lw=1.4, hatch="////"))
    ax.text((S.E + S.W) / 2, (S.N + S.S) / 2, "RESIDENCE (1 STORY)\nSPRINKLERED", ha="center", va="center",
            fontsize=8, weight="bold", bbox=dict(fc="white", ec="none", pad=1.5))
    ax.add_patch(Rectangle((S.E - X.EAVE, S.N - X.EAVE), S.W - S.E + 2 * X.EAVE, S.S - S.N + X.EAVE + X.EAVE_REAR,
                           fill=False, ec=INK, lw=0.7, ls="--"))
    cx0, cy0, cx1, cy1 = S.CARPORT
    ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0, fc="#eeeeee", ec=INK, lw=1.0))
    ax.text((cx0 + cx1) / 2, (cy0 + cy1) / 2, "CARPORT\n(NONCOMBUSTIBLE)", ha="center", va="center", fontsize=6)
    ax.add_patch(MPoly(S.driveway_outline(), closed=True, fc="#f3f3f3", ec=INK, lw=0.8))
    ax.text((cx0 + cx1) / 2, 100, "DRIVEWAY\n(CONCRETE)", ha="center", fontsize=6)
    e0, e1, e2, e3 = S.ENTRY_COURT
    ax.add_patch(Rectangle((e0, e1), e2 - e0, e3 - e1, fc="#f3f3f3", ec=INK, lw=0.6))
    ax.text((e0 + e2) / 2, (e1 + e3) / 2 - 10, "ENTRY COURT\n(PAVERS)", ha="center", va="center", fontsize=5)
    ax.add_patch(Rectangle((S.LOT_X0 + 6, FY + 1), S.E - S.LOT_X0 - 6, 60, fc="#f3f3f3", ec=INK, lw=0.6))
    ax.text((S.LOT_X0 + S.E) / 2, FY + 31, "PAVERS", ha="center", va="center", fontsize=5.5)
    ax.plot([L[0], L[2]], [S.EDGE_OF_PAVEMENT] * 2, color=INK, lw=0.8)
    ax.text((L[0] + L[2]) / 2, -200, "LAUREL DRIVE", ha="center", fontsize=10, weight="bold")
    ax.text(L[0] + 20, S.EDGE_OF_PAVEMENT + 5, "EDGE OF PAVEMENT", fontsize=5)
    ax.text(L[2] - 10, 10, "PROPERTY LINE", fontsize=5.5, ha="right", va="bottom")
    # trees: proposed (mature canopy), existing to remain, removed
    for (x, y), key, d in ((S.PRIVACY_TREE, "T1", 156), (S.FRONT_TREE, "T2", 180)):
        ax.add_patch(Circle((x, y), d / 2, fill=False, ec=GREEN, lw=1.0, ls="--"))
        ax.add_patch(Circle((x, y), 4, fc=GREEN, ec="none"))
        ax.text(x, y + 10, key, fontsize=7, weight="bold", ha="center", color=GREEN)
    for x, y in S.EXIST_TREES:
        ax.add_patch(Circle((x, y), 30, fill=False, ec=GREEN, lw=0.8))
        ax.add_patch(Circle((x, y), 3, fc=GREEN, ec="none"))
    ax.text(sum(t[0] for t in S.EXIST_TREES) / 3, -150, "EXIST. OLIVES IN THE PARKWAY TO REMAIN",
            fontsize=5.5, ha="center", color=GREEN)
    for x, y, lab in S.REMOVED_TREES:
        ax.plot([x - 14, x + 14], [y - 14, y + 14], color=P.RED, lw=1.0)
        ax.plot([x - 14, x + 14], [y + 14, y - 14], color=P.RED, lw=1.0)
        ax.text(x, y - 20, lab + "\nTO BE REMOVED", fontsize=4.5, ha="center", va="top", color=P.RED)
    for x, y in ((700, 70), (780, 100), (1060, 80), (1140, 60), (1240, 100), (470, 90), (1000, 110), (540, 60)):
        ax.add_patch(Circle((x, y), 15, fill=False, ec=GREEN, lw=0.7))           # S1 accents, 10'+ from the house
        ax.text(x, y, "S1", fontsize=4, ha="center", va="center")
    ax.text(1180, 125, "S2 IRIS DRIFTS IN THE G1 BEDS", fontsize=5, ha="center", color=GREEN)
    # zone labels
    ax.text((S.E + S.W) / 2, S.S + 45, "EMBER-RESISTANT ZONE: UNDER THE EAVES AND 5' BEYOND THEM",
            fontsize=6, color="#8a5a1a", ha="center", va="center", bbox=dict(fc="white", ec="none", pad=1))
    ax.text(L[2] - 20, L[3] - 60, "ZONE 1 (A): THE WHOLE PROPERTY\nIS WITHIN 30' OF A STRUCTURE.\n"
            "NO ZONE 2 OR 3 ON THIS LOT.", fontsize=6.5, color="#c0392b", ha="right", va="top",
            bbox=dict(fc="white", ec="none", pad=1.5))


NOTES = """FUEL MODIFICATION NOTES (LA County Fire, Fuel Modification Plan Notes)
EMBER-RESISTANT ZONE (shown hatched)
 1. Extends 5' beyond the edge of any combustible structure, appendage or
    projection, measured from the eaves and the porch canopy; includes the
    areas beneath eaves. Kept free of materials and plants receptive to
    embers: concrete, pavers, gravel or decomposed granite only; no organic
    mulch, plants, wood furniture or storage.
ZONE 1 (A), 0-30' (the whole property)
 2. Irrigated to keep vegetation healthy and fire resistant.
 3. Primarily mowed lawn, low ground covers and widely spaced low shrubs;
    no woody plants over 12" within 10' of the house, none in front of windows.
 4. Trees: dwarf or under 25' tall and wide at maturity, canopies never over
    a roof (T1, T2). No large shrubs beneath tree canopies.
 5. No vines on any structure. No hedges over 6' within 10' of the house.
 6. Species per the County Fuel Modification Plant List; scientific names
    shown in the legend.
EXISTING VEGETATION
 7. The burned lot is cleared: no existing on-lot vegetation remains except
    as shown. The dead lot tree beside the carport is removed; the olive and
    ficus in the east parkway are removed under a County permit. The parkway olives are
    outside the property and remain.
IRRIGATION
 8. Automatic system with a weather-based controller: drip at trees, shrubs
    and ground cover; spray at the lawn. Maintained year-round.
MAINTENANCE
 9. Keep roofs, eaves and gutters free of leaves and debris; keep the ember-
    resistant zone free of anything ember-receptive.
10. Remove dead or dying plants, plant litter and dead wood in all zones;
    prune to break up horizontal and vertical fuel ladders; remove invasive
    species; keep the irrigation working.
11. Compliance is a year-round responsibility; inspections may occur at any
    time. All future planting per the County Fuel Modification Guidelines,
    approved before installation.
Approval of this plan covers only the codes reviewed by the Fuel Modification
Unit; it does not replace any other agency's approval."""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig = P.sheet("FM-1", "FUEL\nMODIFICATION\nPLAN")
    x0, y0, x1, y1 = S.LOT_X0 - 40, -230, S.LOT_X0 + S.LOT_W + 40, S.LOT_D + 40
    ax = P.scaled_axes(fig, 0.9, 7.2, x0, y0, x1, y1, scale=3 / 16)
    plan(ax)
    fig.text(0.9 / P.W_IN, 7.0 / P.H_IN, "FUEL MODIFICATION PLAN   3/16\" = 1'-0\"   (PLAN NORTH = STREET)",
             fontsize=11, weight="bold")
    leg = fig.add_axes([16.0 / P.W_IN, 6.1 / P.H_IN, 6.2 / P.W_IN, 0.75 / P.H_IN]); leg.axis("off")
    leg.set_xlim(0, 62); leg.set_ylim(0, 7.5)
    for i, (fc, ec, h, lab) in enumerate((("#f1e3d3", "#b07a2a", "xx", "Ember-resistant zone: noncombustible surfaces"),
                                          (GC, GREEN, None, "G1 ground cover (irrigated)"),
                                          (LAWN, GREEN, None, "G2 lawn (irrigated, mowed)"))):
        leg.add_patch(Rectangle((0, 5.5 - i * 2.5), 3, 1.6, fc=fc, ec=ec, hatch=h, lw=0.6))
        leg.text(4, 6.3 - i * 2.5, lab, fontsize=7.5, va="center")
    leg.plot([36, 40], [6.3, 6.3], color="#c0392b", lw=1.6, ls="--")
    leg.text(41, 6.3, "Zone 1 (A) limit, 30'", fontsize=7.5, va="center")
    leg.plot([36, 40], [3.8, 3.8], color=INK, lw=0.7, ls="--")
    leg.text(41, 3.8, "Eaves / roof edge", fontsize=7.5, va="center")
    leg.add_patch(Circle((38, 1.3), 1.0, fill=False, ec=GREEN, ls="--"))
    leg.text(41, 1.3, "Tree, mature canopy", fontsize=7.5, va="center")
    P.table(fig, 0.9, 5.6, "PLANT LEGEND (all Zone 1 / A)",
            ("Key", "Botanical name", "Common name", "County zone /\nmin. distance", "Size at maturity", "Qty",
             "Size", "Notes"),
            (0.5, 3.6, 2.6, 1.2, 1.9, 0.7, 1.2, 3.6), [p for p in PLANTS], fs=7)
    P.table(fig, 17.3, 5.6, "EXISTING VEGETATION",
            ("Botanical name", "Common name", "Location", "Disposition"), (1.7, 1.2, 2.7, 1.8),
            [e for e in EXISTING], fs=7)
    fig.text(23.0 / P.W_IN, 23.0 / P.H_IN, NOTES, fontsize=7.6, va="top", linespacing=1.32, family="DejaVu Sans")
    fig.text(23.0 / P.W_IN, 6.6 / P.H_IN, "Prepared by the owner, Richard Acosta. Drawn to scale from the owner's\n"
             "topographic survey and site plan. Fuel Modification Unit: forestryfuelmodification@fire.lacounty.gov,\n"
             "(626) 969-5205.", fontsize=7.2, va="top")
    with PdfPages(OUT / "fuel-modification-plan.pdf") as pdf:
        pdf.savefig(fig)
    Z.save_png(fig, OUT / "FM-1-fuel-modification-plan.png", dpi=80)
    plt.close(fig)
    print("   renders/fuelmod/FM-1-fuel-modification-plan.png")


if __name__ == "__main__":
    main()
