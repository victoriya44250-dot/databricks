import os
import json
import time
import requests
from azure.eventhub import EventHubProducerClient, EventData

from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

connection_string = os.getenv("EVENT_HUB_CONNECTION_STRING")

if not connection_string:
    raise ValueError("EVENT_HUB_CONNECTION_STRING is not configured")


locations = [
    {"country": "Albania", "city": "Tirana", "lat": 41.3275, "lon": 19.8187},
    {"country": "Austria", "city": "Vienna", "lat": 48.2082, "lon": 16.3738},
    {"country": "Belarus", "city": "Minsk", "lat": 53.9006, "lon": 27.5590},
    {"country": "Belgium", "city": "Brussels", "lat": 50.8503, "lon": 4.3517},
    {"country": "Bosnia and Herzegovina", "city": "Sarajevo", "lat": 43.8563, "lon": 18.4131},
    {"country": "Bulgaria", "city": "Sofia", "lat": 42.6977, "lon": 23.3219},
    {"country": "Croatia", "city": "Zagreb", "lat": 45.8150, "lon": 15.9819},
    {"country": "Czechia", "city": "Prague", "lat": 50.0755, "lon": 14.4378},
    {"country": "Denmark", "city": "Copenhagen", "lat": 55.6761, "lon": 12.5683},
    {"country": "Estonia", "city": "Tallinn", "lat": 59.4370, "lon": 24.7536},
    {"country": "Finland", "city": "Helsinki", "lat": 60.1699, "lon": 24.9384},
    {"country": "France", "city": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"country": "Germany", "city": "Berlin", "lat": 52.5200, "lon": 13.4050},
    {"country": "Greece", "city": "Athens", "lat": 37.9838, "lon": 23.7275},
    {"country": "Hungary", "city": "Budapest", "lat": 47.4979, "lon": 19.0402},
    {"country": "Iceland", "city": "Reykjavik", "lat": 64.1466, "lon": -21.9426},
    {"country": "Ireland", "city": "Dublin", "lat": 53.3498, "lon": -6.2603},
    {"country": "Italy", "city": "Rome", "lat": 41.9028, "lon": 12.4964},
    {"country": "Latvia", "city": "Riga", "lat": 56.9496, "lon": 24.1052},
    {"country": "Lithuania", "city": "Vilnius", "lat": 54.6872, "lon": 25.2797},
    {"country": "Luxembourg", "city": "Luxembourg", "lat": 49.6116, "lon": 6.1319},
    {"country": "Malta", "city": "Valletta", "lat": 35.8989, "lon": 14.5146},
    {"country": "Moldova", "city": "Chisinau", "lat": 47.0105, "lon": 28.8638},
    {"country": "Montenegro", "city": "Podgorica", "lat": 42.4304, "lon": 19.2594},
    {"country": "Netherlands", "city": "Amsterdam", "lat": 52.3676, "lon": 4.9041},
    {"country": "North Macedonia", "city": "Skopje", "lat": 41.9973, "lon": 21.4280},
    {"country": "Norway", "city": "Oslo", "lat": 59.9139, "lon": 10.7522},
    {"country": "Poland", "city": "Warsaw", "lat": 52.2297, "lon": 21.0122},
    {"country": "Portugal", "city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
    {"country": "Romania", "city": "Bucharest", "lat": 44.4268, "lon": 26.1025},
    {"country": "Serbia", "city": "Belgrade", "lat": 44.7866, "lon": 20.4489},
    {"country": "Slovak Republic", "city": "Bratislava", "lat": 48.1486, "lon": 17.1077},
    {"country": "Slovenia", "city": "Ljubljana", "lat": 46.0569, "lon": 14.5058},
    {"country": "Spain", "city": "Madrid", "lat": 40.4168, "lon": -3.7038},
    {"country": "Sweden", "city": "Stockholm", "lat": 59.3293, "lon": 18.0686},
    {"country": "Switzerland", "city": "Bern", "lat": 46.9480, "lon": 7.4474},
    {"country": "Ukraine", "city": "Kyiv", "lat": 50.4501, "lon": 30.5234},
    {"country": "United Kingdom", "city": "London", "lat": 51.5074, "lon": -0.1278},
]


def get_weather(location):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m"
        ],
        "timezone": "UTC"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    current = response.json()["current"]

    return {
        "event_timestamp": current["time"],
        "country": location["country"],
        "city": location["city"],
        "temperature_2m": current["temperature_2m"],
        "relative_humidity_2m": current["relative_humidity_2m"],
        "precipitation": current["precipitation"],
        "wind_speed_10m": current["wind_speed_10m"]
    }


producer = EventHubProducerClient.from_connection_string(
    conn_str=connection_string
)

try:
    while True:
        event_batch = producer.create_batch()

        for location in locations:
            weather_event = get_weather(location)

            event_batch.add(
                EventData(json.dumps(weather_event))
            )

            print(
                f"{location['country']}: "
                f"{weather_event['temperature_2m']} °C"
            )

        producer.send_batch(event_batch)

        print(f"{len(locations)} weather events sent to Event Hub\n")

        time.sleep(60)

finally:
    producer.close()