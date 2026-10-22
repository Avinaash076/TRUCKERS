from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from .risk import classify,summarize,recommend,LABELS
from .checkpoints import checkpoints,MILE
from .corridor import grid
from .weather import at,fetch
from .providers import ProviderError,routes
from .views import Trip

NOW = datetime.now(timezone.utc)
def route(identifier="a",scores=(0,0,0),miles=(0,25,32)):
    value = {"id":identifier,"distance_miles":miles[-1],"duration_seconds":1000,"checkpoints":[{"mile":m,"risk":None if s is None else {"score":s}} for m,s in zip(miles,scores)]}
    summarize(value)
    return value

class RiskTests(SimpleTestCase):
    def test_wind_boundaries(self):
        for threshold,level in [(25,1),(35,2),(45,3),(55,4)]:
            for delta,expected in [(-.001,level-1),(0,level),(.001,level)]:
                with self.subTest(threshold=threshold,delta=delta):
                    self.assertEqual(classify(threshold+delta,0,0,0)["score"],expected)
    def test_precipitation_boundaries(self):
        for variable,thresholds in [("rain",[.1,.25,.5,1]),("snow",[.5,1,2,3])]:
            for i,threshold in enumerate(thresholds):
                for delta in [-.00001,0,.00001]:
                    expected = i if delta < 0 or (i == 3 and delta == 0) else i+1
                    values = [0,threshold+delta,0,0] if variable=="rain" else [0,0,threshold+delta,0]
                    with self.subTest(variable=variable,threshold=threshold,delta=delta):
                        self.assertEqual(classify(*values)["score"],expected)
    def test_load_boundaries(self):
        for wind,limit,normal,restricted in [(45,30000,3,4),(54.999,30000,3,4),(35,40000,2,3),(44.999,40000,2,3)]:
            for delta,expected in [(-.01,normal),(0,normal),(.01,restricted)]:
                self.assertEqual(classify(wind,0,0,limit+delta)["score"],expected)
        self.assertEqual(classify(34.999,0,0,100000)["score"],1)
        self.assertEqual(classify(55,0,0,0)["score"],4)
    def test_combined_weather_uses_worst(self):
        self.assertEqual(classify(25,.6,4,0)["score"],4)
        self.assertEqual(classify(35,.6,0,41000)["score"],3)
    def test_partial_segment_and_conservative_endpoints(self):
        r=route(scores=(0,3,2))
        self.assertEqual(r["risk_miles"]["Severe"],32)
        self.assertEqual(r["average_risk"],3)
        self.assertAlmostEqual(sum(r["risk_miles"].values()),r["distance_miles"])
    def test_no_travel_and_unknown_excluded(self):
        for scores in [(0,4,0),(0,None,0)]:
            r=route(scores=scores)
            self.assertFalse(r["eligible"])
            self.assertIsNone(recommend([r]))
    def test_lexicographic_ranking(self):
        a,b=route("a",scores=(3,0,0)),route("b",scores=(2,2,2))
        self.assertEqual(recommend([a,b]),"b")
        a,b=route("a",scores=(2,0,0)),route("b",scores=(1,1,1))
        self.assertEqual(recommend([a,b]),"b")
    def test_average_duration_and_stable_tie(self):
        a,b=route("a",scores=(0,0,0)),route("b",scores=(1,1,1))
        a["duration_seconds"]=2000
        self.assertEqual(recommend([a,b]),"a")
        b=route("b");b["duration_seconds"]=500
        self.assertEqual(recommend([a,b]),"b")
        a["duration_seconds"]=500
        self.assertEqual(recommend([b,a]),"a")

class GeometryTests(SimpleTestCase):
    def test_curved_route_and_segment_time(self):
        points=checkpoints([[0,0],[1,0],[1,1]],[10*MILE,20*MILE],[100,800],10,NOW)
        self.assertEqual([p["mile"] for p in points],[0,10,20,30])
        self.assertEqual(points[2]["coordinate"],[1,.5])
        self.assertEqual(datetime.fromisoformat(points[2]["eta"]),NOW+timedelta(seconds=500))
    def test_partial_endpoint_and_spacing(self):
        for spacing in [10,25,50]:
            points=checkpoints([[0,0],[1,1]],[63*MILE],[630],spacing,NOW)
            self.assertAlmostEqual(points[-1]["mile"],63)
            self.assertEqual(points[-1]["coordinate"],[1,1])
            for a,b in zip(points,points[1:-1]):
                self.assertAlmostEqual(b["mile"]-a["mile"],spacing)
    def test_bad_annotations(self):
        with self.assertRaises(ValueError):
            checkpoints([[0,0],[1,1]],[1,2],[1],10,NOW)
    def test_corridor_has_off_route_points_and_cap(self):
        points,radius=grid([[[0,0],[1,0],[2,0]]])
        self.assertTrue(any(abs(p[1])>.05 for p in points))
        self.assertLessEqual(len(points),120)
        self.assertGreater(radius,0)

class WeatherTests(SimpleTestCase):
    def setUp(self):
        self.t=datetime(2026,1,1,tzinfo=timezone.utc)
        self.series={(0,0):{"epochs":[self.t.timestamp()+h*3600 for h in range(3)],"wind_speed_10m":[10,20,30],"rain":[0,25.4,50.8],"showers":[0,0,0],"snowfall":[0,2.54,5.08]}}
    def test_interval_accumulation_wind_interpolation_units(self):
        w=at(self.series,[0,0],self.t+timedelta(minutes=30))
        self.assertEqual(w["wind_mph"],15)
        self.assertEqual(w["rain_in_hr"],1)
        self.assertEqual(w["snow_in_hr"],1)
    def test_exact_hour_and_timezone(self):
        w=at(self.series,[0,0],datetime.fromisoformat("2026-01-01T06:30:00+05:30"))
        self.assertEqual(w["wind_mph"],20)
        self.assertEqual(w["rain_in_hr"],1)
    def test_missing_and_outside_horizon(self):
        self.assertIsNone(at(self.series,[0,0],self.t-timedelta(seconds=1)))
        self.assertIsNone(at(self.series,[0,0],self.t+timedelta(hours=3)))
        self.series[(0,0)]["rain"][1]=None
        self.assertIsNone(at(self.series,[0,0],self.t+timedelta(minutes=30)))
    @patch("routing.weather.get_json")
    def test_provider_units_and_location_matching(self,mock):
        mock.return_value={"hourly_units":{"wind_speed_10m":"mp/h","rain":"mm","snowfall":"cm"},"hourly":{"time":["2026-01-01T00:00"],"wind_speed_10m":[10],"rain":[0],"showers":[0],"snowfall":[0]}}
        result=fetch([[1,2],[1,2]])
        self.assertIn((1,2),result)
        self.assertEqual(mock.call_args.args[1]["latitude"],"2")
        mock.return_value["hourly_units"]["snowfall"]="mm"
        with self.assertRaises(ProviderError):
            fetch([[1,2]])

class EndpointTests(SimpleTestCase):
    def setUp(self):
        self.client=APIClient()
        self.payload={"origin":[0,0],"destination":[1,1],"departure":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),"load_lb":30000,"interval_miles":25}
    def test_health_and_invalid_input(self):
        self.assertEqual(self.client.get("/api/v1/health/").status_code,200)
        self.assertEqual(self.client.post("/api/v1/assess/",{},format="json").status_code,400)
        for field,value in [("load_lb",-1),("interval_miles",15),("origin",[500,1]),("departure","2026-01-01T00:00")]:
            with self.subTest(field=field):
                self.assertEqual(self.client.post("/api/v1/assess/",{**self.payload,field:value},format="json").status_code,400)
    @patch("routing.views.providers.routes",side_effect=ProviderError("unavailable"))
    def test_provider_failure(self,mock):
        self.assertEqual(self.client.post("/api/v1/assess/",self.payload,format="json").status_code,502)
    @patch("routing.views.weather.fetch",side_effect=ProviderError("weather offline"))
    @patch("routing.views.providers.routes")
    def test_missing_weather_is_honest(self,mock_routes,mock_weather):
        mock_routes.return_value=[{"id":"a","geometry":[[0,0],[1,1]],"distances":[32*MILE],"durations":[1000],"distance_miles":32,"duration_seconds":1000}]
        response=self.client.post("/api/v1/assess/",self.payload,format="json")
        self.assertEqual(response.status_code,200)
        self.assertIsNone(response.data["recommended_id"])
        self.assertEqual(response.data["routes"][0]["unknown_miles"],32)
        self.assertTrue(response.data["warnings"])
    @patch("routing.providers.get_json")
    def test_duplicate_routes_removed(self,mock):
        raw={"geometry":{"coordinates":[[0,0],[1,1]]},"legs":[{"annotation":{"distance":[10],"duration":[1]}}]}
        mock.return_value={"code":"Ok","routes":[raw,raw]}
        self.assertEqual(len(routes([0,0],[1,1])),1)
    def test_nonfinite_load_rejected(self):
        serializer=Trip(data={**self.payload,"load_lb":float("nan")})
        self.assertFalse(serializer.is_valid())

    @patch("routing.weather.get_json",return_value={"hourly_units":{}})
    def test_malformed_weather_rejected(self,mock):
        with self.assertRaises(ProviderError):
            fetch([[0,0]])

    def test_invalid_corridor_and_geocode(self):
        self.assertEqual(self.client.get("/api/v1/geocode/?q=x").status_code,400)
        self.assertEqual(self.client.post("/api/v1/corridor/",{"geometries":[],"load_lb":1},format="json").status_code,400)
