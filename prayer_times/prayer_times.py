#!/usr/bin/env python3

import json
import requests
from datetime import datetime, timedelta
import pytz
import os


def load_env_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                if line.startswith("export "):
                    line = line[len("export "):]
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip('"')


def fetch_timings(city, country_code, method_id):
    return requests.get(
        f"https://api.aladhan.com/v1/timingsByAddress?address={city},{country_code}&method={method_id}"
    ).json()


def fetch_calendar(city, country_code, method_id, month, year):
    return requests.get(
        f"https://api.aladhan.com/v1/calendarByAddress/{year}/{month}?address={city},{country_code}&method={method_id}"
    ).json()


def str_to_time(date_str, hour_minute, timezone):
    return timezone.localize(datetime.strptime(f"{date_str} {hour_minute}", "%Y-%m-%d %H:%M"))

def find_next_prayer(filtered_today, timezone):
    now = datetime.now(timezone)
    times = {
        k: str_to_time(now.strftime("%Y-%m-%d"), v, timezone)
        for k, v in filtered_today.items()
    }

    next_prayer, next_time = None, None
    for name, t in times.items():
        if t > now and (next_time is None or t < next_time):
            next_prayer = name
            next_time = t

    if next_prayer is None:
        fajr_time = times.get("Fajr")
        if fajr_time is None:
            return "No data"
        mins = (
            fajr_time.minute
            + fajr_time.hour * 60
            + 24 * 60
            - (now.minute + now.hour * 60)
        )
        return f"Fajr in {round(mins)}m"
    else:
        diff = (next_time - now).total_seconds()
        hours = int(diff // 3600)
        mins = int((diff % 3600) // 60)
        if hours == 0:
            return f"{next_prayer} in {mins}m"
        else:
            return f"{next_prayer} in {hours}h {mins}m"


def format_tooltip(forecast, method_display_name, city, country_code, next_text):
    emoji_names = {
        "Fajr": "🌄",
        "Sunrise": "🌅",
        "Dhuhr": "🌞",
        "Asr": "🌤️",
        "Maghrib": "🌇",
        "Isha": "🌌",
    }

    lines = [
        f"🧮 Method: {method_display_name}",
        f"📍 Location: {city}, {country_code}",
        f"⏳ Next: {next_text}",
        ""
    ]

    for i, (date_str, timings) in enumerate(forecast):
        if i == 0:
            day_label = f"Today, {date_str}"
        elif i == 1:
            day_label = f"Tomorrow, {date_str}"
        else:
            day_label = f"{date_str}"
        lines.append(f"{day_label}")
        for name, time in timings.items():
            emoji = emoji_names.get(name, "")
            lines.append(f"{emoji} {name}: {time}")
        lines.append("")

    return "\n".join(lines).strip()


def main():
    load_env_file(os.path.expanduser("~/.local/state/.staterc"))
    load_env_file(os.path.expanduser("~/.local/state/hyde/staterc"))
    load_env_file(os.path.expanduser("~/.local/state/hyde/config"))

    city = os.getenv("CITY", "Istanbul")
    country_code = os.getenv("COUNTRY_CODE", "TR")
    method_name = os.getenv("PRAYER_CALC_METHOD", "Diyanet_Isleri_Baskanligi")
    days = int(os.getenv("PRAYER_FORECAST_DAYS", "3"))

    methods = {
        "Muslim_World_League": 3,
        "Islamic_Society_of_North_America": 2,
        "Egyptian_General_Authority_of_Survey": 5,
        "Umm_Al-Qura": 4,
        "University_of_Islamic_Sciences": 1,
        "Tehran": 7,
        "Shia_Ithna-Ashari": 0,
        "Gulf_Region": 8,
        "Kuwait": 9,
        "Qatar": 10,
        "Majlis_Ugama_Islam_Singapura": 11,
        "Union_Organization_Islamic_de_France": 12,
        "Diyanet_Isleri_Baskanligi": 13,
        "Spiritual_Administration_of_Muslims_of_Russia": 14,
        "Moonsighting_Committee_Worldwide": 15,
        "Dubai": 16,
        "Jabatan_Kemajuan_Islam_Malaysia": 17,
        "Tunisia": 18,
        "Algeria": 19,
        "Kementerian_Agama_Republik_Indonesia": 20,
        "Morocco": 21,
        "Comunidade_Islamica_de_Lisboa": 22,
        "Ministry_of_Awqaf": 23,
    }

    method_id = methods.get(method_name, 0)
    method_display_name = method_name.replace("_", " ")

    whitelist = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]

    response = fetch_timings(city, country_code, method_id)
    timezone = pytz.timezone(response["data"]["meta"]["timezone"])
    today_filtered = {
        k: v for k, v in response["data"]["timings"].items() if k in whitelist
    }

    next_text = find_next_prayer(today_filtered, timezone)
    forecast = []

    if days > 0:
        now = datetime.now(timezone)
        cal = fetch_calendar(city, country_code, method_id, now.month, now.year)
        for i in range(days):
            day = now + timedelta(days=i)
            idx = day.day - 1
            raw = cal["data"][idx]["timings"]
            filtered = {k: v for k, v in raw.items() if k in whitelist}
            date_str = day.strftime("%Y-%m-%d")
            forecast.append((date_str, filtered))

        tooltip = format_tooltip(forecast, method_display_name, city, country_code, next_text)
    else:
        tooltip = ""

    print(json.dumps({"text": f"🕌 {next_text}", "tooltip": tooltip}), flush=True)


if __name__ == "__main__":
    main()
