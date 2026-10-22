# API v1
All paths end with /. JSON errors have an error string, and input validation may include fields. No credentials are exposed to the browser.

- GET /api/v1/health/ → {status: "ok", version: 1}
- GET /api/v1/geocode/?q=New%20York → {results: [{label, coordinate: [longitude, latitude]}]}
- POST /api/v1/assess/
```json
{"origin":[-74.006,40.7128],"destination":[-71.0589,42.3601],"departure":"2026-10-22T14:00:00+05:30","load_lb":30000,"interval_miles":25}
```
Use a current/future offset-aware departure; the example date must be changed when needed. Interval is 10, 25 or 50. Coordinates must be finite and inside longitude ±180 and latitude ±85. Load is finite, nonnegative and at most 200,000 lb.

Response: routes[], recommended_id (nullable), warnings[], ranking_rule, assessed_at. Each route contains id, geometry as [longitude,latitude] pairs, distance_miles, duration_seconds, checkpoints[], risk_miles by category, unknown_miles, average_risk (nullable), eligible and optional rank. Checkpoints contain coordinate, mile, eta, weather (nullable), risk (nullable). Weather contains wind_mph, rain_in_hr, snow_in_hr and time; risk contains score 0–4, label and reasons[].

- POST /api/v1/corridor/: {geometries: [route.geometry, ...], load_lb: 30000}
Response: anchor (UTC forecast hour), radius_m, samples[]. Each sample contains coordinate and hours[0..48]. Frames contain weather and risk, or null if unavailable. This endpoint does not change trip ETAs.

HTTP 400: invalid inputs. HTTP 502: unavailable/malformed upstream provider. Weather failure during assessment may return HTTP 200 with real routes, explicit warnings and unknown weather; affected routes are ineligible. This allows honest map inspection during weather outages.
