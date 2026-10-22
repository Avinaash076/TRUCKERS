# Loom walkthrough (target 7–8 minutes)
Before recording: start both services or verify the hosted application; use a departure within the forecast horizon. Use New York → Boston as a verified real-weather example. The public provider returned two alternatives, so explain the visible third-slot limitation honestly.

0:00–0:45 — Introduce WeatherHaul: React/TypeScript, Django and weather-aware route comparison. State the assignment workflow and show the map-first layout.

0:45–2:00 — Search origin and destination explicitly; choose results. Set departure in local time, load in pounds and 25-mile checkpoints. Submit. Explain that routes and weather are real external data.

2:00–3:15 — Compare distance, duration, severe/high miles and average risk. Explain the ordered comparison and why the recommended route wins. Mention that a shorter route does not override higher-priority risk metrics. Explain the public service's actual alternative count without claiming three were returned.

3:15–4:15 — Select a route and a checkpoint marker. Show the actual road geometry, cumulative miles, checkpoint arrival time and associated weather. Change spacing to 10 or 50 miles and reassess.

4:15–5:15 — Move the corridor slider through 0, 24 and 48 hours. Point out changing timestamps and weather values; weather risk categories may stay the same if forecasts remain mild. Explain lateral corridor samples and why the snapshot differs from checkpoint ETA weather.

5:15–6:15 — Explain safety rules: highest applicable hazard; shared boundaries use the higher risk; load/wind restrictions; restricted and missing-weather routes are ineligible. Do not manufacture bad weather for the demo. Show automated boundary tests instead.

6:15–7:15 — Tour backend module boundaries, TypeScript API types, tests, requirements checklist and Render configuration. Show the actual passing test/build commands and explain the no-key provider tradeoff.

7:15–8:00 — Show responsive layout, deployed health endpoint if available and hosted URL. State any remaining limitations: driving-profile restrictions, forecast horizon, public-provider alternative count and free-host cold starts. Finish with repository and submission links.

Recording checklist:
- Share only the app/editor and nonsecret configuration.
- Avoid displaying .env or account tokens.
- Include GitHub URL, verified hosted URL and Loom URL in the final submission.
- Never describe an unverified deployment or unavailable third route as complete.
