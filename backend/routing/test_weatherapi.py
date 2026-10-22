from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from . import weather
from .providers import get_json, ProviderError
from .risk import from_weather
from .weatherapi import normalize

START = datetime(2026, 10, 22, tzinfo=timezone.utc)
def forecast():
    return {"forecast": {"forecastday": [{"hour": [
        {"time_epoch": int((START+timedelta(hours=h)).timestamp()), "wind_mph": wind, "precip_mm": rain, "snow_cm": snow}
        for h, wind, rain, snow in [(0, 35, 2.54, 2.54), (1, 10, 0, 0)]
    ]}]}}

@override_settings(WEATHER_PROVIDER="weatherapi", WEATHERAPI_KEY="test-key-not-real")
class WeatherAPIAdapterTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch("routing.weatherapi.get_json")
    def test_coordinates_days_and_deduplication(self, mock):
        mock.return_value = forecast()
        series = weather.fetch([[1,2],[1,2]], forecast_days=16)
        self.assertEqual(mock.call_count, 1)
        params = mock.call_args.args[1]
        self.assertEqual(params["q"], "2,1")
        self.assertEqual(params["days"], 3)
        self.assertEqual(params["key"], "test-key-not-real")
        self.assertIn((1,2), series)

    def test_hourly_max_wind_units_and_period_start(self):
        series = {(0,0): normalize(forecast())}
        result = weather.at(series, [0,0], START+timedelta(minutes=30))
        self.assertEqual(result["wind_mph"], 35)
        self.assertAlmostEqual(result["rain_in_hr"], .1)
        self.assertAlmostEqual(result["snow_in_hr"], 1)
        self.assertEqual(result["rain_basis"], "total_precipitation")
        # Exactly 01:00 uses the new hour rather than the preceding interval.
        self.assertEqual(weather.at(series,[0,0],START+timedelta(hours=1))["wind_mph"],10)

    def test_timezone_uses_epoch_not_local_time_string(self):
        series = {(0,0): normalize(forecast())}
        when = datetime.fromisoformat("2026-10-22T06:00:00+05:30")
        self.assertEqual(weather.at(series,[0,0],when)["wind_mph"],35)

    def test_last_hour_coverage_and_no_extrapolation(self):
        series = {(0,0): normalize(forecast())}
        self.assertIsNotNone(weather.at(series,[0,0],START+timedelta(hours=1,minutes=59)))
        self.assertIsNone(weather.at(series,[0,0],START+timedelta(hours=2)))
        self.assertIsNone(weather.at(series,[0,0],START-timedelta(seconds=1)))

    def test_missing_snow_does_not_become_zero(self):
        data = forecast()
        del data["forecast"]["forecastday"][0]["hour"][0]["snow_cm"]
        series = {(0,0): normalize(data)}
        self.assertIsNone(weather.at(series,[0,0],START))

    def test_forecast_gap_is_unknown(self):
        data = forecast()
        data["forecast"]["forecastday"][0]["hour"][1]["time_epoch"] += 7200
        series = {(0,0): normalize(data)}
        self.assertIsNone(weather.at(series,[0,0],START+timedelta(hours=2)))

    def test_rain_rule_explains_total_precipitation(self):
        w = weather.at({(0,0):normalize(forecast())},[0,0],START)
        result = from_weather(w,0)
        self.assertTrue(any("Total precipitation" in reason for reason in result["reasons"]))

    @override_settings(WEATHERAPI_KEY="")
    @patch("routing.weatherapi.get_json")
    def test_missing_key_fails_without_public_api_fallback(self,mock):
        with self.assertRaisesMessage(ProviderError,"Set WEATHERAPI_KEY"):
            weather.fetch([[0,0]])
        mock.assert_not_called()

    @patch("routing.weatherapi.get_json")
    def test_malformed_response_is_honest(self,mock):
        mock.return_value = {"forecast": {}}
        with self.assertRaisesMessage(ProviderError,"malformed"):
            weather.fetch([[0,0]])

    @patch("routing.providers.httpx.get")
    def test_key_errors_are_actionable_and_redacted(self,mock):
        import httpx
        mock.return_value = httpx.Response(401,json={"error":{"code":2006,"message":"test-key-not-real"}},request=httpx.Request("GET","https://api.weatherapi.com/v1/forecast.json?key=test-key-not-real"))
        with self.assertRaisesMessage(ProviderError,"key is invalid") as caught:
            get_json("https://api.weatherapi.com/v1/forecast.json",{"key":"test-key-not-real"},kind="weatherapi")
        self.assertNotIn("test-key-not-real",str(caught.exception))

    @patch("routing.providers.httpx.get")
    def test_account_quota_and_location_errors(self,mock):
        import httpx
        for code, expected in [(2007,"monthly quota"),(2009,"plan does not allow"),(1006,"requested location")]:
            cache.clear()
            mock.return_value = httpx.Response(403,json={"error":{"code":code}},request=httpx.Request("GET","https://api.weatherapi.com/v1/forecast.json"))
            with self.subTest(code=code), self.assertRaisesMessage(ProviderError,expected):
                get_json("https://api.weatherapi.com/v1/forecast.json",{"key":"test-key"},kind="weatherapi")

    @patch("routing.providers.httpx.get")
    def test_repeat_location_uses_cache_across_trip_and_corridor(self,mock):
        import httpx
        mock.return_value = httpx.Response(200,json=forecast(),request=httpx.Request("GET","https://api.weatherapi.com/v1/forecast.json"))
        weather.fetch([[1,2]],forecast_days=16)
        weather.fetch([[1,2]],forecast_days=3)
        self.assertEqual(mock.call_count,1)

    def test_provider_metadata_contains_no_key(self):
        info = weather.provider_info()
        self.assertEqual(info["id"],"weatherapi")
        self.assertEqual(info["forecast_days"],3)
        self.assertNotIn("test-key-not-real",str(info))


    @patch("routing.views.providers.routes")
    @patch("routing.weatherapi.get_json")
    def test_assessment_and_corridor_use_weatherapi_end_to_end(self, mock_weather, mock_routes):
        from rest_framework.test import APIClient
        from .checkpoints import MILE
        now = datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
        mock_weather.return_value = {"forecast":{"forecastday":[{"hour":[
            {"time_epoch":int((now+timedelta(hours=h)).timestamp()),"wind_mph":10,"precip_mm":0,"snow_cm":0}
            for h in range(72)
        ]}]}}
        mock_routes.return_value = [{"id":"route-a","geometry":[[0,0],[1,1]],"distances":[30*MILE],"durations":[3600],"distance_miles":30,"duration_seconds":3600}]
        client=APIClient()
        response=client.post("/api/v1/assess/",{
            "origin":[0,0],"destination":[1,1],"load_lb":30000,"interval_miles":25,
            "departure":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        },format="json")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data["weather_provider"]["id"],"weatherapi")
        self.assertEqual(response.data["recommended_id"],"route-a")
        self.assertTrue(all(c["weather"] is not None for c in response.data["routes"][0]["checkpoints"]))
        self.assertTrue(any("total precipitation" in w for w in response.data["warnings"]))
        response=client.post("/api/v1/corridor/",{"geometries":[[[0,0],[1,1]]],"load_lb":30000},format="json")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data["weather_provider"]["id"],"weatherapi")
        self.assertTrue(all(frame is not None for sample in response.data["samples"] for frame in sample["hours"]))
        self.assertNotIn("test-key-not-real",str(response.data))
