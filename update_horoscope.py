import requests
from bs4 import BeautifulSoup
from googletrans import Translator
import json

def get_daily_horoscope(sign):
    base_url = "https://www.astrology.com/horoscope/daily/"
    url = f"{base_url}{sign}.html"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return f"Error: Unable to fetch data for {sign}"
    
    soup = BeautifulSoup(response.text, "html.parser")
    horoscope_div = soup.find("div", {"id": "content"})
    
    if horoscope_div and horoscope_div.p:
        return horoscope_div.p.text.strip()
    else:
        return "Horoscope not found."

# List of Zodiac signs
# zodiac_signs = [
#     "aries", "taurus", "gemini", "cancer", "leo", "virgo", 
#     "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
# ]
zodiac_signs = [
    "aries", "leo", "taurus", "gemini"
]

translator = Translator()

# Scrape horoscopes for all signs
daily_horoscopes = {}
daily_horoscopes_kh = {}

horoscope_data = []

def translate_text(text, target_language="km"):
    translator = Translator()
    return translator.translate(text, dest=target_language).text

for sign in zodiac_signs:
    english_horoscope = get_daily_horoscope(sign)
    if english_horoscope:
        khmer_horoscope = translate_text(english_horoscope, "km")
        daily_horoscopes[sign] = english_horoscope
        daily_horoscopes_kh[sign] = khmer_horoscope
        horoscope_data.append({
            "sign": sign.capitalize(),
            "en": {"today": english_horoscope},
            "kh": {"today": khmer_horoscope}
        })

# Print the results
for sign, horoscope in daily_horoscopes.items():
    print(f"{sign.capitalize()}: {horoscope}\n")

for sign, horoscope in daily_horoscopes_kh.items():
    print(f"{sign.capitalize()}: {horoscope}\n")

    # Save data to JSON file
with open("daily_horoscope.json", "w", encoding="utf-8") as json_file:
    json.dump(horoscope_data, json_file, ensure_ascii=False, indent=4)

print("Horoscope data saved to daily_horoscope.json")
