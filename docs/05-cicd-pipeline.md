# 05 — CI/CD Pipeline (Advanced)

> This document explains how the project is continuously tested and shipped
> (Continuous Integration / Continuous Deployment). The GitHub Actions
> workflows described here are **already implemented and running** in this repo
> (see `.github/workflows/ci.yml` and `.github/workflows/cd.yml`).

## What is CI/CD?

- **Continuous Integration (CI):** every change is automatically tested when you
  push code. If a test fails, you find out in minutes, not on release day.
- **Continuous Deployment (CD):** every pushed change to the main branch is
  automatically built and published to production.

For this project, deployment is **two-layered and live**:
1. **CI on every push/PR** (`ci.yml`) — lint, format, 3-version test matrix with
   a coverage gate, security scans (bandit + TruffleHog + secret-file scan), and
   a Docker build with a container smoke test.
2. **CD on every push to `main`** (`cd.yml`) — builds and pushes the image to
   **GHCR**, then triggers a **Render deploy webhook** so production updates the
   instant CI is green.

## What we test (the test suite)

`tests/` contains 38 pytest tests, split across four files:

| File | Covers |
|------|--------|
| `test_api.py` | HTTP API endpoints (search, weather, ask, errors) using a mocked flask test client |
| `test_insights.py` | The rule engine: AQI categories, alerts, briefings, fallback answers |
| `test_weather.py` | The data services: geocoding, forecast, air quality, caching, retries |
| `test_llm_fallback.py` | LLM fallback branches, cache TTL/LRU, HTTP retry behaviour (coverage booster) |

The tests use **mocks** — they do NOT call the real internet. That means CI is
fast, deterministic, and works offline.

Run locally:

```bash
.venv/bin/python -m pytest -q
```

Expected: `38 passed`.

## CI pipeline steps (GitHub Actions — live in `.github/workflows/ci.yml`)

The workflow runs four independent jobs (simplified below for reading; the file
in the repo is authoritative):

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt -r requirements-dev.txt

      - name: Run tests
        run: python -m pytest -q

      - name: Verify app imports (smoke check)
        run: python -c "from app import app; print('OK', app.config['LLM_ENABLED'])"
```

What this does:

1. Triggers on every push/PR to `main`.
2. Tests against Python 3.10, 3.11, AND 3.12 (a version matrix).
3. Installs deps, runs the 38-test suite, and confirms the app object imports.

## A simple build stage (optional)

If you want to validate the Docker image in CI too, append:

```yaml
  docker:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Build the image
        run: docker build -t ai-weather-tracker:test .
      - name: Smoke test the container
        run: |
          docker run -d -p 8080:8080 ai-weather-tracker:test
          sleep 5
          curl -sf http://localhost:8080/city/Delhi
```

## The environment variables in CI

Because the app never *needs* the LLM (`LLM_ENABLED=false` default), tests pass
**without any secrets**. This is a deliberate design win: CI is hermetic.

If you DO want CI to exercise the LLM, add a GitHub secret and pass it as an env
var — but the test suite intentionally keeps the LLM out of the diff loop so
flaky network calls can't break deploys.

## CD — the Render auto-deploy

Render's web service watches the GitHub repo:

```
git push origin main
   │
   ▼
GitHub webhook → Render
   │
   ▼
Render builds the Dockerfile, starts gunicorn app:app
   │
   ▼
Health check passes (/city/Delhi → 200) → live at https://<service>.onrender.com
```

That's the "Continuous Deployment" part — it already exists for this repo.

## If you wanted full control (GitHub Container Registry)

A deeper CI/CD would also push the image:

```yaml
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Push image
        run: |
          docker tag ai-weather-tracker:test \
            ghcr.io/${{ github.repository }}:latest
          docker push ghcr.io/${{ github.repository }}:latest
```

Then Render can deploy from the registry instead of from the Dockerfile.

## Release hygiene

- `git commit` messages are short and descriptive (e.g. `Theme: switch to
  orange font colors, light-green LLM badge`).
- Secrets never enter commits — GitHub push-protection will actually REJECT a
  push containing a key (resolve via `git rm --cached` + `--amend`, then re-push).
- Keep `requirements*.txt` pinned to exact versions for reproducible builds.
- All GitHub Actions use pinned/semver action versions and minimal `permissions`
  (read-only where possible) to reduce supply-chain risk.

## Summary

- CI (live): ruff lint + format, tests on Python 3.10/3.11/3.12 with a **80%
  coverage gate**, security scans (bandit, TruffleHog, secret-file check), Docker
  build + smoke test. Currently **38 tests passed**, coverage **87%**.
- CD (live): Docker image → GHCR (latest + branch + SHA tags), then Render
  deploy via the `RENDER_DEPLOY_HOOK_URL` secret.
- The rendered pipeline and its recovered failures are documented in
  `docs/07-troubleshooting.md` §§11–13.

Next: a guided tour of the code — **06 Implementation Guide**.