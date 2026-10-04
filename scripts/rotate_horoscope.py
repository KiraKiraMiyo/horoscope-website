import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TIMEZONE = "Asia/Phnom_Penh"

YESTERDAY_FILE = Path("yesterday.json")
TODAY_FILE = Path("today.json")
TOMORROW_FILE = Path("tomorrow.json")


def cambodia_today() -> str:
    return datetime.now(
        ZoneInfo(TIMEZONE)
    ).strftime("%Y-%m-%d")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_tomorrow_file():
    data = load_json(TOMORROW_FILE)

    expected_date = cambodia_today()
    actual_date = data.get("date")

    if actual_date != cambodia_today():
        raise ValueError(
            f"tomorrow.json date is {actual_date}, "
            f"expected {cambodia_today()}"
        )

    if data.get("timezone") != TIMEZONE:
        raise ValueError(
            f"Invalid timezone: {data.get('timezone')}"
        )

    if data.get("version") != 1:
        raise ValueError(
            f"Invalid version: {data.get('version')}"
        )

    horoscope_data = data.get("data")

    if not isinstance(horoscope_data, list):
        raise ValueError(
            "tomorrow.json 'data' must be a list"
        )

    if len(horoscope_data) != 12:
        raise ValueError(
            f"Expected 12 zodiac signs, "
            f"got {len(horoscope_data)}"
        )

    zodiac_signs = {
        "aries",
        "taurus",
        "gemini",
        "cancer",
        "leo",
        "virgo",
        "libra",
        "scorpio",
        "sagittarius",
        "capricorn",
        "aquarius",
        "pisces",
    }

    received_signs = [
        item.get("sign")
        for item in horoscope_data
    ]

    if len(set(received_signs)) != 12:
        raise ValueError(
            "Duplicate zodiac signs detected"
        )

    if set(received_signs) != zodiac_signs:
        raise ValueError(
            f"Invalid zodiac signs: {received_signs}"
        )

    print(
        f"✅ tomorrow.json is valid for {expected_date}"
    )


def rotate_files():
    print("Validating tomorrow.json...")

    validate_tomorrow_file()

    if TODAY_FILE.exists():
        print(
            "Copying today.json -> yesterday.json"
        )

        shutil.copy2(
            TODAY_FILE,
            YESTERDAY_FILE,
        )

    print(
        "Copying tomorrow.json -> today.json"
    )

    shutil.copy2(
        TOMORROW_FILE,
        TODAY_FILE,
    )

    print("✅ Rotation completed successfully.")


def main():
    try:
        rotate_files()

    except Exception as error:
        print(
            f"❌ Rotation failed: {error}",
            file=sys.stderr,
        )

        sys.exit(1)


if __name__ == "__main__":
    main()