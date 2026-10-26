"""Regression checks for scheduled contribution artwork refreshes."""
import copy
from datetime import date, timedelta, datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / "update-activity-art.py"
spec = importlib.util.spec_from_file_location("activity_art", SCRIPT)
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)


def sample_days(through):
    first = through - timedelta(days=167)
    days = [
        {"date": (first + timedelta(days=i)).isoformat(), "count": i % 9,
         "level": 0 if i % 9 == 0 else 1}
        for i in range(168)
    ]
    return first, days


def calendar_html(days):
    parts = []
    for day in days:
        identity = "day-" + day["date"]
        label = (f'{day["count"]} contributions on this day.'
                 if day["count"] else "No contributions on this day.")
        parts.append(f'<td id="{identity}" data-date="{day["date"]}" data-level="{day["level"]}"></td>')
        parts.append(f'<tool-tip for="{identity}">{label}</tool-tip>')
    return "".join(parts)


class CalendarTests(unittest.TestCase):
    def test_parser_handles_zero_singular_and_grouped_counts(self):
        parser = art.CalendarParser()
        parser.feed(
            '<td id="a" data-date="2026-10-23" data-level="0"></td>'
            '<td id="b" data-date="2026-10-24" data-level="1"></td>'
            '<td id="c" data-date="2026-10-25" data-level="4"></td>'
            '<tool-tip for="a">No contributions on October 23rd.</tool-tip>'
            '<tool-tip for="b">1 contribution on October 24th.</tool-tip>'
            '<tool-tip for="c">1,234 contributions on October 25th.</tool-tip>'
        )
        self.assertEqual([item["count"] for item in parser.days().values()], [0, 1, 1234])

    def test_unknown_tooltip_fails_instead_of_inventing_a_zero(self):
        parser = art.CalendarParser()
        parser.feed('<td id="a" data-date="2026-10-25" data-level="0"></td>'
                    '<tool-tip for="a">Calendar unavailable.</tool-tip>')
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            parser.days()

    def test_collection_crosses_the_year_boundary_without_missing_days(self):
        through = date(2027, 1, 4)
        first, days = sample_days(through)
        requested = []

        def public_calendar(request, timeout):
            requested.append(request.full_url)
            self.assertFalse(request.has_header("Authorization"))
            year = int(request.full_url.split("from=")[1][:4])
            subset = [day for day in days if day["date"].startswith(str(year))]
            return io.BytesIO(calendar_html(subset).encode())

        with patch.object(art, "urlopen", side_effect=public_calendar):
            actual_first, actual_days, sources = art.collect_days(through, None)
        self.assertEqual(actual_first, first)
        self.assertEqual(actual_days, days)
        self.assertEqual(len(requested), 2)
        self.assertEqual(sources, requested)

    def test_missing_public_calendar_day_stops_generation(self):
        through = date(2026, 10, 25)
        _, days = sample_days(through)
        with patch.object(art, "urlopen", return_value=io.BytesIO(calendar_html(days[:-1]).encode())):
            with self.assertRaisesRegex(ValueError, "Missing calendar day"):
                art.collect_days(through, None)

    def test_cached_data_rejects_gaps_and_negative_or_noninteger_counts(self):
        through = date(2026, 10, 25)
        first, days = sample_days(through)
        for value in [-1, True, 1.5]:
            invalid = copy.deepcopy(days)
            invalid[0]["count"] = value
            with self.subTest(count=value), self.assertRaises(ValueError):
                art.validate_days(invalid, first, through)
        invalid = copy.deepcopy(days)
        invalid[1]["date"] = invalid[0]["date"]
        with self.assertRaisesRegex(ValueError, "consecutive"):
            art.validate_days(invalid, first, through)

    def test_all_four_images_preserve_calendar_values(self):
        through = date(2026, 10, 25)
        first, days = sample_days(through)
        for dark in (False, True):
            for mobile in (False, True):
                with self.subTest(dark=dark, mobile=mobile):
                    root = ET.fromstring(art.render(days, first, through, dark, mobile))
                    records = [
                        (node.attrib["data-date"], int(node.attrib["data-count"]))
                        for node in root.iter() if "data-date" in node.attrib
                    ]
                    self.assertEqual(records, [(day["date"], day["count"]) for day in days])
                    self.assertEqual(int(root.attrib["data-total"]), sum(day["count"] for day in days))

    def test_a_completely_quiet_period_renders_without_dividing_by_zero(self):
        through = date(2026, 10, 25)
        first, days = sample_days(through)
        for day in days:
            day.update(count=0, level=0)
        root = ET.fromstring(art.render(days, first, through, True, True))
        self.assertEqual(root.attrib["data-total"], "0")
        self.assertEqual(root.attrib["data-active-days"], "0")


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.output = self.root / "assets" / "activity"
        self.readme = self.root / "README.md"
        self.readme.write_text(
            '<p>Keep my other profile content.</p>\n'
            f'<sub>A 24-week snapshot of my <a href="https://github.com/{art.ACCOUNT}?tab=overview">'
            'public GitHub calendar</a>, through October 24, 2026.</sub>\n',
            encoding="utf-8",
        )
        self.through = date(2026, 10, 25)
        self.first, self.days = sample_days(self.through)
        self.patches = [
            patch.object(art, "ROOT", self.root),
            patch.object(art, "OUTPUT", self.output),
            patch("sys.argv", ["update-activity-art.py", "--through", self.through.isoformat()]),
            patch("sys.stdout", new_callable=io.StringIO),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def refresh(self, days=None):
        records = copy.deepcopy(self.days if days is None else days)
        with patch.object(art, "collect_days", return_value=(self.first, records, ["https://github.com/public-calendar"])):
            art.main()

    def files(self):
        return {file.relative_to(self.root).as_posix(): file.read_bytes()
                for file in self.root.rglob("*") if file.is_file()}

    def test_identical_fetches_do_not_change_files_even_when_time_changes(self):
        self.refresh()
        before = self.files()
        with patch.object(art, "datetime") as clock:
            clock.now.return_value = datetime(2099, 1, 1, tzinfo=timezone.utc)
            self.refresh()
        self.assertEqual(self.files(), before)
        self.assertIn("Updated daily.", self.readme.read_text(encoding="utf-8"))
        self.assertIn("Keep my other profile content.", self.readme.read_text(encoding="utf-8"))

    def test_a_backfilled_contribution_changes_data_and_images(self):
        self.refresh()
        before = self.files()
        changed = copy.deepcopy(self.days)
        changed[4]["count"] += 3
        self.refresh(changed)
        after = self.files()
        self.assertNotEqual(before["assets/activity/calendar.json"], after["assets/activity/calendar.json"])
        for name in ("skyline.svg", "skyline-light.svg", "skyline-mobile.svg", "skyline-mobile-light.svg"):
            self.assertNotEqual(before["assets/activity/" + name], after["assets/activity/" + name])

    def test_missing_caption_does_not_publish_partial_outputs(self):
        self.readme.write_text("A different README.\n", encoding="utf-8")
        before = self.files()
        with self.assertRaisesRegex(ValueError, "snapshot caption"):
            self.refresh()
        self.assertEqual(self.files(), before)


if __name__ == "__main__":
    unittest.main()
