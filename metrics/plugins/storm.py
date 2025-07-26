# Copyright (c) 2025 iiPython

import json
from urllib.request import urlopen

WATCHING_CODES = [
    "200",  # Thundery outbreaks in nearby
    "230",  # Blizzard
    "299",  # Moderate rain at times
    "302",  # Moderate rain
    "305",  # Heavy rain at times
    "308",  # Heavy rain
    "314",  # Moderate or Heavy freezing rain
    "329",  # Patchy moderate snow
    "332",  # Moderate snow
    "335",  # Patchy heavy snow
    "338",  # Heavy snow
    "356",  # Moderate or heavy rain shower
    "359",  # Torrential rain shower
    "371",  # Moderate or heavy snow showers
    "386",  # Patchy light rain in area with thunder
    "389",  # Moderate or heavy rain in area with thunder
    "395",  # Moderate or heavy snow in area with thunder	
]

class StormPlugin:
    def __init__(self) -> None:
        pass

    def calculate_notice(self) -> tuple[str, str] | None:
        data = json.loads(urlopen("https://wttr.in/?format=j1").read().decode())

        # Check current conditions
        if data["current_condition"][0]["weatherCode"] in WATCHING_CODES:
            return ("red", "Active storm occuring, service response times may fluctuate.")

        # Process the current days weather
        for hour in data["weather"][0]["hourly"]:
            if hour["weatherCode"] in WATCHING_CODES:
                return ("yellow", "A potential storm is expected in the following hours.")

        return None
