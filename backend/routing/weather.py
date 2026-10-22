from bisect import bisect_left
from math import isfinite
from datetime import datetime,timezone
from django.conf import settings
from .providers import get_json,ProviderError

def _fetch(points, forecast_days):
    unique = list(dict.fromkeys(tuple(round(v,4) for v in p) for p in points))
    result = {}
    for start in range(0,len(unique),30):
        batch = unique[start:start+30]
        data = get_json(settings.WEATHER_URL,{"latitude":",".join(str(p[1]) for p in batch),"longitude":",".join(str(p[0]) for p in batch),"hourly":"wind_speed_10m,rain,showers,snowfall","wind_speed_unit":"mph","precipitation_unit":"mm","timezone":"GMT","forecast_days":forecast_days})
        rows = data if isinstance(data,list) else [data]
        if len(rows) != len(batch):
            raise ProviderError("Weather provider returned incomplete location data.")
        for point,row in zip(batch,rows):
            units = row.get("hourly_units",{})
            if units.get("wind_speed_10m") != "mp/h" or units.get("rain") != "mm" or units.get("snowfall") != "cm":
                raise ProviderError("Unexpected weather units; assessment stopped.")
            hourly = row["hourly"]
            if not hourly.get("time") or any(not isinstance(hourly.get(name),list) or len(hourly[name])!=len(hourly["time"]) for name in ["wind_speed_10m","rain","showers","snowfall"]):
                raise ValueError("Incomplete hourly arrays")
            hourly["epochs"] = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp() for t in hourly["time"]]
            result[point] = hourly
    return result

def fetch(points, forecast_days=16):
    try:
        return _fetch(points, forecast_days)
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        raise ProviderError("Weather provider returned malformed forecast data.") from exc

def at(series,point,when):
    row = series.get(tuple(round(v,4) for v in point))
    if not row:
        return None
    epoch,times = when.timestamp(),row["epochs"]
    if not times or epoch < times[0] or epoch > times[-1]:
        return None
    # Hourly accumulation ends at the reported timestamp.
    right = bisect_left(times,epoch)
    left = max(0,right-1)
    values = [row[k][right] for k in ["rain","showers","snowfall","wind_speed_10m"]]
    previous = row["wind_speed_10m"][left]
    if any(not isinstance(v,(int,float)) or not isfinite(v) or v<0 for v in values+[previous]):
        return None
    rain,showers,snow,wind = values
    fraction = (epoch-times[left])/(times[right]-times[left]) if right != left else 0
    return {"wind_mph":previous+fraction*(wind-previous),"rain_in_hr":(rain+showers)/25.4,"snow_in_hr":snow/2.54,"time":when.isoformat()}
