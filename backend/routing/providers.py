import hashlib,json,threading,time
from math import isfinite
import httpx
from django.conf import settings
from django.core.cache import cache

class ProviderError(Exception):
    pass

_locks = {"osrm":threading.Lock(),"geocode":threading.Lock()}
_last = {"osrm":0.0,"geocode":0.0}

def get_json(url,params,kind="weather",ttl=600):
    key = hashlib.sha256((url+json.dumps(params,sort_keys=True)).encode()).hexdigest()
    saved = cache.get(key)
    if saved is not None:
        return saved
    try:
        if kind in _locks:
            with _locks[kind]:
                time.sleep(max(0,1.05-(time.monotonic()-_last[kind])))
                _last[kind] = time.monotonic()
                response = httpx.get(url,params=params,timeout=25,headers={"User-Agent":settings.PROVIDER_USER_AGENT})
        else:
            response = httpx.get(url,params=params,timeout=35,headers={"User-Agent":settings.PROVIDER_USER_AGENT})
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError,ValueError) as exc:
        raise ProviderError(f"{kind} provider unavailable. Please retry shortly.") from exc
    cache.set(key,result,ttl)
    return result

def geocode(query):
    data = get_json(settings.GEOCODER_URL,{"q":query,"format":"jsonv2","limit":5},"geocode",86400)
    try:
        return [{"label":r["display_name"],"coordinate":[float(r["lon"]),float(r["lat"])]} for r in data]
    except (KeyError,TypeError,ValueError) as exc:
        raise ProviderError("Geocoding provider returned malformed locations.") from exc

def routes(origin,destination):
    coordinates = ";".join(",".join(str(v) for v in point) for point in [origin,destination])
    data = get_json(f"{settings.OSRM_URL}/route/v1/driving/{coordinates}",{"alternatives":"3","overview":"full","geometries":"geojson","annotations":"distance,duration","steps":"false"},"osrm")
    if data.get("code") != "Ok":
        raise ProviderError("No road route found between these locations.")
    result,seen = [],set()
    for raw in data.get("routes",[]):
        geometry = raw["geometry"]["coordinates"]
        fingerprint = hashlib.sha256(json.dumps(geometry).encode()).hexdigest()[:12]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        distances = [v for leg in raw["legs"] for v in leg["annotation"]["distance"]]
        durations = [v for leg in raw["legs"] for v in leg["annotation"]["duration"]]
        if not distances or sum(distances)<=0 or any(not isfinite(v) or v<0 for v in distances+durations):
            raise ProviderError("Route is too short or contains invalid segment data. Choose different locations.")
        result.append({"id":fingerprint,"geometry":geometry,"distances":distances,"durations":durations,"distance_miles":sum(distances)/1609.344,"duration_seconds":sum(durations)})
        if len(result) == 3:
            break
    if not result:
        raise ProviderError("Routing provider returned no usable routes.")
    return result
