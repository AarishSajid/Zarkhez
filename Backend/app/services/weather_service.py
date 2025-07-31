import requests as requests # type: ignore
from app.core.config import settings

def generate_advice(weather_data: dict) -> str:
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    condition = weather_data['weather'][0]['main'].lower()

    advice = []

    if temp > 35:
        advice.append("Very hot day. Irrigate early morning or late evening.")
    elif temp < 15:
        advice.append("Cold weather. Monitor crops for frost damage.")

    if humidity > 70:
        advice.append("High humidity. Increased risk of fungal disease.")
    elif humidity < 30:
        advice.append("Low humidity. Ensure sufficient irrigation.")

    if "rain" in condition:
        advice.append("Rain expected. Delay irrigation and fertilization.")
    elif "clear" in condition:
        advice.append("Clear skies. Normal farming operations are good to go.")

    return " ".join(advice)

def fetch_weather(lat: float = None, lon: float = None, city: str = None) -> dict:
    params = {
        "appid": settings.openweather,
        "units": "metric"
    }

    if city:
        params["q"] = city
    elif lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    else:
        return {"error": "Please provide either city name or lat & lon."}

    response = requests.get(settings.weather_url, params=params)

    if response.status_code != 200:
        return {"error": "Failed to fetch weather data."}

    data = response.json()
    advice = generate_advice(data)

    return {
        "location": data.get("name"),
        "temperature": data["main"]["temp"],
        "condition": data["weather"][0]["description"].capitalize(),
        "humidity": data["main"]["humidity"],
        "advice": advice
    }
