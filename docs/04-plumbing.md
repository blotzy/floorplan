# Plumbing

[← Back to README](../README.md)

The water service enters at the northwest corner (the utilities are at the west end). Unsoftened lines branch off first, then a single main runs to the mechanical closet, where everything downstream is softened.

Interior supply piping is copper. No PEX except for the fire sprinklers (a standalone NFPA 13D system; sprinklers are required for all new single-family homes, including fire rebuilds).

**Existing connections (survey):** the water meter (5/8", Lincoln Avenue Water; their side of the service is 1") is in the parkway at the west end of the frontage; the owner's side of the service line may need replacing if the fire or debris removal damaged it; the sewer cleanout is at the front of the lot, roughly in line with the porch and lounge, so the building sewer runs out under the front of the house to it. The lot falls toward the west and rear, so check the sewer slope from the far (west) baths to that cleanout early. **Public sewer:** an 8" clay main in Laurel Drive (1952 [1952 as-built](../renders/county/laurel-sewer-as-built-1952.png)), its invert roughly 1423 to 1427 along the frontage (1952 elevations, to be verified), so about 8 to 12 ft below the floor: a new lateral to it works by gravity with plenty of fall. The 1952 plan shows the lot served from Las Flores Drive instead, with no Laurel lateral, so where the existing lateral goes is still open (see the [open questions](09-open-questions.md)). Use solid, root-resistant pipe and joints for the building sewer, with root barriers wherever it passes within ~10 ft of a tree (the street-side privacy tree and the existing trees near the front); see [site drainage](03-site-and-landscape.md#drainage-and-root-protection).

**Water service order:** meter (1") → backflow preventer (as the water company requires; a low-loss model) → **fire sprinkler tee** → main house shutoff → pressure regulator only if the measured static pressure is high (the water company's area figure is about 50 psi, so likely none) → smart leak-detection shutoff valve → unsoftened branches → main line to the mechanical closet → sediment pre-filter → softener → water heater, manifold, and the RO filter (drinking water to the kitchen sink tap and the fridge). The sprinkler branch comes off ahead of the house shutoff, any pressure regulator, the leak-detection valve and the softener, so none of them can cut or close off the sprinklers' supply. With only about 50 psi at the main, run at least a 1" line from the meter to the house (a long run from the west-end meter) to keep pressure loss down.

| Line | Water | Notes |
| --- | --- | --- |
| Fire sprinklers | Unsoftened, direct from main | Existing meter 5/8" (Lincoln Avenue Water; their service is 1"): a 1" meter upsize (applied for, about 6-12 weeks) and a backflow preventer, the sprinkler designer confirming the size; fire flow from the water company's area form (Section 4: static at least 50 psi, residual at least 42 psi, 1,100+ gpm at 20 psi from a 4"+ main; [PDF](../renders/county/lawc-fire-flow-section-4-2025-09.pdf)) or a hydrant test; plans due by foundation sign-off; heads placed clear of the ceiling fans (primary, guest, office) |
| Hose bibs and irrigation | Unsoftened | Tee before the softener; includes the courtyard lawn and the bin-pad hose bib. The irrigation branch has its own backflow preventer (per the plumbing code and the water company) and feeds a valve manifold in a box (point of connection agreed between plumber and landscaper) |
| Bathrooms | Softened |  |
| Kitchen | Softened | Plus RO for drinking and the fridge |
| Water heater | Softened |  |
| Laundry | Softened |  |
| Robot vacuum dock | Softened cold | In the laundry counter beside the utility sink: teed off the sink's cold supply, its drain into the sink's trapped drain |

**Irrigation rough-in** (fuel modification plan FM-1 and the state's water-efficient landscape rules)

- Unsoftened irrigation branch, backflow preventer and valve manifold as above; drip zones for trees, shrubs and ground cover, a spray zone only for the courtyard lawn, no overspray onto paving.
- Weather- or soil-moisture-based controller (see the electrical doc for its outlet).
- Sleeves (empty 2"–3" pipes) under the driveway, carport slab, entry court and courtyard pavers before they're poured or laid, so irrigation lines (and future low-voltage landscape lighting) can cross without cutting paving.

**Bathrooms**

- Use epoxy or pre-mixed urethane grout for shower tile work.

**Kitchen**

- Integrated drain board on the dishwasher side of the sink (countertop with a slight slope and grooves).
- Coffee station on the peninsula counter over the drink fridge.
- Kitchen sink in the peninsula, about 5'-9" from the rear wall, where the peninsula meets it: its drain runs in the slab toward the rear wall. Vent it either with a 2" trap arm (within the 8' limit, sloped ¼" per foot) run through the peninsula's back, behind the dishwasher and the corner cabinet (the dishwasher fills the space beside the sink, so the arm can't pass through it), to a vent rising in the rear wall where the peninsula meets it, or with island fixture venting (a loop in the sink cabinet, a foot vent below the slab, a horizontal run under the slab to that riser), per the plumber; California's plumbing code generally doesn't allow air-admittance valves. A cleanout reachable inside the sink cabinet. The dishwasher drains to the sink through a countertop air gap (California requires one): a small fitting on the counter or the sink deck beside the faucet, so plan its hole with the faucet, RO tap and any workstation-sink accessories. Lay it out on the plumbing plan before the slab is poured.
- **Plumbing vents, kept few and simple:** the kitchen sink's vent rises in the rear wall where the peninsula meets it and goes straight up through the roof at the wall line, near the rear eave, below the first solar array. The laundry and the common and primary baths vent up through the attic, combined where it's a short run, through one or two vents on the wing's rear slope. The guest ensuite has its own vent on the wing's street slope. About three or four roof vents in all, each outside the first solar array (see the [solar layout](../renders/experiments/solar-layout.png)), at least 6" above the roof and 10' from (or 3' above) openable windows and air intakes. No dryer vent (ventless heat pump dryer).
- **Fire zone:** plumbing vents are open pipes, not the ventilation openings the wildfire rules regulate, so they need no screens; use metal flashings rather than rubber boots. Every exhaust termination (bath fans, the whole-house fan, the range hood) is metal with a backdraft damper, ember-resistant where a listed product exists; the attic is sealed, so there are no attic, soffit or ridge vents.

**Equipment and fixtures**

- Whole-house water softener with sediment pre-filter, in the mechanical closet. The softener needs a drain with an air gap.
- Heat pump water heater, 80 gal, in the mechanical closet, with a condensate drain and a drain pan with a leak sensor; 6-12" of service clearance above it.
- Thermostatic mixing valve at the water heater outlet: the tank stores at about 140°F (more usable hot water for the double shower and back-to-back showers, more solar energy stored, and Legionella control) and the valve sends tempered water (about 120°F) to the house. Shower and tub valves keep their own anti-scald protection.
- Tankless reverse-osmosis filter in the mechanical closet, fed from the softened line (softening first extends the membrane's life). Food-grade lines run to the RO tap at the kitchen sink and to the fridge, with accessible shutoffs at both ends. Its waste line drains through an air gap or standpipe; it needs an outlet, and shares the closet's leak pan/sensor. A bypass plug replaces the fridge's internal filter. The sink cabinet stays free for the trash pull-out.
- Leak pans under the washer and fridge.
- Primary shower (double, curbless, across the rear wall): two stations facing each other, each a fixed head and a slide-bar handheld on its own thermostatic valve with a diverter (one outlet at a time per valve, or both at a combined 1.8 gpm), so each valve stays within California's 1.8 gpm limit for multiple shower outlets (CALGreen 4.303.1.3.2) and both stations can run at once; confirm the approach with plan check. The main station on the dressing-room wall, its valve by the walk-in entry; the second on the plumbing wall, its valve toward the front of the shower. Supplies drop from the sealed (conditioned) attic. The vanity, WC and second station share the 2x6 plumbing wall with the common bath's sink and WC on its other side. Both stations running draw about 3.6 gpm, so a long double shower uses hot water about twice as fast. Linear drain along the glass line, the floor sloping one way to it from the bench along the rear wall (a shallow slab recess); its outlet at the plumbing-wall end, with a short trap arm to the plumbing wall, venting up that wall with the WC and vanity into VTR-2. No vent in the exterior rear wall, and no air admittance valves. One waterproofed zone (membrane floor, walls and the solid bench). No ceiling rain head.
- Bidet seats at all three baths. Plan toilet locations so each bidet outlet has enough separation from tubs and showers.
- Small utility sink beside the washer on the laundry's bath wall. The heat pump dryer's condensate drains into the washer standpipe.

**Optional**

- No hot water recirculation. Optional: while the walls are open, run a return line from the primary bath (the farthest fixtures) back to the water heater, capped, so an on-demand recirculation pump can be added later without opening walls.
