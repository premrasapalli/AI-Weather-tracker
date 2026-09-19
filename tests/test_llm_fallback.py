import pytest
from weathertracker.services.llm import LLMClient, answer_question
from weathertracker.utils.cache import TTLCache
from weathertracker.utils.http_client import get_json


@pytest.fixture()
def ctx():
    return {
        "city": "Delhi",
        "temp_c": 28.0,
        "feels_like_c": 32.0,
        "condition": "Clear sky",
        "humidity_pct": 40,
        "wind_kmh": 12,
        "cloud_pct": 10,
        "aqi": 160,
        "today_min": 22,
        "today_max": 35,
        "forecast": {
            "today_rain": 0,
            "days": [
                {
                    "date": "2026-09-19",
                    "tmax": 35,
                    "tmin": 22,
                    "condition": "Clear sky",
                    "precip_prob": 0,
                    "weather_code": 0,
                    "precip_sum": 0.0,
                    "precipitation_probability_max": 0,
                    "uv_index_max": 8,
                    "sunrise": "06:05",
                    "sunset": "18:25",
                },
                {
                    "date": "2026-09-20",
                    "tmax": 37,
                    "tmin": 24,
                    "condition": "Rain",
                    "precip_prob": 80,
                    "weather_code": 61,
                    "precip_sum": 12.0,
                    "precipitation_probability_max": 80,
                    "uv_index_max": 5,
                    "sunrise": "06:05",
                    "sunset": "18:24",
                },
            ],
        },
    }


def _disabled_llm():
    return LLMClient(
        base_url="https://example.com/v1", api_key="", model="x", timeout=15
    )


def test_answer_week(ctx):
    out = answer_question(_disabled_llm(), "what about the week ahead?", ctx)
    assert "week" in out.lower() or "peaks" in out or "₹" in out


def test_answer_tomorrow_rain(ctx):
    out = answer_question(_disabled_llm(), "will it rain tomorrow?", ctx)
    assert "tomorrow" in out.lower()
    assert "80%" in out or "rain" in out.lower()


def test_answer_today_no_rain(ctx):
    out = answer_question(_disabled_llm(), "is there rain today?", ctx)
    assert "no significant rain" in out.lower()


def test_answer_wear_hot(ctx):
    out = answer_question(_disabled_llm(), "what should I wear?", ctx)
    assert "clothing" in out.lower() or "cotton" in out.lower() or "hat" in out.lower()


def test_answer_wear_umbrella():
    llm = _disabled_llm()
    rainy = {
        "city": "Kozhikode",
        "temp_c": 29,
        "feels_like_c": 31,
        "humidity_pct": 85,
        "wind_kmh": 6,
        "cloud_pct": 90,
        "aqi": 30,
        "today_min": 25,
        "today_max": 31,
        "forecast": {"today_rain": 75, "days": []},
    }
    out = answer_question(llm, "dress for today please", rainy)
    assert "umbrella" in out.lower()


def test_answer_wear_cold():
    llm = _disabled_llm()
    cold = {
        "city": "Shimla",
        "temp_c": 12,
        "feels_like_c": 10,
        "humidity_pct": 60,
        "wind_kmh": 5,
        "cloud_pct": 20,
        "aqi": 40,
        "today_min": 8,
        "today_max": 15,
        "forecast": {"today_rain": 0, "days": []},
    }
    out = answer_question(llm, "clothing?", cold)
    assert "jacket" in out.lower() or "sweater" in out.lower()


def test_answer_health_bad_aqi(ctx):
    out = answer_question(_disabled_llm(), "is it safe to run?", ctx)
    assert "indoor" in out.lower() or "air quality" in out.lower()


def test_answer_air(ctx):
    out = answer_question(_disabled_llm(), "what is the air quality?", ctx)
    assert "AQI" in out


def test_answer_temperature(ctx):
    out = answer_question(_disabled_llm(), "is it hot right now?", ctx)
    assert "28.0" in out or "28" in out


def test_answer_temperature_fallback():
    llm = _disabled_llm()
    partial = {
        "city": "Mumbai",
        "temp_c": 30,
        "feels_like_c": 34,
        "humidity_pct": 70,
        "wind_kmh": 8,
        "cloud_pct": 40,
        "aqi": 80,
        "today_min": 27,
        "today_max": 33,
        "forecast": {"today_rain": 0, "days": []},
    }
    out = answer_question(llm, "humidity please", partial)
    assert "70%" in out


def test_answer_wind(ctx):
    out = answer_question(_disabled_llm(), "how windy is it?", ctx)
    assert "12" in out


def test_answer_cloud(ctx):
    out = answer_question(_disabled_llm(), "cloudy now?", ctx)
    assert "Clear sky" in out


def test_answer_generic_catch_all(ctx):
    out = answer_question(_disabled_llm(), "hello there!", ctx)
    assert "Ask me about" in out


def test_week_no_days():
    llm = _disabled_llm()
    ctx2 = {"city": "X", "forecast": {"days": [], "today_rain": 0}}
    out = answer_question(llm, "next week forecast?", ctx2)
    assert "not available" in out.lower()


def test_tomorrow_missing():
    llm = _disabled_llm()
    ctx2 = {"city": "X", "forecast": {"days": [ctx_dummy()], "today_rain": 0}}
    out = answer_question(llm, "tomorrow?", ctx2)
    assert "tomorrow" in out.lower()


def ctx_dummy():
    return {
        "tmax": 30,
        "tmin": 20,
        "precip_prob": 0,
        "date": "2026-09-19",
        "condition": "Clear",
    }


def test_llm_client_respects_timeout(monkeypatch):
    import httpx

    def raiser(*args, **kwargs):
        raise httpx.ConnectError("boom", request=None)

    monkeypatch.setattr(httpx.Client, "post", raiser)
    llm = LLMClient(base_url="https://example.com", api_key="k", model="m", timeout=1)
    with pytest.raises(httpx.ConnectError):
        llm.chat([{"role": "user", "content": "hi"}])


def test_cache_get_expired():
    cache = TTLCache(ttl_seconds=0)
    cache.set("k", "v", ttl_seconds=0)
    import time

    time.sleep(0.01)
    assert cache.get("k") is None


def test_cache_eviction_lru():
    cache = TTLCache(ttl_seconds=300, maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_cache_clear():
    cache = TTLCache()
    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None


def test_get_json_retries_then_raises(monkeypatch):
    import httpx

    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def get(self, url, params=None):
            calls["n"] += 1
            resp = httpx.Response(500, request=httpx.Request("GET", url))
            resp.raise_for_status()

        def close(self):
            pass

    monkeypatch.setattr(
        "weathertracker.utils.http_client._client", lambda: FakeClient()
    )
    with pytest.raises(RuntimeError):
        get_json("http://x.in", retries=2)
    assert calls["n"] == 3
