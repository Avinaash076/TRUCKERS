"""Opt-in live provider check. Writes evidence only under ignored output/."""
import os,sys,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
os.environ.setdefault("DEBUG","true")
import django
django.setup()
from routing.providers import routes,geocode,ProviderError
from rest_framework.test import APIClient
candidates=[
 ("New York","Boston",[-74.006,40.7128],[-71.0589,42.3601]),
 ("San Francisco","Los Angeles",[-122.4194,37.7749],[-118.2437,34.0522]),
 ("Dallas","Houston",[-96.797,32.7767],[-95.3698,29.7604]),
 ("Berlin","Hamburg",[13.405,52.52],[9.9937,53.5511]),
]
output=Path(__file__).resolve().parent.parent/"output"
output.mkdir(exist_ok=True)
selected=None
best_count=0
for a,b,origin,destination in candidates:
    try:
        found=routes(origin,destination)
        print(a,b,"routes",len(found),flush=True)
        if len(found)>best_count:
            best_count=len(found)
            selected=(a,b,origin,destination)
        if len(found)==3:
            break
    except ProviderError as exc:
        print(str(exc),flush=True)
if not selected:
    raise SystemExit("No live route journey available")
if best_count<3:
    print("LIMITATION: public provider returned fewer than three distinct alternatives in tested journeys",flush=True)
a,b,origin,destination=selected
payload={"origin":origin,"destination":destination,"departure":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),"load_lb":30000,"interval_miles":50}
client=APIClient()
response=client.post("/api/v1/assess/",payload,format="json")
print("ASSESS",response.status_code,flush=True)
if response.status_code!=200:
    raise SystemExit(response.data)
data=response.data
(output/"live-assessment.json").write_text(json.dumps(data),encoding="utf-8")
print(json.dumps({"journey":[a,b],"routes":[{"miles":r["distance_miles"],"checkpoints":len(r["checkpoints"]),"unknown_miles":r["unknown_miles"],"eligible":r["eligible"]} for r in data["routes"]],"recommended":data["recommended_id"],"warnings":data["warnings"]}),flush=True)
response=client.post("/api/v1/corridor/",{"geometries":[r["geometry"] for r in data["routes"]],"load_lb":30000},format="json")
print("CORRIDOR",response.status_code,flush=True)
if response.status_code!=200:
    raise SystemExit(response.data)
corridor=response.data
(output/"live-corridor.json").write_text(json.dumps(corridor),encoding="utf-8")
print("GRID",len(corridor["samples"]),"HOURS",len(corridor["samples"][0]["hours"]),flush=True)
print("FORECAST_0_24_48",[corridor["samples"][0]["hours"][h] for h in [0,24,48]],flush=True)
for name in [a,b]:
    try:
        places=geocode(name)
        print("GEOCODE",name,len(places),flush=True)
    except ProviderError as exc:
        print("GEOCODE_FAILED",str(exc),flush=True)
(output/"live-journey.json").write_text(json.dumps({"origin":{"label":a,"coordinate":origin},"destination":{"label":b,"coordinate":destination}}),encoding="utf-8")
