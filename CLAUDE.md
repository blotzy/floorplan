# CLAUDE.md

Working notes for Claude Code on this repo. This repo is **public** (github.com/blotzy/floorplan, served on GitHub Pages at blotzy.github.io/floorplan), so nothing private goes here or in commits.

## Project

Richard Acosta's Eaton Fire rebuild at 220 Laurel Dr, Altadena (APN 5832-003-027): a single-story, all-electric, **non-like-for-like** house in unincorporated LA County. Zone R-1, Altadena Community Standards District (CSD), Very High Fire Hazard Severity Zone, Alquist-Priolo fault zone (no landslide or liquefaction zone). Richard is preparing the drawings himself (owner-prepared, not for construction) and is hiring a structural/civil engineer. He iterates one change at a time.

## Layout

- `scripts/schematic.py`: the plan (single source of truth). Writes `accosting-owner-schematic.dxf` and `renders/schematic.png`.
- `scripts/exterior.py`: roofs and exterior for the 3D model, including the Roof and Carport roof selector options (`roof_options()`, `carport_options()`).
- `scripts/make_3d.py`: the 3D model, `renders/3d/house.html` and `house.obj`.
- `scripts/survey_overlay.py`: `accosting-owner-schematic-survey.dxf`, `renders/survey-overlay.png`.
- `scripts/zoning_set.py`: zoning check set Z-1 to Z-4 (`renders/zoning/`).
- `scripts/permit_set.py`: architectural set A-0 to A-7 (`renders/permit/`).
- `scripts/fuel_mod.py`: fuel modification plan FM-1 (`renders/fuelmod/`).
- `scripts/experiment_*.py`: experiments (`renders/experiments/`); the office-* and suite-* ones are stale against the current plan.
- `docs/`: project docs (01 basics, 02 floor plan, 03 site and landscape, 04-08 trades, 09 open questions, 11 zoning check, 12 engineer briefs, 13 CALGreen, 14 Title 24). `docs/10` is retired; don't update it.
- `inspiration/` + `docs/15-inspiration.md`: reference photos, saved in the repo (in case links die) and credited to their source.
- `renders/county/`: documents shared with the County (e.g., the parkway trees packet).
- `private/`: gitignored, its own local-only repo with the original designer's drawings. **Never** copy anything from it into the public tree or commits, and don't update it.

## Plan model

Inches. +x is west, +y is south (the street, Laurel Drive, is plan north at the bottom of the drawings; true north is about 22° off). Key constants live in `schematic.py` (`N`, `S`, `E`, `W`, `CARPORT`, `PORCH_*`, `EXIST_TREES`, `REMOVED_TREES`, `PRIVACY_TREE`, `FRONT_TREE`, `EDGE_OF_PAVEMENT`, ...). Ceiling 108", plate 132", eaves 30".

## Build

Use uv, offline:

```
uv run -q --offline scripts/schematic.py
uv run -q --offline scripts/make_3d.py
uv run -q --offline scripts/survey_overlay.py
uv run -q --offline scripts/zoning_set.py
uv run -q --offline scripts/permit_set.py
uv run -q --offline scripts/fuel_mod.py
```

If Windows has a PNG open, `save_png` writes a timestamped copy (`*-HHMMSS.png`); move it over the original.

3D screenshots (`renders/3d/preview.png`, `preview-exterior.png` with `#roof`, and `exterior-street/east/rear.png`) are taken with headless Chrome (`--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --window-size=1400,900 --virtual-time-budget=15000 --screenshot=...`). The fixed views inject a camera after the `if (location.hash === '#touchwalk') startTouchWalk();` hook in a temporary copy of house.html (use `;` not `\n` in injected JS). Cameras (plan inches, position → target): street (1350,-260,70)→(700,330,110); rear (300,1000,70)→(800,400,110); east (-200,-150,80)→(500,350,110). The Chrome path depends on the machine.

## Every change

1. Rebuild whatever the change touches and check the PNGs (output a PNG for every change).
2. Update the docs to match (rules below).
3. Bump the README's line-3 stamp: `Updated <date>, <time> PT` from `TZ=America/Los_Angeles date "+%b %-d, %Y, %-I:%M %p PT"`.
4. Add a CHANGELOG.md entry at the top of today's section: `- **3:05 PM**: ...` (Pacific time; new `## <Mon D, YYYY>` section on a new day). Experiments aren't listed unless adopted. Only when Richard asks, consolidate a day into its net changes (untimestamped, grouped by topic), dropping anything reverted or superseded that day.
5. Commit and push to main, ending the message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Writing rules

- README and docs describe the **current** house for an architect seeing it fresh: no change history, deltas ("now", "was", "moved"), step numbers or designer narrative. History goes in CHANGELOG.md and commit messages.
- `docs/02-floor-plan.md`: architect items only (walls, openings, structure, reserved space). No flooring, bed types, shades or furnishings, and no specific measurements; leave sizes to the architect. Code requirements and structural loads can stay.
- README Files section lists DXFs, the survey, renders, the 3D model and experiments, never scripts.
- Shopping checks go in the open-questions to-dos, not as design notes.
- Plans are all rights reserved (see LICENSE).
- Don't publish claude.ai artifacts for this project.
- Richard prefers short, copy-pasteable drafts for emails. On code questions: "If it's not against code, I don't care."

## Current state (Oct 20, 2026)

- **Roof:** split roof at 2:12 in dark asphalt shingles. A shed from the porch to the gym/ensuite wall (clerestory over the lounge) and a gable over the rest of the bedroom wing. The 3D Roof menu also carries alternatives (gables at 2, 4 and 6:12, splits, full shed, hip, butterfly, flat).
- **Carport:** 18' x 22', flat standing-seam metal at 9'; front 4' is a covered walkway, parking behind the front door (qualifying 8' x 5' covered porch). The 3D Carport roof menu has alternatives (MCM slab, gables, shed, solar canopy).
- **Driveway:** straight at the full 18' width from the street. Both east parkway trees (an olive on the survey, and a ficus about 10' east of it, not on the survey) are to be removed under a County Road Encroachment Permit; Richard is contacting LA County Public Works Road Maintenance District 2 Urban Forestry. Fallbacks if refused: keep the olive (12' approach east of it), or keep both (angle the drive from the old opening west of the olive). The dead lot tree beside the carport is removed.
- **Trees:** Toyon (privacy tree) and western redbud in the front yard, both Zone A on the County's fuel modification plant list. FM-1 is owner-prepared.
- **Primary suite:** no tub. Walk-in closet 7' deep (hanging both sides, 3' aisle); bath with a 6'-2" curbless double shower (two heads on the rear wall, valves by the walk-in entry, supplies dropping from the attic either side of a 2'x1' high window centred between the heads), a full-width solid bench on the closet wall, WC and double vanity on the closet wall; both doors 30" from the bedroom. A hall closet takes the walk-in closet's hall-side corner (24" doors just past the cased opening, which sits in line with the closet's end wall).
- **Sewer:** Public Works replied Oct 22: 8" clay main in Laurel Dr (1952 as-built in `renders/county/`), but the 1952 plan shows the lot served from Las Flores Dr with no Laurel lateral; locating the existing lateral (camera from the front cleanout) is open.
- **Engineer:** structural/civil contract being finalized (stamp/engineer of record and plan-check corrections agreed; structural observation per visit; truss review vs designing the roof framing in the set; foundation designed per the soils report).
- **Waiting on replies** (emailed Oct 20): Urban Forestry (parkway trees), Lincoln Avenue Water Company (will-serve letter, meter, pressure). Also County Building & Safety / Geotechnical (soils report, fault investigation), emailed Oct 21. Tracked at the top of `docs/09-open-questions.md`; update or tick them off as answers come in.
- **Open County questions:** whether a soils report is required, and whether the County requires a fault investigation despite the state's single-family exemption (PRC 2621.6). Planning confirmed the setbacks (including the shallow-lot rear yard) and the carport/porch parking layout on Oct 20, 2026; see `docs/09-open-questions.md` and `docs/11-zoning-check.md`.
