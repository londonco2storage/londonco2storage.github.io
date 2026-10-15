import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location("refresh_stats", Path(__file__).parents[1] / "scripts/refresh_stats.py")
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class RefreshStatsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "stats.json"
        self.previous = '{"generated":"previous", "hits":[{"path":"download-table1-csv","count":7}],"countries":[]}'
        self.output.write_text(self.previous)
        self.now = datetime(2026, 10, 15, 14, 22, tzinfo=timezone.utc)

    def test_pagination_keeps_low_volume_events_and_all_countries(self):
        calls = []
        def fetch(endpoint, params):
            calls.append((endpoint, params))
            if endpoint == "hits":
                if "exclude_paths" not in params:
                    return {"hits": [{"path_id": 1, "path": "/", "event": False, "count": 100}], "more": True}
                self.assertEqual(params["exclude_paths"], "1")
                return {"hits": [{"path_id": 2, "path": "download-table1-csv", "event": True, "count": 1}], "more": False}
            self.assertEqual(params["include_paths"], "1")
            if params["offset"] == 0:
                return {"stats": [{"id": "GB", "name": "United Kingdom", "count": 10}], "more": True}
            self.assertEqual(params["offset"], 1)
            return {"stats": [{"id": "GR", "name": "Greece", "count": 1}], "more": False}
        result = stats.refresh(self.output, fetch, self.now)
        self.assertEqual(result["hits"][-1]["count"], 1)
        self.assertEqual(result["countries"], [{"name": "United Kingdom", "count": 10}, {"name": "Greece", "count": 1}])
        self.assertEqual(json.loads(self.output.read_text()), result)
        self.assertTrue(all(p["start"] == "2025-01-01" and p["end"] == "2026-10-16" for _, p in calls))

    def test_second_endpoint_failure_preserves_entire_previous_snapshot(self):
        def fetch(endpoint, params):
            if endpoint == "locations":
                raise TimeoutError()
            return {"hits": [{"path_id": 1, "path": "/", "event": False, "count": 1}], "more": False}
        with self.assertRaises(TimeoutError):
            stats.refresh(self.output, fetch, self.now)
        self.assertEqual(self.output.read_text(), self.previous)

    def test_malformed_or_incomplete_data_does_not_become_zero(self):
        for payload in ({}, {"hits": None, "more": False}, {"hits": [], "more": True},
                        {"hits": []}, {"hits": [{"path": "a", "path_id": 1, "count": "1"}], "more": False}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    stats.refresh(self.output, lambda *args: payload, self.now)
                self.assertEqual(self.output.read_text(), self.previous)

    def test_repeated_page_does_not_loop_or_double_count(self):
        page = {"hits": [{"path_id": 1, "path": "/", "event": False, "count": 1}], "more": True}
        with self.assertRaises(ValueError):
            stats.refresh(self.output, lambda *args: page, self.now)
        self.assertEqual(self.output.read_text(), self.previous)

    def test_china_includes_taiwan_once_and_map_excludes_events(self):
        def fetch(endpoint, params):
            if endpoint == "hits":
                return {"hits": [
                    {"path_id": 1, "path": "/", "event": False, "count": 10},
                    {"path_id": 2, "path": "download-table1-csv", "event": True, "count": 40},
                    {"path_id": 3, "path": "/data", "event": False, "count": 4}], "more": False}
            self.assertEqual(params["include_paths"], "1,3")
            return {"stats": [
                {"id": "CN", "name": "China", "count": 10},
                {"id": "TW", "name": "Taiwan", "count": 4}], "more": False}
        result = stats.refresh(self.output, fetch, self.now)
        self.assertEqual(result["countries"], [{"name": "China", "count": 14}])
        self.assertEqual(next(r["count"] for r in result["hits"] if r["path"] == "download-table1-csv"), 40)

    def test_events_only_do_not_become_map_visits(self):
        def fetch(endpoint, params):
            self.assertEqual(endpoint, "hits")
            return {"hits": [{"path_id": 2, "path": "download-table1-csv", "event": True, "count": 4}], "more": False}
        self.assertEqual(stats.refresh(self.output, fetch, self.now)["countries"], [])

    def test_missing_event_classification_preserves_snapshot(self):
        with self.assertRaises(ValueError):
            stats.refresh(self.output, lambda *args: {"hits": [{"path_id": 1, "path": "/", "count": 1}], "more": False}, self.now)
        self.assertEqual(self.output.read_text(), self.previous)

    def test_valid_empty_data_is_zero_not_failure(self):
        result = stats.refresh(self.output, lambda endpoint, params: {"hits" if endpoint == "hits" else "stats": [], "more": False}, self.now)
        self.assertEqual(result["hits"], [])
        self.assertEqual(result["countries"], [])


if __name__ == "__main__":
    unittest.main()
