# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Owner schematic, drawn from scratch (no designer content).

Reproduces the current owner-edits layout (through step 21) with real wall
thicknesses and writes a clean DXF + PNG:

    Accosting - owner schematic.dxf
    renders/schematic.png, renders/schematic-zoom.png

    uv run scripts/schematic.py

Coordinates are inches, +x west and +y south; the street lot line is y = 0 and the
east property line is x = LOT_X0 (the house's numbers stay fixed, so LOT_X0 slides the
house east or west on the lot). Plan north is at the bottom of the sheet, matching the
designer's sheet. Everything is defined in the DATA section;
change a number and re-run.

Not for construction. Schematic for owner review / architect briefing.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Accosting - owner schematic.dxf"
RENDERS = ROOT / "renders"

# =============================================================================
# DATA
# =============================================================================
EXT = 9.0      # exterior: 1/2" gyp + 2x6 + 1/2" sheathing + 1" rigid insul. + 7/8" stucco
INT = 4.5      # interior: 2x4 + 1/2" gyp each side
WET = 6.5      # plumbing walls: 2x6 + 1/2" gyp each side

LOT_W, LOT_D = 1356.0, 777.25        # 113.00' x 64.77' per the topographic survey (source_files/survey)
LOT_X0 = 2.0                         # x of the east property line (side setbacks: 10% of LOT_W each)
E, W, N, S = 356.1, 1220.0, 241.2, 619.2   # house outer faces (72' x 31'-6")
E_IN, W_IN, N_IN, S_IN = E + EXT, W - EXT, N + EXT, S - EXT

# Corner porch notch (outer faces) at the north-east corner.
PORCH_X, PORCH_Y = 444.1, 289.2      # notch is E..PORCH_X by N..PORCH_Y
FOYER_WALL_END = PORCH_Y + EXT + 108.0   # foyer/TV wall: 9' of foyer inside the front wall
CARPORT = (140.1, N, E, 481.3)       # x0, y0, x1, y1 (18' x 20')
# Driveway: a 12' entrance between the parkway street tree (~26'-6" from the east line) and the
# tree inside the lot (~8'-6"), flaring west to the carport's full width. Runs out across the
# parkway to the edge of pavement (no curb on Laurel Drive).
DRIVE_IN = (LOT_X0 + 150.0, LOT_X0 + 290.0)   # entrance edges (x) at the property line
EDGE_OF_PAVEMENT = -160.0            # y of the street's edge of pavement (survey)
# Entry court in front of the porch, edged on the street side by a 24" seat wall (8" block) that
# returns to the house just short of the lounge window; you walk in from the driveway side.
ENTRY_COURT = (E, 156.0, 504.0, N)   # x0, y0, x1, y1
ENTRY_WALLS = [(E + 36.0, 156.0, 504.0, 164.0), (496.0, 164.0, 504.0, N)]
ENTRY_WALL_H = 24.0
PLAN_NORTH_AZ = 22.4                 # azimuth of plan north: survey side lines N22°23'00"E

# Interior walls: (name, axis, centreline, from, to, thickness).
# axis "x" = wall runs along x at y = centreline; "y" = runs along y at x = centreline.
WALLS = [
    ("foyer wall",        "y", PORCH_X + EXT - INT / 2, PORCH_Y, FOYER_WALL_END, INT),
    ("lounge|gym",       "y", 692.0,  N_IN, 405.45, INT),
    ("gym|ensuite",       "y", 826.0,  N_IN, 405.45, WET),
    ("ensuite|guest",     "y", 905.0,  N_IN, 405.45, INT),
    ("guest|office",     "y", 1064.0, N_IN, 405.45, INT),
    ("bedroom hall wall", "x", 403.2,  689.75, W_IN, INT),
    ("south hall wall",   "x", 459.2,  671.75, W_IN, INT),
    ("kitchen|pantry",    "y", 674.0,  457.0, S_IN, INT),
    ("pantry|laundry",    "y", 750.0,  457.0, S_IN, INT),
    ("pantry|mech",       "x", 555.2,  674.0, 750.0, INT),
    ("laundry|bath",      "y", 874.0 - WET - 52.0, 457.0, S_IN, WET),   # 52" clear bath, full depth
    ("bath|storage",      "x", 566.0 + INT / 2, 874.0 - WET - 52.0, 874.0, INT),  # storage behind the bath
    ("utility|bath",      "y", 874.0,  457.0, S_IN, WET),
    ("bath|wic",          "x", S_IN - 72.0 - INT / 2, 874.0, 1062.0, INT),   # bath exactly tub-deep
    ("suite|primary",     "y", 1062.0, 457.0, S_IN, INT),   # 30" taken from the bedroom for the wet room
]

# Openings: (wall name, from, to, kind, hinge, swing)
#   kind: door | slider | bifold | window | cased | pocket (hinge = pocket side)
#   windows may add (sill, head) heights in inches; the default is a 30" sill and 8' head.
#   Window widths and heights are standard 6" steps; anything wider than 8' is two mulled units.
#   transom: (sill, head) glass above a door on the same span.
#   hinge: "a" = at `from`, "b" = at `to`;  swing: +1 / -1 along the wall normal
#   (normal = +y for "x" walls, +x for "y" walls).
OPENINGS = [
    # exterior
    ("north",       511.1, 631.1, "window"),             # lounge 10'
    ("north",       722.1, 794.1, "window"),             # gym 6'
    ("north",       851.0, 881.0, "window"),             # shared ensuite
    ("north",       948.1, 1020.1, "window"),            # guest 6'
    ("north",       1102.6, 1174.6, "window"),           # office 6'
    ("porch front", 385.0, 423.0, "door", "a", +1),      # front door 36", opens flat against the east wall
    ("porch side",  255.0, 279.0, "window"),             # reeded glass
    ("south",       397.0, 517.0, "window", 18.0, 96.0),  # dining 10' (two 5' units), low 18" sill
    ("south",       592.0, 652.0, "window", 42.0, 96.0),  # kitchen sink: sill just above the backsplash
    ("south",       880.0, 928.0, "window", 72.0, 96.0),   # primary bath: 4'-0" x 2'-0" high window over the tub
    ("south",       975.0, 1023.0, "window", 72.0, 96.0),  # primary bath: matching 4'-0" x 2'-0" over the walkway
    ("south",       1101.6, 1173.6, "window"),           # primary bedroom 6' (centred; faces SSW, so kept modest)
    ("east",        503.75, 599.75, "slider"),           # dining 8' slider (centred between the carport fence and the corner)
    ("west",        414.7, 450.7, "door", "b", -1),      # hall-end exterior door
    ("west",        414.7, 450.7, "transom", 98.0, 110.0),  # fixed 3'-0" x 1'-0" transom over it: daylight down the hall
    # interior
    ("bedroom hall wall", 781.5, 817.5, "door", "b", -1),   # gym
    ("bedroom hall wall", 867.5, 897.5, "door", "b", -1),   # shared ensuite
    ("ensuite|guest", 335.0, 365.0, "door", "a", +1),       # guest en-suite: swings into the guest room (the bath is narrow)
    ("bedroom hall wall", 912.0, 948.0, "door", "a", -1),  # guest
    ("bedroom hall wall", 1069.0, 1105.0, "door", "a", -1), # office: at the guest-wall end, opposite the primary door
    ("south hall wall", 682.5, 712.5, "door", "a", +1),     # pantry (by the fridge)
    ("south hall wall", 760.0, 790.0, "door", "a", +1),     # laundry
    ("south hall wall", 820.0, 848.0, "door", "a", +1),     # common bath, against its east wall
    ("south hall wall", 1070.0, 1106.0, "door", "a", +1),   # primary bedroom
    ("pantry|laundry", 577.2, 607.2, "bifold", "a", +1),    # mech closet (louvered)
    ("laundry|bath", 574.0, 606.0, "cased"),                # storage room, open to the laundry
    ("suite|primary", 574.0, 606.0, "door", "b", -1),       # primary bath, from the bedroom; opens flat by the rear wall
    ("suite|primary", 463.0, 495.0, "door", "a", -1),       # walk-in closet, 32": swings in, opens flat by the hall wall
]

# =============================================================================
# geometry helpers
# =============================================================================
EXT_WALLS = {
    # name: (axis, outer face, inner direction, from, to)
    "north":       ("x", N, +1, PORCH_X, W),
    "porch front": ("x", PORCH_Y, +1, E, PORCH_X + EXT),
    "porch side":  ("y", PORCH_X, +1, N, PORCH_Y + EXT),
    "south":       ("x", S, -1, E, W),
    "east":        ("y", E, +1, PORCH_Y, S),
    "west":        ("y", W, -1, N, S),
}


def wall_rect(axis, c, a, b, t):
    lo, hi = sorted((a, b))
    return box(lo, c - t / 2, hi, c + t / 2) if axis == "x" else box(c - t / 2, lo, c + t / 2, hi)


def ext_rect(axis, face, d, a, b):
    lo, hi = sorted((a, b))
    c0, c1 = sorted((face, face + d * EXT))
    return box(lo, c0, hi, c1) if axis == "x" else box(c0, lo, c1, hi)


def wall_info(name):
    """(axis, centreline, thickness) for an interior or exterior wall."""
    if name in EXT_WALLS:
        axis, face, d, _, _ = EXT_WALLS[name]
        return axis, face + d * EXT / 2, EXT
    for n, axis, c, _, _, t in WALLS:
        if n == name:
            return axis, c, t
    raise KeyError(name)


def face(name, side):
    """Face coordinate of an interior wall: side -1 = low face, +1 = high face."""
    _, c, t = wall_info(name)
    return c + side * t / 2


def fmt(inches: float) -> str:
    i = int(round(inches))
    return f"{i // 12}'-{i % 12}\""


# =============================================================================
# drawing
# =============================================================================
class Sheet:
    def __init__(self):
        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = ezdxf.units.IN
        self.msp = self.doc.modelspace()
        self.heads = []                     # shower heads for the 3D model: (wall x, wall y, dir x, dir y)
        for name, color in [("A-WALL", 7), ("A-WALL-PATT", 8), ("A-DOOR", 3), ("A-GLAZ", 4),
                            ("A-FURN", 9), ("A-EQPM", 6), ("A-AREA-IDEN", 7), ("A-ANNO-DIMS", 1),
                            ("A-ANNO-TEXT", 7), ("C-PROP", 5), ("L-SITE", 94), ("L-PLNT", 3),
                            ("A-FENC", 8), ("A-CLNG", 8)]:
            self.doc.layers.add(name, color=color)
        st = self.doc.dimstyles.new("OWNER")
        st.dxf.dimtxt, st.dxf.dimasz, st.dxf.dimexo, st.dxf.dimexe = 8.0, 6.0, 3.0, 3.0
        st.dxf.dimtsz = 4.0                 # architectural ticks
        st.dxf.dimgap = 2.0

    def line(self, a, b, layer):
        self.msp.add_line(a, b, dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer):
        self.msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                                dxfattribs={"layer": layer})

    def circle(self, c, r, layer):
        self.msp.add_circle(c, r, dxfattribs={"layer": layer})

    def text(self, s, x, y, h, layer="A-ANNO-TEXT", rot=0.0):
        t = self.msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": layer})
        t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)
        return t

    def dim(self, p1, p2, base, label, angle=0):
        d = self.msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="OWNER",
                                    text=label, dxfattribs={"layer": "A-ANNO-DIMS"})
        d.render()


def room_label(sh, name, x0, y0, x1, y1, cx=None, cy=None, h=8.0):
    """Room name plus its clear size (x extent by y extent)."""
    cx = (x0 + x1) / 2 if cx is None else cx
    cy = (y0 + y1) / 2 if cy is None else cy
    sh.text(name, cx, cy + h * 0.7, h, "A-AREA-IDEN")
    sh.text(f"{fmt(x1 - x0)} x {fmt(y1 - y0)}", cx, cy - h * 0.5, h * 0.65, "A-AREA-IDEN")


# Bath fit-outs are separate functions so experiments can swap them.
TUB_L, TUB_W = 72.0, 48.0          # two-person jetted tub (primary bath)
LEDGE_D = 6.0                      # primary shower: closet wall built out below chest height


def wet_zone(sh, x0, y0, x1, y1):
    h = sh.msp.add_hatch(color=151, dxfattribs={"layer": "A-EQPM"})
    h.paths.add_polyline_path([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], is_closed=True)
    h.transparency = 0.75


def tub(sh, x0, y0, x1, y1, label="72x48 JET TUB"):
    sh.rect(x0, y0, x1, y1, "A-EQPM")
    sh.rect(x0 + 4, y0 + 4, x1 - 4, y1 - 4, "A-EQPM")
    rot = 90 if (y1 - y0) > (x1 - x0) else 0
    sh.text(label, (x0 + x1) / 2, (y0 + y1) / 2, 4.0, rot=rot)


def glass(sh, a, b):
    """Fixed glass panel from point a to point b (axis-aligned), drawn 1" thick."""
    (ax, ay), (bx, by) = a, b
    if ax == bx:
        sh.rect(ax - 0.5, min(ay, by), ax + 0.5, max(ay, by), "A-GLAZ")
    else:
        sh.rect(min(ax, bx), ay - 0.5, max(ax, bx), ay + 0.5, "A-GLAZ")


def drain(sh, a, b):
    """Linear drain."""
    sh.line(a, b, "A-EQPM")
    sh.circle(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 1.0, "A-EQPM")


def shower_head(sh, x, y, d):
    """Wall-mounted shower head at (x, y) on a wall face, spraying in y-direction d (+1/-1)."""
    sh.heads.append((x, y, 0.0, float(d)))
    sh.circle((x, y + d * 2.5), 2.5, "A-EQPM")
    for dx in (-5.0, 0.0, 5.0):
        sh.line((x + dx * 0.4, y + d * 5.5), (x + dx, y + d * 11.0), "A-EQPM")


def wc(sh, x0, y0, x1, y1):
    sh.rect(x0, y0, x1, y1, "A-EQPM"); sh.text("WC", (x0 + x1) / 2, (y0 + y1) / 2, 3.0)


def vanity(sh, x0, y0, x1, y1, label, rot=0):
    sh.rect(x0, y0, x1, y1, "A-EQPM"); sh.text(label, (x0 + x1) / 2, (y0 + y1) / 2, 3.0, rot=rot)


def common_bath(sh):
    """72" x 32" alcove tub with a shower head across the window end. Tub drain, valve and
    head, the WC and the vanity all on the east (plumbing) wall shared with the gym."""
    c0, c1 = face("gym|ensuite", +1), face("ensuite|guest", -1)          # 73.5" clear: fur the west end ~1.5"
    hall = face("bedroom hall wall", -1)
    ty = N_IN + 32.0
    tub(sh, c0, N_IN, c0 + 72.0, ty, "TUB 72x32")
    sh.circle((c0 + 4, N_IN + 16), 2.0, "A-EQPM")                     # shower head + valve, plumbing wall
    sh.heads.append((c0, N_IN + 16, 1.0, 0.0))
    sh.line((c0, ty + 1), (c0 + 72.0, ty + 1), "A-EQPM")              # curtain rod
    wc(sh, c0, ty + 2, c0 + 28, ty + 32)                               # 17" to the tub
    vanity(sh, c0, ty + 41, c0 + 21, ty + 89, "VANITY 48", rot=90)     # 24" from the WC centreline
    sh.rect(c0, hall - 24, c0 + 30, hall, "A-FURN")                          # linen closet in the
    sh.line((c0, hall - 24), (c0 + 30, hall), "A-FURN")                       # corner by the door
    sh.text("LINEN", c0 + 15, hall - 16, 3.0)
    room_label(sh, "SHARED ENSUITE", c0, N_IN, c1, hall, cx=(c0 + 21 + c1) / 2 + 1, cy=ty + 55, h=3.4)


def primary_bath(sh):
    """Wet room: jetted tub on the plumbing wall + curbless shower behind glass; WC and double vanity on
    the closet (north) wall; door from the bedroom at the rear-wall end."""
    m0, m1 = face("utility|bath", +1), face("suite|primary", -1)
    top = face("bath|wic", +1)
    gx = m0 + TUB_W + 42.0                                             # tub + 42" shower zone
    wet_zone(sh, m0, top, gx, S_IN)
    tub(sh, m0, S_IN - TUB_L, m0 + TUB_W, S_IN)                       # wall to wall, no end gap
    sh.text("CURBLESS", m0 + TUB_W + 21, 575.0, 3.5, rot=90)
    sx = m0 + TUB_W + 21                                               # two heads, facing each other
    ly = S_IN - LEDGE_D                                                # ledge wall on the rear wall, under
    sh.rect(m0 + TUB_W, ly, gx, S_IN, "A-EQPM")                       # the everyday head by the entry:
    sh.text("LEDGE", sx, ly + LEDGE_D / 2, 2.0)                        # tiled shelf, that head's plumbing inside
    shower_head(sh, sx, ly, -1)                                        # above the ledge, arm clears it
    shower_head(sh, sx, top, +1)
    glass(sh, (gx, top), (gx, ly - 30))                                # glass wall to wall: fixed panel from the closet wall,
    glass(sh, (gx, ly - 30), (gx, ly))                                 # then a 30" glass door hung off the ledge wall's end
    sh.line((gx, ly), (gx + 30, ly), "A-DOOR")                         # (no gap or inside corner to clean); swings out
    sh.msp.add_arc((gx, ly), 30, 270, 360, dxfattribs={"layer": "A-DOOR"})
    drain(sh, (gx - 3, top + 3), (gx - 3, ly - 3))
    wc(sh, gx + 2.25, top, gx + 32.25, top + 28)                       # north wall: 17.25" to glass, 15.25" to vanity
    vanity(sh, m1 - 60, top, m1, top + 22, "DOUBLE VANITY 60")
    for hx in (904.0, 999.0):                                          # both rear windows: sill at 6'
        sh.text("HIGH WINDOW", hx, S_IN - 4, 2.0)
    room_label(sh, "PRIMARY BATH", m0, top, m1, S_IN, cx=(gx + m1) / 2 - 2, cy=570.0, h=3.2)


def utility_block(sh):
    """Common bath and laundry side by side (labels + fixtures); experiments can swap this."""
    eq, fu = "A-EQPM", "A-FURN"
    hall = face("south hall wall", +1)
    l0, lw = face("pantry|laundry", +1), face("laundry|bath", -1)            # laundry galley
    b0, b1 = face("laundry|bath", +1), face("utility|bath", -1)              # bath
    be = face("bath|storage", -1)
    # bath: sink, toilet, then a curbless shower across the end, all on the primary-bath wall
    vanity(sh, b1 - 20, 466.0, b1, 490.0, "SINK", rot=90)
    wc(sh, b1 - 28, 497.0, b1, 527.0)
    gy = 530.0                                                               # shower: full width x 36"
    wet_zone(sh, b0, gy, b1, be)
    sh.rect(b0, gy, b1, be, eq)
    glass(sh, (b0 + 24, gy), (b1, gy))                                       # 24" open entry, door side
    sh.text("SHOWER", (b0 + b1) / 2, gy + 14, 3.2)
    sh.heads.append((b1, gy + 20, -1.0, 0.0))
    sh.circle((b1 - 2.5, gy + 20), 2.5, eq)
    for dy in (-5.0, 0.0, 5.0):
        sh.line((b1 - 5.5, gy + 20 + dy * 0.4), (b1 - 11.0, gy + 20 + dy), eq)
    drain(sh, (b0 + 3, be - 3), (b1 - 3, be - 3))
    room_label(sh, "COMMON BATH", b0, hall, b1, be, cx=b0 + 12, cy=505.0, h=2.4)
    # storage room behind the bath, open to the laundry
    s0 = face("bath|storage", +1)
    sh.rect(b1 - 12, s0, b1, S_IN, fu); sh.text("SHELVES", b1 - 6, (s0 + S_IN) / 2, 2.2, rot=90)
    room_label(sh, "STORAGE", b0, s0, b1, S_IN, cx=(b0 + b1 - 12) / 2, h=3.4)
    # laundry galley, all on the bath wall: folding counter (shelves above) and sink by the door,
    # then the dryer and washer on pedestals; panel near the door across open floor
    sh.rect(lw - 22, hall, lw, 514.0, fu)                    # 22" deep: clears the door swing
    sh.text("FOLDING COUNTER", lw - 11, (hall + 499.0) / 2, 2.2, rot=90)
    sh.text("SHELVES ABOVE", lw - 5, (hall + 499.0) / 2, 1.6, rot=90)
    vanity(sh, lw - 18, 500.0, lw, 514.0, "SINK", rot=90)    # set into the counter
    y = 515.0
    for lbl in ("DRYER", "WASHER"):                          # facing the wall, washer on the left: the
                                                             # doors open apart (left-hinged washer)
        sh.rect(lw - 30, y, lw, y + 27, eq); sh.text(lbl, lw - 17, y + 13.5, 2.6, rot=90)
        sh.text("ON PEDESTAL", lw - 9, y + 13.5, 1.6, rot=90); y += 28
    sh.rect(l0, 466.0, l0 + 4, 486.0, eq); sh.text("PANEL", l0 + 10, 476.0, 2.5, rot=90)
    ax0, ax1 = l0 + 4, l0 + 26                               # pulley ceiling airer over the aisle
    sh.msp.add_lwpolyline([(ax0, 515.0), (ax1, 515.0), (ax1, 575.0), (ax0, 575.0)], close=True,
                          dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    sh.text("CEILING AIRER", (ax0 + ax1) / 2, 545.0, 2.2, "A-CLNG", rot=90)
    sh.rect(l0 + 12, S_IN - 12, lw - 12, S_IN, fu)                           # rear wall: full-height shelves
    sh.text("SHELVES", (l0 + lw) / 2, S_IN - 6, 2.2)                         # between the mech and storage openings
    room_label(sh, "LAUNDRY", l0, hall, lw, S_IN, cx=(l0 + lw) / 2 - 8, cy=582.0, h=4.0)


def wic(sh):
    x0, x1 = face("utility|bath", +1), face("suite|primary", -1)
    y0, y1 = face("south hall wall", +1), face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):                   # 24"-deep hanging section with its rod
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hang(x0 + 24, 1023.0, y0, +1)           # entry side: stops 3' short of the bedroom wall (landing inside
    hang(x0 + 24, x1, y1, -1)               # the cased entry); far side runs to the bedroom wall
    for ya, yb in ((y0, y0 + 24), (y1 - 24, y1)):  # end wall wrapped in one built-in: corner shelves
        sh.rect(x0, ya, x0 + 24, yb, fu)    # (shoes, folded, bags) either side of a drawer stack
        sh.text("SHELVES", x0 + 12, (ya + yb) / 2, 2.2)
    sh.rect(x0, y0 + 24, x0 + 20, y1 - 24, fu)
    sh.text("DRAWERS", x0 + 10, (y0 + y1) / 2, 2.2, rot=90)
    room_label(sh, "WIC", x0, y0, x1, y1, cx=1000.0, h=5.0)


def driveway_outline():
    """Closed outline of the driveway, parkway apron included (lot inches)."""
    x0, x1 = DRIVE_IN
    cx0, cy0, cx1, _ = CARPORT
    curve = []                                   # west edge: straight out of the entrance, then
    for i in range(13):                          # bending west into the carport (quadratic)
        t = i / 12
        curve.append(((1 - t) ** 2 * x1 + 2 * (1 - t) * t * x1 + t * t * cx1,
                      (1 - t) ** 2 * 0 + 2 * (1 - t) * t * 170 + t * t * cy0))
    return [(x0, EDGE_OF_PAVEMENT), (x1, EDGE_OF_PAVEMENT), *curve, (cx0, cy0), (x0, 0.0)]


def wall_geometry():
    """All walls as one shapely (Multi)Polygon with the openings cut out."""
    solids = [ext_rect(ax, f, d, a, b) for ax, f, d, a, b in EXT_WALLS.values()]
    solids += [wall_rect(ax, c, a, b, t) for _, ax, c, a, b, t in WALLS]
    cuts = []
    for o in OPENINGS:
        axis, c, t = wall_info(o[0])
        cuts.append(wall_rect(axis, c, o[1], o[2], t + 0.2))
    return unary_union(solids).difference(unary_union(cuts))


def build() -> Sheet:
    sh = Sheet()

    # ---- walls: union of exterior + interior rectangles, minus openings -----
    walls = wall_geometry()
    for poly in getattr(walls, "geoms", [walls]):
        h = sh.msp.add_hatch(color=8, dxfattribs={"layer": "A-WALL-PATT"})
        h.paths.add_polyline_path(list(poly.exterior.coords), is_closed=True)
        for ring in poly.interiors:
            h.paths.add_polyline_path(list(ring.coords), is_closed=True)
        sh.msp.add_lwpolyline(list(poly.exterior.coords), close=True, dxfattribs={"layer": "A-WALL"})
        for ring in poly.interiors:
            sh.msp.add_lwpolyline(list(ring.coords), close=True, dxfattribs={"layer": "A-WALL"})

    # ---- openings --------------------------------------------------------------
    for o in OPENINGS:
        name, a, b, kind = o[0], o[1], o[2], o[3]
        axis, c, t = wall_info(name)

        def P(u, v):                       # u along wall, v across (offset from centreline)
            return (u, c + v) if axis == "x" else (c + v, u)

        if kind == "window":
            for v in (-t / 6, t / 6):
                sh.line(P(a, v), P(b, v), "A-GLAZ")
            sh.line(P(a, -t / 2), P(b, -t / 2), "A-GLAZ")
            sh.line(P(a, t / 2), P(b, t / 2), "A-GLAZ")
        elif kind == "slider":
            m = (a + b) / 2
            sh.rect(*P(a, -2.0), *P(m + 2, -0.5), "A-GLAZ")
            sh.rect(*P(m - 2, 0.5), *P(b, 2.0), "A-GLAZ")
        elif kind == "door":
            hinge, swing = o[4], o[5]
            w = b - a
            hu = a if hinge == "a" else b
            fu = b if hinge == "a" else a
            v0 = swing * t / 2
            tip = P(hu, v0 + swing * w)
            sh.line(P(hu, v0), tip, "A-DOOR")
            # arc from the leaf tip to the far jamb
            cx, cy = P(hu, v0)
            ang1 = math.degrees(math.atan2(tip[1] - cy, tip[0] - cx))
            fx, fy = P(fu, v0)
            ang2 = math.degrees(math.atan2(fy - cy, fx - cx))
            lo, hi = sorted((ang1, ang2))
            if hi - lo > 180:
                lo, hi = hi, lo + 360
            sh.msp.add_arc((cx, cy), w, lo, hi, dxfattribs={"layer": "A-DOOR"})
        elif kind == "bifold":
            swing = o[5]
            v0 = swing * t / 2
            q = (b - a) / 4
            pts = [P(a, v0), P(a + q, v0 + swing * 10), P(a + 2 * q, v0),
                   P(a + 3 * q, v0 + swing * 10), P(b, v0)]
            for p0, p1 in zip(pts, pts[1:]):
                sh.line(p0, p1, "A-DOOR")
        elif kind == "pocket":             # leaf slid into the wall on the `hinge` side
            w = b - a
            p0, p1 = (a - w, a) if o[4] == "a" else (b, b + w)
            sh.line(P(p0, 0.0), P(p1, 0.0), "A-DOOR")
            sh.msp.add_line(P(a, 0.0), P(b, 0.0), dxfattribs={"layer": "A-DOOR", "linetype": "DASHED"})
        elif kind == "transom":            # glass above a door: note it in plan
            mx, my = P((a + b) / 2, 0.0)
            sh.text("TRANSOM ABOVE", mx + (8 if axis == "y" else 0), my, 2.0, rot=90 if axis == "y" else 0)
        # cased openings: just the gap

    # ---- rooms: labels with clear sizes ---------------------------------------
    def room(*a, **k):
        room_label(sh, *a, **k)

    hall_n, hall_s = face("bedroom hall wall", -1), face("south hall wall", -1)   # bedroom / lobby faces
    srow = face("south hall wall", +1)
    pen_out, pen_in = 546.9, 598.0
    room("FOYER", E_IN, PORCH_Y + EXT, face("foyer wall", -1), FOYER_WALL_END, cx=410.0, cy=385.0, h=6.0)
    room("LOUNGE", face("foyer wall", +1), N_IN, face("lounge|gym", -1), hall_s, cx=600.0, cy=428.0)
    room("DINING", E_IN, srow, pen_out, S_IN, cy=592.0)
    room("KITCHEN", pen_out, srow, face("kitchen|pantry", -1), S_IN, cx=622.0, cy=545.0, h=7.0)
    room("GYM", face("lounge|gym", +1), N_IN, face("gym|ensuite", -1), hall_n, cy=272.0)
    room("GUEST", face("ensuite|guest", +1), N_IN, face("guest|office", -1), hall_n, cy=272.0)
    room("OFFICE", face("guest|office", +1), N_IN, W_IN, hall_n, cy=272.0)
    room("PANTRY", face("kitchen|pantry", +1), srow, face("pantry|laundry", -1), face("pantry|mech", -1), h=5.5)
    room("MECH", face("kitchen|pantry", +1), face("pantry|mech", +1), face("pantry|laundry", -1), S_IN,
         cy=575.0, h=5.0)
    utility_block(sh)
    wic(sh)
    room("PRIMARY", face("suite|primary", +1), srow, W_IN, S_IN, cx=(face("suite|primary", +1) + W_IN - 80) / 2)
    hx0, hy = 990.0, (face("bedroom hall wall", +1) + hall_s) / 2      # attic pull-down in the hall,
    sh.msp.add_lwpolyline([(hx0, hy - 12.75), (hx0 + 54, hy - 12.75), (hx0 + 54, hy + 12.75),
                           (hx0, hy + 12.75)], close=True,             # across from the closet wall
                          dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    sh.text("ATTIC HATCH", hx0 + 27, hy, 2.6, "A-CLNG")
    sh.text("LOBBY", 950.0, (face("bedroom hall wall", +1) + hall_s) / 2, 7.0, "A-AREA-IDEN")
    sh.text("PORCH", (E + PORCH_X) / 2, (N + PORCH_Y) / 2, 7.0, "A-AREA-IDEN")

    # ---- fixtures & furniture (simple symbols) --------------------------------
    eq, fu = "A-EQPM", "A-FURN"
    kw = face("kitchen|pantry", -1)
    sh.rect(pen_out, srow, pen_in, S_IN, eq)                                  # peninsula
    sh.rect(pen_in - 24, S_IN - 48, pen_in, S_IN - 24, eq)                     # dishwasher: peninsula, kitchen
    sh.text("DW", pen_in - 12, S_IN - 36, 3.5)                                 # side, around the corner from the sink
    sh.rect(pen_in - 24, S_IN - 72, pen_in, S_IN - 48, eq)                     # 24" triple pull-out beside the DW:
    sh.text("TRASH", pen_in - 12, S_IN - 60, 3.0)                              # trash, recycling, food scraps
    sh.rect(pen_out, S_IN - 15, pen_out + 24, S_IN, eq)                        # 15" drink fridge under the counter,
    sh.text("BEV", pen_out + 12, S_IN - 7.5, 3.0)                              # stool side, corner by the south wall
    sh.line((pen_out + 15, srow), (pen_out + 15, S_IN), eq)                   # 15" overhang
    sh.rect(pen_in, S_IN - 24, kw, S_IN, eq)                                  # sink run, into the corner
    ta, r0 = srow + 36 + 15, srow + 36 + 15 + 12                              # range wall: tall cabinet,
    tb = r0 + 30 + 15                                                         # 12" landing, range, 15"
    sh.rect(kw - 24, ta, kw, tb, eq)                                          # landing, tall cabinet
    for y0, y1 in ((srow + 36, ta), (tb, S_IN - 24)):
        sh.rect(kw - 24, y0, kw, y1, eq); sh.text("TALL STORAGE", kw - 12, (y0 + y1) / 2, 1.6, rot=90)
    sh.rect(kw - 24, r0, kw, r0 + 30, eq); sh.text("RANGE", kw - 12, r0 + 15, 3.5, rot=90)
    sh.rect(kw - 30, srow, kw, srow + 36, eq); sh.text("FRIDGE", kw - 15, srow + 18, 3.5, rot=90)
    sh.rect(607.0, S_IN - 20, 637.0, S_IN - 4, eq); sh.text("SINK", 622.0, S_IN - 12, 3.0)
    for y in (476.7, 512.9, 544.5):                                           # 3 stools
        sh.circle((pen_out - 8, y), 7.5, fu)
    dcx = (E_IN + pen_out) / 2                                                # dining table
    sh.rect(dcx - 20, 523 - 42, dcx + 20, 523 + 42, fu)                      # 84" x 40" table
    for dy in (-28, 0, 28):                                                   # 8 chairs: 3 a side + ends
        sh.circle((dcx - 28, 523 + dy), 7, fu); sh.circle((dcx + 28, 523 + dy), 7, fu)
    for y in (523 - 51, 523 + 51):
        sh.circle((dcx, y), 7, fu)
    seat_cy = (305.0 + 396.0) / 2           # centre of the sectional's seating area
    tv = face("foyer wall", +1)             # 90" TV, ~78.5" wide, centred on the seating
    sh.rect(tv, seat_cy - 39.25, tv + 3, seat_cy + 39.25, fu); sh.text('TV 90"', tv + 8, seat_cy, 4.0, rot=90)
    sh.msp.add_lwpolyline([(505.0, 267.0), (635.0, 267.0), (635.0, 396.0), (597.0, 396.0), (597.0, 305.0),
                           (505.0, 305.0)], close=True, dxfattribs={"layer": fu})   # L sectional, 38" deep
    sh.text("L SECTIONAL", 551.0, 287.0, 4.0)
    sh.rect(636.5, 305.0, 651.5, 396.0, fu); sh.text("CONSOLE", 644.0, 350.5, 3.5, rot=90)
    sh.rect(533.0, seat_cy - 23, 579.0, seat_cy + 23, fu)                     # 46" square table
    fw = face("foyer wall", -1)             # closet + bench on the foyer side of the TV wall
    sh.rect(fw - 18, 300.0, fw, 333.0, fu); sh.text("CLOSET", fw - 9, 316.5, 3.0, rot=90)
    sh.rect(fw - 18, 333.0, fw, 366.0, fu); sh.text("BENCH", fw - 9, 349.5, 3.0, rot=90)

    def bed(head_x, cy, w, d):              # 80" mattress + 3" headboard on the wall at head_x,
        hb = head_x + d * 3                 # running in x-direction d; 18" x 16" nightstands
        ft = hb + d * 80
        y0, y1 = cy - w / 2, cy + w / 2
        sh.rect(min(head_x, hb), y0, max(head_x, hb), y1, fu)                 # headboard
        sh.rect(min(hb, ft), y0, max(hb, ft), y1, fu)                         # mattress
        p0, p1 = sorted((hb + d * 2, hb + d * 16))
        sh.rect(p0, y0 + 3, p1, cy - 2, fu); sh.rect(p0, cy + 2, p1, y1 - 3, fu)   # pillows
        n0, n1 = sorted((head_x, head_x + d * 16))
        for ny in (y0 - 18, y1):
            sh.rect(n0, ny, n1, ny + 18, fu)                                  # nightstands

    open_mid = (N_IN + hall_n - 24) / 2     # gym, guest, office: head wall from the window side to the closets
    bed(face("lounge|gym", +1), open_mid, 60, +1)
    bed(face("guest|office", -1), open_mid, 60, -1)   # guest: head on the office wall, clear of the bath door
    bed(W_IN, open_mid, 60, -1)
    bed(W_IN, (srow + S_IN) / 2, 76, -1)   # primary: the whole west wall is open

    def closet(x0, x1, label="CL"):          # 24" reach-in closets on the hall wall
        y1 = hall_n
        sh.rect(x0, y1 - 24, x1, y1, fu)
        sh.line((x0, y1 - 12), (x1, y1 - 12), fu)
        sh.text(label, (x0 + x1) / 2, y1 - 18, 4.0)

    closet(face("lounge|gym", +1), 776.0)
    closet(958.0, face("guest|office", -1))   # guest: one long closet past the door
    closet(1111.0, W_IN)                     # office: one long closet past the door

    common_bath(sh)


    p0, p1 = face("kitchen|pantry", +1), face("pantry|laundry", -1)          # pantry shelves
    pm = face("pantry|mech", -1)
    sh.rect(p0, 495.0, p0 + 16, pm, eq); sh.rect(p1 - 16, srow, p1, pm, eq)
    sh.rect(p0 + 16, pm - 16, p1 - 16, pm, eq)

    sh.circle((p0 + 13, S_IN - 13), 12.0, eq); sh.text("HPWH", p0 + 13, S_IN - 13, 3.0)   # mech
    sh.circle((p0 + 36, S_IN - 10), 9.0, eq); sh.circle((p0 + 51, S_IN - 7), 5.0, eq)
    sh.rect(p0, face("pantry|mech", +1), p0 + 22, face("pantry|mech", +1) + 22, eq)
    sh.text("RACK", p0 + 11, face("pantry|mech", +1) + 11, 3.0)

    primary_bath(sh)

    # ---- site ----------------------------------------------------------------------
    sh.rect(LOT_X0, 0, LOT_X0 + LOT_W, LOT_D, "C-PROP")
    cx0, cy0, cx1, cy1 = CARPORT
    for x0, y0 in ((cx0, cy0), (cx0, cy1 - 6)):
        sh.rect(x0, y0, x0 + 6, y0 + 6, "A-WALL")
    sh.msp.add_lwpolyline([(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)], close=True,
                          dxfattribs={"layer": "L-SITE", "linetype": "DASHED"})
    sh.text("CARPORT", (cx0 + cx1) / 2, (cy0 + cy1) / 2, 10.0, "A-AREA-IDEN")
    sh.text("18' x 20'", (cx0 + cx1) / 2, (cy0 + cy1) / 2 - 12, 6.5, "A-AREA-IDEN")
    sh.msp.add_lwpolyline(driveway_outline(), close=True, dxfattribs={"layer": "L-SITE"})
    sh.text("DRIVEWAY", (DRIVE_IN[0] + DRIVE_IN[1]) / 2 + 10, 120.0, 9.0, "A-AREA-IDEN")
    sh.rect(E + 4, N - 24, PORCH_X - 4, N, "L-SITE")                          # porch step
    sh.rect(E, N, E + 6, N + 6, "A-WALL")                                     # porch corner post (carport beam lands here)
    sh.rect(*ENTRY_COURT, "L-SITE")                                           # entry court + seat wall
    sh.text("ENTRY COURT", (ENTRY_COURT[0] + ENTRY_COURT[2]) / 2, 205.0, 6.0, "A-AREA-IDEN")
    for b in ENTRY_WALLS:
        sh.rect(*b, "A-WALL")
    sh.text('24" SEAT WALL', (ENTRY_WALLS[0][0] + ENTRY_WALLS[0][2]) / 2, 146.0, 5.0)
    # courtyard
    fy = cy1 + 3
    sh.rect(LOT_X0 + 6, fy + 1, E, fy + 61, "L-SITE"); sh.text("PAVERS", LOT_X0 + 106, fy + 31, 6.0)
    sh.rect(E - 144, fy + 1, E, LOT_D - 42, "L-SITE"); sh.text("DINING PATIO 12' x 21'", E - 72, 600.0, 5.0)
    sh.rect(E - 72 - 20, 650 - 36, E - 72 + 20, 650 + 36, fu)
    sh.rect(LOT_X0 + 18, fy + 73, E - 156, LOT_D - 54, "L-PLNT"); sh.text("LAWN", (LOT_X0 + 18 + E - 156) / 2, 640.0, 7.0)
    sh.rect(LOT_X0 + 6, LOT_D - 42, E, LOT_D - 6, "L-PLNT"); sh.text("RAISED PLANTERS", (LOT_X0 + E) / 2, LOT_D - 24, 5.0)
    sh.line((LOT_X0, fy), (160, fy), "A-FENC"); sh.line((208, fy), (E, fy), "A-FENC")
    sh.text("6' FENCE / GATE", 184, fy - 10, 4.0)
    sh.rect(LOT_X0 + 6, 262, LOT_X0 + 54, 382, "L-SITE"); sh.text("BINS", LOT_X0 + 30, 322, 5.0, rot=90)        # bin pad
    hx = (face("pantry|laundry", +1) + face("laundry|bath", -1)) / 2                   # heat pump outdoor
    sh.rect(hx - 21, S + 10, hx + 21, S + 30, "A-EQPM")                                 # unit behind the laundry
    sh.rect(hx - 27, S + 4, hx + 27, S + 36, "A-FENC")                                  # dog guard
    sh.text("HP", hx, S + 20, 5.0)
    sh.line((LOT_X0, 386), (LOT_X0 + 60, 386), "A-FENC"); sh.line((LOT_X0 + 60, 386), (LOT_X0 + 60, 258), "A-FENC")
    sh.line((W, N), (W + 20, N), "A-FENC"); sh.line((W + 68, N), (LOT_X0 + LOT_W, N), "A-FENC")  # west fence
    sh.text("6' FENCE + GATE", (W + LOT_X0 + LOT_W) / 2, N - 10, 4.0)

    # ---- dimensions ----------------------------------------------------------------
    yb = LOT_D + 28
    for x0, x1, lab in ((LOT_X0, cx0, None), (cx0, E, None), (E, W, None), (W, LOT_X0 + LOT_W, None)):
        sh.dim((x0, LOT_D), (x1, LOT_D), (0, yb), lab or fmt(x1 - x0))
    sh.dim((LOT_X0, 0), (LOT_X0 + LOT_W, 0), (0, -30), fmt(LOT_W))
    xv = W + 40
    for y0, y1 in ((0, N), (N, S), (S, LOT_D)):
        sh.dim((W, y0), (W, y1), (xv, 0), fmt(y1 - y0), angle=90)

    # ---- true north, title -----------------------------------------------------
    t = math.radians(PLAN_NORTH_AZ)
    ux, uy = math.sin(t), -math.cos(t)
    bx, by, L = 1060.0, 210.0, 100.0
    tip = (bx + ux * L, by + uy * L)
    sh.line((bx, by), tip, "A-ANNO-TEXT")
    hx, hy = -uy, ux
    base = (tip[0] - ux * 18, tip[1] - uy * 18)
    sh.msp.add_solid([tip, (base[0] + hx * 7, base[1] + hy * 7), (base[0] - hx * 7, base[1] - hy * 7)],
                     dxfattribs={"layer": "A-ANNO-TEXT"})
    sh.text("TRUE N", tip[0] + ux * 14, tip[1] + uy * 14, 11.0)
    sh.text("PLAN NORTH (STREET) ↓", LOT_W / 2, -70.0, 12.0)
    sh.text("ACCOSTING REBUILD - OWNER SCHEMATIC (NOT FOR CONSTRUCTION)", LOT_W / 2, LOT_D + 95, 16.0)
    sh.text(f"Walls: exterior {EXT:g}\", interior {INT:g}\", plumbing {WET:g}\". "
            "Room sizes are clear (finish face to finish face).", LOT_W / 2, LOT_D + 75, 8.0)
    return sh


def render(doc, png: Path, x0, y0, x1, y1, width_in=20, dpi=110):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    fig = plt.figure(figsize=(width_in, width_in * (y1 - y0) / (x1 - x0)))
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR,
                        lineweight_scaling=1.5)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(
        doc.modelspace(), finalize=False)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")
    png.parent.mkdir(exist_ok=True)
    try:
        fig.savefig(png, dpi=dpi)
    except OSError:                    # locked by a Windows image viewer
        import time
        png = png.with_name(f"{png.stem}-{time.strftime('%H%M%S')}{png.suffix}")
        fig.savefig(png, dpi=dpi)
    plt.close(fig)
    print("  ", png.relative_to(ROOT))


def main():
    sh = build()
    sh.doc.saveas(OUT)
    print("wrote", OUT.name)
    render(sh.doc, RENDERS / "schematic.png", -40, -110, LOT_W + 140, LOT_D + 130, dpi=220)
    render(sh.doc, RENDERS / "schematic-zoom.png", E - 20, N - 40, W + 20, S + 30, width_in=24, dpi=250)
    print("rendered")


if __name__ == "__main__":
    main()
