# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4"]
# ///
"""Rough 3D massing model.

Default source is the owner schematic (scripts/schematic.py, no designer
content), written to renders/3d/:
  house.html  - browser viewer (orbit + walk mode, touch controls), open directly
  house.obj   - same geometry for Windows 3D Viewer / Blender

Walls rise to the 10' ceiling; doors and windows get 8' headers, windows a
30" sill and glass. Fixtures and furniture are boxes whose heights come from
their labels.

    uv run scripts/make_3d.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


CEIL, HEAD, SILL, FENCE = 120.0, 96.0, 30.0, 72.0   # inches
ROOT = Path(__file__).resolve().parent.parent


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



# =============================================================================
# Schematic source (public): owner-drawn, no designer content
# =============================================================================
LABEL_H = [            # label inside a shape -> (z0, z1); first match wins
    ("FRIDGE", (0, 70)), ("RANGE", (0, 36)), ("DOUBLE VANITY", (0, 34)), ("VANITY", (0, 34)),
    ("VAN", (0, 34)), ("WC", (0, 16)), ("TUB ACCESS", None), ("TUB", (0, 20)), ("DRYER", (0, 38)),
    ("WASHER", (0, 38)), ("FOLDING", (0, 36)), ("PANEL", (36, 66)), ("RACK", (0, 72)),
    ("CLOSET", (0, 96)), ("CL", (0, 96)), ("BENCH", (0, 18)), ("TV", (40, 70)), ("CONSOLE", (0, 30)),
    ("SINK", (0, 36)), ("HP", (0, 36)),
]


def _texts(msp):
    out = []
    for t in msp.query("TEXT"):
        pt = t.dxf.align_point if t.dxf.hasattr("align_point") else t.dxf.insert
        out.append((t.dxf.text.strip(), t.dxf.layer, pt.x, pt.y))
    return out


def build_schematic() -> Scene:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schematic as S
    sh = S.build()
    msp = sh.msp
    sc = Scene()
    E_, W_, N_, S_ = S.E, S.W, S.N, S.S
    px, py = S.PORCH_X, S.PORCH_Y
    footprint = [[E_, py], [px, py], [px, N_], [W_, N_], [W_, S_], [E_, S_]]

    # ---- ground, slab, carport, porch ------------------------------------------
    sc.polys["ground"].append([[[0, 0], [S.LOT_W, 0], [S.LOT_W, S.LOT_D], [0, S.LOT_D]], -1.0, 0.0])
    sc.polys["slab"].append([footprint, 0.0, 4.0])
    cx0, cy0, cx1, cy1 = S.CARPORT
    sc.polys["concrete"].append([[[cx0, cy0], [cx1, cy0], [cx1, cy1], [cx0, cy1]], 0.0, 2.0])
    sc.polys["concrete"].append([[[cx0, 0], [cx1, 0], [cx1, cy0], [cx0, cy0]], 0.0, 1.0])
    sc.polys["concrete"].append([[[E_, N_ - 24], [px, N_ - 24], [px, py], [E_, py]], 0.0, 3.0])
    sc.boxes["roof"].append([cx0 - 6, cy0 - 6, cx1, cy1 + 6, 108, 112])

    # ---- walls: a face along every edge of the wall outline ----------------------
    geom = S.wall_geometry()
    for poly in getattr(geom, "geoms", [geom]):
        for ring in [poly.exterior, *poly.interiors]:
            pts = list(ring.coords)
            for a, b in zip(pts, pts[1:]):
                if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 0.05:
                    sc.quad("wall", a, b, 0, CEIL)
    # Openings: headers; windows also get a sill and glass; the slider is glass.
    for o in S.OPENINGS:
        name, a, b, kind = o[0], o[1], o[2], o[3]
        axis, c, t = S.wall_info(name)
        def seg(v):
            return ((a, c + v), (b, c + v)) if axis == "x" else ((c + v, a), (c + v, b))
        for v in (-t / 2, t / 2):
            sc.quad("wall", *seg(v), HEAD, CEIL)
        if kind == "window":
            sill = 0.0 if name == "porch front" else SILL      # sidelight beside the front door
            if sill:
                for v in (-t / 2, t / 2):
                    sc.quad("wall", *seg(v), 0, sill)
            sc.quad("glass", *seg(0), sill, HEAD)
        elif kind == "slider":
            sc.quad("glass", *seg(0), 0, HEAD)

    # ---- fixtures, furniture, site --------------------------------------------------
    texts = _texts(msp)
    inside_house = lambda x0, y0, x1, y1: E_ <= x0 and x1 <= W_ and N_ <= y0 and y1 <= S_
    pantry = (S.face("kitchen|pantry", +1), S.face("south hall wall", +1),
              S.face("pantry|laundry", -1), S.face("pantry|mech", -1))
    lounge = (S.face("foyer wall", +1), S.N_IN, S.face("lounge|bed2", -1), S.face("south hall wall", -1))
    def label_in(x0, y0, x1, y1, layers=("A-ANNO-TEXT",)):
        for txt, lay, x, y in texts:
            if lay in layers and x0 <= x <= x1 and y0 <= y <= y1:
                return txt.upper()
        return ""
    def within(b, r):
        return r[0] - 1 <= b[0] and b[2] <= r[2] + 1 and r[1] - 1 <= b[1] and b[3] <= r[3] + 1

    for e in msp.query("LWPOLYLINE"):
        if not e.closed:
            continue
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        b = (min(xs), min(ys), max(xs), max(ys))
        w, h = b[2] - b[0], b[3] - b[1]
        lay = e.dxf.layer
        if lay in ("A-EQPM", "A-FURN"):
            if len(pts) > 4:                                    # L sectional
                sc.polys["furniture"].append([[list(p) for p in pts], 0.0, 30.0])
                continue
            lab = label_in(*b)
            z = None
            for key, zz in LABEL_H:
                if key in lab.split() or (key in lab and len(key) > 3):
                    z = zz
                    break
            else:
                if within(b, pantry) and min(w, h) <= 17:
                    sc.boxes["closet"].append([*b, 0, 60.0])     # pantry shelving
                    continue
                if lay == "A-FURN" and within(b, lounge) and abs(w - h) < 2 and w > 30:
                    z = (0, 18)                                  # coffee table
                elif lay == "A-FURN" and min(w, h) <= 4:
                    z = (0, 44)                                  # headboard
                elif lay == "A-FURN" and max(w, h) <= 20:
                    z = (0, 24)                                  # nightstand
                elif lay == "A-FURN":
                    z = (0, 24) if w * h >= 60 * 70 else (0, 30)  # beds vs. tables
                else:
                    z = (0, 36)                                  # counters
            if z is None:
                continue
            if lab.startswith("CL") or lab == "CLOSET":
                sc.boxes["closet"].append([*b, *z])
            else:
                sc.boxes["furniture" if lay == "A-FURN" else "fixture"].append([*b, *z])
        elif lay == "A-GLAZ" and inside_house(*b) and min(w, h) <= 1.5 and \
                not any(abs(v - f) < 10 for v in (b[1], b[3]) for f in (N_, S_)) and \
                not any(abs(v - f) < 10 for v in (b[0], b[2]) for f in (E_, W_)):
            sc.boxes["glass"].append([*b, 0, 80.0])              # fixed shower glass
        elif lay == "L-SITE":
            if e.dxf.get("linetype", "BYLAYER").upper().startswith("DASH"):
                continue                                         # carport roof outline
            lab = label_in(*b)
            if "PAVERS" in lab or "PATIO" in lab:
                sc.polys["pavers"].append([[list(p) for p in pts], 0.0, 2.0])
            elif "BINS" in lab:
                sc.polys["concrete"].append([[list(p) for p in pts], 0.0, 3.0])
        elif lay == "L-PLNT":
            lab = label_in(*b)
            sc.polys["planter" if "PLANTER" in lab else "lawn"].append(
                [[list(p) for p in pts], 0.0, 24.0 if "PLANTER" in lab else 1.0])
        elif lay == "A-WALL" and w <= 8 and h <= 8 and not inside_house(*b):
            sc.boxes["post"].append([*b, 0, 108])               # carport posts
        elif lay == "A-FENC":
            for a, c in zip(pts, pts[1:] + pts[:1]):
                sc.quad("fence", a, c, 0, 30)                   # low dog guard
    for ln in msp.query("LINE[layer=='A-FENC']"):
        sc.quad("fence", (ln.dxf.start.x, ln.dxf.start.y), (ln.dxf.end.x, ln.dxf.end.y), 0, FENCE)
    for c in msp.query("CIRCLE"):
        x, y, r = c.dxf.center.x, c.dxf.center.y, c.dxf.radius
        if r < 3:
            continue                                             # shower heads, drains
        if c.dxf.layer == "A-EQPM":
            sc.cyls["fixture"].append([x, y, r, 0, 62.0 if r >= 11 else (40.0 if r >= 8 else 48.0)])
        elif c.dxf.layer == "A-FURN":
            sc.cyls["furniture"].append([x, y, r, 0, 30.0 if r >= 7.5 else 18.0])
    for txt, lay, x, y in texts:
        if lay == "A-AREA-IDEN" and inside_house(x, y, x, y) and "'" not in txt and '"' not in txt:
            sc.labels.append([txt, x, y])

    sc.polys["ceiling"].append([footprint, CEIL, CEIL + 1])
    sc.meta = {"center": [(E_ + W_) / 2, (N_ + S_) / 2], "entry": [E_ + 40.0, N_ + 70.0],
               "roof": [[E_ - 24, N_ - 24], [W_ + 24, N_ - 24], [W_ + 24, S_ + 24], [E_ - 24, S_ + 24]]}
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


def write_model(sc: Scene, out_dir: Path, meta: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"quads": sc.quads, "boxes": sc.boxes, "cyls": sc.cyls, "polys": sc.polys,
            "labels": sc.labels, **meta, "roof_z": CEIL + 14.0}
    (out_dir / "house.html").write_text(HTML.replace("__DATA__", json.dumps(data)))
    write_obj(sc, out_dir / "house.obj")
    print("walls", len(sc.quads["wall"]), "windows", len(sc.quads["glass"]),
          "boxes", sum(len(v) for v in sc.boxes.values()), "labels", len(sc.labels))
    print("wrote", out_dir / "house.html")


def main():
    sc = build_schematic()
    write_model(sc, ROOT / "renders" / "3d", sc.meta)


if __name__ == "__main__":
    main()
