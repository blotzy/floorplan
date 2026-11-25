# Title 24 inputs for the energy consultant

[← Back to README](../README.md)

What the energy consultant needs to model the house and produce the compliance forms (CF1R). Rooftop solar PV and battery storage aren't required for Eaton and Palisades fire rebuilds (LA County, under Executive Order N-29-25, Sep 2025), but the house must be solar-ready (Energy Code §110.10: a solar zone on the roof, a conduit path to the panel and breaker space); the panels are added later under a separate permit, clamped to the standing seams. In CBECC, turn on the LA fire PV/battery exception (Project tab): the CF1R then states the solar requirement is suspended, and no PV is required or modeled. Values marked "target" are starting points for the model (2025 Energy Code, CBECC 2025).

## Building

| Item | Value |
| --- | --- |
| Location | 220 Laurel Dr, Altadena CA 91001 (climate zone 9: confirm) |
| Type | New single-family, 1 story, all-electric, 4 bedrooms, 3 baths; Eaton Fire rebuild, non-like-for-like; 2025 Energy Code |
| Conditioned floor area | About 2,226 sq ft (porch and open carport excluded) |
| Orientation | The street (front) wall faces about 22° (NNE); rear faces about 202° (SSW); the dining slider faces about 112° (ESE); the west end faces about 292° (WNW) |
| Ceilings | 9' flat under a sealed attic; the great room (lounge, dining, kitchen, about 840 sq ft) vaulted under the roof, about 16' at the street down to 11'; the foyer (about 60 sq ft) flat at 9' with conditioned storage above, inside the roof-deck insulation |
| Roof | 2:12 split roof: a shed over the great room and the east end of the bedroom wing, a gable over the rest of the wing; dark standing-seam metal, matching the carport (CRRC-rated color: use its reflectance and emittance), 2'-6" eaves |

## Envelope (targets)

| Assembly | Target |
| --- | --- |
| Roof | Unvented attic: R-19 spray foam at the underside of the roof deck (over the attic); vault: R-30 in the 2x10 rafter bays (rafter size per the structural set); uninsulated ceiling between the house and the sealed attic |
| Walls | 2x6 at 16" with R-19 cavity insulation (R-21 may be installed), stucco; no continuous insulation |
| Slab | Slab on grade, unheated, no edge insulation unless the model needs it |
| Windows and doors | U-factor 0.30 or lower, SHGC 0.23 or lower (targets); dual-pane with at least one tempered pane (fire zone) |
| Air sealing | Quality insulation installation (QII) and a tight envelope; sealed attic means ducts are in conditioned space |

## Windows and glazed doors

| Wall (faces) | Window | Size (W x H) | Area |
| --- | --- | --- | --- |
| Street (22°) | Lounge | 10'-0" x 5'-6" | 55.0 sq ft |
| Street (22°) | Clerestory over the lounge (three 5'-6" units) | 16'-6" x 3'-0" | 49.5 sq ft |
| Street (22°) | Gym, guest, office (3) | 6'-0" x 5'-6" each | 99.0 sq ft |
| Street (22°) | Guest ensuite (high) | 2'-6" x 1'-6" | 3.8 sq ft |
| Porch side (112°) | Reeded window | 2'-0" x 5'-6" | 11.0 sq ft |
| East (112°) | Dining slider | 6'-0" x 8'-0" | 48.0 sq ft |
| Rear (202°) | Dining (two units) | 12'-0" x 6'-0" | 72.0 sq ft |
| Rear (202°) | Kitchen | 5'-0" x 4'-0" | 20.0 sq ft |
| Rear (202°) | Laundry (high); primary bath | 3'-6" x 2'-0"; 4'-0" x 2'-6" | 17.0 sq ft |
| Rear (202°) | Primary bedroom | 6'-0" x 5'-6" | 33.0 sq ft |
| West (292°) | Reading nook | 3'-0" x 4'-6" | 13.5 sq ft |
| West (292°) | Office (high) | 4'-0" x 2'-0" | 8.0 sq ft |
| | **Total** | | **about 430 sq ft (about 19.3% of the floor area, just under the prescriptive 20%)** |

Shading: 2'-6" eaves at the street and sides, 2'-0" at the rear; at the rear, 3'-deep metal canopies over the kitchen and primary bedroom windows. The front door's glass lite (if any) is still to be chosen.

## Equipment

| System | Planned |
| --- | --- |
| Heating and cooling | Two ducted heat pump systems, ideally on one multi-zone outdoor unit (about 3 tons in all, sized by the Manual J): a full-size air handler for the great room and bedroom wing, and a slim ducted unit for the primary suite; no zone dampers; air handler and all ducts in the sealed attic |
| Water heating | Heat pump water heater: Rheem ProTerra 80 gal, XE80T10HS45U1 (Performance Platinum; NEEA Tier 4, 4.07 UEF, built-in LeakGuard shutoff, top water connections; JA13 demand-response readiness to confirm; about 2' diameter x 6'-3" tall), or equal, indoors in the mechanical closet (unducted, louvered into the laundry); thermostatic mixing valve at the outlet, tank at about 140°F; no recirculation |
| Ventilation | Continuous exhaust fan sized to the code rate (about 105 cfm: 0.03 x floor area + 7.5 x (bedrooms + 1)); an ERV is an open question |
| Kitchen | Induction range; range hood ducted outside, 400 cfm or less |
| Laundry | Heat pump (ventless) dryer |
| Lighting | All LED, high-efficacy, with the required controls |
| Solar and battery | None in the Title 24 run (LA fire PV/battery exception, EO N-29-25); solar-ready roof zone, conduit and breaker space; ready for a future battery |

## HERS verifications to expect

Duct leakage, air handler fan efficacy and airflow, refrigerant charge, quality insulation installation, whole-house ventilation airflow, and the kitchen hood.
