# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4", "matplotlib", "shapely>=2"]
# ///
"""Owner schematic, drawn from scratch (no designer content).

Reproduces the current owner-edits layout (through step 21) with real wall
thicknesses and writes a clean DXF + PNG:

    accosting-owner-schematic.dxf
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
OUT = ROOT / "accosting-owner-schematic.dxf"
RENDERS = ROOT / "renders"

# =============================================================================
# DATA
# =============================================================================
EXT = 9.0      # exterior: 1/2" gyp + 2x6 + 1/2" sheathing + 1" rigid insul. + 7/8" stucco
INT = 4.5      # interior: 2x4 + 1/2" gyp each side
WET = 6.5      # plumbing walls: 2x6 + 1/2" gyp each side

LOT_W, LOT_D = 1356.0, 777.25        # 113.00' x 64.77' per the topographic survey (private/survey)
LOT_X0 = 2.0                         # x of the east property line (side setbacks: 10% of LOT_W each)
E, W, N, S = 356.1, 1220.0, 243.2, 619.2   # house outer faces (72' x 31'-4")
E_IN, W_IN, N_IN, S_IN = E + EXT, W - EXT, N + EXT, S - EXT

# Corner porch notch (outer faces) at the north-east corner.
PORCH_X, PORCH_Y = 444.1, 291.2      # notch is E..PORCH_X by N..PORCH_Y
FOYER_WALL_END = PORCH_Y + EXT + 108.0   # foyer/TV wall: 9' of foyer inside the front wall
# Hearth bench: a built-in bench on the lounge's TV wall, centred on the TV: from just past the reeded porch-side
# window to just short of the foyer-to-hall walkway. Framed and drywalled on a recessed base (it reads as
# floating); a linear electric fireplace in its face under the TV, a matching cubby each side. The street-wall
# corner by the reeded window stays open floor.
HEARTH_D = 21.0                          # deep enough for a receiver in a cubby
TV_CY = (305.0 + 396.0) / 2 - 9.0        # 90" TV centre line: about centred on the wall
HEARTH_Y = (2 * TV_CY - 398.0, 398.0)    # symmetrical about the TV, its walkway end just short of the walkway
HEARTH_FIRE = (TV_CY - 30.0, TV_CY + 30.0)   # 60" linear electric fireplace, centred under the TV
HEARTH_CUBBIES = [(HEARTH_FIRE[0] - 24.0, HEARTH_FIRE[0] - 4.0),    # two matching 20" cubbies, one each side
                  (HEARTH_FIRE[1] + 4.0, HEARTH_FIRE[1] + 24.0)]    # of the fireplace (4" between)
# Porch: a qualifying covered entry porch under Table 22.140.520-D (8' x 5', ceiling no more than 12' above
# its floor). It runs 1' past the house front toward the street (a covered porch may project up to 5' into
# the front yard, §22.110.090.D.2) under a slim canopy at the porch ceiling's height, and 8" east into the
# carport's walkway; the front door stays at the back of the notch.
PORCH_FWD, PORCH_EAST = 12.0, 8.0
PORCH_OUT = (E - PORCH_EAST, N - PORCH_FWD)    # the porch's outer corner (x, y)
# Carport: its roof is in line with the house front, so the walk to the porch stays covered, but its front
# 4' (to the front door's line) is a covered walkway, not parking: with the qualifying porch, the parking
# needs only to sit no closer to the street than the front door (§22.140.520 b.i).
CARPORT_WALK, STALL_W, STALL_D = PORCH_Y - N, 102.0, 216.0
CARPORT = (140.1, N, E, N + CARPORT_WALK + STALL_D)   # x0, y0, x1, y1: 18' x 22'
CARPORT_ROOF = (CARPORT[0] - 6, PORCH_OUT[1], E, CARPORT[3] + 6)   # 6" past the posts; its front edge in line
                                                                   # with the porch canopy's
# Driveway: straight and the carport's full 18' width from the edge of pavement (no curb on Laurel
# Drive) to the carport; the lot tree and the east parkway olive and ficus in its way are removed.
EXIST_TREES = [(1255.0, -112.0), (1087.0, -98.0), (1019.0, -110.0)]   # survey trunks: the mature olives
                                                                        # in the northwest parkway
REMOVED_TREES = [(107.0, 158.0, "EXIST. DEAD TREE"), (322.0, -114.0, "EXIST. OLIVE"),   # in the driveway's way;
                 (160.0, -86.0, "EXIST. FICUS")]                                     # ficus ~13'-6" east of the olive (survey rev. 102a)
GATE_L = 168.0                       # courtyard gate behind the carport: 14' wide, hinged at the house corner,
                                     # it opens flat against the house wall, joining carport and courtyard
FRONT_TREE = (880.0, 40.0)           # new: front yard, in front of the bedroom wing, ~17' from the house front
                                     # (fuel modification: canopy well clear of the roof), clear of the olives
PRIVACY_TREE = (624.0, 28.0)         # new: inside the front line, west of the lounge window's centre, 15'+ from the eaves,
                                     # 10'+ from the sewer run to the cleanout (survey ~(492, 22))
EDGE_OF_PAVEMENT = -160.0            # y of the street's edge of pavement (survey)
# Entry court in front of the porch, edged on the street side by a 24" seat wall (8" block) that
# returns to the house just short of the lounge window; you walk in from the driveway side.
ENTRY_COURT = (E, 156.0, 504.0, N)   # x0, y0, x1, y1
ENTRY_WALLS = [(E + 36.0, 156.0, 504.0, 164.0), (496.0, 164.0, 504.0, N)]
ENTRY_WALL_H = 24.0
PLAN_NORTH_AZ = 22.4                 # azimuth of plan north: survey side lines N22°23'00"E

NOTICE = ("\u00a9 2026 Richard Acosta. All rights reserved. For 220 Laurel Dr only: "
          "not to be copied, adapted or built from anywhere else.")

# The bedroom hall ends in a wall just past the office and primary doors; beyond it, the hall's last
# stretch is the primary bedroom's reading nook. Halfway down, just past the common bath, a cased opening
# with a dropped header marks the bedroom end (no door).
HALL_END = 1110.5                    # centreline of the hall's end wall
HALL_N = 407.2                       # centreline of the hall's north (bedroom) wall
HALL_S = HALL_N + INT + 44.0         # centreline of the hall's south wall: a 3'-8" clear hall
KITCHEN_ROW = 461.45                 # front line of the kitchen peninsula and fridge (the lounge's south edge)
WIC_D = 84.0                         # primary walk-in closet depth: 24" hanging + 36" aisle + 24" hanging
SHOWER_W = 74.0                      # primary shower: 6'-2" from the common bath wall
SHOWER_WIN = (912.0, 936.0)          # primary shower: high strip window, the two heads 18" either side of its centre
SHOWER_BENCH_D = 16.0                # primary shower: solid bench along the closet wall
SHOWER_ENTRY = 30.0                  # primary shower: walk-in entry by the rear wall
NOOK_CEIL = 90.0                     # reading nook: lowered ceiling at 7'-6" (the room's is 9'), built-in cabinets
NOOK_CAB_D = 24.0                    # above it with doors facing the bedroom; the nook window's head meets it
HALL_ARCH = 883.5                    # centreline of the threshold wall: in line with the walk-in closet's end
                                     # wall, just past the common bath door
ARCH_HEAD = 90.0                     # its dropped header: 7'-6" under the 9' ceiling
HALL_CL_DOOR = (HALL_ARCH + INT / 2 + 3.5, HALL_ARCH + INT / 2 + 27.5)   # hall closet: a 24" door (7'-6", in line
                                     # with the header), 3 1/2" past the opening's stub for casing
HALL_CL_W, HALL_CL_D = HALL_CL_DOOR[1] + 1.5 - (HALL_ARCH + INT / 2), 24.0   # in the walk-in closet's corner
PART = 3.5                           # its two walls to the walk-in closet: 2x3 + 1/2" gyp each side
HATCH_X = 954.0                         # attic access panel (22" x 54", passes the air handler) along the hall,
                                        # from here west: room for a recessed light either side of it (about 5'-8"
                                        # to the header, 5'-1" to the skylight), beside the air handler platform
HALL_TUBE = HALL_END - INT / 2 - 32.0   # 14" tubular skylight on the hall's centreline, 2'-8" short of the end
                                        # wall: lights the end wall

# Interior walls: (name, axis, centreline, from, to, thickness).
# axis "x" = wall runs along x at y = centreline; "y" = runs along y at x = centreline.
WALLS = [
    ("foyer wall",        "y", PORCH_X + EXT - INT / 2, PORCH_Y, FOYER_WALL_END, INT),
    ("lounge|gym",       "y", 674.0,  N_IN, HALL_N + INT / 2, INT),   # in line with the kitchen|pantry wall
    ("gym|ensuite",       "y", 826.0,  N_IN, HALL_N + INT / 2, WET),
    ("ensuite|guest",    "y", 897.5,  N_IN, HALL_N + INT / 2, INT),
    ("guest|office",     "y", 1062.0, N_IN, HALL_N + INT / 2, INT),
    ("bedroom hall wall", "x", HALL_N,  671.75, W_IN, INT),
    ("south hall wall",   "x", HALL_S, 671.75, HALL_END + INT / 2, INT),
    ("hall end",          "y", HALL_END, HALL_N, HALL_S, INT),      # the reading nook behind it
    ("hall threshold",    "y", HALL_ARCH, HALL_N, HALL_S, INT),     # cased opening, dropped header
    ("kitchen|pantry",    "y", 674.0,  HALL_S - INT / 2, S_IN, INT),
    ("pantry|laundry",    "y", 750.0,  HALL_S - INT / 2, S_IN, INT),
    ("pantry|mech",       "x", 555.2,  674.0, 750.0, INT),
    ("laundry|bath",      "y", 826.0,  HALL_S - INT / 2, S_IN, WET),   # 52" clear bath, full depth
    ("bath|storage",      "x", 566.0 + INT / 2, 826.0, 883.5, INT),  # storage behind the bath
    ("utility|bath",      "y", 883.5,  HALL_S - INT / 2, S_IN, INT),   # 2x4: nothing plumbed in it
    ("bath|wic",          "x", HALL_S + INT / 2 + WIC_D + WET / 2, 883.5, 1062.0, WET),   # closet 7' deep; plumbing
                                                                                 # wall (WC, double vanity)
    ("suite|primary",     "y", 1062.0, HALL_S - INT / 2, S_IN, INT),
    ("hall closet|wic",   "x", HALL_S + INT / 2 + HALL_CL_D + PART / 2, 883.5,
     HALL_ARCH + INT / 2 + HALL_CL_W + PART, PART),                          # hall closet's back wall
    ("hall closet|wic end", "y", HALL_ARCH + INT / 2 + HALL_CL_W + PART / 2, HALL_S,
     HALL_S + INT / 2 + HALL_CL_D + PART, PART),                             # and its side wall
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
    ("north",       502.4, 622.4, "window"),             # lounge 10' (centred)
    ("north",       714.0, 786.0, "window"),             # gym 6' (centred)
    ("north",       847.25, 877.25, "window", 78.0, 96.0),  # guest ensuite: high window above the shower spray
    ("north",       943.75, 1015.75, "window"),          # guest 6'
    ("north",       1101.6, 1173.6, "window"),           # office 6'
    ("porch front", 385.0, 423.0, "door", "a", +1),      # front door 36", opens flat against the east wall
    ("porch side",  255.0, 279.0, "window"),             # reeded glass
    ("south",       384.0, 528.0, "window", 24.0, 96.0),  # dining: one 12' window (two 6' x 6' units, a common
                                                          # size), sill below the table top; centred on the wall and table
    ("south",       588.0, 648.0, "window", 42.0, 96.0),  # kitchen sink, 5' (clear of the corner cabinets): sill just above the backsplash
    ("south",       *SHOWER_WIN, "window", 84.0, 96.0),   # primary shower: 2'-0" x 1'-0" strip above and between the
                                                           # two heads (stud bays either side clear for their drops)
    ("south",       766.5, 808.5, "window", 72.0, 96.0),  # laundry: 3'-6" x 2'-0" high window, matching the tub's
    ("south",       978.0, 1020.0, "window", 72.0, 96.0),  # primary bath: 3'-6" x 2'-0" high window over the walkway
    ("south",       1101.6, 1173.6, "window"),           # primary bedroom 6' (centred; faces SSW, so kept modest)
    ("west",        289.6, 337.6, "window", 72.0, 96.0),    # office: 4'-0" x 2'-0" high window over the bed head
                                                          # (cross-breeze, privacy from the neighbour's 2nd floor)
    ("west",        415.45, 451.45, "window", 42.0, NOOK_CEIL - 6.0),  # reading nook: 3'-0" x 3'-6", its head 6"
                                                                     # below the lowered ceiling: 3'-0" x 4'-0", centred on the nook,
                                                          # light over the reader's shoulder from the bench
    ("east",        516.0, 588.0, "slider"),             # dining 6' slider: ~4" past the courtyard fence's post,
                                                          # leaving ~2'-7" of solid wall at the dining corner
    # interior
    ("bedroom hall wall", 781.5, 817.5, "door", "b", -1),   # gym
    ("ensuite|guest", 335.0, 365.0, "door", "a", +1),       # guest ensuite's only door: swings into the guest room (the bath is narrow)
    ("bedroom hall wall", 906.5, 942.5, "door", "a", -1),  # guest
    ("bedroom hall wall", 1067.0, 1103.0, "door", "a", -1), # office: at the guest-wall end, by the hall's end
    ("south hall wall", 682.5, 712.5, "door", "a", +1),     # pantry (by the fridge)
    ("south hall wall", 760.0, 790.0, "door", "a", +1),     # laundry
    ("south hall wall", 847.75, 877.75, "door", "b", +1),   # common bath, 30", by its west wall (3 1/2" for casing
                                                            # beside the cased opening's stub)
    ("south hall wall", *HALL_CL_DOOR, "door", "b", -1),    # hall closet: opens into the hall, hinged away from
                                                            # the cased opening so it folds back along the hall wall
    ("south hall wall", 1070.0, 1106.0, "door", "b", +1),   # primary bedroom, at the closet corner: hinged on its
                                                            # far side, so the open door never blocks the closet door
    ("hall threshold", 413.2, 449.2, "cased", 0.0, ARCH_HEAD),  # 3'-0" opening under a 7'-6" header
    ("pantry|laundry", 577.2, 607.2, "bifold", "a", +1),    # mech closet (louvered)
    ("laundry|bath", 574.0, 606.0, "cased"),                # storage room, open to the laundry
    ("suite|primary", 576.0, 606.0, "door", "b", -1),       # primary bath, 30", from the bedroom; opens flat by the rear wall
    ("suite|primary", HALL_S + 4.0, HALL_S + 34.0, "door", "a", -1),       # walk-in closet, 30": swings in, opens flat by the hall wall
]

# Street-facade articulation (County building articulation, Table 22.140.520-C): the punched street windows
# (lounge, gym, guest, office, guest ensuite) are recessed into the wall, over 50% of the facade's window area;
# the clerestory band stays flush. At the rear, flat metal canopies shade the kitchen and primary bedroom
# windows; each runs 1' past its window and no farther (22.110.090.B).
WINDOW_RECESS = 6.0                  # glass behind the stucco face
CANOPY_D, CANOPY_RUN, CANOPY_Z = 36.0, 12.0, 98.0   # depth off the wall, run past each side, underside


def canopies(wall=None):
    """[(wall, x0, x1)] of the window canopies: the kitchen and primary bedroom windows at the rear
    (the standard-sill ones: not the dining window's lower sill or the baths' and laundry's high ones)."""
    out = []
    for o in OPENINGS:
        sill = o[4] if len(o) > 4 else 30.0
        if o[3] == "window" and o[0] == "south" and 30 <= sill < 60:
            out.append((o[0], o[1] - CANOPY_RUN, o[2] + CANOPY_RUN))
    return [c for c in out if wall in (None, c[0])]


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


# The hall skylight is centred in the hall, in line with its lights; in the attic its tube jogs toward the
# street (two adjustable elbows) to a dome on the gable's street slope just below the ridge, off the solar area.
HALL_TUBE_Y = (face("bedroom hall wall", +1) + face("south hall wall", -1)) / 2


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
        self.movable = []                   # loose furniture (beds, sofa, table...): left off permit drawings
        for name, color in [("A-WALL", 7), ("A-WALL-PATT", 8), ("A-DOOR", 3), ("A-GLAZ", 4),
                            ("A-FURN", 9), ("A-EQPM", 6), ("A-AREA-IDEN", 7), ("A-ANNO-DIMS", 1),
                            ("A-ANNO-TEXT", 7), ("C-PROP", 5), ("L-SITE", 94), ("L-PLNT", 3),
                            ("A-FENC", 8), ("A-CLNG", 8), ("A-CANP", 8)]:
            self.doc.layers.add(name, color=color)
        st = self.doc.dimstyles.new("OWNER")
        st.dxf.dimtxt, st.dxf.dimasz, st.dxf.dimexo, st.dxf.dimexe = 8.0, 6.0, 3.0, 3.0
        st.dxf.dimtsz = 4.0                 # architectural ticks
        st.dxf.dimgap = 2.0

    def mark(self):
        return len(self.msp)

    def movable_since(self, n):
        self.movable += list(self.msp)[n:]

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
    """66" x 32" alcove tub with a shower head across the window end. Tub drain, valve and
    head, the WC and the vanity all on the east (plumbing) wall shared with the gym."""
    c0, c1 = face("gym|ensuite", +1), face("ensuite|guest", -1)          # 66" clear: tub wall to wall
    hall = face("bedroom hall wall", -1)
    ty = N_IN + 32.0
    tub(sh, c0, N_IN, c0 + 66.0, ty, "TUB 66x32")
    sh.circle((c0 + 4, N_IN + 16), 2.0, "A-EQPM")                     # shower head + valve, plumbing wall
    sh.heads.append((c0, N_IN + 16, 1.0, 0.0))
    sh.line((c0, ty + 1), (c0 + 66.0, ty + 1), "A-EQPM")              # curtain rod
    wc(sh, c0, ty + 2, c0 + 28, ty + 32)                               # 17" to the tub
    vanity(sh, c0, ty + 41, c0 + 21, ty + 89, "VANITY 48", rot=90)     # 24" from the WC centreline
    sh.rect(c0, hall - 18, c1, hall, "A-FURN")                               # wall-to-wall linen closet in the
    sh.line((c0, hall - 18), (c1, hall - 18), "A-DOOR")                       # old hall-door space, opening
    sh.text("LINEN CLOSET", (c0 + c1) / 2, hall - 9, 3.0)                    # into the bath (bifold doors)
    room_label(sh, "GUEST ENSUITE", c0, N_IN, c1, hall, cx=(c0 + 21 + c1) / 2 + 1, cy=ty + 55, h=3.4)


def primary_bath(sh):
    """No tub: a 6' curbless double shower at the plumbing-wall end, with two heads on the rear wall and their
    valves by the walk-in entry, a solid bench along the closet wall facing them; WC and double vanity on the
    closet (north) wall; door from the bedroom at the rear-wall end."""
    m0, m1 = face("utility|bath", +1), face("suite|primary", -1)
    top = face("bath|wic", +1)
    gx = m0 + SHOWER_W
    wet_zone(sh, m0, top, gx, S_IN)
    for hx in (sum(SHOWER_WIN) / 2 - 18, sum(SHOWER_WIN) / 2 + 18):    # two heads on the rear wall, 36" apart,
        shower_head(sh, hx, S_IN, -1)                                  # spraying toward the closet wall; supplies
    sh.text("VALVES", gx - 7, S_IN - 9, 1.8, rot=90)                   # drop from the attic beside the window
    sh.rect(m0, top, gx, top + SHOWER_BENCH_D, "A-EQPM")               # solid bench, full width, facing the heads
    sh.text("BENCH (SOLID)", (m0 + gx) / 2, top + SHOWER_BENCH_D / 2, 2.2)
    n0, n1 = SHOWER_WIN                                                # niche in the rear wall between the heads,
    for p0, p1 in (((n0, S_IN), (n0, S_IN + 3.5)), ((n0, S_IN + 3.5), (n1, S_IN + 3.5)),
                   ((n1, S_IN + 3.5), (n1, S_IN))):                     # below the window and its width (lines:
        sh.line(p0, p1, "A-EQPM")                                      # a recess, not a 3D box)
    sh.text("NICHE", sum(SHOWER_WIN) / 2, S_IN - 4, 1.6)
    sh.text("CURBLESS SHOWER", (m0 + gx) / 2, top + SHOWER_BENCH_D + 9, 2.6)
    glass(sh, (gx, top), (gx, S_IN - SHOWER_ENTRY))                    # fixed panel from the closet wall; walk-in
                                                                       # entry by the rear wall (drain: plumbing notes)
    wc(sh, gx + 2.25, top, gx + 32.25, top + 28)                       # north wall: 17.25" to glass, 22.5" to vanity
    vanity(sh, m1 - 60, top, m1, top + 22, "DOUBLE VANITY 60")
    sh.text("HIGH WINDOW ABOVE, SILL 7'", (m0 + gx) / 2, S_IN - 16, 1.6)
    sh.text("HIGH WINDOW", 999.0, S_IN - 4, 2.0)
    room_label(sh, "PRIMARY BATH", m0, top, m1, S_IN, cx=(gx + m1) / 2, cy=S_IN - 14, h=2.6)


def utility_block(sh):
    """Common bath and laundry side by side (labels + fixtures); experiments can swap this."""
    eq, fu = "A-EQPM", "A-FURN"
    hall = face("south hall wall", +1)
    l0, lw = face("pantry|laundry", +1), face("laundry|bath", -1)            # laundry galley
    b0, b1 = face("laundry|bath", +1), face("utility|bath", -1)              # bath
    be = face("bath|storage", -1)
    # bath: sink, toilet, then a curbless shower across the end; sink, toilet and shower drain on the laundry
    # wall (one plumbing wall for both rooms); the door is at the west end, so the toilet is out of view from
    # the lounge. The shower's valve and head are on its end wall at the entry, spraying away from it
    vanity(sh, b0, 468.0, b0 + 20, 492.0, "SINK", rot=90)    # clear of the door's swing
    wc(sh, b0, 497.0, b0 + 28, 527.0)
    gy = 530.0                                                               # shower: full width x 36"
    wet_zone(sh, b0, gy, b1, be)
    sh.rect(b0, gy, b1, be, eq)
    glass(sh, (b0, gy), (b1 - 24, gy))                                       # 24" open entry, door side
    sh.text("SHOWER", (b0 + b1) / 2, gy + 14, 3.2)
    hy = gy + 20.0                                                           # head on the end wall (the primary
    sh.heads.append((b1, hy, -1.0, 0.0))                                     # suite's), spraying down the shower's
    sh.circle((b1 - 2.5, hy), 2.5, eq)                                       # length, away from the entry
    for dy in (-5.0, 0.0, 5.0):
        sh.line((b1 - 5.5, hy + dy * 0.4), (b1 - 11.0, hy + dy), eq)
    sh.text("VALVE", b1 - 5, gy + 6, 1.6)                                    # valve beside the entry
    drain(sh, (b0 + 3, be - 3), (b1 - 3, be - 3))
    room_label(sh, "COMMON BATH", b0, hall, b1, be, cx=b1 - 12, cy=505.0, h=2.4)
    sh.msp.add_circle((b1 - 13, 520.0), 6.0, dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})   # 10" tube
    sh.text("SKYLIGHT", b1 - 13, 520.0, 1.6, "A-CLNG")                     # skylight + exhaust fan
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
    sh.rect(l0, 496.0, l0 + 4, 516.0, eq); sh.text("PANEL", l0 + 10, 506.0, 2.5, rot=90)   # past the open door
    sh.rect(l0 + 12, S_IN - 12, lw - 12, S_IN, fu)                           # rear wall: full-height shelves
    sh.text("SHELVES TO 6'", (l0 + lw) / 2, S_IN - 6, 2.2)                  # up to the high window's sill
    room_label(sh, "LAUNDRY", l0, hall, lw, S_IN, cx=(l0 + lw) / 2 - 8, cy=582.0, h=4.0)


def wic(sh):
    """Walk-in closet: hanging on both long walls (the hall side starting past the hall closet and stopping
    short of the bedroom wall for the door's landing), corner shelves and a drawer stack on the end wall.
    The hall closet takes the hall-side corner, opening onto the hall."""
    x0, x1 = face("utility|bath", +1), face("suite|primary", -1)
    y0, y1 = face("south hall wall", +1), face("bath|wic", -1)
    fu = "A-FURN"

    def hang(a, b, y, d):                   # 24"-deep hanging section with its rod
        sh.rect(a, min(y, y + d * 24), b, max(y, y + d * 24), fu)
        sh.line((a, y + d * 12), (b, y + d * 12), fu)
        sh.text("HANG", (a + b) / 2, y + d * 18, 3.0)

    hx, cy = face("hall closet|wic end", +1), face("hall closet|wic", +1)
    hang(hx, 1023.0, y0, +1)                # entry side: from the hall closet to 3' short of the bedroom wall
    hang(x0 + 24, x1, y1, -1)               # far side runs to the bedroom wall
    sh.rect(x0, y1 - 24, x0 + 24, y1, fu)   # end wall: corner shelves (shoes, folded, bags) and a drawer stack
    sh.text("SHELVES", x0 + 12, y1 - 12, 2.2)
    sh.rect(x0, cy, x0 + 20, y1 - 24, fu)
    sh.text("DRAWERS", x0 + 10, (cy + y1 - 24) / 2, 2.2, rot=90)
    room_label(sh, "WIC", x0, y0, x1, y1, cx=1000.0, h=5.0)
    c1, cb = face("hall closet|wic end", -1), face("hall closet|wic", -1)   # hall closet: shelves at the back
    sh.rect(x0, cb - 14, c1, cb, fu); sh.text("SHELVES", (x0 + c1) / 2, cb - 7, 1.8)
    sh.text("HALL CLOSET", (x0 + c1) / 2, cb - 18, 1.6)


def carport_size():
    """The carport's size label, e.g. 18' x 23'."""
    cx0, cy0, cx1, cy1 = CARPORT
    return f"{round((cx1 - cx0) / 12)}' x {round((cy1 - cy0) / 12)}'"


def driveway_outline():
    """Closed outline of the driveway, parkway apron included (lot inches)."""
    cx0, cy0, cx1, _ = CARPORT
    return [(cx0, EDGE_OF_PAVEMENT), (cx1, EDGE_OF_PAVEMENT), (cx1, cy0), (cx0, cy0)]


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
        elif kind == "cased" and len(o) > 5:   # dropped header over the opening: dashed, with its height
            for v in (-t / 2, t / 2):
                sh.msp.add_line(P(a, v), P(b, v), dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
            mx, my = P((a + b) / 2, -t / 2 - 8)
            sh.text(f"HEADER AT {fmt(o[5])}", mx, my, 2.4, "A-CLNG", rot=90 if axis == "y" else 0)
        # other cased openings: just the gap

    # ---- rooms: labels with clear sizes ---------------------------------------
    def room(*a, **k):
        room_label(sh, *a, **k)

    hall_n, hall_s = face("bedroom hall wall", -1), face("south hall wall", -1)   # bedroom / lobby faces
    srow = face("south hall wall", +1)
    pen_out, pen_in = 546.9, 598.0
    room("FOYER", E_IN, PORCH_Y + EXT, face("foyer wall", -1), FOYER_WALL_END, cx=410.0, cy=385.0, h=6.0)
    room("LOUNGE", face("foyer wall", +1), N_IN, face("lounge|gym", -1), KITCHEN_ROW - INT, cx=600.0, cy=428.0)
    room("DINING", E_IN, KITCHEN_ROW, pen_out, S_IN, cy=592.0)
    room("KITCHEN", pen_out, KITCHEN_ROW, face("kitchen|pantry", -1), S_IN, cx=622.0, cy=545.0, h=7.0)
    room("GYM", face("lounge|gym", +1), N_IN, face("gym|ensuite", -1), hall_n, cy=272.0)
    room("GUEST", face("ensuite|guest", +1), N_IN, face("guest|office", -1), hall_n, cy=272.0)
    room("OFFICE", face("guest|office", +1), N_IN, W_IN, hall_n, cy=272.0)
    room("PANTRY", face("kitchen|pantry", +1), srow, face("pantry|laundry", -1), face("pantry|mech", -1), h=5.5)
    room("MECH", face("kitchen|pantry", +1), face("pantry|mech", +1), face("pantry|laundry", -1), S_IN,
         cy=575.0, h=5.0)
    utility_block(sh)
    wic(sh)
    room("PRIMARY", face("suite|primary", +1), srow, W_IN, S_IN, cx=(face("suite|primary", +1) + W_IN - 80) / 2)
    hx0, hy = HATCH_X, (face("bedroom hall wall", +1) + hall_s) / 2      # attic access panel in the hall,
    sh.msp.add_lwpolyline([(hx0, hy - 12.75), (hx0 + 54, hy - 12.75), (hx0 + 54, hy + 12.75),
                           (hx0, hy + 12.75)], close=True,             # across from the closet wall
                          dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    sh.text("ATTIC HATCH", hx0 + 27, hy, 2.6, "A-CLNG")
    sh.msp.add_circle((HALL_TUBE, HALL_TUBE_Y), 8.0, dxfattribs={"layer": "A-CLNG", "linetype": "DASHED"})
    sh.text('14" SKYLIGHT', HALL_TUBE, HALL_TUBE_Y, 1.6, "A-CLNG")
    sh.text("LOBBY", (HATCH_X + 54 + HALL_TUBE - 9) / 2, (face("bedroom hall wall", +1) + hall_s) / 2, 7.0, "A-AREA-IDEN")
    sh.text("PORCH", (E + PORCH_X) / 2, (N + PORCH_Y) / 2, 7.0, "A-AREA-IDEN")

    # ---- fixtures & furniture (simple symbols) --------------------------------
    eq, fu = "A-EQPM", "A-FURN"
    kw = face("kitchen|pantry", -1)
    sh.rect(pen_out, KITCHEN_ROW, pen_in, S_IN, eq)                           # peninsula
    sh.rect(pen_in - 24, S_IN - 48, pen_in, S_IN - 24, eq)                     # dishwasher: peninsula, kitchen
    sh.text("DW", pen_in - 12, S_IN - 36, 3.5)                                 # side, around the corner from the sink
    sh.rect(pen_in - 24, S_IN - 72, pen_in, S_IN - 48, eq)                     # 24" triple pull-out beside the DW:
    sh.text("TRASH", pen_in - 12, S_IN - 60, 3.0)                              # trash, recycling, food scraps
    py0 = 497.0                                                               # prep sink: peninsula, kitchen side,
    sh.rect(pen_in - 20, py0, pen_in - 4, py0 + 16, eq)                       # across from the fridge/range gap
    sh.text("PREP SINK", pen_in - 12, py0 + 8, 2.2, rot=90)
    sh.rect(pen_out, S_IN - 15, pen_out + 24, S_IN, eq)                        # 15" drink fridge under the counter,
    sh.text("BEV", pen_out + 12, S_IN - 7.5, 3.0)                              # stool side, corner by the south wall
    sh.line((pen_out + 15, KITCHEN_ROW), (pen_out + 15, S_IN), eq)            # 15" overhang
    sh.rect(pen_in, S_IN - 24, kw, S_IN, eq)                                  # sink run, into the corner
    ta, r0 = KITCHEN_ROW + 36 + 15, KITCHEN_ROW + 36 + 15 + 12                # range wall: tall cabinet,
    tb = r0 + 30 + 15                                                         # 12" landing, range, 15"
    sh.rect(kw - 24, ta, kw, tb, eq)                                          # landing, tall cabinet
    for y0, y1 in ((KITCHEN_ROW + 36, ta), (tb, S_IN - 24)):
        sh.rect(kw - 24, y0, kw, y1, eq); sh.text("TALL STORAGE", kw - 12, (y0 + y1) / 2, 1.6, rot=90)
    sh.rect(kw - 24, r0, kw, r0 + 30, eq); sh.text("RANGE", kw - 12, r0 + 15, 3.5, rot=90)
    sh.rect(kw - 30, KITCHEN_ROW, kw, KITCHEN_ROW + 36, eq); sh.text("FRIDGE", kw - 15, KITCHEN_ROW + 18, 3.5, rot=90)
    sh.rect(603.0, S_IN - 20, 633.0, S_IN - 4, eq); sh.text("SINK", 618.0, S_IN - 12, 3.0)   # centred under its window
    m0 = sh.mark()
    for y in (476.7, 512.9, 544.5):                                           # 3 stools
        sh.circle((pen_out - 8, y), 7.5, fu)
    dcx = (E_IN + pen_out) / 2                                                # dining table
    sh.rect(dcx - 20, 523 - 42, dcx + 20, 523 + 42, fu)                      # 84" x 40" table
    for dy in (-28, 0, 28):                                                   # 8 chairs: 3 a side + ends
        sh.circle((dcx - 28, 523 + dy), 7, fu); sh.circle((dcx + 28, 523 + dy), 7, fu)
    for y in (523 - 51, 523 + 51):
        sh.circle((dcx, y), 7, fu)
    seat_cy = (305.0 + 396.0) / 2           # centre of the sectional's seating area
    tv = face("foyer wall", +1)
    hx, (hy0, hy1) = tv + HEARTH_D, HEARTH_Y              # hearth bench (drawn before the TV, whose label sits
    sh.rect(tv, hy0, hx, hy1, fu)                          # over it: the 3D model reads the first label inside)
    sh.text("HEARTH BENCH", tv + 16, TV_CY - 12, 3.0, rot=90)       # clear of the TV label's search box
    for (a, b), lab in ((HEARTH_FIRE, "ELEC. FIREPLACE"), *((c, "CUBBY") for c in HEARTH_CUBBIES)):
        for p, q in (((hx - 3, a), (hx, a)), ((hx - 3, b), (hx, b)), ((hx - 3, a), (hx - 3, b))):
            sh.line(p, q, "A-EQPM")                        # openings in the bench face
        sh.text(lab, hx + 6, (a + b) / 2, 2.5 if lab == "CUBBY" else 3.0, rot=90)
    sh.rect(tv, TV_CY - 39.25, tv + 3, TV_CY + 39.25, fu); sh.text('TV 90"', tv + 8, TV_CY, 4.0, rot=90)   # 90" TV
    sh.msp.add_lwpolyline([(505.0, 267.0), (635.0, 267.0), (635.0, 396.0), (597.0, 396.0), (597.0, 305.0),
                           (505.0, 305.0)], close=True, dxfattribs={"layer": fu})   # L sectional, 38" deep
    sh.text("L SECTIONAL", 551.0, 287.0, 4.0)
    sh.rect(533.0, seat_cy - 23, 579.0, seat_cy + 23, fu)                     # 46" square table
    sh.movable_since(m0)
    fw = face("foyer wall", -1)             # closet | bench niche | closet on the foyer side of the TV wall
    for y0, y1, lab in ((300.0, 330.0, "CLOSET"), (330.0, 370.0, "BENCH"), (370.0, 400.0, "CLOSET")):
        sh.rect(fw - 18, y0, fw, y1, fu); sh.text(lab, fw - 9, (y0 + y1) / 2, 3.0, rot=90)

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
    m0 = sh.mark()
    bed(face("lounge|gym", +1), open_mid, 60, +1)
    bed(face("guest|office", -1), open_mid, 60, -1)   # guest: head on the office wall, clear of the bath door
    bed(W_IN, open_mid, 60, -1)
    bed(W_IN, (srow + S_IN) / 2, 76, -1)   # primary: the whole west wall is open
    sh.movable_since(m0)
    n0, ny = HALL_END + INT / 2, hall_n + INT                                 # reading nook: built-in bench the
    sh.rect(n0, ny, W_IN, ny + 24, fu)                                        # length of the office wall
    sh.text("BENCH", (n0 + W_IN) / 2, ny + 12, 3.5)
    sh.text("READING NOOK", (n0 + W_IN) / 2, ny + 38, 3.5, "A-AREA-IDEN")
    ys = face("south hall wall", -1) + INT                                    # the nook's open (bedroom) edge
    dash = {"layer": "A-CLNG", "linetype": "DASHED"}
    for p, q in (((n0, ny - INT), (W_IN, ny - INT)), ((n0, ys), (W_IN, ys)), ((n0, ys - NOOK_CAB_D), (W_IN, ys - NOOK_CAB_D))):
        sh.msp.add_line(p, q, dxfattribs=dash)                                # lowered ceiling; cabinet backs
    sh.text("CABINETS ABOVE, LOWERED CEILING 7'-6\"", (n0 + W_IN) / 2, ys - 6, 2.5, "A-CLNG")

    def closet(x0, x1, label="CL"):          # 24" reach-in closets on the hall wall
        y1 = hall_n
        sh.rect(x0, y1 - 24, x1, y1, fu)
        sh.line((x0, y1 - 12), (x1, y1 - 12), fu)
        sh.text(label, (x0 + x1) / 2, y1 - 18, 4.0)

    closet(face("lounge|gym", +1), 776.0)
    closet(950.5, face("guest|office", -1))   # guest: one long closet past the door
    closet(1109.0, W_IN)                     # office: one long closet past the door

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
    py = cy0 + CARPORT_WALK                                                   # walkway | parking line
    sh.msp.add_line((cx0, py), (cx1, py), dxfattribs={"layer": "L-SITE", "linetype": "DASHED"})
    sh.text("COVERED WALKWAY (NOT PARKING)", (cx0 + cx1) / 2, cy0 + CARPORT_WALK / 2, 7.0)
    sx = cx0 + 6                                                              # two stalls, clear of the posts
    for k in range(2):
        sh.rect(sx + k * STALL_W, py, sx + (k + 1) * STALL_W, py + STALL_D, "L-SITE")
    sh.text("CARPORT", (cx0 + cx1) / 2, py + STALL_D / 2 + 14, 10.0, "A-AREA-IDEN")
    sh.text(carport_size(), (cx0 + cx1) / 2, py + STALL_D / 2, 6.5, "A-AREA-IDEN")
    sh.text("2 SPACES, 8'-6\" x 18'-0\"", (cx0 + cx1) / 2, py + STALL_D / 2 - 14, 5.0, "A-AREA-IDEN")
    sh.msp.add_lwpolyline(driveway_outline(), close=True, dxfattribs={"layer": "L-SITE"})
    sh.text("DRIVEWAY", (CARPORT[0] + CARPORT[2]) / 2, 120.0, 9.0, "A-AREA-IDEN")
    for wall, x0, x1 in canopies():                                           # window canopies
        y, d = (N, -CANOPY_D) if wall == "north" else (S, CANOPY_D)
        sh.msp.add_lwpolyline([(x0, y), (x0, y + d), (x1, y + d), (x1, y)],
                              dxfattribs={"layer": "A-CANP", "linetype": "DASHED"})
        sh.text("CANOPY ABOVE", (x0 + x1) / 2, y + d / 2, 3.0, "A-CANP")
    px0, py0 = PORCH_OUT                                                      # porch: 1' forward and 8" east,
    sh.rect(px0, py0, PORCH_X, N, "L-SITE"); sh.rect(px0, N, E, PORCH_Y, "L-SITE")   # its step in front
    sh.rect(px0 + 4, py0 - 24, PORCH_X - 4, py0, "L-SITE")
    sh.msp.add_lwpolyline([(px0, py0), (PORCH_X, py0), (PORCH_X, N), (px0, N)], close=True,
                          dxfattribs={"layer": "A-CANP", "linetype": "DASHED"})          # canopy over the 1'
    sh.text("CANOPY ABOVE (9')", (px0 + PORCH_X) / 2, py0 + 5, 2.4, "A-CANP")
    rx0, ry0, rx1, ry1 = CARPORT_ROOF                                         # carport roof: its front edge in
    sh.msp.add_lwpolyline([(rx0, ry0), (rx1, ry0), (rx1, ry1), (rx0, ry1)], close=True,   # line with the canopy's
                          dxfattribs={"layer": "A-CANP", "linetype": "DASHED"})
    sh.text("CARPORT ROOF ABOVE (9')", (rx0 + rx1) / 2, ry0 + 5, 2.4, "A-CANP")
    sh.text("8'-0\" x 5'-0\"", (px0 + PORCH_X) / 2, N + 12, 3.0)
    sh.rect(E, N, E + 6, N + 6, "A-WALL")                                     # porch corner post
    sh.rect(*ENTRY_COURT, "L-SITE")                                           # entry court + seat wall
    sh.text("ENTRY COURT", (ENTRY_COURT[0] + ENTRY_COURT[2]) / 2, 205.0, 6.0, "A-AREA-IDEN")
    for b in ENTRY_WALLS:
        sh.rect(*b, "A-WALL")
    sh.text('24" SEAT WALL', (ENTRY_WALLS[0][0] + ENTRY_WALLS[0][2]) / 2, 146.0, 5.0)
    sh.text("WOOD-LOOK FEATURE WALL", (E + PORCH_X) / 2, PORCH_Y - 6, 2.4)        # porch back walls
    # courtyard
    fy = cy1 + 3
    sh.rect(LOT_X0 + 6, fy + 1, E, fy + 61, "L-SITE"); sh.text("PAVERS", LOT_X0 + 106, fy + 31, 6.0)
    sh.rect(E - 60, fy + 61, E, LOT_D - 42, "L-SITE")                                  # 5' noncombustible strip
    sh.text("GRAVEL", E - 30, 660.0, 4.0, rot=90)                                     # along the house (no patio)
    sx0, sx1 = next(o[1:3] for o in OPENINGS if o[0] == "east" and o[3] == "slider")
    sh.rect(E - 36, sx0, E, sx1, "L-SITE"); sh.text("LANDING", E - 18, (sx0 + sx1) / 2, 3.5, rot=90)  # at grade
    sh.rect(LOT_X0 + 18, fy + 61, E - 156, LOT_D - 42, "L-PLNT")                       # edged by the pavers and planter wall
    sh.text("LAWN", (LOT_X0 + 18 + E - 156) / 2, 650.0, 7.0)
    sh.rect(LOT_X0 + 6, LOT_D - 42, E, LOT_D - 6, "L-PLNT"); sh.text("RAISED PLANTERS", (LOT_X0 + E) / 2, LOT_D - 24, 5.0)
    gx = E - GATE_L                                                                     # carport gate: hinged at the
    sh.line((LOT_X0, fy), (gx, fy), "A-FENC"); sh.line((gx, fy), (E, fy), "A-FENC")   # house corner, swings into
    sh.msp.add_arc((E, fy), GATE_L, 180.0, 270.0,                                      # the carport and opens flat
                   dxfattribs={"layer": "A-FENC", "linetype": "DASHED"})               # against the house wall
    sh.text("6' FENCE", (LOT_X0 + gx) / 2, fy + 10, 4.0)
    sh.text(f"{fmt(GATE_L)} GATE, OPENS FLAT AGAINST THE HOUSE", (gx + E) / 2, fy + 10, 4.0)
    for x, y in EXIST_TREES:                                                            # existing olives in the parkway
        sh.circle((x, y), 18.0, "L-PLNT"); sh.circle((x, y), 3.0, "L-PLNT")
    sh.circle(PRIVACY_TREE, 18.0, "L-PLNT"); sh.circle(PRIVACY_TREE, 3.0, "L-PLNT")
    sh.text("NEW PRIVACY TREE", PRIVACY_TREE[0], PRIVACY_TREE[1] + 28, 5.0)
    sh.circle(FRONT_TREE, 18.0, "L-PLNT"); sh.circle(FRONT_TREE, 3.0, "L-PLNT")
    sh.text("NEW TREE", FRONT_TREE[0], FRONT_TREE[1] + 28, 5.0)
    tx = sum(t[0] for t in EXIST_TREES) / len(EXIST_TREES)
    sh.text("EXIST. MATURE OLIVE TREES TO REMAIN", tx, -140.0, 5.0)
    sh.rect(LOT_X0 + 6, 262, LOT_X0 + 54, 382, "L-SITE"); sh.text("BINS", LOT_X0 + 30, 322, 5.0, rot=90)        # bin pad
    hx = sum(next(w[3:5] for w in WALLS if w[0] == "bath|storage")) / 2               # heat pump outdoor: behind the storage
                                                                                        # room, between the two high windows
    sh.rect(hx - 21, S + 10, hx + 21, S + 30, "A-EQPM")                                 # unit behind the laundry
    sh.rect(hx - 27, S + 4, hx + 27, S + 36, "A-FENC")                                  # dog guard
    sh.text("CONDENSER", hx, S + 20, 3.5)
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
    sh.text(NOTICE, LOT_W / 2, LOT_D + 58, 7.0)
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
    render(sh.doc, RENDERS / "schematic.png", -40, -180, LOT_W + 140, LOT_D + 130, dpi=220)
    render(sh.doc, RENDERS / "schematic-zoom.png", E - 20, N - 40, W + 20, S + 30, width_in=24, dpi=250)
    print("rendered")


if __name__ == "__main__":
    main()
