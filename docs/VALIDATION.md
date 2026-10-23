# Verification record — 22 October 2026
## Passed
- Backend: 23 test methods with parameterized subtests covering all wind/rain/snow thresholds; 30,000/40,000 lb boundaries; worst-hazard selection; weighted ranking; partial segments; unknown and No Travel exclusion; geometry, spacing, ETAs, timezone, units, horizons; validation and provider failures.
- Django system check: no issues.
- Python dependency consistency: pip check passed.
- Frontend: four Vitest tests covering duration rounding, selected inputs, API failure/retry, and slider 0/24/48 with retained route assessment.
- TypeScript and Vite production build passed.
- npm audit: zero vulnerabilities after upgrading Vitest.
- Headless Edge browser: actual recorded live route geometry and corridor data; all available route selectors and third unavailable slot; slider frames 0/24/48; layer toggle; mobile width 390; no uncaught page errors.
- Visual inspection: desktop and mobile screenshots reviewed. Replaced a tile provider requiring a key with OpenStreetMap; changed heatmap to a smooth Canvas layer below road geometries.
- Actual provider requests: New York–Boston assessment HTTP 200, two distinct routes (~214 and ~232 miles), six checkpoints each at 50-mile spacing, zero unknown miles, eligible recommendation.
- Actual corridor request: HTTP 200, 49 spatial samples, 49 forecast hours. Sample wind at hours 0/24/48 changed (4.7 / 11.4 / 4.1 mph in the captured response).
- Actual geocoding: New York and Boston returned results.
- Running local Django health endpoint returned status ok.

## Limitations and pending checks
- A three-genuine-route example was not obtained. Sixteen tested city pairs returned one or two public OSRM alternatives. Three comparison slots are implemented; unavailable alternatives are explicitly labeled. This acceptance item is not claimed as passed.
- Two browser tests passed: recorded-data rendering/interactions and the complete live browser-to-Django-to-provider workflow. Live geocoding, assessment, corridor retrieval and hour-48 slider update all passed. Checkpoint detail inspection and desktop/mobile screenshots also passed.
- No GitHub remote, GitHub CLI, Render CLI, or Render/GitHub deployment credentials were available in the environment inspected. GitHub and Render plugins were found but are not connected; connection suggestions were provided. No repository publication or hosted deployment was verified.
- Loom recording remains to be performed by the user with the supplied script.
- Production URL/CORS/cold-start behavior must be checked after Render account authorization.
- Evidence JSON and screenshots are local in ignored output/; live weather changes over time.


## Production weather investigation
- Verified https://truckers-api-1keh.onrender.com/api/v1/health/ returns HTTP 200.
- Verified https://truckers-web.onrender.com returns HTTP 200 and its JS build contains the correct backend URL.
- Verified CORS preflight returns the exact frontend origin.
- Reproduced production corridor HTTP 502 with JSON weather-provider error; identical 25-location retrieval succeeded locally.
- Added explicit upstream HTTP statuses/timeouts without leaking URLs or secrets, and reduced corridor weather from 16 to 3 calendar days while retaining all 49 slider frames.
- Expanded backend suite: 27 tests passed.
- A likely shared-host provider limit must be confirmed from the new deployed status; a 502 alone does not establish HTTP 429.


## WeatherAPI integration
- Added key-based provider selection and WeatherAPI hourly forecast normalization using epoch timestamps and real coverage limits.
- Backend: 41 test methods passed, including 14 WeatherAPI-specific tests for coordinates, units, period boundaries, missing snow, timestamp gaps, caching, quota/auth errors, key redaction and metadata.
- Frontend: four tests passed; provider attribution is verified by a frontend assertion.
- Live verification with a real WeatherAPI account remains pending the user setting WEATHERAPI_KEY on Render.
- Precipitation interpretation is explicit: WeatherAPI total precipitation is a conservative bound for the rain rule; it is not presented as separately measured liquid rainfall.

- Production frontend build and recorded-data Edge browser workflow passed after the WeatherAPI integration; real-key verification is still pending Render configuration.


## Route and layout update ? 23 October 2026
- Backend suite expanded to 51 passing tests, including native/waypoint alternative counts, duplicate and same-road rejection, dead-end/excessive-detour rejection, cached annotation integrity and preview validation/ETAs.
- Seven frontend tests passed, covering early ETAs, honest pending risk, independent corridor loading, retained route selection, errors, slider updates and duration formatting.
- Production frontend build passed.
- Edge browser check passed for three actual recorded road routes, arrival times in route cards, removal of the map-wide selected-route bar, forecast hours 0/24/48 and mobile overflow.
- Desktop timeline width was constrained to at most 540px and height below 165px; mobile timeline fit 390px width and stayed below 195px. Desktop/mobile screenshots were visually reviewed.
- Actual routing API checks: New York-Boston returned 3 routes (~214, 232, 228 miles); Chicago-Detroit returned 3 (~282, 299, 310 miles); Ohio-Texas returned 3 (~1251, 1255, 1299 miles).
- Ohio-Texas route retrieval took approximately 4 seconds in the checked request. Routing latency varies with providers and cache state; weather loading is separate.
- Live local assessment and corridor checks passed with actual Open-Meteo data: three distinct routes with complete checkpoint weather, and 76 corridor samples with 49 hours each. No local WeatherAPI secret was used.
- Pre-existing local HTML formatting and UI edits were preserved; original copies are stored under ignored .cache/ui-request-baseline/.
