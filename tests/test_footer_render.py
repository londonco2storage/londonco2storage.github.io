"""Exercise the real Hugo template with known event counts and missing data."""
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FooterParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.numbers = []
        self.labels = []
        self.capture = None
        self.countries = {}

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "dd" and attributes.get("class") == "stat-num":
            self.capture = self.numbers
            self.capture.append("")
        if tag == "dt" and attributes.get("class") == "stat-label":
            self.capture = self.labels
            self.capture.append("")
        if tag == "path" and "data-country" in attributes:
            self.countries[attributes["data-country"]] = attributes

    def handle_endtag(self, tag):
        if tag in ("dd", "dt"):
            self.capture = None

    def handle_data(self, value):
        if self.capture is not None:
            self.capture[-1] += value


@unittest.skipUnless(shutil.which("hugo"), "Hugo is required for template regression tests")
class FooterRenderTests(unittest.TestCase):
    def render(self, snapshot):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "config.toml").write_text('baseURL = "https://example.test/subpath/"\n')
            (source / "layouts/partials").mkdir(parents=True)
            (source / "layouts/index.html").write_text('{{ partial "visitor-stats.html" . }}')
            shutil.copy(ROOT / "layouts/partials/visitor-stats.html", source / "layouts/partials")
            (source / "data").mkdir()
            shutil.copy(ROOT / "data/visitor_map.json", source / "data")
            if snapshot is not None:
                (source / "data/livestats.json").write_text(json.dumps(snapshot))
            subprocess.run(["hugo", "--source", str(source), "--minify"], capture_output=True, check=True)
            html = (source / "public/index.html").read_text()
            parser = FooterParser()
            parser.feed(html)
            return parser, html

    def test_only_2026_reports_count_in_the_correct_bucket(self):
        fixtures = [
            ("download-London_Register_Annual_Report_2025.pdf", 900),
            ("download-London_Register_Methodology_2025.pdf", 800),
            ("download-DNV_Data_Quality_Assurance_2025.pdf", 700),
            ("download-London_Register_Annual_Report_2026_draft.pdf", 2),
            ("download-London_Register_Annual_Report_2026.pdf", 3),
            ("download-London_Register_Methodology_2026_draft.pdf", 7),
            ("download-London_Register_Methodology_2026.pdf", 4),
            ("download-DNV_Data_Assurance_Summary_2026_draft.pdf", 13),
            ("download-DNV_Data_Assurance_Summary_2026.pdf", 4),
            ("download-table1-csv", 19),
            ("goto-zenodo", 23),
            ("/", 10),
            ("/data", 20),
            ("/index.html", 2),
        ]
        parser, html = self.render({"generated": "2026-10-15 14:22 UTC", "hits": [
            {"path": path, "count": count} for path, count in fixtures], "countries": [
                {"name": "United Kingdom", "count": 10}, {"name": "Greece", "count": 1}]})
        self.assertEqual(parser.numbers, ["5", "11", "17", "19", "23", "32"])
        self.assertTrue(all(label.startswith("2026 ") for label in parser.labels[:3]))
        self.assertEqual(len(parser.countries), 175)
        self.assertEqual(parser.countries["United Kingdom"]["data-count"], "10")
        self.assertEqual(parser.countries["Greece"]["data-count"], "1")
        self.assertIn("visits-medium", parser.countries["United Kingdom"]["class"])
        self.assertIn("visits-low", parser.countries["Greece"]["class"])
        self.assertNotIn("<script", html)
        self.assertNotIn("ZgotmplZ", html)

    def test_china_geometry_and_count_include_taiwan_in_legacy_snapshots(self):
        parser, html = self.render({"generated": "2026-10-15 14:22 UTC", "hits": [], "countries": [
            {"name": "China", "count": 7}, {"name": "Taiwan", "count": 5}]})
        self.assertEqual(parser.countries["China"]["data-count"], "12")
        self.assertIn("visits-medium", parser.countries["China"]["class"])
        self.assertNotIn("Taiwan", parser.countries)
        self.assertIn("China: 12 recorded visits", html)
        self.assertNotIn("Taiwan:", html)
        self.assertNotIn("map-legend", html)
        self.assertNotIn("visitor-countries", html)

    def test_2025_downloads_do_not_increment_2026_counters(self):
        parser, _ = self.render({"generated": "2026-10-15 14:22 UTC", "hits": [
            {"path": "download-London_Register_Annual_Report_2025.pdf", "count": 123},
            {"path": "download-DNV_Data_Quality_Assurance_2025.pdf", "count": 456}], "countries": []})
        self.assertEqual(parser.numbers, ["0"] * 6)

    def test_unavailable_and_empty_snapshots_are_distinct(self):
        parser, html = self.render(None)
        self.assertEqual(parser.numbers, ["–"] * 6)
        self.assertIn("Statistics are not available yet", html)
        parser, html = self.render({"generated": "2026-10-15 14:22 UTC", "hits": [], "countries": []})
        self.assertEqual(parser.numbers, ["0"] * 6)
        self.assertIn("No country visits recorded", html)
