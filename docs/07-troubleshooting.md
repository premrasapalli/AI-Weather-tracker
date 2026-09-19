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

Expected healthy result: **38 passed** (18 original + 20 added to reach the
80% coverage gate).

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

## 11. CI/CD jobs fail on GitHub

**Symptom:** a commit is pushed but the "Actions" tab shows a red ✗.

Most common failures and their exact fixes (all were hit in this project):

| Job & symptom | Why it happened | How it was fixed | Where |
|---------------|-----------------|------------------|-------|
| Import smoke test — `ModuleNotFoundError: No module named 'flask'` | Lint job only installed `requirements-dev.txt` (no runtime deps) | Lint job now installs `requirements.txt` **and** `requirements-dev.txt` | `.github/workflows/ci.yml` → `lint` job |
| Tests (Python 3.10) — `ImportError: cannot import name 'UTC' from 'datetime'` | `datetime.UTC` only exists in Python 3.11+; CI matrix runs 3.10 | Replaced `datetime.UTC` with `timezone.utc`; added ruff `UP017` ignore with a comment so it stays 3.10-compatible | `weathertracker/services/assistant.py`, `pyproject.toml` |
| Security — TruffleHog "BASE and HEAD commits are the same. TruffleHog won't scan anything" | On a push the base ref = HEAD, so the action errors out | Scan now uses `github.event.before`, falling back to `HEAD~1` when empty/new | `.github/workflows/ci.yml` → `security` job |
| Coverage gate — "Required test coverage of 80% not reached. Total coverage: 75%" | Only 18 tests existed; LLM fallback (`llm.py`) was ~31% covered | Added 20 tests in `tests/test_llm_fallback.py` (fallback branches, cache, HTTP retries) → **87%** | `tests/test_llm_fallback.py` |
| CD run fails instantly — "This run likely failed because of a workflow file issue" | `secrets` is NOT allowed in a job-level `if:` (${{ secrets.X != '' }}) — invalid expression | Moved the secret into a job `env:`, gated the step with `if: env.RENDER_DEPLOY_HOOK_URL != ''`, added a warning step when unset | `.github/workflows/cd.yml` → `deploy-render` job |

**Rough order to debug your own red CI:**
1. Click the failed job in the Actions tab → read the red step.
2. Match the symptom to the table above.
3. Fix locally, re-run the local gate (ruff + pytest), commit, push.

## 12. The GitHub "secret" runbook (real incident log)

This project actually hit a **blocked push**. GitHub refused the push because a
file containing the Groq API key was about to be committed. Here is exactly what
happened and how it was fixed.

**What you see:**

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Push cannot contain secrets
remote:   ———————————————————
remote:   - Groq API Key
remote:     locations:
remote:     - commit: <sha>
remote:       path: .env.swp:1
```

**Root cause:** editing `.env` in a text editor created a **Vim swap file**
`.env.swp` in the repo root. `git add -A` accidentally staged it, so the key
would have been pushed. GitHub's Push Protection detected the secret and
declined the push.

**The exact fix (in order):**

```bash
# 1. Remove the offending file locally (and stop the editor that made it)
rm .env.swp

# 2. Make sure swap files are always ignored from now on
printf '\n*.swp\n*.swo\n' >> .gitignore

# 3. Unstage + never track it
git rm --cached .env.swp 2>/dev/null

# 4. Rebuild the commit WITHOUT the secret
git add .gitignore
git commit --amend -m "your message"
git push
```

**Verify nothing sensitive is trackable again:**

```bash
git ls-files | grep -i env          # only .env.example should appear
grep -rniE "gsk_|sk-" --include="*.py" --include="*.md" . 2>/dev/null | grep -v .env || echo "no keys"
```

**Follow-up hardening added to this repo:**
- `*.swp` / `*.swo` are in `.gitignore`.
- CI now runs **TruffleHog secret scanning** on every push and PR
  (`.github/workflows/ci.yml` → `security` job).
- CI scans the file tree for `.env.swp` / `.pem` / `.key` files and fails if any
  are present.
- **`.env` key was rotated at Groq** after it appeared in logs — rotating is the
  only real cleanup once a secret is exposed anywhere.

**Golden rule:** secrets live ONLY in local `.env` (gitignored) and in the
deploy platform's Environment tab / GitHub Secrets. Never in git, docs, or chat.

## 13. Resolved-issue log (this project, most recent first)

A running record of issues actually hit during development and deployment of
*this* app, with **what / why / how / where**. Use it as a checklist of known-
recovered problems.

| # | Issue | Why it happened | How we resolved it | Where |
|---|-------|-----------------|--------------------|-------|
| 1 | **`.env` key got pushed (blocked by GitHub)** | A `git add -A` staged a Vim swap file `.env.swp` containing the Groq key; GitHub Push Protection refused the push | Deleted the file, gitignored `*.swp`, `--amend`'ed the commit, re-pushed; then **rotated the key** and added TruffleHog scanning to CI | `.gitignore`, `docs/07` §12, `.github/workflows/ci.yml` |
| 2 | **CD workflow failed instantly ("workflow file issue")** | `if: ${{ secrets.RENDER_DEPLOY_HOOK_URL != '' }}` at *job* level — `secrets` is not an allowed context there | Moved the secret to a job `env:` and gated at *step* level with `if: env.RENDER_DEPLOY_HOOK_URL != ''`; added a skip-warning step | `.github/workflows/cd.yml` |
| 3 | **Python 3.10 test job failed: `cannot import name 'UTC'`** | `datetime.UTC` was added in Python 3.11, but CI tests 3.10 too | Switched to `timezone.utc` (works everywhere); ignored ruff `UP017` so linter stops asking to revert | `weathertracker/services/assistant.py`, `pyproject.toml` |
| 4 | **Lint job failed: `No module named 'flask'`** | The lint CI job only installed dev requirements, not runtime ones | Lint now installs `requirements.txt` + `requirements-dev.txt` | `.github/workflows/ci.yml` |
| 5 | **TruffleHog failed: "BASE and HEAD are the same"** | On push events `base` defaulted to the branch tip == HEAD, so there was nothing to scan | Switched base to `github.event.before`, falling back to `HEAD~1` when empty | `.github/workflows/ci.yml` |
| 6 | **Coverage gate failed (75% < 80%)** | Only 18 tests existed; the LLM fallback engine was barely covered | Added 20 tests (all fallback branches, cache TTL/LRU, HTTP retries) → 87% | `tests/test_llm_fallback.py` |
| 7 | **Local LLM answered but deployed app only gave fallback answers** | Render's Env tab still had a retired model / old key | Updated `LLM_MODEL` to a live Groq model + new key in Render → Environment → Save & Deploy | Render dashboard, `.env` |
| 8 | **Groq returned `404` / `model_decommissioned`** | Groq retires models; `llama-3.3-70b-versatile` no longer exists | Listed live models via `GET /v1/models`, set `LLM_MODEL=openai/gpt-oss-120b` | `.env` |
| 9 | **Local folder rename broke everything** | Moving `SIMPLE-WEATHER-APP → AI-Weather-tracker` left a nested duplicate and an empty `.env` *directory*; tooling still pointed at the old path | Consolidated into one folder, moved the real `.env` + `.venv` up, deleted the nested copy | filesystem |
| 10 | **`.venv` interpreter broken after rename** | The venv's shebang still had the old absolute path | Recreated the venv: `rm -rf .venv && python3 -m venv .venv && pip install -r requirements*.txt` | terminal |
| 11 | **Chat answers sometimes didn't render (older release)** | Frontend tracked the last bubble with a fragile `querySelector(".chat-ai:last-child")` | Replaced with a direct element-reference variable; added richer fallback answers for tomorrow/week/wear/health | `static/js/app.js`, `weathertracker/services/llm.py` |
| 12 | **Gunicorn: "Failed to find attribute 'app' in 'app'" (older release)** | The internal package was named `app/` and shadowed `app.py` | Renamed the package `app/` → `weathertracker/`; `gunicorn ... app:app` now resolves cleanly | repo layout, commit `1afd924` |

## The one-page "I'm stuck" checklist

1. `source .venv/bin/activate` then run the app — still failing?
2. `pip install -r requirements.txt -r requirements-dev.txt` — still failing?
3. Read the terminal traceback's LAST 10 lines.
4. If it mentions a Groq/HTTP error → see issue 3 (model/key/base URL).
5. If it's a Render problem → issue 6.
6. If it's a CI/CD red job → issue 11.
7. If it's "push rejected / secret" → issue 12.
8. If it's something we've hit before → scan the resolved-issue log (§13).
9. If nothing helps, include the last lines of the terminal in your message.

Next: what it costs to run and how to keep it healthy — **08 Cost & Operations**.