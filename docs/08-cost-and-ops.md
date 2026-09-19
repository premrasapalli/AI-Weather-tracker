# 08 — Cost & Operations (Advanced)

> This document covers the real-world cost model of running the app (mostly
> FREE!), how to monitor it, scale it, and operate it like a small production
> service.

## The headline: cost ≈ ₹0/week

This app is engineered to run at (essentially) zero cost:

| Component | Cost |
|-----------|------|
| Weather data (Open-Meteo) | Free (open data, CC-BY 4.0) |
| Air quality (Open-Meteo) | Free |
| Rule-based AI (Brain 1) | Free, on your own CPU |
| Docker host (Render Free / local) | Free tier available |
| Optional LLM (Groq) | Free tier; pennies at hobby scale |
| GitHub repo | Free |

## Cost anatomy

### 1. Fixed costs — the host

| Option | Cost | Notes |
|--------|------|-------|
| Your laptop (dev) | ₹0 | For development |
| Render Free web service | ₹0 | Sleeps after inactivity (~15 min), wakes on request; slower cold start |
| Render Starter ($7/mo) | ~₹600/mo | Always-on, faster, no cold starts |
| Any VPS (2 vCPU/1GB) | ~₹400–800/mo | Full control |

If you just want the demo working: **Render Free = ₹0**.

### 2. Variable costs — the LLM

The only real "per-use" cost. Groq's short answers are tiny:

- Weather Q&A: a few hundred tokens per chat answer.
- Briefing polish: ~200 tokens per city load (when the LLM is on).

On Groq's free tier this is effectively ₹0 for hobby use. If you exceed free
tier, expect cents per thousand requests — a serious app serving thousands of
queries/day would still cost under a few dollars/month.

### 3. Zero-cost engineering decisions (why this is cheap)

| Decision | Effect on cost |
|----------|----------------|
| Open-Meteo instead of paid APIs | Data cost → ₹0 |
| Caching (5-min TTL) | Fewer LLM/data calls; most repeat visitors cost nothing |
| Two-brain fallback | LLM outage → rule engine, so no "pay for load-balance" complexity |
| Rule engine as default | LLM only when explicitly enabled |

## Cost per request (estimate)

| Request | Data | LLM | ~Cost |
|---------|------|-----|-------|
| `GET /` or `/api/weather` | Open-Meteo call(s) | maybe briefing polish | ₹0 (free) |
| `/api/ask` (LLM off) | cached/one fetch | none | ₹0 |
| `/api/ask` (LLM on) | cached context | ~300 tokens in+out | ~₹0.0003 |
| Repeated same-city ask | cache hits | same | ₹0 extra |

Even at 10,000 LLM queries/month you're looking at a few $ at most on a paid
plan — or ₹0 on the typical free tier.

## Operations — keeping it healthy

### Logs

The app writes structured logs (level from `LOG_LEVEL`, default INFO). Where to
see them:

- Local: the terminal running the app.
- Render: Dashboard → service → **Logs** tab.

Watch for `LLM enrichment failed` / `LLM question failed` warnings — those mean
the generative brain is down and the rule engine took over (app still works).

### Health checks

- docker-compose: pings `/city/Delhi` every 60s.
- Render: uses its own health ping to the home page.

### Monitoring (beyond free host)

For real production, add **API monitoring**:

1. Log access counts / latencies (add a small middleware in `web/__init__.py`).
2. External uptime ping (UptimeRobot free tier → your `/`).
3. Optional structured logs to a service like Better Stack / Grafana Cloud.

### Rate limiting / abuse protection (if it gets popular)

The app is intentionally public + read-only, so abuse costs you nothing except
upstream rate limits. If usage ever stresses Open-Meteo:

- Raise `CACHE_TTL_SECONDS` (fewer upstream hits).
- Add a simple per-IP rate limiter in Flask (e.g. `flask-limiter`).
- Keep `DEBUG=false` publicly.

## Scaling decisions

This app is lightweight. Real scaling signals:

| Signal | Highest-value action |
|--------|----------------------|
| Many simultaneous users | More gunicorn workers (`-w`) or move off Render Free to a VPS |
| LLM latency | Fast provider (Groq), smaller model, or drop briefing polish to every-page |
| Upstream rate limiting (429) | Increase `CACHE_TTL_SECONDS` + retries |
| Memory pressure | Reduce `CACHE_MAXSIZE` (default 256 cities) |

The app is stateless (no DB), so scaling horizontally is trivial: run N replicas
behind a proxy — each has its own in-memory cache, which is fine (best case
slightly more upstream calls).

## Backup / data

There is **no persistent database** to back up — weather is derived from
Open-Meteo on demand. The only things to protect:

1. **`.env`** (secrets) — keep it OUT of git; have a copy elsewhere (password
   manager). If lost, re-create from `.env.example` + provider keys.
2. **Code** — already versioned in GitHub.

## Operational runbook — a bad day

| Incident | Detect | Respond |
|----------|--------|---------|
| Open-Meteo down | 502s in logs | App auto-retries; rule engine still answers asks with cached/prior context. Optionally bump `CACHE_TTL_SECONDS` until recovery |
| LLM provider down | `LLM ... failed` warnings | Nothing to do — Brain 1 covers. When provider returns, restart app to re-enable |
| Render rebuilt but broken | Health checks fail | Check Deploys log; env vars; push fix |
| City "not found" | 404 | Search autocomplete for exact name; India-only is intentional |

## Security operations

- **Rotate keys** whenever one is exposed in logs/chat/git history.
- GitHub push-protection is a safety net — it will REJECT secret pushes.
- Non-root container user (`appuser`) in the Dockerfile limits blast radius.
- `DEBUG=false` everywhere except local dev.

## Versioning & upgrade checklist

1. `git pull` latest.
2. `pip install -r requirements.txt` (there may be new deps).
3. Re-run tests: `.venv/bin/python -m pytest -q` → expect `38 passed`.
4. Diff `.env.example` vs `.env` to catch new settings.
5. Smoke test locally, then push → Render auto-redeploys.

## TL;DR

- Runs for **₹0** on free tiers.
- Only optional cost is the LLM (pennies at hobby scale / free tier).
- Stateless, cache-friendly, self-healing fallbacks → low ops burden.
- Keep `.env` secret, rotate keys when exposed, watch logs for `LLM failed`
  warnings, and everything else runs itself.