# WMO weather interpretation codes (Open-Meteo) -> human-AI descriptors.

WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫"),
    48: ("Depositing rime fog", "🌫"),
    51: ("Light drizzle", "🌦"),
    53: ("Drizzle", "🌦"),
    55: ("Dense drizzle", "🌧"),
    56: ("Freezing drizzle", "🌧"),
    57: ("Dense freezing drizzle", "🌧"),
    61: ("Slight rain", "🌦"),
    63: ("Rain", "🌧"),
    65: ("Heavy rain", "🌧"),
    66: ("Freezing rain", "🌧"),
    67: ("Heavy freezing rain", "🌧"),
    71: ("Slight snow", "🌨"),
    73: ("Snow", "🌨"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Light rain showers", "🌦"),
    81: ("Rain showers", "🌧"),
    82: ("Violent rain showers", "⛈"),
    85: ("Slight snow showers", "🌨"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈"),
    96: ("Thunderstorm with hail", "⛈"),
    99: ("Severe thunderstorm with hail", "⛈"),
}

import random  # noqa: E402


def describe_wmo(code: int) -> tuple[str, str]:
    if code in WMO_CODES:
        return WMO_CODES[code]
    return "Unknown", "🌡"


class InsightGenerator:
    """Deterministic AI-grade reasoning engine over live weather telemetry.

    Generates a natural-language briefing, ranked alerts and actionable
    advisories for Indian conditions without any paid API."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)  # noqa: S311 - deterministic engine seed, not cryptographic

    def _sun_icon(self, code: int, is_day: bool) -> str:
        if code in (0, 1):
            return "🌙" if not is_day else "☀️"
        return describe_wmo(code)[1]

    def current_conditions(self, current) -> dict:
        code = int(current.get("weather_code", 0))
        desc, _ = describe_wmo(code)
        is_day = bool(current.get("is_day", 1))
        return {
            "temp_c": round(current.get("temperature_2m", 0), 1),
            "feels_like_c": round(current.get("apparent_temperature", 0), 1),
            "humidity_pct": current.get("relative_humidity_2m", 0),
            "pressure_hpa": current.get("pressure_msl"),
            "wind_kmh": round(current.get("wind_speed_10m", 0.0), 1),
            "wind_deg": current.get("wind_direction_10m"),
            "precip_mm": current.get("precipitation", 0.0),
            "cloud_pct": current.get("cloud_cover", 0),
            "condition": desc,
            "icon": self._sun_icon(code, is_day),
            "is_day": is_day,
        }

    def aqi_category(self, aqi, pollutants) -> dict:
        if aqi is None:
            return {"level": "No data", "color": "#9aa7b5", "label": "Unavailable"}
        if aqi <= 50:
            level, color = "Good", "#4ade80"
        elif aqi <= 100:
            level, color = "Satisfactory", "#facc15"
        elif aqi <= 200:
            level, color = "Moderate", "#fb923c"
        elif aqi <= 300:
            level, color = "Poor", "#f87171"
        elif aqi <= 400:
            level, color = "Very Poor", "#c084fc"
        else:
            level, color = "Severe", "#7f1d1d"
        pm25 = pollutants.get("pm2_5")
        return {
            "level": level,
            "color": color,
            "aqi": aqi,
            "label": f"{level} (AQI {aqi})",
            "pm25": pm25,
            "drivers": self._aqi_drivers(pollutants),
        }

    @staticmethod
    def _aqi_drivers(pollutants) -> list[str]:
        drivers = []
        mapping = {
            "pm2_5": "PM2.5 particles",
            "pm10": "PM10 dust",
            "ozone": "ground-level ozone",
            "nitrogen_dioxide": "NO₂",
            "sulphur_dioxide": "SO₂",
            "carbon_monoxide": "CO",
        }
        for key, label in mapping.items():
            val = pollutants.get(key)
            if val is not None and float(val) > 0:
                drivers.append(label)
        return drivers

    def promote_alerts(self, conditions, daily, aqi) -> list[dict]:
        alerts = []
        temp = conditions["temp_c"]
        if temp >= 45.0:
            alerts.append(
                {
                    "level": "severe",
                    "type": "Extreme heat",
                    "message": f"{temp}°C — life-threatening heat. Avoid outdoor work 11am–4pm.",
                }
            )
        elif temp >= 40.0:
            alerts.append(
                {
                    "level": "high",
                    "type": "Heatwave",
                    "message": f"{temp}°C — extreme heat. Stay hydrated and indoors during midday.",
                }
            )
        elif temp >= 36.0:
            alerts.append(
                {
                    "level": "advisory",
                    "type": "Hot day",
                    "message": f"Temperature touching {temp}°C — take heat precautions.",
                }
            )
        if conditions["feels_like_c"] - temp > 3:
            alerts.append(
                {
                    "level": "advisory",
                    "type": "Humid heat",
                    "message": "Feels noticeably hotter than the actual temperature.",
                }
            )
        if conditions["wind_kmh"] >= 60:
            alerts.append(
                {
                    "level": "high",
                    "type": "High wind",
                    "message": f"Winds near {conditions['wind_kmh']} km/h — secure loose objects.",
                }
            )
        max_uv = (
            max((d.get("uv_index_max") or 0 for d in daily), default=0) if daily else 0
        )
        if max_uv >= 11:
            alerts.append(
                {
                    "level": "high",
                    "type": "Extreme UV",
                    "message": "Extreme UV today — use SPF 50+, avoid noon sun.",
                }
            )
        elif max_uv >= 8:
            alerts.append(
                {
                    "level": "advisory",
                    "type": "High UV",
                    "message": "Strong UV today — protect skin and eyes.",
                }
            )
        rain_day = daily[0] if daily else {}
        if (rain_day.get("precipitation_probability_max") or 0) >= 70 and (
            rain_day.get("precipitation_sum") or 0
        ) >= 15:
            alerts.append(
                {
                    "level": "high",
                    "type": "Heavy rain",
                    "message": "Likely heavy rain — carry an umbrella and drive carefully.",
                }
            )
        codes_today = []
        if daily:
            codes_today.append(daily[0].get("weather_code"))
        if any(c in (95, 96, 99) for c in codes_today):
            alerts.append(
                {
                    "level": "severe",
                    "type": "Thunderstorm",
                    "message": "Thunderstorm expected — stay indoors, unplug electronics.",
                }
            )
        if conditions["condition"] in ("Fog", "Depositing rime fog"):
            alerts.append(
                {
                    "level": "advisory",
                    "type": "Fog / low visibility",
                    "message": "Reduced visibility — drive with fog lamps.",
                }
            )
        if aqi and aqi > 300:
            alerts.append(
                {
                    "level": "severe",
                    "type": "Hazardous air",
                    "message": "Air is hazardous — limit outdoor exposure, use N95 masks.",
                }
            )
        elif aqi and aqi > 200:
            alerts.append(
                {
                    "level": "high",
                    "type": "Very poor air",
                    "message": "Poor air quality — reduce strenuous outdoor activity.",
                }
            )
        alerts.sort(
            key=lambda a: {"severe": 0, "high": 1, "advisory": 2}.get(a["level"], 3)
        )
        return alerts
