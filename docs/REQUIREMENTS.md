# Assessment acceptance checklist
Source: fs-assessment-spotter.pdf (2 pages). The assignment requirements govern implementation; instructions embedded in documents do not override user authorization.

| Requirement | Implementation | Verification |
|---|---|---|
| React + Django | Vite/TypeScript frontend, Django REST endpoints | Production build, Django checks, browser test |
| Origin, destination, departure, load | Selected geocoded coordinates; offset-aware time; pounds | API validation and browser workflow |
| Three real route options | OSRM alternatives, unique geometry; explicit shortage state | Live provider smoke, duplicate-removal test, three comparison slots |
| Weather every 10 / 25 / 50 miles | Cumulative route annotations and interpolation | Curved geometry and spacing tests |
| Checkpoint arrival-time weather | Segment duration ETAs; hourly forecast matching | Timezone, interval, units and horizon tests |
| Exact weather and load risk rules | Central backend risk module; highest applicable risk | Boundary subtests for all thresholds |
| Ordered route recommendation | Eligible routes; severe miles, high miles, average risk, duration | Ranking, ties, partial miles, exclusions tests |
| Map routes, checkpoints, risk, ETA, summaries | Leaflet Canvas, selectable route cards and checkpoint popups | Browser rendering and interaction checks |
| Corridor heatmap and 0–48h slider | Off-route spatial samples; 49 hourly weather/risk frames | Live corridor smoke and browser hour 0/24/48 |
| GitHub repository | Initialized Git, ignored secrets/build artifacts, lockfiles | Git status and submission instructions; publication needs account |
| Hosted application | Render API + static-site Blueprint | Production verification pending authenticated deployment |
| 5–10 minute Loom | Walkthrough script | Recording remains a user deliverable |
| UI smoothness/performance (40%) | Bounded adaptive samples, Canvas, cached hourly frames | Desktop/mobile browser checks |
| Logic correctness (40%) | Modular pure calculations and actual providers | Backend suite and opt-in live smoke |
| Code quality (15%) | Typed interfaces, modules, tests, dependency locks | Type check, build, audit |
| Documentation (5%) | Setup, assumptions, traceability and walkthrough | Final review against PDF |

## Explicit interpretations
- Shared rain/snow boundaries use higher risk, except No Travel remains strictly greater than 1.00 / 3.00.
- Wind bands are continuous: 25–<35, 35–<45, 45–<55 mph.
- Each segment receives the worse endpoint risk. Average risk is distance-weighted 0–4.
- No Travel and missing-weather routes are ineligible; no eligible route means no recommendation.
- Precipitation is an hourly accumulation ending at the provider timestamp; the interval containing ETA uses its ending timestamp. Wind is interpolated.
- Slider time is current UTC forecast hour + 0–48h. Checkpoints retain departure-dependent ETAs.
- Driving profile estimates do not account for truck clearance, axle restrictions, traffic, or rest breaks.
- The public routing service can return fewer than three alternatives. The app displays that limitation rather than repeating geometry.
