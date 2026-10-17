import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "rotation", Path(__file__).resolve().parents[1] / "scripts" / "rotate_horoscope.py"
)
rotation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rotation)


def forecast(day):
    entries = []
    for index, sign in enumerate(rotation.SIGNS):
        partner = rotation.SIGNS[(index + 1) % 12]
        text = {field: f"{day} {sign} {field}" for field in rotation.TEXT_FIELDS}
        english = {**text, "compatibility": partner.title()}
        khmer = {**text, "compatibility": sorted(rotation.KHMER_SIGNS[partner])[0]}
        entries.append({"sign": sign, "en": english, "kh": khmer, "luckyNumber": index + 1,
                        "scores": {key: 70 for key in rotation.SCORE_FIELDS}})
    return {"date": day, "timezone": rotation.TIMEZONE, "version": 1, "data": entries}


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.put("yesterday.json", forecast("2026-10-16"))
        self.put("today.json", forecast("2026-10-17"))
        self.put("tomorrow.json", forecast("2026-10-18"))
        self.put("day_after_tomorrow.json", forecast("2026-10-19"))

    def put(self, name, data):
        (self.root / name).write_text(json.dumps(data), encoding="utf-8")

    def get(self, name):
        return json.loads((self.root / name).read_text(encoding="utf-8"))

    def snapshot(self):
        return {file.name: file.read_bytes() for file in self.root.glob("*.json")}

    def test_midnight_publishes_two_distinct_dates(self):
        self.assertTrue(rotation.rotate_files(self.root, "2026-10-18"))
        self.assertEqual(self.get("yesterday.json")["date"], "2026-10-17")
        self.assertEqual(self.get("today.json")["date"], "2026-10-18")
        self.assertEqual(self.get("tomorrow.json")["date"], "2026-10-19")
        self.assertNotEqual(self.get("today.json")["data"], self.get("tomorrow.json")["data"])

    def test_retry_is_byte_for_byte_noop(self):
        rotation.rotate_files(self.root, "2026-10-18")
        before = self.snapshot()
        self.assertFalse(rotation.rotate_files(self.root, "2026-10-18"))
        self.assertEqual(self.snapshot(), before)

    def test_evening_run_does_not_promote_future_readings(self):
        before = self.snapshot()
        self.assertFalse(rotation.rotate_files(self.root, "2026-10-17"))
        self.assertEqual(self.snapshot(), before)

    def test_missing_buffer_changes_no_published_files(self):
        (self.root / "day_after_tomorrow.json").unlink()
        before = self.snapshot()
        with self.assertRaises(FileNotFoundError):
            rotation.rotate_files(self.root, "2026-10-18")
        self.assertEqual(self.snapshot(), before)

    def test_stale_buffer_changes_nothing(self):
        self.put("day_after_tomorrow.json", forecast("2026-10-18"))
        before = self.snapshot()
        with self.assertRaises(ValueError):
            rotation.rotate_files(self.root, "2026-10-18")
        self.assertEqual(self.snapshot(), before)

    def test_different_date_cannot_disguise_reused_content(self):
        duplicate = self.get("tomorrow.json")
        duplicate["date"] = "2026-10-19"
        self.put("day_after_tomorrow.json", duplicate)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            rotation.rotate_files(self.root, "2026-10-18")
        self.assertEqual(self.snapshot(), before)

    def test_malformed_forecasts_are_rejected(self):
        mutations = [
            lambda data: data["data"].pop(),
            lambda data: data["data"][0].update(sign="taurus"),
            lambda data: data["data"][0]["kh"].pop("health"),
            lambda data: data["data"][0].update(luckyNumber=True),
            lambda data: data["data"][0]["scores"].update(love=99),
            lambda data: data["data"][0]["en"].update(compatibility="Aries"),
            lambda data: data["data"][0]["kh"].update(compatibility="សីហ"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = forecast("2026-10-19")
                mutation(data)
                with self.assertRaises(ValueError):
                    rotation.validate_forecast(data, "2026-10-19")

    def test_old_copy_only_rotation_can_be_repaired_without_losing_yesterday(self):
        self.put("tomorrow.json", forecast("2026-10-17"))
        self.put("day_after_tomorrow.json", forecast("2026-10-18"))
        yesterday = (self.root / "yesterday.json").read_bytes()
        today = (self.root / "today.json").read_bytes()
        self.assertTrue(rotation.rotate_files(self.root, "2026-10-17"))
        self.assertEqual(self.get("tomorrow.json")["date"], "2026-10-18")
        self.assertEqual((self.root / "yesterday.json").read_bytes(), yesterday)
        self.assertEqual((self.root / "today.json").read_bytes(), today)

    def test_year_and_leap_day_boundaries(self):
        for previous, today, tomorrow in [
            ("2026-12-31", "2027-01-01", "2027-01-02"),
            ("2028-02-28", "2028-02-29", "2028-03-01"),
        ]:
            with self.subTest(today=today):
                self.put("today.json", forecast(previous))
                self.put("tomorrow.json", forecast(today))
                self.put("day_after_tomorrow.json", forecast(tomorrow))
                rotation.rotate_files(self.root, today)
                self.assertEqual(self.get("tomorrow.json")["date"], tomorrow)


if __name__ == "__main__":
    unittest.main()
