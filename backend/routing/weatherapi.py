"""WeatherAPI forecast adapter. No key or upstream URL is returned to clients."""
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from math import isfinite
from django.conf import settings
from .providers import get_json, ProviderError

URL = "https://api.weatherapi.com/v1/forecast.json"


def normalize(data):
    hours = [hour for day in data["forecast"]["forecastday"] for hour in day["hour"]]
    if not hours:
        raise ValueError("No hourly forecasts")
    hours.sort(key=lambda hour: hour["time_epoch"])
    epochs = [hour["time_epoch"] for hour in hours]
    if any(not isinstance(t, (int, float)) or not isfinite(t) for t in epochs):
        raise ValueError("Invalid forecast timestamps")
    if any(b <= a for a, b in zip(epochs, epochs[1:])):
        raise ValueError("Duplicate forecast timestamps")
    return {
        "epochs": epochs,
        "wind_speed_10m": [hour.get("wind_mph") for hour in hours],
        # This is total precipitation, not separately reported liquid rainfall.
        # Keeping it whole gives a conservative bound for the rain risk rules.
        "rain": [hour.get("precip_mm") for hour in hours],
        "showers": [0 for _ in hours],
        "snowfall": [hour.get("snow_cm") for hour in hours],
        "interval": "start",
        "rain_basis": "total_precipitation",
    }


def fetch(points, forecast_days=3):
    if not settings.WEATHERAPI_KEY:
        raise ProviderError("Set WEATHERAPI_KEY in the backend environment to enable WeatherAPI.")
    unique = list(dict.fromkeys(tuple(round(v, 4) for v in point) for point in points))
    if not unique:
        return {}
    days = min(forecast_days, 3)
    def retrieve(point):
        data = get_json(URL, {
            "key": settings.WEATHERAPI_KEY,
            "q": f"{point[1]},{point[0]}",
            "days": days,
            "aqi": "no",
            "alerts": "no",
        }, kind="weatherapi", ttl=900)
        try:
            return point, normalize(data)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ProviderError("WeatherAPI returned malformed hourly forecast data.") from exc

    # Free WeatherAPI accounts use one request per location (bulk is paid).
    # Bound parallelism and total request time to fit the web-service timeout.
    pool = ThreadPoolExecutor(max_workers=6)
    futures = [pool.submit(retrieve, point) for point in unique]
    result = {}
    try:
        for future in as_completed(futures, timeout=90):
            point, series = future.result()
            result[point] = series
    except TimeoutError as exc:
        raise ProviderError("WeatherAPI forecast retrieval timed out. Try a shorter trip or wider checkpoint spacing.") from exc
    finally:
        for future in futures:
            future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
    return result
