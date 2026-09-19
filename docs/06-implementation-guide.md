# 06 — Implementation Guide (Advanced)

> A file-by-file walkthrough of the codebase, written for developers who want to
> modify or extend the project. Read docs 00–05 first for context.

## Map of the repository

```
AI-Weather-tracker/
├── app.py                        # entrypoint — gunicorn targets `app:app`
├── requirements.txt              # runtime deps (pinned)
├── requirements-dev.txt          # test deps (pytest)
├── Dockerfile                    # container build
├── docker-compose.yml            # local one-command run
├── .env.example                  # committed template of all settings
├── .env                          # gitignored — YOUR secrets
├── .gitignore                    # keeps .env, caches, *.swp out of git
├── README.md                     # project homepage in the repo
├── docs/                         # this documentation series
├── tests/                        # 38 pytest tests
│   ├── test_api.py
│   ├── test_insights.py
│   └── test_weather.py
├── templates/                    # Jinja2 HTML
│   ├── index.html
│   └── error.html
├── static/
│   ├── css/style.css             # dark + orange theme
│   └── js/app.js                 # front-end logic
└── weathertracker/               # the application package
    ├── __init__.py               # create_app() factory + error handlers
    ├── config.py                 # env-driven Config class
    ├── services/
    │   ├── geocoding.py          # city name → coordinates
    │   ├── weather.py            # forecast + air quality fetchers (cached)
    │   ├── insights.py           # rule engine: WMO codes, AQI, alerts
    │   ├── llm.py                # OpenAI-compatible LLM client + fallback
    │   └── assistant.py          # orchestrates the weather bundle + Q&A
    ├── web/
    │   ├── __init__.py           # exposes page_bp and api_bp
    │   ├── pages.py              # HTML routes (/, /city/<city>)
    │   └── api.py                # REST JSON routes (/api/*)
    └── utils/
        ├── __init__.py
        ├── cache.py              # thread-safe LRU TTL cache
        ├── http_client.py        # cached httpx client + retries
        └── logging_config.py     # logging setup
```

## 1. Entry point — `app.py`

```python
from weathertracker import create_app
app = create_app()
if __name__ == "__main__":
    port = int(app.config.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
```

- Creates the Flask app once (module-level `app`).
- Gunicorn uses `app:app` — the `app` object inside the `app` module.
- When run directly, serves on `0.0.0.0:8080`.

## 2. The factory — `weathertracker/__init__.py`

`create_app()` is the composition root:

```python
def create_app(config=None):
    setup_logging(...)
    app = Flask(__name__, template_folder=..., static_folder=...)
    app.config.from_object(config or Config())

    llm = LLMClient(...)           # build the LLM client from config
    app.extensions["llm"] = llm    # expose it app-wide

    app.register_blueprint(page_bp)
    app.register_blueprint(api_bp)
    register_error_handlers(app)
    register_template_helpers(app)
    return app
```

Key ideas:

- Everything is built in one place → easy to test (inject config) and easy to
  reason about.
- The LLM client is stored in `app.extensions["llm"]` so any route can reach it
  via `current_app.extensions["llm"]`.

Error handlers are smart about format: if the request path starts with `/api/`
they return JSON, otherwise an HTML error page.

```python
@app.errorhandler(CityServiceError)
def handle_city_error(exc):
    if request.path.startswith("/api/"):
        return jsonify({"error": str(exc), "success": False}), exc.status_code
    return render_template("error.html", ...), exc.status_code
```

## 3. Configuration — `weathertracker/config.py`

A single `Config` class, driven entirely by environment variables:

```python
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "ai-weather-tracker-secret")
    DEBUG = _env_bool("DEBUG", False)
    ...
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    PORT = int(os.getenv("PORT", "8080"))
```

Notes:

- `load_dotenv()` runs at import time — `.env` (if present) is read automatically.
- `_env_bool()` treats `1/true/yes/on` as true — forgiving.

## 4. Services — the kitchen

### `geocoding.py`
Wraps Open-Meteo geocoding. `lookup_city()` returns a small location object
(name, admin1, country_code, timezone, lat, lon); `search_cities()` returns a
list for autocomplete. `india_only` filtering keeps the product India-focused.

### `weather.py`
Two cached fetchers:

```python
fetch_forecast(lat, lon, tz)      # current + hourly + daily from /forecast
fetch_air_quality(lat, lon, tz)   # pollutants + us_aqi from /air-quality
```

Both use the shared cached HTTP client so repeated calls hit the in-memory TTL
cache instead of the network.

### `insights.py` — the deterministic AI engine
- `WMO_CODES` maps Open-Meteo weather codes (0–99) to human text + emoji.
- `InsightGenerator` turns raw numbers into structured insight:
  - `current_conditions()` → temp/feels/humidity/wind/condition/icon.
  - `aqi_category()` → Good/Satisfactory/.../Severe with color + pollutant drivers.
  - `promote_alerts()` → ranked severe > high > advisory alerts (heat, wind, UV,
    rain, fog, thunder, air).

The `seed=hash(city)` keeps per-city behavior stable (used briefly in dev).

### `llm.py` — the optional generative layer
Already covered deeply in docs 02. Highlights:

- `LLMClient.enabled` ⇔ `bool(api_key)`.
- `chat()` → `POST {base}/chat/completions`, returns first choice text.
- `enrich_briefing()` → polish the briefing (falls back gracefully).
- `answer_question()` → full LLM call, or `_fallback_answer(question, context)`.
- `_fallback_answer()` → the rule-based Brain 1: matches keywords (week,
  tomorrow, rain, wear, health, air, temp, wind, humidity, cloud) against the
  same context. Every branch returns a sensible, grounded sentence.

### `assistant.py` — the orchestrator
`get_weather_bundle(city)` does the full pipeline:

1. geocode the city (404 → `CityServiceError`),
2. fetch forecast + AQI,
3. compute conditions, AQI category, alerts, briefing, hourly (24h), daily (7d),
4. build the compact `context` dict,
5. return one bundle JSON.

Helpers:
- `_buckets(hourly)` → first 24 hours formatted ("9 pm", "Tue", temp, precip).
- `_compose_briefing()` → rule-based natural sentence from the numbers.
- `enrich_with_llm(bundle, llm)` → optional LLM polish + flags `llm_enabled`.
- `ask_city(llm, bundle, question)` → the Q&A entry point used by the API.

## 5. Web layer

### `web/__init__.py`
```python
from weathertracker.web.api import api_bp
from weathertracker.web.pages import page_bp
```
Simple re-export so `__init__.py` can `from weathertracker.web import api_bp, page_bp`.

### `web/pages.py`
HTML routes:
- `/` → dashboard with first featured city.
- `/city/<city>` → dashboard pre-loaded for a city.

### `web/api.py`
REST blueprint (prefix `/api`) — full reference in docs 03.

## 6. Utilities

### `utils/cache.py`
```python
class TTLCache:
    def __init__(self, ttl_seconds=300, maxsize=256): ...
    def get(key) -> value | None      # expires expired keys on read, LRU touch
    def set(key, value, ttl=None)     # inserts, evicts oldest when over maxsize
    def clear()                      # purge everything
```
Thread-safe via `threading.RLock`; perf-ordered via `OrderedDict`.

### `utils/http_client.py`
- One shared `httpx.Client` (lru_cache) with a UA header.
- `get_json(url, params, retries=2)` → retries transparently, raises a single
  `RuntimeError` after exhausting attempts.

### `utils/logging_config.py`
Structured, level-driven logging setup so warnings (e.g. LLM fallback) are
visible in logs.

## 7. Front end

### `templates/index.html`
Single-page dashboard: hero, city search, temp card, AQI card, hourly strip,
7-day forecast, alert chips, and the chat panel with `#llm-badge`.

### `static/js/app.js`
- Fetches `/api/weather/<city>` and renders cards.
- Debounced autocomplete via `/api/search?q=`.
- The AI chat: appends a user bubble, shows a thinking bubble, calls
  `/api/ask/<city>?q=`, replaces the bubble with the answer.
- The thinking bubble is tracked by an element reference (not `querySelector`)
  so answers render reliably — a real fix from the bug history.

### `static/css/style.css`
Dark theme with orange accents and a light-green AI reply/LLM badge.

## 8. Tests — patterns worth copying

Mock-based, separate from real network. Example of the API test pattern:

```python
@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()
```

Weather services are unit-tested with injected fake responses (the `responses`
lib left in dev deps for compatibility) so CI needs no internet.

## Where to add features

| Want to add... | Touch these files |
|----------------|--------------------|
| A new city stat (e.g. pollen) | `weather.py` (new fetch), `assistant.py` (context), `web/api.py` (optional route), `app.js` (render) |
| A new AI fallback pattern | `llm.py` `_fallback_answer()` — add keyword branch |
| A new alert type | `insights.py` `promote_alerts()` |
| A new config knob | `config.py` + `.env.example` |
| A new API endpoint | `web/api.py` |
| A new test | `tests/test_*.py` |

Next: fixing common problems — **07 Troubleshooting**.