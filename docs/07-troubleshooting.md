# 07 — Troubleshooting (For Everyone)

> A friendly, plain-English guide to the most common problems: what you see,
> what it means, and exactly how to fix it. Read this when something doesn't work.

## 1. "I turn it on but the page won't open"

**Symptom:** you run `python app.py` but the browser shows "can't reach
localhost:8080" (or the app claims the port is in use).

**Likely causes & fixes:**

| Cause | How to recognize | Fix |
|-------|------------------|-----|
| App still starting | Pretty quick after install | Wait a few seconds and refresh |
| Port already in use | "Address already in use" in terminal | `lsof -i :8080` to find the process; kill it or set `PORT=8081` |
| Wrong URL | — | Use exactly `http://localhost:8080` |
| Dependencies missing | Import errors in the terminal | `pip install -r requirements.txt` |

**Terminal check:** the last lines should end with something like
`Running on http://0.0.0.0:8080`. If you see a traceback instead, paste the last
lines into a search or jump to issue 2.

## 2. "Dependencies / module not found" on startup

**Symptom:** screen of red text ending with `ModuleNotFoundError: No module
named 'flask'`.

**Why:** Python can have multiple environments. The app is installed in one and
started from another.

**Fix (do all three in order):**

```bash
cd AI-Weather-tracker
python3 -m venv .venv                 # (re)create the environment
source .venv/bin/activate             # activate it
pip install -r requirements.txt       # install packages INSIDE it
python app.py                          # run from the SAME environment
```

Always use `source .venv/bin/activate` in the same terminal where you run the app.

## 3. "I added an LLM key but the chat still gives simple answers"

**Symptom:** questions like "2+2" get a weather-style reply instead of a real
(<shrug>) answer — i.e. the generative model isn't answering.

**Why almost always:** the LLM call is failing and the app is (by design)
quietly using the rule engine. Failing causes:

| Cause | How to check | Fix |
|-------|--------------|-----|
| Wrong/old model for Groq | model was retired → 404 `model_decommissioned` | List live models (see below), update `LLM_MODEL` |
| Key missing/mistyped | 401 Unauthorized in logs | Re-check `.env` `LLM_API_KEY`, no spaces/quotes |
| Wrong base URL | 404/401 | `https://api.groq.com/openai/v1` (no trailing `/chat/completions`) |
| Timeout | slow model | Raise `LLM_TIMEOUT` (e.g. 30) |
| Env not loaded | key visible but ignored | Restart the app; `.env` is read at startup |

**List live Groq models:**

```bash
curl -H "Authorization: Bearer $LLM_API_KEY" https://api.groq.com/openai/v1/models
```

Pick a current id, e.g. `openai/gpt-oss-120b`, set it in `.env`, restart.

**Quick proof the LLM is working:**

```bash
curl "http://localhost:8080/api/ask/Delhi?q=what%20is%202%20plus%202"
```

- Direct answer like a polite arithmetic refusal → LLM on ✓
- Generic weather fallback sentence → still off, check the table above.

## 4. "The AI says a city is not found"

**Symptom:** `City 'X' not found` for a real place.

**Why:** search is India-only by default (`INDIA_ONLY=true`), and the geocoding
step found nothing for that spelling.

**Fixes:**

- Try alternate spelling ("Bangalore" → "Bengaluru", "Pondicherry" → "Puducherry").
- Search first via `/api/search?q=` to discover the exact name.
- If you intentionally want worldwide: set `INDIA_ONLY=false` in `.env`.

## 5. "Weather is stale or exactly the same for minutes"

**Symptom:** numbers don't move even after a while.

**Why:** caching! By design each city is cached for `CACHE_TTL_SECONDS`
(default 300s = 5 min). Open-Meteo refreshes are hourly.

**Fixes:**

- Wait 2–5 minutes and refresh.
- For immediate refresh: `curl -X POST http://localhost:8080/api/cache/clear`.
- Set `CACHE_TTL_SECONDS=60` if you want fresher data at the cost of more
  upstream calls.

## 6. "It worked locally but fails/acts odd on Render"

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| App never starts | Port/env mismatch | Ensure `PORT=8080` is set (Render expects it) |
| LLM fallback on prod | Prod `LLM_MODEL` is an old/retired model | Update Render → Environment → `LLM_MODEL` → Save & Deploy |
| Random restarts | Health check failing | Check Render logs; `/city/Delhi` should return 200 |
| Old code | Render didn't redeploy | Push to GitHub `main` triggers auto-deploy; check Deploys tab |

## 7. "Push to GitHub got REJECTED with a secret warning"

**Symptom:**

```
remote: - Push cannot contain secrets
remote: - Groq API Key
```

**Why:** a file containing your key (e.g. a stray `.env` or an editor swap
file like `.env.swp`) got staged and committed. GitHub blocked it for your safety.

**Fix:**

```bash
git rm --cached .env.swp       # or whatever file GitHub flagged
rm .env.swp                    # delete it locally too
# make sure gitignore covers it, then recommit the file list WITHOUT secrets
printf '\n*.swp\n*.swo\n' >> .gitignore
git add .gitignore
git commit --amend -m "your message"   # clean the bad commit
git push
```

Confirm nothing sensitive is tracked:

```bash
git ls-files | grep -i env
```

Only `.env.example` (no secrets) should appear.

## 8. Tests fail locally

**Symptom:** `pytest` shows failures/errors.

**Fixes, in order:**

1. Recreate the environment completely:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

2. Run only the failing test for detail:

```bash
.venv/bin/python -m pytest tests/test_api.py -q
```

3. If failures are about network → tests use mocks, so check your code/edits
   didn't change an expected response contract.

Expected healthy result: `18 passed`.

## 9. "Docker build is slow" / "Image failed to build"

| Problem | Fix |
|---------|-----|
| Slow because reinstall every build | Make sure `COPY requirements.txt` + `pip install` comes BEFORE `COPY . .` (Docker layer caching) |
| `gunicorn: command not found` | Confirm `gunicorn==23.0.0` is in `requirements.txt` |
| Port conflict | Map another host port: `docker run -p 8099:8080 ...` |

Local build:

```bash
docker compose up --build      # takes a couple of minutes first time
```

## 10. "I edited .env but nothing changed"

**Why:** config is read **once at startup**. `.env` is not hot-reloaded
unless `DEBUG=true` (Flask dev server watches `app.py` only, not `.env`).

**Fix:** stop the app (Ctrl-C) and start it again. Also make sure you edited the
right file — there is exactly one `.env` at the repo root, not inside a subfolder.

## The one-page "I'm stuck" checklist

1. `source .venv/bin/activate` then run the app — still failing?
2. `pip install -r requirements.txt -r requirements-dev.txt` — still failing?
3. Read the terminal traceback's LAST 10 lines.
4. If it mentions a Groq/HTTP error → see issue 3 (model/key/base URL).
5. If it's a Render problem → issue 6.
6. If nothing helps, include the last lines of the terminal in your message.

Next: what it costs to run and how to keep it healthy — **08 Cost & Operations**.