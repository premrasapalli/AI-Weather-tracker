# 03 — API Gateway & Integration (Intermediate)

> This document explains the REST API: every endpoint, example calls, error
> handling, and how other apps (or scripts) can integrate with this one.

## What is an API?

An **API** (Application Programming Interface) is a set of rules that lets one
program talk to another. This app exposes an **HTTP/REST JSON API**: you visit a
URL, the app answers with data in JSON format (text that computers can read).

The API is a "gateway" — the single door through which machines ask the app for
weather or AI answers. The website's own browser code uses it, and *your* scripts
or other apps can use the same door.

## Base URL

- Local: `http://localhost:8080`
- Deployed: `https://ai-weather-tracker.onrender.com`

All API paths below are appended to the base URL.

## Endpoint reference

### 1. City search / autocomplete

```
GET /api/search?q=<query>
```

Used by the search box to suggest cities as you type (minimum 2 characters,
India-only by default).

Example:

```bash
curl "http://localhost:8080/api/search?q=ban"
```

Sample response:

```json
{
  "success": true,
  "results": [
    {"name": "Bengaluru", "admin1": "Karnataka", "country": "India", ...}
  ]
}
```

### 2. Full weather bundle for a city

```
GET /api/weather/<city>
```

Returns the complete live package the dashboard renders: conditions, AQI,
alerts, briefing, hourly (24h) and daily (7-day) forecast, plus the AI context.

Example:

```bash
curl "http://localhost:8080/api/weather/Delhi"
```

Response structure (highlights):

```json
{
  "success": true,
  "city": "Delhi",
  "state": "Delhi",
  "conditions": {"temp_c": 28.1, "feels_like_c": 34.0, "humidity_pct": 38,
                 "wind_kmh": 12.0, "condition": "Clear sky", "icon": "☀️"},
  "aqi": {"aqi": 160, "level": "Poor", "label": "Poor (AQI 160)",
          "pm25": 62.0, "drivers": ["PM2.5 particles", ...]},
  "alerts": [{"level": "severe", "type": "Heatwave", "message": "..."}],
  "briefing": "In Delhi the sky is clear, temperature around 28°C...",
  "hourly": [{"time": "9 pm", "temp": 26.4, "precip_prob": 10, ...}, ...],
  "daily":  [{"date": "2026-09-19", "condition": "Clear sky", "tmax": 35.0,
              "tmin": 22.0, "precip_prob": 10, "uv": 9, ...}, ...],
  "context": {"city": "Delhi", "temp_c": 28.1, "aqi": 160, ...},
  "source": "Open-Meteo (free) + AI engine",
  "served_at": "2026-09-19T12:00:00Z"
}
```

### 3. Ask the AI assistant

```
GET /api/ask/<city>?q=<question>
```

Q&A about a city. Uses the LLM when configured, otherwise the rule engine.

Example:

```bash
curl "http://localhost:8080/api/ask/Delhi?q=should%20I%20go%20for%20a%20run%20tonight"
```

Response:

```json
{
  "success": true,
  "city": "Delhi",
  "answer": "Air quality is poor (AQI 160)... prefer indoor exercise tonight.",
  "llm_enabled": true
}
```

The `llm_enabled` field tells the caller which brain answered.

### 4. Clear the weather cache

```
POST /api/cache/clear
```

Flushes the 5-minute in-memory cache. Useful after heavy dev testing.

```bash
curl -X POST "http://localhost:8080/api/cache/clear"
```

```json
{"success": true, "message": "cache cleared"}
```

## Error convention

Every API response is wrapped in a predictable shape:

- Success: `{"success": true, ...data}`
- Failure: `{"success": false, "error": "message"}` with an HTTP status code
  (400 bad request, 404 city not found, 502 upstream failure).

Example failure:

```bash
curl "http://localhost:8080/api/weather/Atlantis"
```

```json
{"error": "City 'Atlantis' not found", "success": false}
```

## How the website uses the API (itself)

The browser code (`static/js/app.js`) is a living example:

1. On load → `GET /api/weather/<city>` → render cards.
2. Typing in search → `GET /api/search?q=` (debounced) → show suggestions.
3. Clicking a suggestion → `GET /api/weather/<selected>` → re-render.
4. Sending a chat message → `GET /api/ask/<city>?q=` → paste answer into a bubble.

No server-side page reload — the API is the engine of the whole UI.

## Integration recipes

### Python script (using `requests` or `httpx`)

```python
import httpx

base = "http://localhost:8080"
r = httpx.get(f"{base}/api/weather/Delhi")
data = r.json()
print(data["city"], data["conditions"]["temp_c"], "°C, AQI", data["aqi"]["aqi"])
```

### Node.js fetch

```javascript
const res = await fetch("https://ai-weather-tracker.onrender.com/api/ask/Delhi?q=" +
  encodeURIComponent("what to wear tomorrow"));
const data = await res.json();
console.log(data.answer);
```

### bash / curl automation

```bash
curl -s https://ai-weather-tracker.onrender.com/api/weather/Mumbai | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['conditions']['temp_c'])"
```

### Google Sheets / Excel

Use the built-in `IMPORTJSON`-style add-on or Power Query pointing at
`/api/weather/<city>` — the JSON keys map directly to columns.

## Rate/caching behavior to know

- Each city's data is cached **5 minutes** (`CACHE_TTL_SECONDS`).
- Repeated API calls for the same city within the TTL are instant and free.
- `POST /api/cache/clear` forces a refresh.
- Upstream (Open-Meteo) failures auto-retry twice before returning 502.

## Versioning & extensibility

The API lives in `weathertracker/web/api.py` as a Flask blueprint with prefix
`/api`. Adding an endpoint = add one route function:

```python
@api_bp.route("/uv/<city>")
def uv(city):
    bundle = get_weather_bundle(city)
    return jsonify({"success": True, "uv_now": bundle["context"].get("uv_now")})
```

## Security notes for API users

- The API is **read-only** and keyless by design. Anyone can query weather — no
  harm, by design (free public data).
- Don't put this behind a paid data wall without noting the free source.
- If you deploy publicly, keep `DEBUG=false` so stack traces never leak.

Next: putting this whole thing online — **04 Deployment & Prerequisites**.