import hashlib,json,threading,time
import logging
from copy import deepcopy
from math import isfinite
import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

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
                response = httpx.get(url,params=params,timeout=12 if kind == "osrm" else 25,headers={"User-Agent":settings.PROVIDER_USER_AGENT})
        else:
            response = httpx.get(url,params=params,timeout=12 if kind == "weatherapi" else 35,headers={"User-Agent":settings.PROVIDER_USER_AGENT})
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.warning("%s provider returned HTTP %s", kind, status)
        if kind == "weatherapi":
            try:
                code = exc.response.json().get("error", {}).get("code")
            except (ValueError, AttributeError):
                code = None
            messages = {
                1002: "WeatherAPI key is missing. Set WEATHERAPI_KEY on the backend.",
                2006: "WeatherAPI key is invalid. Update WEATHERAPI_KEY on the backend.",
                2007: "WeatherAPI monthly quota is exhausted. Check your WeatherAPI account usage.",
                2008: "WeatherAPI key is disabled. Check your WeatherAPI account.",
                2009: "The WeatherAPI plan does not allow this forecast request.",
                1006: "WeatherAPI could not find weather for a requested location.",
            }
            message = messages.get(code, f"WeatherAPI request failed (HTTP {status}). Check the key and account quota.")
            raise ProviderError(message) from exc
        if status == 429:
            message = f"{kind.capitalize()} provider rate limit reached (HTTP 429). Shared hosting IPs may share the provider quota. Wait for the quota to reset or configure dedicated provider access."
        elif status in (401, 403):
            message = f"{kind.capitalize()} provider denied access (HTTP {status}). Check the provider endpoint and access configuration."
        elif status == 400:
            message = f"{kind.capitalize()} provider rejected the request (HTTP 400). Check the provider endpoint and forecast parameters."
        else:
            message = f"{kind.capitalize()} provider unavailable (HTTP {status}). Please retry later."
        raise ProviderError(message) from exc
    except httpx.TimeoutException as exc:
        logger.warning("%s provider request timed out", kind)
        raise ProviderError(f"{kind.capitalize()} provider timed out. Please retry later.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("%s provider connection or response failed (%s)", kind, type(exc).__name__)
        raise ProviderError(f"{kind.capitalize()} provider connection or response failed. Please retry later.") from exc
    cache.set(key,result,ttl)
    return result

def geocode(query):
    data = get_json(settings.GEOCODER_URL,{"q":query,"format":"jsonv2","limit":5},"geocode",86400)
    try:
        return [{"label":r["display_name"],"coordinate":[float(r["lon"]),float(r["lat"])]} for r in data]
    except (KeyError,TypeError,ValueError) as exc:
        raise ProviderError("Geocoding provider returned malformed locations.") from exc

def _request_routes(points, alternatives):
    coordinates = ";".join(",".join(str(v) for v in point) for point in points)
    return get_json(f"{settings.OSRM_URL}/route/v1/driving/{coordinates}", {
        "alternatives": "true" if alternatives else "false",
        "overview": "full", "geometries": "geojson",
        "annotations": "distance,duration", "steps": "false",
    }, "osrm")


def _normalize_route(raw, kind="provider_alternative", via=None):
    geometry = raw["geometry"]["coordinates"]
    distances = [v for leg in raw["legs"] for v in leg["annotation"]["distance"]]
    durations = [v for leg in raw["legs"] for v in leg["annotation"]["duration"]]
    if not distances or len(distances)!=len(geometry)-1 or len(durations)!=len(distances) or sum(distances)<=0 or any(not isfinite(v) or v<0 for v in distances+durations):
        raise ProviderError("Routing provider returned invalid segment data. Choose different locations.")
    fingerprint = hashlib.sha256(json.dumps(geometry).encode()).hexdigest()[:12]
    return {"id":fingerprint,"geometry":geometry,"distances":distances,"durations":durations,
            "distance_miles":sum(distances)/1609.344,"duration_seconds":sum(durations),
            "route_kind":kind,"via_coordinate":via}


def routes(origin,destination):
    from .alternatives import waypoint_candidates, substantially_distinct, reasonable
    cache_key = "road-routes:" + hashlib.sha256(json.dumps([settings.OSRM_URL,origin,destination]).encode()).hexdigest()
    saved = cache.get(cache_key)
    if saved is not None:
        return deepcopy(saved)
    data = _request_routes([origin,destination], True)
    if data.get("code") != "Ok":
        raise ProviderError("No road route found between these locations.")
    result, seen = [],set()
    for raw in data.get("routes",[]):
        route = _normalize_route(raw)
        if route["id"] not in seen:
            result.append(route)
            seen.add(route["id"])
        if len(result)==3:
            break
    if not result:
        raise ProviderError("Routing provider returned no usable routes.")
    baseline = min(result,key=lambda r:r["duration_seconds"])
    deadline = time.monotonic()+18
    for point in waypoint_candidates(baseline) if len(result)<3 else []:
        if time.monotonic()>=deadline:
            break
        try:
            extra = _request_routes([origin,point,destination], False)
            if extra.get("code")!="Ok":
                continue
            waypoints = extra.get("waypoints",[])
            if len(waypoints)>1 and waypoints[1].get("distance",0)>10000:
                continue
            for raw in extra.get("routes",[]):
                route = _normalize_route(raw,"via_waypoint",point)
                if route["id"] not in seen and reasonable(route,baseline) and substantially_distinct(route,result):
                    result.append(route)
                    seen.add(route["id"])
                    break
        except (ProviderError,KeyError,TypeError,ValueError,IndexError):
            # Extra routes are best-effort; keep the valid native road routes.
            continue
        if len(result)==3:
            break
    cache.set(cache_key,deepcopy(result),600)
    return result
