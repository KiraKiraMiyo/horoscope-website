"""Promote two prepared forecasts at Cambodia midnight, safely on retries."""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Phnom_Penh"
SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
    "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
TEXT_FIELDS = (
    "summary", "love", "career", "money", "health", "mood",
    "luckyColor", "compatibility",
)
SCORE_FIELDS = ("love", "career", "money", "health", "luck")
KHMER_SIGNS = {
    "aries": {"មេស", "មេសា"}, "taurus": {"ឧសភ"},
    "gemini": {"មិថុន"}, "cancer": {"កក្កដ", "កក្កដា"},
    "leo": {"សីហ"}, "virgo": {"កញ្ញា"}, "libra": {"តុលា"},
    "scorpio": {"វិច្ឆិក", "វិច្ឆិកា"}, "sagittarius": {"ធ្នូ"},
    "capricorn": {"មករ", "មករា"}, "aquarius": {"កុម្ភៈ", "កុម្ភ"},
    "pisces": {"មីន", "មីនា"},
}


def cambodia_today() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def validate_forecast(data: dict, expected_date: str) -> None:
    if not isinstance(data, dict) or data.get("date") != expected_date:
        raise ValueError(f"Expected forecast for {expected_date}")
    if data.get("timezone") != TIMEZONE or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Expected Asia/Phnom_Penh timezone and version 1")
    entries = data.get("data")
    if not isinstance(entries, list) or len(entries) != 12:
        raise ValueError("Expected exactly 12 zodiac entries")
    if not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("Every zodiac entry must be an object")
    signs = [entry.get("sign") for entry in entries]
    if not all(isinstance(sign, str) for sign in signs) or set(signs) != set(SIGNS):
        raise ValueError("Expected each lowercase zodiac sign exactly once")
    for entry in entries:
        for language in ("en", "kh"):
            text = entry.get(language)
            if not isinstance(text, dict) or any(
                not isinstance(text.get(key), str) or not text[key].strip()
                for key in TEXT_FIELDS
            ):
                raise ValueError(f"Missing {language} text for {entry['sign']}")
        partner = entry["en"]["compatibility"].strip().lower()
        if partner not in SIGNS or partner == entry["sign"]:
            raise ValueError("Compatibility must name a different zodiac sign")
        if entry["kh"]["compatibility"].strip() not in KHMER_SIGNS[partner]:
            raise ValueError("English and Khmer compatibility must match")
        number = entry.get("luckyNumber")
        if type(number) is not int or not 1 <= number <= 99:
            raise ValueError("Lucky numbers must be integers from 1 to 99")
        scores = entry.get("scores")
        if not isinstance(scores, dict) or any(
            type(scores.get(key)) is not int or not 40 <= scores[key] <= 98
            for key in SCORE_FIELDS
        ):
            raise ValueError("Scores must be integers from 40 to 98")
    for language in ("en", "kh"):
        if len({entry[language]["summary"].strip() for entry in entries}) != 12:
            raise ValueError(f"Duplicate {language} summaries across signs")


def validate_distinct(first: dict, second: dict) -> None:
    before = {entry["sign"]: entry for entry in first["data"]}
    for entry in second["data"]:
        for language in ("en", "kh"):
            if entry[language]["summary"].strip() == before[entry["sign"]][language]["summary"].strip():
                raise ValueError(f"Reused {language} summary for {entry['sign']} across dates")


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def rotate_files(root: Path = Path("."), today: str | None = None) -> bool:
    current_day = date.fromisoformat(today or cambodia_today())
    next_day = (current_day + timedelta(days=1)).isoformat()
    previous_day = (current_day - timedelta(days=1)).isoformat()
    today_path = root / "today.json"
    tomorrow_path = root / "tomorrow.json"
    current = load_json(today_path)
    prepared = load_json(tomorrow_path)

    # A retry must not replace yesterday with today's reading or consume the
    # buffer twice. Validate the already-published pair before returning.
    if current.get("date") == current_day.isoformat():
        validate_forecast(current, current_day.isoformat())
        if prepared.get("date") == next_day:
            validate_forecast(prepared, next_day)
            validate_distinct(current, prepared)
            print("Today and Tomorrow are already current; no changes.")
            return False
        # Recover the old copy-only rotation without overwriting yesterday.
        validate_forecast(prepared, current_day.isoformat())
        buffer = load_json(root / "day_after_tomorrow.json")
        validate_forecast(buffer, next_day)
        validate_distinct(current, buffer)
        write_json(tomorrow_path, buffer)
        print("Restored Tomorrow from the prepared buffer.")
        return True

    # Validate every input before touching any output. A missing/invalid buffer
    # fails visibly instead of publishing today's reading as tomorrow's.
    validate_forecast(current, previous_day)
    validate_forecast(prepared, current_day.isoformat())
    buffer = load_json(root / "day_after_tomorrow.json")
    validate_forecast(buffer, next_day)
    validate_distinct(current, prepared)
    validate_distinct(prepared, buffer)
    write_json(root / "yesterday.json", current)
    write_json(today_path, prepared)
    write_json(tomorrow_path, buffer)
    print(f"Published Today={current_day} and Tomorrow={next_day}.")
    return True


def main() -> None:
    try:
        rotate_files()
    except Exception as error:
        print(f"Horoscope rotation failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
