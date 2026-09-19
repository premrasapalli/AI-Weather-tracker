import pytest
import weathertracker.services.weather as weather_mod
from weathertracker import create_app

GEO = [
    {
        "name": "Delhi",
        "admin1": "Delhi",
        "country_code": "IN",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timezone": "Asia/Kolkata",
    }
]

FORECAST = {
    "current": {
        "temperature_2m": 30.0,
        "relative_humidity_2m": 60,
        "apparent_temperature": 31.0,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 2,
        "cloud_cover": 30,
        "pressure_msl": 1010.0,
        "wind_speed_10m": 10.0,
        "wind_direction_10m": 90,
    },
    "hourly": {
        "time": [f"2026-09-19T{hour:02d}:00:00" for hour in range(24)],
        "temperature_2m": [29.0] * 24,
        "precipitation_probability": [10] * 24,
        "weather_code": [2] * 24,
        "relative_humidity_2m": [60] * 24,
    },
    "daily": {
        "time": ["2026-09-19"],
        "weather_code": [2],
        "temperature_2m_max": [34.0],
        "temperature_2m_min": [23.0],
        "precipitation_sum": [0.0],
        "precipitation_probability_max": [10],
        "sunrise": ["2026-09-19T06:05:00"],
        "sunset": ["2026-09-19T18:25:00"],
        "uv_index_max": [8.0],
    },
}

AQI = {
    "current": {
        "us_aqi": 95,
        "pm2_5": 38,
        "pm10": 60,
        "ozone": 50,
        "nitrogen_dioxide": 18,
        "sulphur_dioxide": 8,
        "carbon_monoxide": 0.4,
    }
}


@pytest.fixture()
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_upstream(monkeypatch):
    monkeypatch.setattr(weather_mod, "get_json", _route_get_json)


def _route_get_json(url, params=None, retries=2):
    if "geocoding" in url:
        if params.get("name", "").lower() in ("nopeville", "xyz"):
            return {"results": []}
        return {"results": GEO}
    if "air-quality" in url:
        return AQI
    return FORECAST


def test_weather_api_success(client):
    resp = client.get("/api/weather/Delhi")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["city"] == "Delhi"
    assert body["briefing"]
    assert body["aqi"]["aqi"] == 95
    assert body["hourly"] and len(body["hourly"]) == 24
    assert body["daily"]


def test_weather_api_city_not_found(client):
    resp = client.get("/api/weather/NopeVille")
    assert resp.status_code == 404
    assert resp.get_json()["success"] is False


def test_search_requires_long_query(client):
    resp = client.get("/api/search?q=a")
    assert resp.status_code == 400


def test_search_list(client):
    resp = client.get("/api/search?q=del")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] and body["results"][0]["name"] == "Delhi"


def test_ask_api_rule_fallback(client):
    resp = client.get("/api/ask/Delhi?q=is%20it%20hot")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert "°C" in body["answer"] or "hot" in body["answer"].lower()


def test_ask_api_tomorrow(client):
    resp = client.get("/api/ask/Delhi?q=what%20about%20tomorrow")
    assert resp.status_code == 200
    assert resp.get_json()["answer"]


def test_index_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"AI Weather Tracker" in resp.data


def test_city_page_renders(client):
    resp = client.get("/city/Bengaluru")
    assert resp.status_code == 200
    assert b"Bengaluru" in resp.data
