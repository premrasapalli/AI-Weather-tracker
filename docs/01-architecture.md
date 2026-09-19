# 01 — Architecture (Beginner)

> This document explains how the app is organized, using everyday analogies.
> No coding knowledge needed beyond the previous document.

## The big picture

Think of the app as a **restaurant**:

```
                    ┌────────────────────────────────┐
   Guest (browser)  │           The Restaurant       │
   ┌────────────┐   │  ┌──────────┐                  │
   │ You / your │──▶│  │  Waiter  │──┐               │
   │ phone      │   │  │ (Flask)  │  │               │
   └────────────┘   │  └──────────┘  │               │
                    │        ┌───────▼────────┐      │
                    │        │  Kitchen       │      │
                    │        │ (services)     │      │
                    │        └───────┬────────┘      │
                    │          │     │     │         │
                    │          │     │     │         │
                    │   ┌──────▼─┐ ┌──▼────▼──┐      │
                    │   │Weather │ │ Air quality│    │
                    │   │ (Open- │ │ (Open-    │    │
                    │   │ Meteo) │ │ Meteo)    │    │
                    │   └────────┘ └───────────┘    │
                    └────────────────────────────────┘
```

- **The Waiter (Flask web framework)** receives your request ("give me Delhi's
  weather" or "answer my question about Delhi").
- **The Kitchen (services)** does the real work: it fetches weather numbers from
  the free data source, applies the AI brain, and packages the result.
- **The Menu (REST API)** lists the things you can order through a URL.
- **The Data suppliers (Open-Meteo)** are the external free weather services.

## The parts, one by one

### 1. The entry point — `app.py`

A tiny file that makes one thing clear to the world: *"the app object is here."*

- It tells servers (like gunicorn) where the app is.
- When you run `python app.py`, it starts the app on your computer (port 8080).

Think of it as the **front door** of the restaurant. Small, but everything comes
through it.

### 2. The app core — `weathertracker/`

This folder is the real app. It contains:

- `__init__.py` — the **factory**. It assembles the whole app: config, AI
  client, web pages, error handling. One function, `create_app()`, builds
  everything.
- `config.py` — the **settings.** All the knobs (timeouts, cache size, city
  list, AI provider settings) live here, and most can be changed without editing.
- `services/` — the **kitchen.**
- `web/` — the **menu + waiter routes.**
- `utils/` — shared helpers.

### 3. The services (kitchen)

| File | Job (plain English) |
|------|---------------------|
| `geocoding.py` | Turns a city *name* ("Bangalore") into *coordinates* (latitude/longitude) |
| `weather.py` | Fetches current weather + forecast from Open-Meteo (with caching) |
| `insights.py` | Brain 1: the rule engine that writes alerts, briefings, tips |
| `llm.py` | Brain 2: the optional real AI model client + its fallback logic |
| `assistant.py` | The **head chef**: combines everything into one "weather bundle" and answers questions |

### 4. The web layer (waiter + menu)

| File | Job |
|------|-----|
| `web/pages.py` | The screens you see in the browser (/, /city/<city>) |
| `web/api.py` | The machine-friendly URLs (starting with /api/) |

### 5. The utilities

| File | Job |
|------|-----|
| `utils/cache.py` | Remembers answers for 5 minutes so the app doesn't re-fetch every click |
| `utils/http_client.py` | The reliable way the app talks to the internet (retries if a call fails) |
| `utils/logging_config.py` | Writes clean logs so you can see what's happening |

## The request journey (step by step)

Let's follow what happens when someone opens the site and asks a question:

1. **Browser** asks the waiter: `GET /api/ask/Delhi?q=should I go for a run?`
2. **Flask (web/api.py)** receives it and calls the head chef (`assistant.py`).
3. **Head chef** calls the kitchen:
   - `geocoding` → finds Delhi's coordinates;
   - `weather` → fetches current temp, humidity, wind, clouds;
   - `weather` → fetches air quality (AQI);
   - `insights` → computes alerts + a natural-language briefing;
   - `llm` → (if enabled) asks the AI model to answer, else uses rules.
4. **Header chef** packages everything into one JSON "parcel".
5. **Waiter** hands the parcel back to the browser.
6. **Browser (static/js/app.js)** draws it: temperature, AQI card, chat bubble.

Total time: well under a second.

## Important design decisions

### Decision 1 — External data is always behind a "curtain"

The app **never** talks to Open-Meteo directly from the browser. All fetch
requests go through the app's own code. Why?

- We can **cache** (remember) results, so we fetch less and the site feels fast.
- We can **retry** when the internet hiccups.
- We can **add logic** (India-only search, AQI categories) in one place.

### Decision 2 — Two AI brains, one interface

Brain 1 (rules) and Brain 2 (LLM) are interchangeable:

- Same function `answer_question()` is called in both cases.
- If Brain 2 is not configured or fails, the app catches the problem silently
  and uses Brain 1. The guest never sees an error.

### Decision 3 — Caching for speed

Weather doesn't change every second. The app caches each city's data for
`CACHE_TTL_SECONDS` (default 300s = 5 minutes). This:

- makes repeat visitors fast,
- protects the free weather service from being hammered,
- gives instant answers for the same city.

## A picture of the automated build

The app is small but well-tested: **38 automated tests** (in `tests/`) check the
kitchen and the waiter so that changes don't break things. Later documents cover
how those tests run automatically.

## Where to go next

- Want to understand the "restaurant" menu (API)? → **03**
- Want to understand where the raw ingredients come from? → **02**
- Want to see the kitchen in code? → **06**