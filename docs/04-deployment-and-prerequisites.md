# 04 — Deployment & Prerequisites (Intermediate)

> This document explains everything needed before you deploy the app — and the
> supported ways to put it on the internet (Docker locally, then Render free
> tier in production).

## Prerequisites — the checklist

| Requirement | Version | Check with | Why |
|-------------|---------|------------|-----|
| Python | 3.10+ (3.11 recommended) | `python3 --version` | The app is Python |
| pip | any recent | `pip --version` | Installs dependencies |
| Git (to clone) | any | `git --version` | Pulls the source |
| Docker (+ compose) | optional for Django-style container run | `docker --version` | Recommended deploy path |
| A terminal | any | — | Where you run commands |

No database, no API keys, no paid accounts are required for a weather-only
deployment. A cloud account (Render free) is optional but makes the app public.

## Environment files — the one thing to notele

The app reads configuration from **environment variables**. Two files matter:

- `.env.example` — the template (committed, safe to push).
- `.env` — your real settings (gitignored; NEVER pushed).

```bash
cp .env.example .env   # then edit .env
```

Key things `.env` controls: debug mode, port, cache TTL, featured cities,
India-only search, and the optional LLM settings.

## Deploying locally (already covered in 00)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://localhost:8080.

## Deploying with Docker (local container)

Two supported ways:

### Option A — Compose (recommended)

```bash
docker compose up --build
```

What it does: builds the image, maps port 8080, sets env vars, adds a health
check that pings `/city/Delhi` every 60 seconds, and restarts on failure.

### Option B — Raw docker

```bash
docker build -t ai-weather-tracker .
docker run -p 8080:8080 \
  -e LLM_ENABLED=true \
  -e LLM_API_KEY=your-key \
  -e LLM_MODEL=openai/gpt-oss-120b \
  ai-weather-tracker
```

## The Dockerfile (explained)

```dockerfile
FROM python:3.11-slim        # slim base = small image
WORKDIR /app                 # app lives in /app
COPY requirements.txt .      # install deps FIRST (layer caching = faster builds)
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                     # then copy source
RUN useradd appuser && chown -R appuser:appuser /app   # non-root user = safer
USER appuser
ENV PORT=8080
EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "3", "--threads", "2", "--timeout", "60", "app:app"]
```

Highlights:

- **Non-root user** — the container never runs as root (hardening).
- **Gunicorn with 3 workers × 2 threads** — parallel request handling.
- `app:app` — "module `app` (app.py), attribute `app` (the Flask object)".
- Layer order — dependencies install before source copy, so code changes don't
  reinstall the world.

## Deploying to Render (free, production)

1. Push the repo to GitHub.
2. On [render.com](https://render.com) → **New → Web Service** → connect the repo.
3. Set **Runtime = Docker** (uses the included Dockerfile).
4. Environment variables (Environment tab):

   ```
   LLM_ENABLED=true
   LLM_API_KEY=<your key>            # only if using the LLM
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=openai/gpt-oss-120b
   SECRET_KEY=<long random string>
   ```

5. **Save & Deploy.**

Render publishes at `https://<service-name>.onrender.com`, auto-restarts on
crash, and **auto-redeploys on every push to main**.

Live example of this repo:
[https://ai-weather-tracker.onrender.com](https://ai-weather-tracker.onrender.com)

## Choosing the LLM model at deploy time

This is the currently-common pitfall: Groq changes its model lineup. If your
deployed app answers "2+2" with a weather snippet instead of a real answer, the
LLM call is failing — usually because `LLM_MODEL` on the deployed env points at a
retired model. Fix: list live models and set `LLM_MODEL` accordingly.

```bash
curl -H "Authorization: Bearer $LLM_API_KEY" \
     https://api.groq.com/openai/v1/models
```

## Ports

- The app listens on **8080** by default (`PORT` env).
- Locally you asked for `0.0.0.0:8080` — reachable via `localhost:8080`.
- Render maps 8080 automatically (web services use the port from the Dockerfile).

## Verifying a deployment

Smoke test after any deploy:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://your-app.onrender.com/        # → 200
curl -s https://your-app.onrender.com/api/weather/Delhi | head -c 300          # → JSON
curl -s "https://your-app.onrender.com/api/ask/Delhi?q=hi"                     # → answer
```

## Common deploy mistakes

- Forgetting env vars → LLM off (fine) or broken model id (confusing fallback answers).
- Not setting `SECRET_KEY` → default value used (fine locally, set a unique one publicly).
- Pushing `.env` → GitHub will BLOCK it via push-protection (secret scanning) —
  keep keys out of git at all costs.

Next: automating build/test/deploy — **05 CI/CD Pipeline**.