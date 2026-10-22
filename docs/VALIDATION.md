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
