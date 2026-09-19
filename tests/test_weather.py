import pytest

import weathertracker.services.weather as weather_mod
from weathertracker.services.weather import fetch_forecast, fetch_air_quality


@pytest.fixture(autouse=True)
def _no_cache():
    old = weather_mod._cache
    weather_mod._cache = type(old)(ttl_seconds=300)
    yield
    weather_mod._cache = old


def test_fetch_forecast(monkeypatch):
    def fake_get_json(url, params=None, retries=2):
        assert "api.open-meteo.com" in url
        return {
            "latitude": 28.61,
            "longitude": 77.21,
            "timezone": "Asia/Kolkata",
            "current": {"temperature_2m": 31.2, "weather_code": 2},
            "hourly": {"time": [], "temperature_2m": []},
            "daily": {"time": [], "weather_code": []},
        }

    monkeypatch.setattr(weather_mod, "get_json", fake_get_json)
    data = fetch_forecast(28.61, 77.21, "Asia/Kolkata", use_cache=False)
    assert data["current"]["temperature_2m"] == 31.2


def test_fetch_air_quality(monkeypatch):
    def fake_get_json(url, params=None, retries=2):
        assert "air-quality-api.open-meteo.com" in url
        return {"current": {"us_aqi": 120, "pm2_5": 42}}

    monkeypatch.setattr(weather_mod, "get_json", fake_get_json)
    data = fetch_air_quality(28.61, 77.21, "Asia/Kolkata", use_cache=False)
    assert data["current"]["us_aqi"] == 120


def test_cache_hit(monkeypatch):
    calls = {"n": 0}

    def fake_get_json(url, params=None, retries=2):
        calls["n"] += 1
        return {"current": {"temperature_2m": 25.0}, "hourly": {}, "daily": {}}

    monkeypatch.setattr(weather_mod, "get_json", fake_get_json)
    fetch_forecast(10, 10, "auto", use_cache=True)
    fetch_forecast(10, 10, "auto", use_cache=True)
    assert calls["n"] == 1