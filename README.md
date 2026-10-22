# WeatherHaul
Weather-aware road-route comparison for the Spotter full-stack assessment. React 19 + TypeScript + Vite, Django REST Framework, Leaflet and a Canvas corridor forecast.

## Run locally (Windows PowerShell)
Requires Python 3.10+ and Node 22.12+.
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000
```
In another terminal:
```powershell
cd frontend
npm ci
npm run dev
```
Open http://127.0.0.1:5173. Search each location explicitly using its search button or Enter, then select a result. Enter departure time, pounds and checkpoint interval. Submit; select routes and checkpoint markers; explore corridor forecast hours.

Open-Meteo is available without a key. For the hosted deployment, WeatherAPI can be enabled with a server-side key to avoid the observed Open-Meteo shared-IP quota issue. No runtime fixtures or mock forecasts are used.

## Configuration
Copy the complete root .env.example. Django loads root .env; DEBUG=true is for local development. Vite proxies /api locally. For deployment set VITE_API_URL in the frontend build environment, since Vite embeds it during build.

| Variable | Purpose |
|---|---|
| DEBUG | true locally; false on Render |
| DJANGO_SECRET_KEY | Unique random production secret |
| ALLOWED_HOSTS | Comma-separated backend hosts, without schemes; Render hostname is added automatically |
| CORS_ALLOWED_ORIGINS | Exact frontend origins, including https://, without trailing slash |
| VITE_API_URL | Backend public origin, e.g. https://your-api.onrender.com; empty locally |
| OSRM_URL | Routing service base URL |
| WEATHER_URL | Open-Meteo forecast endpoint (only used in Open-Meteo mode) |
| WEATHERAPI_KEY | Backend-only WeatherAPI.com key; automatically selects WeatherAPI when set |
| WEATHER_PROVIDER | Optional explicit selection: weatherapi or open_meteo |
| GEOCODER_URL | Nominatim-compatible search endpoint |
| PROVIDER_USER_AGENT | Identify this application; add your project URL/contact for public services |

## Architecture and calculations
- backend/routing: providers, checkpoint geometry, weather conversion/time matching, risk, corridor sampling and API orchestration are separate modules.
- frontend/src: typed API client, explicit place search, map/Canvas layer and route workflow.
- No persistent user data, accounts, database or background worker is required.
- OSRM returns full road geometry and per-edge distances/durations. Checkpoints use cumulative distance and interpolate position and duration inside the containing edge.
- Weather: wind is requested in mph; rain plus showers is converted from mm to inches; snowfall depth is converted from cm to inches. Accumulation uses the containing hourly interval ending at the provider timestamp. Wind is interpolated between surrounding hours.
- Risk is the maximum of wind, rain, snow and load/wind rules. Shared rain/snow boundaries use the higher category, except No Travel remains strictly >1 in/hr rain or >3 in/hr snow.
- Each checkpoint segment receives its worse endpoint risk. All segments, including the final remainder, contribute their actual miles. Average risk uses distance-weighted category scores 0–4.
- Complete routes without No Travel are ranked by (Severe miles, High miles, average risk, duration, stable route ID). No eligible route produces no recommendation.
- The corridor contains lateral weather samples away from the road. At most 120 adaptive spatial samples supply 49 hourly frames. The Canvas heatmap interpolates visual opacity around sampled points; it is not a radar image or exact weather boundary.
- Slider time is the current forecast hour plus 0–48 hours. Route assessments retain departure-based arrival times. Changing the slider updates corridor colors, peak variables and forecast time.
- See docs/API.md for request/response contracts and docs/REQUIREMENTS.md for traceability.

## Providers and limits
[OSRM API](https://project-osrm.org/docs/v5.24.0/api/) and [demo policy](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server): request three genuine alternatives, deduplicate geometry, and display an explicit shortfall. **The public service returned at most two routes in the journeys verified here. The three-genuine-route acceptance item remains unverified.** No route is copied to fill a slot. The routing adapter can use another compatible OSRM endpoint through configuration.

[Open-Meteo](https://open-meteo.com/en/docs): hourly forecasts up to 16 days, with actual availability checked at each ETA. Unknown or missing weather makes a route ineligible. Arrival beyond the available horizon is never filled with invented weather.

[Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/): explicit searches only, no autocomplete, cache searches for 24 hours, identify the application, provide attribution, and enforce at most one request/second application-wide. Public OSRM requests receive the same cap. Deployment uses one worker process so its thread lock and in-memory cache apply across requests; do not increase workers or instances without adding shared rate limiting/cache.

[OpenStreetMap tiles](https://operations.osmfoundation.org/policies/tiles/): browser map requests use standard visible attribution and browser caching. Do not bulk-download or prefetch tiles. Provider availability and free-service quotas remain external dependencies.

Routes use the car driving profile. Truck clearances, axle limits, live traffic, legal driving breaks and road closures are not modeled. Trips are bounded to 5,000 miles and load input to 200,000 lb for this assessment.

## Verification
```powershell
$env:DEBUG='true'
.\.venv\Scripts\python.exe backend/manage.py test routing -v 2
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/live_smoke.py
cd frontend
npm test
npm run build
npm audit
npx playwright test
```
The live smoke requires network access and writes evidence under ignored output/. Run it before the recorded-data browser test. The browser test uses installed Edge; change the channel or install a Playwright browser on another OS. Unit and browser fixtures are test-only. To check the complete browser-to-provider flow:
```powershell
$env:LIVE_PROVIDERS='1'
npx playwright test
```
See docs/VALIDATION.md for actual results and remaining limits.

## Render deployment
The repository includes a two-service render.yaml: Django/Gunicorn web service and Vite static site. No paid database is needed. Free services may cold-start; the interface displays loading and errors.

1. Create a GitHub repository and push this project. Connect that repository to a Render Blueprint.
2. Set the frontend VITE_API_URL to the backend HTTPS origin. Set backend CORS_ALLOWED_ORIGINS to the frontend HTTPS origin. Use exact origins with no trailing slash.
3. Render generates DJANGO_SECRET_KEY. Keep DEBUG=false. Set PROVIDER_USER_AGENT to include your project URL/contact.
4. Deploy the backend, then rebuild the frontend after setting its API URL. Frontend environment changes require a new build.
5. Check backend /api/v1/health/, then use the hosted frontend to geocode, assess routes, inspect checkpoints and move the slider. Confirm tiles load and browser requests have no CORS errors.
6. Record actual hosted and GitHub URLs in your submission only after verification.

The API uses one Gunicorn worker with four threads and a 240-second timeout to allow bounded weather batches. This preserves public-provider rate limiting within one service instance. Persistent trips and multi-instance scaling would require shared storage/rate limiting.

## Submission
Use docs/WALKTHROUGH.md for the 5–10 minute Loom recording. Include repository URL, hosted URL, Loom URL and the provider limitation about alternative count. GitHub repository: https://github.com/Avinaash076/TRUCKERS. Deployed frontend: https://truckers-web.onrender.com. Deployed backend: https://truckers-api-1keh.onrender.com. Health, frontend asset configuration and CORS have been verified; production Open-Meteo requests were confirmed to receive HTTP 429 from Render. WeatherAPI integration is available; authenticated live forecasts require WEATHERAPI_KEY in Render. Loom recording remains a user deliverable.


## Weather errors on hosted deployments
A 502 response from /api/v1/corridor/ can mean the backend received an error from the weather provider. Check its JSON error message, rather than changing the frontend API URL or CORS without evidence.
- HTTP 429: provider quota/rate limit. Open-Meteo documents shared-IP limits for Render: https://open-meteo.com/en/terms. Wait for reset or arrange dedicated provider access; restarting your app does not guarantee a new quota.
- HTTP 401/403: check provider access and WEATHER_URL.
- HTTP 400: check provider endpoint and forecast parameters.
- Timeout/connection failures: retry later and inspect Render logs.
The backend logs provider names and statuses without request URLs or secrets. Corridor forecasts request three calendar days, which cover the current forecast hour through +48h. Trip ETA weather retains the 16-day request and actual-horizon checks.


## Enable WeatherAPI on Render
1. In Render open **truckers-api > Environment > Add Environment Variable**.
2. Set **WEATHERAPI_KEY** to your own key from WeatherAPI.com.
3. Set **WEATHER_PROVIDER** to **weatherapi**.
4. Choose **Save, rebuild, and deploy** (or save and deploy the latest commit).
5. Open https://truckers-api-1keh.onrender.com/api/v1/health/ and confirm weather_provider.id is weatherapi.
6. On https://truckers-web.onrender.com plan a trip departing soon and inspect checkpoint weather and the corridor slider.

Keep VITE_API_URL and CORS_ALLOWED_ORIGINS unchanged. WEATHER_URL belongs to the optional Open-Meteo adapter and is ignored in WeatherAPI mode. Store the key only in the backend environment, never in a VITE_ variable, GitHub, or frontend code.

WeatherAPI free accounts provide three calendar days of hourly forecasts. Requests use one call per unique location, up to six simultaneous calls, a 90-second total retrieval budget, and a 15-minute per-location cache. Bulk requests are not used. Missing values and hours beyond actual returned coverage remain unknown, and affected routes remain ineligible.

WeatherAPI time_epoch defines the beginning of an hourly forecast period; its wind_mph is the hourly maximum, so it is used directly without interpolation. precip_mm is total precipitation, not separately reported liquid rainfall. The adapter conservatively applies rain thresholds to total precipitation, converts snowfall cm to inches, and exposes this interpretation in warnings and risk reasons. WeatherAPI attribution appears in the frontend after a trip assessment.

The existing deterministic tests use test-only keys and responses. A real WeatherAPI live check cannot be claimed until your key is configured in Render. Provider reference: https://www.weatherapi.com/docs/forecast-api/
