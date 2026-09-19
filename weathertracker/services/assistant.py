"""City weather assistant: composes geo + forecast + air quality + AI insights."""

from datetime import datetime, timezone

from weathertracker.services.geocoding import lookup_city
from weathertracker.services.insights import InsightGenerator, describe_wmo
from weathertracker.services.llm import LLMClient, enrich_briefing, answer_question
from weathertracker.services.weather import fetch_forecast, fetch_air_quality


class CityServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def _buckets(hourly) -> list[dict]:
    """Split raw hourly forecast into the next-24h with human labels."""
    out = []
    times = hourly.get("time", [])
    for i, t in enumerate(times[:24]):
        try:
            label_h = datetime.fromisoformat(t).strftime("%I %p").lstrip("0").lower()
            day_label = datetime.fromisoformat(t).strftime("%a")
        except ValueError:
            day_label, label_h = "?", "?"
        out.append(
            {
                "time": label_h,
                "day": day_label,
                "temp": round(hourly["temperature_2m"][i], 1),
                "precip_prob": hourly["precipitation_probability"][i],
                "code": hourly["weather_code"][i],
                "humidity": hourly["relative_humidity_2m"][i],
            }
        )
    return out


def get_weather_bundle(city: str, india_only: bool = True) -> dict:
    """Full live weather + air quality + AI insights for a city."""
    loc = lookup_city(city, india_only=india_only)
    if loc is None:
        raise CityServiceError(f"City '{city}' not found", status_code=404)

    data = fetch_forecast(loc.latitude, loc.longitude, loc.timezone)
    aq_raw = fetch_air_quality(loc.latitude, loc.longitude, loc.timezone)

    current_raw = data.get("current", {})
    hourly_raw = data.get("hourly", {})
    daily_raw = data.get("daily", {})

    engine = InsightGenerator(seed=hash((loc.name)))
    conditions = engine.current_conditions(current_raw)

    # Build forecast structure
    daily = []
    for i, d in enumerate(daily_raw.get("time", [])):
        code = daily_raw["weather_code"][i]
        desc, icon = describe_wmo(code)
        daily.append(
            {
                "date": d,
                "code": code,
                "condition": desc,
                "icon": icon,
                "tmax": round(daily_raw["temperature_2m_max"][i], 1),
                "tmin": round(daily_raw["temperature_2m_min"][i], 1),
                "precip_sum": daily_raw["precipitation_sum"][i],
                "precip_prob": daily_raw["precipitation_probability_max"][i],
                "uv": daily_raw["uv_index_max"][i],
                "sunrise": daily_raw["sunrise"][i],
                "sunset": daily_raw["sunset"][i],
            }
        )

    pollutants = {k: v for k, v in current_raw.items() if k in ("pm2_5", "pm10", "ozone", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide")}
    # AQI comes from the air-quality endpoint, not the forecast endpoint
    aq_current = aq_raw.get("current", {}) if aq_raw else {}
    if "us_aqi" in aq_current:
        pollutants = {
            "pm2_5": aq_current.get("pm2_5"),
            "pm10": aq_current.get("pm10"),
            "ozone": aq_current.get("ozone"),
            "nitrogen_dioxide": aq_current.get("nitrogen_dioxide"),
            "sulphur_dioxide": aq_current.get("sulphur_dioxide"),
            "carbon_monoxide": aq_current.get("carbon_monoxide"),
        }
    aqi_val = aq_current.get("us_aqi")
    aqi = engine.aqi_category(aqi_val, pollutants)

    alerts = engine.promote_alerts(conditions, daily, aqi_val)
    today = daily[0] if daily else {}
    briefing = _compose_briefing(loc.name, conditions, today, aqi, daily)
    hourly = _buckets(hourly_raw)

    context = {
        "city": loc.name,
        "state": loc.admin1,
        "temp_c": conditions["temp_c"],
        "feels_like_c": conditions["feels_like_c"],
        "condition": conditions["condition"],
        "humidity_pct": conditions["humidity_pct"],
        "pressure_hpa": conditions["pressure_hpa"],
        "wind_kmh": conditions["wind_kmh"],
        "cloud_pct": conditions["cloud_pct"],
        "aqi": aqi_val,
        "today_max": today.get("tmax"),
        "today_min": today.get("tmin"),
        "sunrise": today.get("sunrise"),
        "sunset": today.get("sunset"),
        "forecast": {"today_rain": today.get("precip_prob"), "days": daily},
        "txn": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "city": loc.name,
        "state": loc.admin1,
        "country_code": loc.country_code,
        "timezone": loc.timezone,
        "conditions": conditions,
        "aqi": aqi,
        "alerts": alerts,
        "briefing": briefing,
        "hourly": hourly,
        "daily": daily,
        "context": context,
        "source": "Open-Meteo (free) + AI engine",
        "served_at": datetime.now(timezone.utc).isoformat(),
    }


def enrich_with_llm(bundle: dict, llm: LLMClient) -> dict:
    """Attach LLM-polished briefing and open the Q&A hook when configured."""
    if llm.enabled:
        bundle["briefing"] = enrich_briefing(llm, bundle["context"], bundle["briefing"])
    bundle["llm_enabled"] = llm.enabled
    return bundle


def ask_city(llm: LLMClient, bundle: dict, question: str) -> str:
    return answer_question(llm, question, bundle["context"])


def _compose_briefing(city, conditions, today, aqi, daily) -> str:
    parts = []
    condition = conditions["condition"]
    if condition.lower().endswith("sky"):
        sky_desc = condition[:-4].strip().lower() or "clear"
    else:
        sky_desc = condition.lower()
    parts.append(f"In {city} the sky is {sky_desc}")
    feels = f"feels like {conditions['feels_like_c']}°C" if conditions["feels_like_c"] != conditions["temp_c"] else f"{conditions['temp_c']}°C"
    parts.append(f"temperature around {feels}")
    parts.append(f"humidity at {conditions['humidity_pct']}%")
    if conditions["wind_kmh"] >= 20:
        parts.append(f"wind {conditions['wind_kmh']} km/h")
    if today:
        parts.append(f"today spanning {today['tmin']}–{today['tmax']}°C")
        rain = today.get("precip_prob") or 0
        if rain >= 60:
            parts.append(f"{rain}% chance of rain")
        elif rain > 0:
            parts.append(f"isolated showers possible ({rain}%)")
    if aqi and aqi["aqi"]:
        parts.append(f"air quality {aqi['level'].lower()} with AQI {aqi['aqi']}")
    sentence = ", and ".join(parts) + "."
    if daily and len(daily) > 1:
        warmest = max(daily, key=lambda d: d["tmax"])
        sentence += f" The warmest day ahead is {warmest['date']} at {warmest['tmax']}°C."
    return sentence


def get_city_list() -> list[str]:
    from weathertracker.config import Config

    return [c for c in Config.FEATURED_CITIES]