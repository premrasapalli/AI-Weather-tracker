# AI Weather Tracker

Enterprise-level AI weather tracker for India with a responsive dark UI, live
weather + air quality from Open-Meteo (100% free, no API key required), and an
optional LLM-powered AI assistant for natural-language questions.

## Features

- **Live weather & 7-day forecast** for Indian cities — current conditions, hourly
  breakdown, daily highs/lows, UV, sunrise/sunset.
- **Live air quality (AQI)** with pollutant breakdown (PM2.5, PM10, ozone, NO₂,
  SO₂, CO) and US-AQI health guidance.
- **AI insights engine** — deterministic, offline-safe briefing + health/dressing
  tips (works with zero API keys).
- **Optional LLM assistant** — ask anything ("should I run tonight?", "what to
  wear tomorrow?"). Works with any OpenAI-compatible endpoint (Groq, OpenAI,
  Ollama, vLLM...).
- **REST API** — `/api/weather/<city>`, `/api/ask/<city>?q=...`, `/api/search?q=...`.
- **India-first** — geo-search restricted to India by default, 19 featured cities.
- **Resilient** — in-memory caching (TTL 5 min), retries with backoff on upstream
  failures, graceful fallback to the rule engine when the LLM is unavailable.
- **Deploy-ready** — Dockerfile, docker-compose, gunicorn, healthcheck included;
  deployed on Render.

## Tech stack

| Layer    | Tech                                             |
|----------|--------------------------------------------------|
| Web      | Flask 3 (blueprints, error handlers, context processors) |
| HTTP     | httpx (retries + timeout)                        |
| Data     | Open-Meteo (geocoding, forecast, air quality)    |
| AI       | Built-in heuristic engine + optional OpenAI-compatible LLM |
| Tests    | pytest (38 tests, 87% coverage gate)              |
| Infra    | Docker, docker-compose, gunicorn                 |

## Quickstart (local)

```bash
git clone https://github.com/premrasapalli/AI-Weather-tracker.git
cd AI-Weather-tracker

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env   # optional; app runs with defaults

python app.py          # -> http://localhost:8080
```

No API keys are required — the app is fully functional out of the box using
Open-Meteo and the built-in AI engine.

## Optional LLM setup (Groq, OpenAI, ...)

To enable the generative AI assistant:

1. Create a key (e.g. at https://console.groq.com/keys).
2. Edit `.env`:

```env
LLM_ENABLED=true
LLM_API_KEY=your-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
LLM_TIMEOUT=15
```

> The default Groq model above (`openai/gpt-oss-120b`) is current as of 2026.
> Groq periodically retires models — if you see `404 model_decommissioned`
> (or a 404 on `/chat/completions`), check the live list:
> `GET https://api.groq.com/openai/v1/models` and update `LLM_MODEL`.

The app works with any OpenAI-compatible endpoint: change `LLM_BASE_URL` +
`LLM_MODEL` to point at OpenAI, Ollama (`http://localhost:11434/v1`), vLLM, etc.
When the LLM call fails or no key is set, the app silently falls back to the
built-in rule engine.

## Docker

```bash
# build & run with compose
docker compose up --build

# or raw docker
docker build -t ai-weather-tracker .
docker run -p 8080:8080 -e LLM_API_KEY=... -e LLM_MODEL=openai/gpt-oss-120b ai-weather-tracker
```

Health check hits `/city/Delhi` every 60s.

## Configuration

All env vars are optional. Copy `.env.example` → `.env` for the full list.

| Variable            | Default                          | Purpose                          |
|---------------------|----------------------------------|----------------------------------|
| `SECRET_KEY`        | `ai-weather-tracker-secret`      | Flask secret                     |
| `DEBUG`             | `false`                          | Flask debug mode                 |
| `PORT`              | `8080`                           | App port                         |
| `INDIA_ONLY`        | `true`                           | Restrict geo-search to India     |
| `DEFAULT_CITY`      | `Delhi`                          | Initial city on `/`              |
| `FEATURED_CITIES`   | 19 Indian cities                 | Search chips on the dashboard    |
| `HTTP_TIMEOUT`      | `10`                             | Upstream request timeout (s)     |
| `HTTP_RETRIES`      | `2`                              | Retries on upstream failure      |
| `CACHE_TTL_SECONDS` | `300`                            | In-memory cache TTL (s)          |
| `LLM_ENABLED`       | `false`                          | Enable LLM assistant             |
| `LLM_API_KEY`       | *(empty)*                        | LLM provider key                 |
| `LLM_BASE_URL`      | `https://api.openai.com/v1`      | OpenAI-compatible base URL       |
| `LLM_MODEL`         | `gpt-4o-mini`                    | Model id                         |

## REST API

### GET `/api/weather/<city>`

Live bundle: conditions, AQI, alerts, briefing, hourly + daily forecast,
LLM context, source, `served_at`.

```bash
curl http://localhost:8080/api/weather/Delhi
```

### GET `/api/ask/<city>?q=<question>`

Natural-language Q&A about that city (LLM if enabled, else rule engine).

```bash
curl "http://localhost:8080/api/ask/Delhi?q=should%20I%20go%20for%20a%20run%20tonight"
```

Returns `{"success": true, "city": "Delhi", "answer": "...", "llm_enabled": true}`.

### GET `/api/search?q=<query>`

City autocomplete (min 2 chars, India-only).

### POST `/api/cache/clear`

Flush the in-memory weather cache.

## Pages

- `/` — dashboard (default city + featured-city chips)
- `/city/<city>` — dashboard pre-loaded for a specific city

## Tests

```bash
.venv/bin/python -m pytest -q
```

38 tests covering the API, insight engine, LLM fallback, and weather services
(mocked upstreams — no network needed).

## Deploy on Render

1. Push to GitHub (Render auto-deploys on push).
2. Create a **Web Service** from the repo, runtime **Docker** (uses `Dockerfile`).
3. Add env vars in **Environment** tab (see `LLM_*` above; keep `LLM_MODEL`
   current for Groq).
4. Render exposes port `8080` automatically.

Live demo: <https://ai-weather-tracker.onrender.com>

## Project layout

```
app.py                                    # WSGI entry (gunicorn app:app)
weathertracker/
  __init__.py                             # create_app factory, error handlers
  config.py                               # env-driven Config
  services/
    geocoding.py                          # city search/lookup via Open-Meteo
    weather.py                            # forecast + air quality fetchers (cached)
    insights.py                           # deterministic AI engine (briefing/tips)
    llm.py                                # OpenAI-compatible chat client + fallback
    assistant.py                          # orchestrates bundle + Q&A
  web/
    pages.py                              # dashboard routes
    api.py                                # REST endpoints
  utils/
    cache.py                              # LRU TTL cache
    http_client.py                        # retry/backoff httpx wrapper
    logging_config.py                     # structured logging setup
templates/                                # Jinja views (index, error)
static/                                   # CSS/JS (dark orange theme)
tests/                                    # 38 pytest tests
Dockerfile, docker-compose.yml            # container deploys
```

## License / data sources

Weather & air-quality data © [Open-Meteo](https://open-meteo.com/) (free under
CC-BY 4.0). AI answers are generated locally (rule engine) or by the configured
LLM provider; verify critical weather decisions with official sources.