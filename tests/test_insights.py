import pytest

from app.services.insights import InsightGenerator, describe_wmo


@pytest.fixture()
def engine():
    return InsightGenerator(seed=42)


def test_describe_wmo_known_code():
    desc, icon = describe_wmo(95)
    assert "thunder" in desc.lower()
    assert icon


def test_describe_wmo_unknown_code():
    desc, icon = describe_wmo(9999)
    assert desc == "Unknown"


def test_current_conditions_normalization(engine):
    current = {
        "temperature_2m": 34.2,
        "relative_humidity_2m": 55,
        "apparent_temperature": 36.0,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 2,
        "cloud_cover": 40,
        "pressure_msl": 1008.4,
        "wind_speed_10m": 12.5,
        "wind_direction_10m": 120,
    }
    c = engine.current_conditions(current)
    assert c["temp_c"] == 34.2
    assert c["humidity_pct"] == 55
    assert c["wind_kmh"] == 12.5
    assert c["is_day"] is True
    assert c["icon"] == "⛅"


def test_aqi_category_good():
    g = InsightGenerator(seed=1)
    cat = g.aqi_category(45, {"pm2_5": 10})
    assert cat["level"] == "Good"


def test_aqi_category_severe():
    g = InsightGenerator(seed=1)
    cat = g.aqi_category(410, {"pm2_5": 250})
    assert cat["level"] == "Severe"


def test_heat_alert():
    g = InsightGenerator(seed=1)
    cond = {
        "temp_c": 46.5,
        "feels_like_c": 47.0,
        "humidity_pct": 30,
        "wind_kmh": 5,
        "condition": "Clear sky",
    }
    daily = [{"tmax": 46, "tmin": 28, "precipitation_probability_max": 0, "precipitation_sum": 0, "weather_code": 0, "uv_index_max": 9}]
    alerts = g.promote_alerts(cond, daily, 60)
    assert alerts[0]["type"] == "Extreme heat"


def test_rain_alert():
    g = InsightGenerator(seed=1)
    cond = {"temp_c": 28, "feels_like_c": 28, "humidity_pct": 85, "wind_kmh": 10, "condition": "Overcast"}
    daily = [{"tmax": 30, "tmin": 24, "precipitation_probability_max": 90, "precipitation_sum": 40, "weather_code": 61, "uv_index_max": 3}]
    alerts = g.promote_alerts(cond, daily, 80)
    types = [a["type"] for a in alerts]
    assert "Heavy rain" in types