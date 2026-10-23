from copy import deepcopy
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from .providers import routes, _normalize_route, ProviderError
from .alternatives import waypoint_candidates, reasonable, substantially_distinct


def raw(geometry=None, distances=None, duration=3600):
    geometry = geometry or [[0,0],[.5,0],[1,0]]
    distances = distances or [100000/(len(geometry)-1)]*(len(geometry)-1)
    return {"geometry":{"coordinates":geometry},"legs":[{"annotation":{"distance":distances,"duration":[duration/(len(geometry)-1)]*(len(geometry)-1)}}]}


BASE = raw()
SECOND = raw([[0,0],[.5,.05],[1,0]], [52000,52000], 3800)
THIRD = raw([[0,0],[.4,-.2],[.7,-.2],[1,0]], [35000,35000,35000], 4000)


class AlternativeTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch("routing.providers.get_json")
    def test_fills_missing_third_with_real_waypoint_route(self,mock):
        mock.side_effect = [{"code":"Ok","routes":[BASE,SECOND]},{"code":"Ok","routes":[THIRD]}]
        found = routes([0,0],[1,0])
        self.assertEqual(len(found),3)
        self.assertEqual(found[2]["route_kind"],"via_waypoint")
        self.assertEqual(len({r["id"] for r in found}),3)
        self.assertEqual(mock.call_count,2)
        self.assertEqual(mock.call_args.args[1]["alternatives"],"false")
        self.assertIsNotNone(found[2]["via_coordinate"])

    @patch("routing.providers.get_json")
    def test_keeps_native_three_without_extra_search(self,mock):
        mock.return_value={"code":"Ok","routes":[BASE,SECOND,THIRD]}
        self.assertEqual(len(routes([0,0],[1,0])),3)
        self.assertEqual(mock.call_count,1)

    @patch("routing.providers.get_json")
    def test_cache_is_reused_and_annotations_are_not_mutated(self,mock):
        mock.side_effect=[{"code":"Ok","routes":[BASE,SECOND]},{"code":"Ok","routes":[THIRD]}]
        first=routes([0,0],[1,0])
        first[0].pop("distances")
        second=routes([0,0],[1,0])
        self.assertIn("distances",second[0])
        self.assertEqual(mock.call_count,2)

    @patch("routing.providers.get_json")
    def test_missing_alternatives_do_not_duplicate_native_route(self,mock):
        mock.return_value={"code":"Ok","routes":[BASE,BASE]}
        found=routes([0,0],[1,0])
        self.assertEqual(len(found),1)
        self.assertLessEqual(mock.call_count,5)

    @patch("routing.providers.get_json")
    def test_optional_provider_failure_keeps_valid_routes(self,mock):
        mock.side_effect=[{"code":"Ok","routes":[BASE,SECOND]}]+[ProviderError("offline")]*4
        self.assertEqual(len(routes([0,0],[1,0])),2)

    def test_same_road_with_different_vertices_is_not_an_alternative(self):
        baseline=_normalize_route(BASE)
        subdivided=_normalize_route(raw([[0,0],[.25,0],[.5,0],[.75,0],[1,0]]))
        self.assertFalse(substantially_distinct(subdivided,[baseline]))
        self.assertTrue(substantially_distinct(_normalize_route(THIRD),[baseline,_normalize_route(SECOND)]))

    def test_excessive_detour_and_dead_end_are_rejected(self):
        baseline=_normalize_route(BASE)
        too_long=_normalize_route(raw(distances=[80000,80000]))
        self.assertFalse(reasonable(too_long,baseline))
        slow=_normalize_route(raw(duration=6000))
        self.assertFalse(reasonable(slow,baseline))
        dead_end=_normalize_route(raw([[0,0],[.5,0],[.5,.2],[.5,0],[1,0]],[45000,5000,5000,45000]))
        self.assertFalse(reasonable(dead_end,baseline))

    def test_short_trips_do_not_force_detours(self):
        route=_normalize_route(raw(distances=[1000,1000]))
        self.assertEqual(waypoint_candidates(route),[])

    @patch("routing.views.weather.fetch")
    @patch("routing.views.providers.routes")
    def test_preview_returns_eta_before_weather_and_never_recommends(self,mock_routes,mock_weather):
        mock_routes.return_value=[_normalize_route(BASE)]
        departure=datetime.now(timezone.utc)+timedelta(hours=1)
        payload={"origin":[0,0],"destination":[1,0],"departure":departure.isoformat(),"load_lb":30000,"interval_miles":25}
        response=APIClient().post("/api/v1/routes/",payload,format="json")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data["assessment_status"],"pending")
        self.assertIsNone(response.data["recommended_id"])
        self.assertFalse(response.data["routes"][0]["eligible"])
        self.assertEqual(datetime.fromisoformat(response.data["routes"][0]["checkpoints"][-1]["eta"]),departure+timedelta(hours=1))
        mock_weather.assert_not_called()

    def test_preview_validates_input(self):
        client = APIClient()
        self.assertEqual(client.post("/api/v1/routes/",{},format="json").status_code,400)
        oversized = _normalize_route(BASE)
        oversized["distance_miles"] = 6000
        payload = {"origin":[0,0],"destination":[1,0],"departure":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),"load_lb":30000,"interval_miles":25}
        with patch("routing.views.providers.routes", return_value=[oversized]):
            response = client.post("/api/v1/routes/",payload,format="json")
        self.assertEqual(response.status_code,400)
        self.assertIn("5,000",str(response.data["error"]))
