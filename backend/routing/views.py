from datetime import datetime,timezone,timedelta
from math import isfinite
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import providers,weather
from .checkpoints import checkpoints
from .corridor import grid
from .risk import from_weather,summarize,recommend

class Point(serializers.ListField):
    def __init__(self,**kwargs):
        super().__init__(child=serializers.FloatField(),min_length=2,max_length=2,**kwargs)
    def to_internal_value(self,data):
        point = super().to_internal_value(data)
        if not (-180 <= point[0] <= 180 and -85 <= point[1] <= 85):
            raise serializers.ValidationError("Use [longitude, latitude] within map bounds.")
        return point

class LoadSerializer(serializers.Serializer):
    def validate_load_lb(self,value):
        if not isfinite(value):
            raise serializers.ValidationError("Load must be a finite number.")
        return value

class Trip(LoadSerializer):
    origin = Point()
    destination = Point()
    departure = serializers.CharField()
    load_lb = serializers.FloatField(min_value=0,max_value=200000)
    interval_miles = serializers.ChoiceField(choices=[10,25,50])
    def validate_departure(self,value):
        try:
            date = datetime.fromisoformat(value.replace("Z","+00:00"))
            if date.utcoffset() is None:
                raise ValueError()
        except ValueError:
            raise serializers.ValidationError("Use an ISO timestamp with a timezone offset.")
        now = datetime.now(timezone.utc)
        if not now-timedelta(minutes=10) <= date <= now+timedelta(days=15):
            raise serializers.ValidationError("Departure must be within the future forecast window.")
        return date
    def validate(self,value):
        if value["origin"] == value["destination"]:
            raise serializers.ValidationError("Choose different origin and destination locations.")
        return value

@api_view(["GET"])
def health(request):
    return Response({"status":"ok","version":1,"weather_provider":weather.provider_info()})

@api_view(["GET"])
def geocode(request):
    query = request.query_params.get("q","").strip()
    if not 2 <= len(query) <= 200:
        return Response({"error":"Enter a location between 2 and 200 characters."},status=400)
    try:
        return Response({"results":providers.geocode(query)})
    except providers.ProviderError as exc:
        return Response({"error":str(exc)},status=502)

@api_view(["POST"])
def assess(request):
    serializer = Trip(data=request.data)
    if not serializer.is_valid():
        return Response({"error":"Check the trip inputs.","fields":serializer.errors},status=400)
    data,warnings = serializer.validated_data,[]
    info = weather.provider_info()
    if info["notice"]:
        warnings.append(info["notice"])
    try:
        routes = providers.routes(data["origin"],data["destination"])
        for route in routes:
            if route["distance_miles"] > 5000:
                return Response({"error":"Choose a road journey under 5,000 miles."},status=400)
            route["checkpoints"] = checkpoints(route["geometry"],route.pop("distances"),route.pop("durations"),data["interval_miles"],data["departure"])
        try:
            series = weather.fetch([c["coordinate"] for r in routes for c in r["checkpoints"]])
        except providers.ProviderError as exc:
            series = {}
            warnings.append(str(exc))
        for route in routes:
            for checkpoint in route["checkpoints"]:
                w = weather.at(series,checkpoint["coordinate"],datetime.fromisoformat(checkpoint["eta"]))
                checkpoint["weather"] = w
                checkpoint["risk"] = from_weather(w,data["load_lb"]) if w else None
            summarize(route)
        if len(routes) < 3:
            warnings.append(f"Provider returned {len(routes)} distinct route(s). Three alternatives are not available for every journey.")
        if any(r["unknown_miles"] for r in routes):
            warnings.append("Some checkpoint weather is unavailable. Incomplete routes cannot be recommended.")
        winner = recommend(routes)
        return Response({"weather_provider":info,"routes":routes,"recommended_id":winner,"warnings":warnings,"ranking_rule":"Severe miles, High miles, distance-weighted average risk, duration","assessed_at":datetime.now(timezone.utc).isoformat()})
    except providers.ProviderError as exc:
        return Response({"error":str(exc)},status=502)
    except (KeyError,ValueError,TypeError,IndexError):
        return Response({"error":"Routing provider returned unsupported segment data. Try another journey."},status=502)

class Corridor(LoadSerializer):
    geometries = serializers.ListField(child=serializers.ListField(child=Point(),min_length=2,max_length=100000),min_length=1,max_length=3)
    load_lb = serializers.FloatField(min_value=0,max_value=200000)

@api_view(["POST"])
def corridor(request):
    serializer = Corridor(data=request.data)
    if not serializer.is_valid():
        return Response({"error":"Invalid corridor request.","fields":serializer.errors},status=400)
    data = serializer.validated_data
    points,radius = grid(data["geometries"])
    anchor = datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    try:
        series = weather.fetch(points, forecast_days=3)
        samples = []
        for point in points:
            hours = []
            for h in range(49):
                w = weather.at(series,point,anchor+timedelta(hours=h))
                hours.append({"weather":w,"risk":from_weather(w,data["load_lb"])} if w else None)
            samples.append({"coordinate":point,"hours":hours})
        return Response({"weather_provider":weather.provider_info(),"anchor":anchor.isoformat(),"radius_m":radius,"samples":samples})
    except providers.ProviderError as exc:
        return Response({"error":str(exc)},status=502)
