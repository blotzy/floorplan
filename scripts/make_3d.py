# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4"]
# ///
"""Rough 3D massing model of the owner-edits plan.

Reads the generated owner-edits DXF and writes:
  renders/3d/house.html  - browser viewer (orbit + walk mode), open directly
  renders/3d/house.obj   - same geometry for Windows 3D Viewer / Blender

Walls are the plan's wall lines extruded to the 10' ceiling (the designer
drew each wall as two loose face lines, so walls read as paired surfaces).
Openings between collinear wall pieces get an 8' header; openings with a
window get a 30" sill, glass, and the header. Fixtures/furniture are boxes.

    uv run scripts/make_3d.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ezdxf import bbox, recover

import owner_edits as oe
from owner_edits import OX, OY

OUT_DIR = oe.RENDERS / "3d"
CEIL, HEAD, SILL, FENCE = 120.0, 96.0, 30.0, 72.0   # inches

HOUSE_E = oe.HOUSE_E                       # 356.1
HOUSE_W = oe.HOUSE_E + oe.HOUSE_W          # 1220
N, S = 241.2, 621.2                        # house north / south outer faces


def lot(pt):
    return (pt[0] - OX, pt[1] - OY)


class Scene:
    def __init__(self):
        self.quads = defaultdict(list)     # material -> [[x0,y0,x1,y1,z0,z1], ...] (plan inches)
        self.boxes = defaultdict(list)     # material -> [[x0,y0,x1,y1,z0,z1], ...]
        self.cyls = defaultdict(list)      # material -> [[cx,cy,r,z0,z1], ...]
        self.polys = defaultdict(list)     # material -> [[[x,y],...], z0, z1]
        self.labels = []                   # [text, x, y]
        self.bed_sizes = []

    def quad(self, mat, a, b, z0, z1):
        self.quads[mat].append([a[0], a[1], b[0], b[1], z0, z1])


def in_site(b):
    x0, y0 = lot((b.extmin.x, b.extmin.y))
    x1, y1 = lot((b.extmax.x, b.extmax.y))
    return x0 > -30 and x1 < 1390 and y0 > -30 and y1 < 800, (x0, y0, x1, y1)


def in_exterior_wall(a, c, notch_x, notch_y):
    """True when a line lies within an exterior wall's 9" band (real windows do;
    the bedroom 3 / common bath partition, drawn on the Window layer, doesn't)."""
    bands = (lambda x, y: N - 1 <= y <= N + 10, lambda x, y: S - 10 <= y <= S + 1,
             lambda x, y: HOUSE_E - 1 <= x <= HOUSE_E + 10, lambda x, y: HOUSE_W - 10 <= x <= HOUSE_W + 1,
             lambda x, y: notch_y - 1 <= y <= notch_y + 10 and x <= notch_x + 10,
             lambda x, y: notch_x - 1 <= x <= notch_x + 10 and y <= notch_y + 10)
    return any(f(*a) and f(*c) for f in bands)


def add_bed(sc: Scene, ins):
    """Bed symbol -> mattress box + nightstand boxes (the symbol's outline also
    takes in the nightstands and a rug at the foot, which isn't furniture)."""
    lines = []
    def walk(ent):
        for v in ent.virtual_entities():
            if v.dxftype() == "INSERT":
                walk(v)
            elif v.dxftype() == "LINE":
                a, c = lot(v.dxf.start), lot(v.dxf.end)
                lines.append((min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])))
    walk(ins)
    long_ = [l for l in lines if max(l[2] - l[0], l[3] - l[1]) > 40]       # mattress edges
    mx0, my0 = min(l[0] for l in long_), min(l[1] for l in long_)
    mx1, my1 = max(l[2] for l in long_), max(l[3] for l in long_)
    sc.boxes["bed"].append([mx0, my0, mx1, my1, 0, 24.0])
    sides = {}                                                             # nightstands beside it
    for l in lines:
        outside_y = l[3] <= my0 + 0.5 or l[1] >= my1 - 0.5
        outside_x = l[2] <= mx0 + 0.5 or l[0] >= mx1 - 0.5
        if outside_y or outside_x:
            key = ("y0" if l[3] <= my0 + 0.5 else "y1") if outside_y else ("x0" if l[2] <= mx0 + 0.5 else "x1")
            b = sides.setdefault(key, [l[0], l[1], l[2], l[3]])
            b[:] = [min(b[0], l[0]), min(b[1], l[1]), max(b[2], l[2]), max(b[3], l[3])]
    for x0, y0, x1, y1 in sides.values():
        if 8 < x1 - x0 < 30 and 8 < y1 - y0 < 30:
            sc.boxes["furniture"].append([x0, y0, x1, y1, 0, 24.0])
    sc.bed_sizes.append((round(mx1 - mx0, 1), round(my1 - my0, 1)))


def build(doc) -> Scene:
    sc = Scene()
    msp = doc.modelspace()

    # ---- ground, slabs, hardscape ------------------------------------------
    sc.polys["ground"].append([[[0, 0], [1356, 0], [1356, 777.2], [0, 777.2]], -1.0, 0.0])
    notch_x, notch_y = HOUSE_E + 88.0, N + 48.0      # corner porch notch
    sc.polys["slab"].append([[[HOUSE_E, notch_y], [notch_x, notch_y], [notch_x, N], [HOUSE_W, N],
                              [HOUSE_W, S], [HOUSE_E, S]], 0.0, 4.0])
    cp_e = oe.CARPORT_E
    sc.polys["concrete"].append([[[cp_e, N], [HOUSE_E, N], [HOUSE_E, 481.3], [cp_e, 481.3]], 0.0, 2.0])
    sc.polys["concrete"].append([[[cp_e, 0], [HOUSE_E, 0], [HOUSE_E, N], [cp_e, N]], 0.0, 1.0])
    sc.polys["concrete"].append([[[HOUSE_E, N - 24], [notch_x, N - 24], [notch_x, notch_y],
                                  [HOUSE_E, notch_y]], 0.0, 3.0])          # porch + step
    # Carport: corner posts + roof.
    for px, py in ((cp_e, N), (cp_e, 481.3 - 6)):
        sc.boxes["post"].append([px, py, px + 6, py + 6, 0, 108])
    sc.boxes["roof"].append([cp_e - 6, N - 6, HOUSE_E, 481.3 + 6, 108, 112])

    # ---- walk the DXF ---------------------------------------------------------
    wall_lines = []                  # (x0,y0,x1,y1)
    windows = []                     # (x0,y0,x1,y1) window-layer lines
    round_tables = {}                # (cx, cy) -> outer radius
    for e in msp:
        t, layer = e.dxftype(), e.dxf.layer
        b = bbox.extents([e], fast=True)
        if not b.has_data:
            continue
        ok, (bx0, by0, bx1, by1) = in_site(b)
        if not ok:
            continue
        if t == "LINE":
            a, c = lot(e.dxf.start), lot(e.dxf.end)
            length = ((a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2) ** 0.5
            if length < 0.5:
                continue
            if layer in ("Wall", "Seal"):
                if e.dxf.get("linetype", "BYLAYER").upper().startswith("HIDDEN"):
                    continue                              # carport beam (dashed)
                if max(a[1], c[1]) <= N + 0.5 and min(a[1], c[1]) < N - 0.5:
                    continue                              # driveway edges / lines in the front yard
                if min(a[0], c[0]) < HOUSE_E - 0.5 or max(a[0], c[0]) > HOUSE_W + 0.5:
                    continue                              # lot lines, carport, side yards
                if min(a[1], c[1]) < N - 0.5 or max(a[1], c[1]) > S + 0.5:
                    continue                              # front / rear yards
                wall_lines.append((*a, *c))
            elif layer == "Window":
                if in_exterior_wall(a, c, notch_x, notch_y):
                    windows.append((*a, *c))
                else:
                    wall_lines.append((*a, *c))           # interior wall the designer put on Window
            elif layer == "Low - High Wall":
                sc.quad("fence", a, c, 0, FENCE)
            elif layer == "H" and HOUSE_E < bx0 and bx1 < HOUSE_W and N < by0 and by1 < S:
                # Closets: the designer marks each with a corner-to-corner diagonal.
                # Reach-in closets (doors) go to door height; walk-in hanging and
                # the linen cabinet are open shelving to 7'.
                walk_in = by0 > 459.0
                linen = (bx1 - bx0) < 36 and (by1 - by0) < 36
                sc.boxes["closet"].append([bx0, by0, bx1, by1, 0, 84.0 if walk_in or linen else HEAD])
        elif t == "LWPOLYLINE":
            pts = [lot(p) for p in e.get_points("xy")]
            if layer == "Window" and len(pts) == 2:
                windows.append((*pts[0], *pts[1]))
                continue
            if not e.closed or len(pts) < 3:
                continue
            w, h = bx1 - bx0, by1 - by0
            if layer == "Floor Pattern":
                if w * h >= 8 * 144:                      # skip the subpanel working-space outline
                    sc.polys["pavers"].append([pts, 0.0, 2.0])
            elif layer == "Plants":
                if min(w, h) <= 40:
                    sc.polys["planter"].append([pts, 0.0, 24.0])
                else:
                    sc.polys["lawn"].append([pts, 0.0, 1.0])
            elif layer == "Table":                       # coffee table (owner step 33)
                sc.boxes["furniture"].append([bx0, by0, bx1, by1, 0, 18.0])
            elif layer == "Bed":                         # owner step 25 beds
                if min(w, h) >= 50:
                    sc.boxes["bed"].append([bx0, by0, bx1, by1, 0, 24.0])
                elif min(w, h) <= 4:
                    sc.boxes["furniture"].append([bx0, by0, bx1, by1, 0, 44.0])   # headboard
                else:
                    sc.boxes["furniture"].append([bx0, by0, bx1, by1, 0, 24.0])   # nightstand
                sc.bed_sizes.append((round(w, 1), round(h, 1))) if min(w, h) >= 50 else None
            elif layer == "Fridge":
                sc.boxes["fixture"].append([bx0, by0, bx1, by1, 0, 70.0])
            elif layer in ("Bath - Kit.Fixture", "Furniture"):
                in_pantry = oe.BLK_E - 1 <= bx0 and bx1 <= oe.BLK_E + 71 and by1 <= 560.0
                if in_pantry and (w <= 17 or h <= 17):
                    sc.boxes["closet"].append([bx0, by0, bx1, by1, 0, 60.0])     # pantry shelving
                elif layer == "Furniture" and (w <= 17 or h <= 17) and max(w, h) > 40:
                    sc.boxes["furniture"].append([bx0, by0, bx1, by1, 0, 30.0])  # console
                else:
                    sc.boxes["fixture"].append([bx0, by0, bx1, by1, 0, 36.0])
        elif t == "CIRCLE" and layer == "Furniture":                # round tables (concentric rims)
            c = lot(e.dxf.center)
            key = (round(c[0]), round(c[1]))
            if HOUSE_E < c[0] < HOUSE_W and N < c[1] < S:
                round_tables[key] = max(round_tables.get(key, 0.0), e.dxf.radius)
        elif t == "CIRCLE" and layer == "Bath - Kit.Fixture":
            c = lot(e.dxf.center)
            r = e.dxf.radius
            sc.cyls["fixture"].append([c[0], c[1], r, 0, 60.0 if r >= 11 else 36.0])
        elif t == "INSERT" and layer in ("Furniture", "Bath - Kit.Fixture", "Wall"):
            if bx1 - bx0 > 150 or by1 - by0 > 150:
                continue
            name = e.dxf.name.upper()
            if "BED" in name:
                add_bed(sc, e)
                continue
            h = 30.0
            if "BED" in name:
                h = 24.0
            elif name == "A$C33A7765F":                   # fridge
                h = 70.0
            elif name in ("A$C1E1364CB",):                # range
                h = 36.0
            elif name in ("CT-03",):
                h = 22.0
            mat = "fixture" if layer != "Furniture" else "furniture"
            sc.boxes[mat].append([bx0, by0, bx1, by1, 0, h])
        elif t == "TEXT" and layer == "Area Titles":
            x, y = lot(e.dxf.insert)
            if HOUSE_E < x < HOUSE_W and N < y < S:
                sc.labels.append([e.dxf.text.strip(), (bx0 + bx1) / 2, (by0 + by1) / 2])

    for (cx, cy), r in round_tables.items():
        sc.cyls["furniture"].append([cx, cy, r, 0, 18.0])

    # ---- kitchen counters & peninsula (drawn as loose lines in the DXF) -------
    e_ = doc.entitydb
    pen_out = lot(e_["416AC4"].dxf.start)[0]
    pen_in = lot(e_["4168CE"].dxf.start)[0]
    run = lot(e_["4168C9"].dxf.start)[0]
    run_y0 = min(lot(e_["4168C9"].dxf.start)[1], lot(e_["4168C9"].dxf.end)[1])
    wall = lot(e_["41689D"].dxf.start)[0]
    sc.boxes["counter"].append([min(pen_out, pen_in), 455.2, max(pen_out, pen_in), 613.2, 0, 36])
    sc.boxes["counter"].append([pen_in, 589.2, run, 613.2, 0, 36])           # sink run
    sc.boxes["counter"].append([run, run_y0, wall, 589.2, 0, 36])            # range run

    # ---- walls, with headers / sills / glass in openings ---------------------
    for x0, y0, x1, y1 in wall_lines:
        sc.quad("wall", (x0, y0), (x1, y1), 0, CEIL)

    def in_gap(axis_val, lo, hi, horizontal):
        for wx0, wy0, wx1, wy1 in windows:
            mx, my = (wx0 + wx1) / 2, (wy0 + wy1) / 2
            if horizontal and abs(wy0 - wy1) < 0.5 and abs(my - axis_val) < 6 and lo - 1 < mx < hi + 1:
                return True
            if not horizontal and abs(wx0 - wx1) < 0.5 and abs(mx - axis_val) < 6 and lo - 1 < my < hi + 1:
                return True
        return False

    for horizontal in (True, False):
        groups = defaultdict(list)
        for x0, y0, x1, y1 in wall_lines:
            if horizontal and abs(y0 - y1) < 0.05:
                groups[round(y0, 1)].append(tuple(sorted((x0, x1))))
            elif not horizontal and abs(x0 - x1) < 0.05:
                groups[round(x0, 1)].append(tuple(sorted((y0, y1))))
        for k, segs in groups.items():
            segs.sort()
            reach = segs[0][1]
            for lo, hi in segs[1:]:
                gap = lo - reach
                if 10 < gap < 130:
                    a = (reach, k) if horizontal else (k, reach)
                    c = (lo, k) if horizontal else (k, lo)
                    sc.quad("wall", a, c, HEAD, CEIL)
                    if in_gap(k, reach, lo, horizontal):
                        sc.quad("wall", a, c, 0, SILL)
                        sc.quad("glass", a, c, SILL, HEAD)
                reach = max(reach, hi)

    # Ceiling (toggleable in the viewer).
    sc.polys["ceiling"].append([[[HOUSE_E, notch_y], [notch_x, notch_y], [notch_x, N], [HOUSE_W, N],
                                 [HOUSE_W, S], [HOUSE_E, S]], CEIL, CEIL + 1])
    return sc


def write_obj(sc: Scene, path: Path):
    """Feet, Y up, X = west, Z = north (right-handed)."""
    v, f, out = [], [], []

    def P(x, y, z):                      # plan inches -> obj feet
        v.append((x / 12, z / 12, -y / 12))
        return len(v)

    def face(*ids):
        f.append(ids)

    for mat, items in sc.quads.items():
        for x0, y0, x1, y1, z0, z1 in items:
            face(P(x0, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y0, z1))
    for mat, items in sc.boxes.items():
        for x0, y0, x1, y1, z0, z1 in items:
            c = [P(x, y, z) for z in (z0, z1) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
                face(*[c[i] for i in q])
    for line in [f"v {a:.3f} {b:.3f} {c:.3f}" for a, b, c in v] + \
                ["f " + " ".join(map(str, ids)) for ids in f]:
        out.append(line)
    path.write_text("# Accosting rebuild massing model (feet, Y up)\n" + "\n".join(out) + "\n")


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Accosting rebuild 3D</title>
<style>
  html,body{margin:0;height:100%;overflow:hidden;background:#dfe7ee;font:14px system-ui,sans-serif}
  #ui{position:absolute;top:10px;left:10px;background:#fffd;padding:8px 10px;border-radius:8px;box-shadow:0 1px 4px #0003}
  #ui label{display:block;margin:2px 0}
  #ui button{margin-top:6px}
  #help{position:absolute;bottom:10px;left:10px;background:#fffd;padding:6px 10px;border-radius:8px}
  /* touch walk mode */
  #stick{position:absolute;left:24px;bottom:24px;width:120px;height:120px;border-radius:50%;
         background:#fff6;border:2px solid #fffc;box-shadow:0 1px 6px #0004;display:none;touch-action:none}
  #knob{position:absolute;left:35px;top:35px;width:50px;height:50px;border-radius:50%;background:#fffe;
        box-shadow:0 1px 4px #0005;pointer-events:none}
  #exitwalk{position:absolute;top:12px;left:12px;display:none;padding:10px 14px;font:inherit;font-size:15px;
            border:0;border-radius:8px;background:#fffe;box-shadow:0 1px 4px #0003}
  canvas{touch-action:none}
  @media (max-width:600px){ #ui{font-size:13px;padding:6px 8px} #help{font-size:12px;right:10px} }
</style>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js",
"three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script>
</head><body>
<div id="ui">
  <b>Accosting rebuild</b>
  <label><input type="checkbox" id="ceil"> Ceiling</label>
  <label><input type="checkbox" id="furn" checked> Furniture / fixtures</label>
  <label><input type="checkbox" id="labels" checked> Room labels</label>
  <label><input type="checkbox" id="roofsh" checked> Roof shadows (24" eaves)</label>
  <label>Sun: <select id="day">
    <option value="172">Jun 21</option><option value="80">Mar 20 / Sep 22</option>
    <option value="355">Dec 21</option></select></label>
  <label><input type="range" id="hour" min="6" max="19" step="0.25" value="10" style="width:150px"> <span id="hourTxt"></span></label>
  <button id="walk">Walk (eye level)</button>
</div>
<div id="help">Orbit: drag · zoom: scroll · pan: right-drag. Walk: click the button, WASD/arrows to move, mouse to look, Esc to exit.</div>
<div id="stick"><div id="knob"></div></div>
<button id="exitwalk">Exit walk</button>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {PointerLockControls} from 'three/addons/controls/PointerLockControls.js';
const D = __DATA__;
const IN = 1/12;                                   // inches -> feet
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfe7ee);
const camera = new THREE.PerspectiveCamera(60, innerWidth/innerHeight, 0.1, 2000);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth, innerHeight); renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
// Fill light stands in for sky + ground bounce (no global illumination):
// sky from above, warm bounce from below, and a soft ambient so walls facing
// away from the sun read as shaded rather than black.
const hemi = new THREE.HemisphereLight(0xdfeaff, 0xb8a588, 1.1);
scene.add(hemi);
scene.add(new THREE.AmbientLight(0xffffff, 0.35));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
const sun = new THREE.DirectionalLight(0xfff4e0, 2.2);
sun.castShadow = true;
Object.assign(sun.shadow.camera, {left:-75,right:75,top:75,bottom:-75,near:1,far:400});
sun.shadow.mapSize.set(4096,4096); sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.04;
scene.add(sun); scene.add(sun.target);

const M = {
  wall:{color:0xf4f1ea, side:THREE.DoubleSide},
  glass:{color:0x9cc8e8, transparent:true, opacity:0.35, side:THREE.DoubleSide},
  fence:{color:0x6b6f73, side:THREE.DoubleSide},
  ground:{color:0xc9c2a8}, slab:{color:0xb9a98f}, concrete:{color:0xbdbdbd},
  pavers:{color:0xa89f94}, lawn:{color:0x6fa04a}, planter:{color:0x7d6a55},
  ceiling:{color:0xffffff, side:THREE.DoubleSide, transparent:true, opacity:0.92},
  fixture:{color:0xd9d4cc}, furniture:{color:0x8fa3b8}, counter:{color:0x9a8f84},
  closet:{color:0xb59a7a}, bed:{color:0xe8e1d4},
  post:{color:0x5a5f66}, roof:{color:0x4a4f55, transparent:true, opacity:0.85},
};
const mat = k => new THREE.MeshStandardMaterial(Object.assign(
  {roughness:0.9, polygonOffset:true, polygonOffsetFactor:1, polygonOffsetUnits:1}, M[k]||{color:0xcccccc}));
// Dark outlines on walls, fences and boxes so corners and wall ends read clearly.
const EDGE = new THREE.LineBasicMaterial({color:0x3a3d42});
const EDGED = new Set(['wall', 'fence']);
// plan (x west, y south, z up) in inches -> three (x = west, y = up, z = north).
// three.js is right-handed, so north must be +z or the model comes out mirrored.
const V = (x,y,z) => new THREE.Vector3(x*IN, z*IN, -y*IN);
const groups = {furn:new THREE.Group(), ceil:new THREE.Group(), labels:new THREE.Group()};
Object.values(groups).forEach(g=>scene.add(g));

for (const [k, items] of Object.entries(D.quads)) {
  const pos = [];
  for (const [x0,y0,x1,y1,z0,z1] of items) {
    const a=V(x0,y0,z0), b=V(x1,y1,z0), c=V(x1,y1,z1), d=V(x0,y0,z1);
    pos.push(...a.toArray(),...b.toArray(),...c.toArray(), ...a.toArray(),...c.toArray(),...d.toArray());
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos,3)); g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat(k)); m.castShadow = m.receiveShadow = k!=='glass'; scene.add(m);
  if (EDGED.has(k)) {                         // all four edges of every wall/fence face
    const lp = [];
    for (const [x0,y0,x1,y1,z0,z1] of items) {
      const a=V(x0,y0,z0), b=V(x1,y1,z0), c=V(x1,y1,z1), d=V(x0,y0,z1);
      for (const [p,q] of [[a,b],[b,c],[c,d],[d,a]]) lp.push(...p.toArray(), ...q.toArray());
    }
    const lg = new THREE.BufferGeometry();
    lg.setAttribute('position', new THREE.Float32BufferAttribute(lp,3));
    scene.add(new THREE.LineSegments(lg, EDGE));
  }
}
for (const [k, items] of Object.entries(D.boxes)) for (const [x0,y0,x1,y1,z0,z1] of items) {
  const m = new THREE.Mesh(new THREE.BoxGeometry((x1-x0)*IN,(z1-z0)*IN,(y1-y0)*IN), mat(k));
  m.position.set((x0+x1)/2*IN, (z0+z1)/2*IN, -(y0+y1)/2*IN); m.castShadow = m.receiveShadow = true;
  m.add(new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry), EDGE));
  (k==='fixture'||k==='furniture'||k==='counter'||k==='bed' ? groups.furn : scene).add(m);
}
for (const [k, items] of Object.entries(D.cyls)) for (const [cx,cy,r,z0,z1] of items) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r*IN, r*IN, (z1-z0)*IN, 24), mat(k));
  m.position.set(cx*IN, (z0+z1)/2*IN, -cy*IN); m.castShadow = true; groups.furn.add(m);
}
for (const [k, items] of Object.entries(D.polys)) for (const [pts,z0,z1] of items) {
  const shape = new THREE.Shape(pts.map(([x,y])=>new THREE.Vector2(x*IN, -y*IN)));
  const g = new THREE.ExtrudeGeometry(shape, {depth:(z1-z0)*IN, bevelEnabled:false});
  g.rotateX(Math.PI/2);                       // shape xy -> world xz, extrude downward
  const m = new THREE.Mesh(g, mat(k)); m.position.y = z1*IN; m.receiveShadow = true;
  (k==='ceiling' ? groups.ceil : scene).add(m);
}
for (const [text,x,y] of D.labels) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 128;
  const ctx = c.getContext('2d'); ctx.font = 'bold 56px system-ui'; ctx.fillStyle = '#223';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 256, 64);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c), depthTest:false}));
  s.scale.set(8, 2, 1); s.position.set(x*IN, 9, -y*IN); groups.labels.add(s);
}
groups.ceil.visible = false;
// Invisible roof that still casts shadows (hidden objects don't cast in
// three.js, so the ceiling never did): house outline incl. the corner porch,
// 24" eaves, just above the ceiling. Sun only reaches inside through glass.
const roofCaster = (() => {
  const shape = new THREE.Shape(D.roof.map(([x,y])=>new THREE.Vector2(x*IN, -y*IN)));
  const g = new THREE.ExtrudeGeometry(shape, {depth:0.5, bevelEnabled:false}); g.rotateX(Math.PI/2);
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({colorWrite:false, depthWrite:false}));
  m.position.y = (D.roof_z)*IN; m.castShadow = true; scene.add(m); return m;
})();
const ctr = new THREE.Vector3(D.center[0]*IN, 0, -D.center[1]*IN);
// Sun position for Altadena (34.19 N), solar time.
// World axes follow the PLAN: x = plan west, y = up, z = plan north.
// Plan north is NOT true north: per LA County parcel GIS (APN 5832-003-027,
// CA State Plane V), the street (plan north) lot line runs at 111.1 deg and
// the side lines at ~21 deg, so plan north points 21 deg east of true north.
const LAT = 34.19 * Math.PI/180;
const PLAN_N = 21.0 * Math.PI/180;      // true azimuth of plan north
function placeSun() {
  const day = +document.getElementById('day').value, hr = +document.getElementById('hour').value;
  const dec = 23.44*Math.PI/180 * Math.sin(2*Math.PI*(284+day)/365);
  const H = (hr-12)*15*Math.PI/180;
  const alt = Math.asin(Math.sin(LAT)*Math.sin(dec) + Math.cos(LAT)*Math.cos(dec)*Math.cos(H));
  const azS = Math.atan2(Math.sin(H), Math.cos(H)*Math.sin(LAT) - Math.tan(dec)*Math.cos(LAT)); // from south, + west
  const east = -Math.cos(alt)*Math.sin(azS), north = -Math.cos(alt)*Math.cos(azS), up = Math.sin(alt);
  // true (east, north) -> plan (east, north)
  const pe = east*Math.cos(PLAN_N) - north*Math.sin(PLAN_N);
  const pn = north*Math.cos(PLAN_N) + east*Math.sin(PLAN_N);
  sun.target.position.copy(ctr);
  sun.position.set(ctr.x - pe*150, up*150, ctr.z + pn*150);
  sun.intensity = alt > 0 ? 2.2 : 0;
  const h = Math.floor(hr), m = Math.round((hr-h)*60);
  document.getElementById('hourTxt').textContent =
    `${((h+11)%12)+1}:${String(m).padStart(2,'0')} ${h<12?'am':'pm'} · sun ${Math.max(0,alt*180/Math.PI).toFixed(0)}° up`;
}
// True-north arrow in the front yard (west of the driveway).
{
  const dir = new THREE.Vector3(Math.sin(PLAN_N), 0, Math.cos(PLAN_N));   // true north in plan world
  const base = new THREE.Vector3(D.center[0]*IN + 25, 0.5, -10*IN);
  scene.add(new THREE.ArrowHelper(dir, base, 14, 0xc0392b, 4, 2.5));
  const c = document.createElement('canvas'); c.width = 128; c.height = 128;
  const g = c.getContext('2d'); g.font = 'bold 96px system-ui'; g.fillStyle = '#c0392b';
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('N', 64, 64);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c)}));
  s.scale.set(4, 4, 1); s.position.copy(base).addScaledVector(dir, 18).setY(2); scene.add(s);
}
document.getElementById('day').onchange = placeSun;
document.getElementById('hour').oninput = placeSun;
placeSun();
camera.position.set(ctr.x - 30, 70, ctr.z + 75);
const orbit = new OrbitControls(camera, renderer.domElement); orbit.target.copy(ctr); orbit.update();
const walk = new PointerLockControls(camera, document.body);
const keys = {};
addEventListener('keydown', e=>keys[e.code]=true); addEventListener('keyup', e=>keys[e.code]=false);
const isTouch = matchMedia('(pointer: coarse)').matches || navigator.maxTouchPoints > 0;
if (isTouch) document.getElementById('help').textContent =
  'Orbit: drag · pinch to zoom · two fingers to pan. Walk: tap the button, move with the stick, drag to look.';
function toEntry() {
  camera.position.set(D.entry[0]*IN, 64*IN, -D.entry[1]*IN);  // inside the foyer, 5'-4" eye height
  camera.lookAt(D.entry[0]*IN, 64*IN, -D.entry[1]*IN - 10);    // facing south, into the house
}
function toOrbit() { orbit.enabled = true; camera.position.set(ctr.x-30,70,ctr.z+75); orbit.target.copy(ctr); orbit.update(); }
walk.addEventListener('unlock', toOrbit);

// ---- touch walk: left stick moves, dragging anywhere else turns the view ------
const stick = document.getElementById('stick'), knob = document.getElementById('knob');
const exitBtn = document.getElementById('exitwalk');
const tw = {on:false, jx:0, jy:0, stickId:null, lookId:null, lx:0, ly:0, yaw:0, pitch:0};
function startTouchWalk() {
  toEntry(); orbit.enabled = false;
  const e = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
  tw.yaw = e.y; tw.pitch = e.x; tw.on = true;
  stick.style.display = exitBtn.style.display = 'block';
  document.getElementById('ui').style.display = document.getElementById('help').style.display = 'none';
}
function stopTouchWalk() {
  tw.on = false; tw.jx = tw.jy = 0; tw.stickId = tw.lookId = null; knob.style.transform = '';
  stick.style.display = exitBtn.style.display = 'none';
  document.getElementById('ui').style.display = document.getElementById('help').style.display = '';
  toOrbit();
}
exitBtn.onclick = stopTouchWalk;
function setStick(ev) {
  const r = stick.getBoundingClientRect(), R = r.width / 2;
  let dx = ev.clientX - (r.left + R), dy = ev.clientY - (r.top + R);
  const m = Math.hypot(dx, dy), lim = R - 10;
  if (m > lim) { dx *= lim / m; dy *= lim / m; }
  tw.jx = dx / lim; tw.jy = dy / lim;
  knob.style.transform = `translate(${dx}px,${dy}px)`;
}
stick.addEventListener('pointerdown', ev => { tw.stickId = ev.pointerId; stick.setPointerCapture(ev.pointerId); setStick(ev); });
stick.addEventListener('pointermove', ev => { if (ev.pointerId === tw.stickId) setStick(ev); });
const releaseStick = ev => { if (ev.pointerId === tw.stickId) { tw.stickId = null; tw.jx = tw.jy = 0; knob.style.transform = ''; } };
stick.addEventListener('pointerup', releaseStick); stick.addEventListener('pointercancel', releaseStick);
const cv = renderer.domElement;
cv.addEventListener('pointerdown', ev => { if (tw.on && tw.lookId === null) { tw.lookId = ev.pointerId; tw.lx = ev.clientX; tw.ly = ev.clientY; } });
cv.addEventListener('pointermove', ev => {
  if (!tw.on || ev.pointerId !== tw.lookId) return;
  tw.yaw -= (ev.clientX - tw.lx) * 0.005; tw.pitch -= (ev.clientY - tw.ly) * 0.005;
  tw.pitch = Math.max(-1.4, Math.min(1.4, tw.pitch)); tw.lx = ev.clientX; tw.ly = ev.clientY;
});
const releaseLook = ev => { if (ev.pointerId === tw.lookId) tw.lookId = null; };
cv.addEventListener('pointerup', releaseLook); cv.addEventListener('pointercancel', releaseLook);

document.getElementById('walk').onclick = () => {
  if (isTouch) { startTouchWalk(); return; }
  toEntry(); orbit.enabled = false; walk.lock();
};
if (location.hash === '#touchwalk') startTouchWalk();         // test hook
const bind = (id, g) => document.getElementById(id).onchange = e => g.visible = e.target.checked;
bind('ceil', groups.ceil); bind('furn', groups.furn); bind('labels', groups.labels); bind('roofsh', roofCaster);
const clock = new THREE.Clock();
renderer.setAnimationLoop(()=>{
  const dt = clock.getDelta();
  if (walk.isLocked) {
    const v = 6*dt;   // ft/s
    if (keys.KeyW||keys.ArrowUp) walk.moveForward(v);
    if (keys.KeyS||keys.ArrowDown) walk.moveForward(-v);
    if (keys.KeyA||keys.ArrowLeft) walk.moveRight(-v);
    if (keys.KeyD||keys.ArrowRight) walk.moveRight(v);
  }
  if (tw.on) {
    camera.rotation.set(tw.pitch, tw.yaw, 0, 'YXZ');
    const v = 6*dt;   // ft/s at full stick
    walk.moveForward(-tw.jy * v); walk.moveRight(tw.jx * v);
  }
  renderer.render(scene, camera);
});
addEventListener('resize', ()=>{ camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
</script></body></html>
"""


def main():
    doc, _ = recover.readfile(oe.OUT)
    sc = build(doc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {"quads": sc.quads, "boxes": sc.boxes, "cyls": sc.cyls, "polys": sc.polys,
            "labels": sc.labels,
            "center": [(HOUSE_E + HOUSE_W) / 2, (N + S) / 2],
            "entry": [HOUSE_E + 40.0, N + 70.0],
            "roof": [[HOUSE_E - 24, N - 24], [HOUSE_W + 24, N - 24], [HOUSE_W + 24, S + 24],
                     [HOUSE_E - 24, S + 24]],
            "roof_z": CEIL + 14.0}
    (OUT_DIR / "house.html").write_text(HTML.replace("__DATA__", json.dumps(data)))
    write_obj(sc, OUT_DIR / "house.obj")
    print("beds (L x W in plan axes)", sc.bed_sizes, "closets", len(sc.boxes["closet"]))
    print("walls", len(sc.quads["wall"]), "windows", len(sc.quads["glass"]),
          "boxes", sum(len(v) for v in sc.boxes.values()), "labels", len(sc.labels))
    print("wrote", OUT_DIR / "house.html")


if __name__ == "__main__":
    main()
