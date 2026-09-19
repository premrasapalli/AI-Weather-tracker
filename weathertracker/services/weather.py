from weathertracker.utils.http_client import get_json
from weathertracker.utils.cache import TTLCache

_cache = TTLCache(ttl_seconds=300)
_current_fields = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,"
    "weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m"
)
_hourly_fields = "temperature_2m,precipitation_probability,weather_code,is_day,relative_humidity_2m"
_daily_fields = (
    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,sunrise,sunset,uv_index_max"
)


def fetch_forecast(lat, lon, timezone="auto", forecast_days=7, use_cache=True):
    key = (lat, lon, timezone, forecast_days)
    if use_cache:
        cached = _cache.get(key)
        if cached:
            return cached
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": _current_fields,
        "hourly": _hourly_fields,
        "daily": _daily_fields,
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    data = get_json("https://api.open-meteo.com/v1/forecast", params=params)
    if use_cache:
        _cache.set(key, data)
    return data


def fetch_air_quality(lat, lon, timezone="auto", use_cache=True):
    key = ("aq", lat, lon, timezone)
    if use_cache:
        cached = _cache.get(key)
        if cached:
            return cached
    fields = "us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": fields,
        "timezone": timezone,
    }
    data = get_json("https://air-quality-api.open-meteo.com/v1/air-quality", params=params)
    if use_cache:
        _cache.set(key, data)
    return data


def clear_cache():
    _cache.clear()