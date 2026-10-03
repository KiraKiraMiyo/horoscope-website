import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import List

from google import genai
from pydantic import BaseModel, Field
import time


TIMEZONE = "Asia/Phnom_Penh"
OUTPUT_FILE = Path("today.json")


class LocalizedHoroscope(BaseModel):
    summary: str
    love: str
    career: str
    money: str
    health: str
    mood: str
    luckyColor: str
    compatibility: str


class HoroscopeScores(BaseModel):
    love: int = Field(ge=40, le=98)
    career: int = Field(ge=40, le=98)
    money: int = Field(ge=40, le=98)
    health: int = Field(ge=40, le=98)
    luck: int = Field(ge=40, le=98)


class HoroscopeItem(BaseModel):
    sign: str
    en: LocalizedHoroscope
    kh: LocalizedHoroscope
    luckyNumber: int = Field(ge=1, le=99)
    scores: HoroscopeScores


class HoroscopeResponse(BaseModel):
    date: str
    timezone: str
    version: int
    data: List[HoroscopeItem]


ZODIAC_SIGNS = [
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
]


def cambodia_today() -> str:
    return datetime.now(
        ZoneInfo(TIMEZONE)
    ).strftime("%Y-%m-%d")


def build_prompt(date: str) -> str:
    return f"""
Generate a daily horoscope for all 12 Western zodiac signs.

Date:
{date}

Timezone:
Asia/Phnom_Penh

Audience:
Cambodian users.

Languages:
English and Khmer.

Generate exactly these signs:

aries
taurus
gemini
cancer
leo
virgo
libra
scorpio
sagittarius
capricorn
aquarius
pisces

For every zodiac sign provide:

- summary
- love
- career
- money
- health
- mood
- luckyColor
- compatibility
- luckyNumber
- love score
- career score
- money score
- health score
- luck score

Rules:

SUMMARY
Write 2-3 short sentences.

LOVE
Write 1-2 sentences about communication, relationships,
emotional awareness, patience, or boundaries.

Do not guarantee specific romantic events.

CAREER
Write 1-2 sentences about productivity, teamwork,
focus, learning, or decision making.

Do not guarantee promotions or jobs.

MONEY
Write 1-2 sentences of general reflective guidance.

Do not give investment, trading, gambling, borrowing,
or financial transaction advice.

HEALTH
Write only general wellness content such as:
rest, hydration, movement, balance, stress management,
or taking breaks.

Do not diagnose medical conditions.
Do not recommend medicines or treatments.

MOOD
Use a short value such as:
Confident
Calm
Focused
Optimistic
Creative
Reflective
Energetic
Patient
Curious
Determined

LUCKY COLOR
Use a normal recognizable color.

LUCKY NUMBER
Integer from 1 to 99.

SCORES
All scores must be integers from 40 to 98.

COMPATIBILITY
Must be one of:
Aries
Taurus
Gemini
Cancer
Leo
Virgo
Libra
Scorpio
Sagittarius
Capricorn
Aquarius
Pisces

Do not select the same zodiac sign as the current sign.

KHMER
Khmer must sound natural to Cambodian readers.

Do not produce awkward literal translations.

English and Khmer must represent the same meaning.

The Khmer lucky color must correspond to the English color.

The Khmer compatibility name must represent the same zodiac sign.

VARIETY
Every sign should receive meaningfully different content.

Avoid repeating the same sentences across multiple signs.

The response date must be:
{date}

timezone must be:
Asia/Phnom_Penh

version must be:
1
"""


def validate(data: HoroscopeResponse):
    if data.timezone != TIMEZONE:
        raise ValueError("Invalid timezone")

    if data.version != 1:
        raise ValueError("Invalid version")

    if len(data.data) != 12:
        raise ValueError(
            f"Expected 12 signs, got {len(data.data)}"
        )

    received = [item.sign for item in data.data]

    if len(set(received)) != 12:
        raise ValueError("Duplicate zodiac signs detected")

    if set(received) != set(ZODIAC_SIGNS):
        raise ValueError(
            f"Unexpected signs: {received}"
        )

MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]


def call_gemini_with_fallback(client, prompt, schema):
    last_error = None

    for model in MODELS:
        print(f"Trying model: {model}")

        for attempt in range(1, 5):
            try:
                response = client.interactions.create(
                    model=model,
                    input=prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": schema,
                    },
                )

                if not response.output_text:
                    raise RuntimeError("Gemini returned empty output")

                print(f"✅ Success with {model}")
                return response.output_text

            except Exception as error:
                last_error = error

                message = str(error).lower()

                is_retryable = (
                    "503" in message
                    or "service_unavailable" in message
                    or "unavailable" in message
                    or "429" in message
                    or "resource_exhausted" in message
                )

                if not is_retryable:
                    raise

                wait_seconds = min(2 ** attempt * 5, 60)

                print(
                    f"⚠️ {model} attempt {attempt}/4 failed: {error}"
                )

                if attempt < 4:
                    print(f"Retrying in {wait_seconds}s...")
                    time.sleep(wait_seconds)

        print(f"⚠️ Falling back from {model}")

    raise RuntimeError(
        f"All Gemini models failed. Last error: {last_error}"
    )

def generate():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    today = cambodia_today()

    client = genai.Client(api_key=api_key)

    output_text = call_gemini_with_fallback(
        client=client,
        prompt=build_prompt(today),
        schema=HoroscopeResponse.model_json_schema(),
    )

    horoscope = HoroscopeResponse.model_validate_json(
        output_text
    )

    if horoscope.date != today:
        raise ValueError(
            f"Expected date {today}, got {horoscope.date}"
        )

    validate(horoscope)

    return horoscope


def save(data: HoroscopeResponse):
    OUTPUT_FILE.write_text(
        json.dumps(
            data.model_dump(),
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def main():
    try:
        horoscope = generate()

        save(horoscope)

        print(
            f"✅ Generated {horoscope.date} horoscope"
        )

    except Exception as error:
        print(
            f"❌ Generation failed: {error}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()