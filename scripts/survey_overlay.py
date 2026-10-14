# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Overlay the topographic survey (source_files/survey/*.dxf) on the owner schematic.

The survey is in California State Plane (feet). It is moved onto the plan's lot
coordinates (inches, origin at the street-side east corner, +x west, +y south)
using the survey's own lot lines, so the fit is exact. Draws the survey's
existing conditions (walls, chimney, concrete, fences, edge of pavement, trees,
utilities), spot elevations, and 1' contours computed from the ground shots.

Writes "Accosting - owner schematic + survey.dxf" and renders/survey-overlay.png.

    uv run scripts/survey_overlay.py
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schematic as S  # noqa: E402

SURVEY = next((S.ROOT / "source_files" / "survey").glob("*.dxf"))
OUT = S.ROOT / "Accosting - owner schematic + survey.dxf"
PNG = S.RENDERS / "survey-overlay.png"

LAYERS = {   # survey layer keyword -> (our layer, ACI colour, line weight in 1/100 mm)
    "sw wall": ("V-SURV-WALL", 1, 50), "sw chimney": ("V-SURV-WALL", 1, 50),
    "sw bldg": ("V-SURV-MISC", 4, 25), "sw conc": ("V-SURV-PAVE", 8, 18),
    "sw ep": ("V-SURV-PAVE", 8, 25), "sw chainlink fence": ("V-SURV-FENC", 3, 18),
    "our lot": ("V-SURV-LOT", 5, 35),
}
GROUND = ("FG", "CONC", "FS", "EP")          # shots on the ground (not wall tops)


def lot_transform(msp):
    """State plane ft -> plan inches, from the survey's 'our lot' lines."""
    lines = [((l.dxf.start.x, l.dxf.start.y), (l.dxf.end.x, l.dxf.end.y))
             for l in msp.query("LINE") if l.dxf.layer.endswith("our lot")]
    street = next(t for t in msp.query("TEXT") if t.dxf.text.strip() == "LAUREL DRIVE")
    sx, sy = street.dxf.insert.x, street.dxf.insert.y
    front = min(lines, key=lambda l: math.hypot((l[0][0] + l[1][0]) / 2 - sx, (l[0][1] + l[1][1]) / 2 - sy))
    e0, w0 = sorted(front, key=lambda p: -p[0])          # east corner has the larger easting
    L = math.hypot(w0[0] - e0[0], w0[1] - e0[1])
    ux = ((w0[0] - e0[0]) / L, (w0[1] - e0[1]) / L)      # toward the west corner
    uy = (ux[1], -ux[0])                                 # perpendicular, away from the street
    if (sx - e0[0]) * uy[0] + (sy - e0[1]) * uy[1] > 0:
        uy = (-uy[0], -uy[1])

    def to_lot(x, y):
        dx, dy = x - e0[0], y - e0[1]
        return (S.LOT_X0 + 12 * (dx * ux[0] + dy * ux[1]), 12 * (dx * uy[0] + dy * uy[1]))
    az = math.degrees(math.atan2(-uy[0], -uy[1])) % 360  # azimuth of plan north (toward the street)
    return to_lot, L, az


def main():
    sv = ezdxf.readfile(SURVEY)
    smsp = sv.modelspace()
    to_lot, frontage, plan_n = lot_transform(smsp)
    print(f"survey frontage {frontage:.2f} ft (plan {S.LOT_W / 12:.2f}); plan north azimuth {plan_n:.2f} deg")

    sh = S.build()
    msp = sh.msp
    for name, color, _ in set(LAYERS.values()):
        if not sh.doc.layers.has_entry(name):
            sh.doc.layers.add(name, color=color)
    for name, color in (("V-SURV-TREE", 3), ("V-SURV-UTIL", 6), ("V-SURV-ELEV", 30), ("V-TOPO", 34),
                        ("V-SURV-TEXT", 1)):
        sh.doc.layers.add(name, color=color)

    # ---- existing conditions ----------------------------------------------------------
    for e in smsp:
        key = next((k for k in LAYERS if e.dxf.layer.endswith(k)), None)
        if not key:
            continue
        lay, _, lw = LAYERS[key]
        if e.dxftype() == "LINE":
            pts = [to_lot(e.dxf.start.x, e.dxf.start.y), to_lot(e.dxf.end.x, e.dxf.end.y)]
        elif e.dxftype() == "LWPOLYLINE":
            pts = [to_lot(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
        else:
            continue
        attrs = {"layer": lay, "lineweight": lw}
        if key == "our lot":
            attrs["linetype"] = "DASHED"
        if key == "sw chainlink fence":
            attrs["linetype"] = "DASHED2"
        msp.add_lwpolyline(pts, dxfattribs=attrs)
    for e in smsp.query("INSERT"):
        if e.dxf.layer.endswith("tree trunk"):
            x, y = to_lot(e.dxf.insert.x, e.dxf.insert.y)
            msp.add_circle((x, y), 18, dxfattribs={"layer": "V-SURV-TREE"})
            sh.text("TREE", x, y + 30, 7, "V-SURV-TREE")
    names = {"WM": "WATER METER", "SSCO": "SEWER CLEANOUT", "PP": "POWER POLE", "CHIMNEY": "EXIST. CHIMNEY"}
    for t in smsp.query("TEXT"):
        if t.dxf.text.strip() in names:
            x, y = to_lot(t.dxf.insert.x, t.dxf.insert.y)
            msp.add_circle((x, y), 4, dxfattribs={"layer": "V-SURV-UTIL"})
            sh.text(names[t.dxf.text.strip()], x, y - 12, 7, "V-SURV-UTIL")
    for wall_label, (x, y) in (("EXIST. RETAINING WALL", (430, 560)), ("EXIST. WALL ON PROPERTY LINE", (S.LOT_X0 + 40, 300))):
        sh.text(wall_label, x, y, 7, "V-SURV-TEXT", rot=90 if x < 100 else 0)

    # ---- spot elevations and 1' contours ---------------------------------------------------
    shots = []
    for m in smsp.query("MTEXT"):
        if "pts label" not in m.dxf.layer:
            continue
        hit = re.search(r"\b(FG|CONC|FS|EP|CL TW|TW FW)\s+(14\d\d\.\d\d)", m.plain_text())
        if not hit:
            continue
        x, y = to_lot(m.dxf.insert.x, m.dxf.insert.y)
        z = float(hit.group(2))
        if -200 < y < S.LOT_D + 60 and -80 < x < S.LOT_W + 100:
            sh.text(f"{z:.1f}", x, y, 6, "V-SURV-ELEV")
        if hit.group(1) in GROUND and -200 < y < S.LOT_D + 60 and -80 < x < S.LOT_W + 100:
            shots.append((x, y, z))                      # our lot and the parkway only

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    import numpy as np
    xs, ys, zs = (np.array(v) for v in zip(*shots))
    tri = mtri.Triangulation(xs, ys)
    t = tri.triangles                                    # drop long, thin triangles across gaps
    edge = np.max([np.hypot(xs[t[:, i]] - xs[t[:, (i + 1) % 3]], ys[t[:, i]] - ys[t[:, (i + 1) % 3]])
                   for i in range(3)], axis=0)
    tri.set_mask(edge > 360)
    gx, gy = np.meshgrid(np.arange(xs.min(), xs.max(), 12.0), np.arange(ys.min(), ys.max(), 12.0))
    gz = mtri.CubicTriInterpolator(tri, zs, kind="geom")(gx, gy)   # smooth surface on a 1' grid
    lo, hi = math.floor(zs.min()), math.ceil(zs.max())
    cs = plt.figure().add_subplot().contour(gx, gy, gz, levels=range(lo, hi + 1))
    for level, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            if len(seg) < 2:
                continue
            msp.add_lwpolyline([tuple(p) for p in seg],
                               dxfattribs={"layer": "V-TOPO", "lineweight": 35 if level % 5 == 0 else 13})
            if len(seg) >= 30:                           # label longer runs once
                mx, my = seg[len(seg) // 2]
                sh.text(f"{level:.0f}'", mx, my, 8, "V-TOPO")

    sh.text("SURVEY OVERLAY: existing conditions (colour) on the owner schematic. "
            "Orange: spot elevations (ft); brown: 1' contours from the ground shots.",
            S.LOT_W / 2, S.LOT_D + 115, 10.0)
    sh.doc.saveas(OUT)
    print("wrote", OUT.name)
    S.render(sh.doc, PNG, -100, -330, S.LOT_W + 160, S.LOT_D + 135, width_in=22, dpi=120)


if __name__ == "__main__":
    main()
