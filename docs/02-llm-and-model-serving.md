# 02 — LLM & Model Serving (Intermediate)

> This document explains how a real AI model is connected to the app: which
> providers work, how the model is served, and how to configure it safely.

## What is an LLM?

An **LLM** (Large Language Model) is a big AI brain that reads text and writes
natural, human-sounding text. Unlike the rule engine (Brain 1 — fixed "if A then
B" instructions), an LLM can:

- understand a question written in hundreds of different ways,
- write helpful, fluent prose,
- reason about numbers inside a sentence ("28°C feels like 34°C... running tonight?").

The app calls the LLM "the optional brain." When it's off, the rule engine
handles everything. When it's on, the LLM answers chat questions and can rewrite
the weather briefing in a more natural style.

## Who serves the model?

The app does **not** run a model itself. It is a *client* that sends a request
to a **model-serving endpoint** that someone else (or you) operates. The app
only needs an internet URL and a key (unless you run a local server).

Supported endpoints (anything OpenAI-compatible):

| Provider | Base URL (example) | Own key? | Notes |
|----------|--------------------|----------|-------|
| **Groq** | `https://api.groq.com/openai/v1` | Yes (free tier) | Very fast, good free models |
| **OpenAI** | `https://api.openai.com/v1` | Yes | Original provider |
| **Together / OpenRouter** | provider-specific | Yes | Many models in one place |
| **Ollama (local)** | `http://localhost:11434/v1` | No | 100% free, runs on your PC |
| **vLLM (self-host)** | your server | Usually not | For datacenter deploys |

The magic is the **"OpenAI-compatible"** standard: as long as a server understands
the same request format, the app can use it — the model-serving details (GPU,
batching, etc.) are hidden behind that URL.

## The three settings that matter

Set these in the `.env` file (copied from `.env.example`):

```env
LLM_ENABLED=true
LLM_API_KEY=your-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
LLM_TIMEOUT=15
```

| Setting | What it does |
|---------|--------------|
| `LLM_ENABLED` | Master switch (true/false) |
| `LLM_API_KEY` | The secret that proves who you are |
| `LLM_BASE_URL` | Which serving endpoint to talk to |
| `LLM_MODEL` | Which model to use on that endpoint |
| `LLM_TIMEOUT` | How many seconds to wait before giving up |

> `LLM_MODEL` naming follows the provider. For Groq, current fast free options
> include `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, and `qwen/qwen3.8-27b`.
> Groq retires old models — if you see "model_decommissioned" or a 404, list the
> live ones:
>
> ```bash
> curl -H "Authorization: Bearer $LLM_API_KEY" \
>      https://api.groq.com/openai/v1/models
> ```

## How the app talks to the model (in code)

The file `weathertracker/services/llm.py` contains a small `LLMClient` class:

```python
class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=15.0): ...
    @property
    def enabled(self): return bool(self.api_key)
    def chat(self, messages, temperature=0.4) -> str: ...
```

- `enabled` is `True` only when an API key exists.
- `chat()` posts a `POST {base}/chat/completions` request, with:
  - `model`: which model to use,
  - `messages`: the conversation (system + user),
  - `temperature`: 0.0 (precise) to 1.0 (creative).
- It returns the model's first reply text.

**This is why it's called "model serving compreend":** the app never stores or
trains models — it just *serves* (= requests) predictions from a remote brain.

## Two uses of the LLM

1. **Answering questions** (`answer_question`): the user's question + live
   weather numbers get sent, and the model writes an answer.
2. **Polishing the briefing** (`enrich_briefing`): the model rewrites the plain
   briefing into a more natural paragraph.

Both are wrapped in `try/except` — if the model fails (timeout, bad key, no
internet), the app silently uses the rule engine result. Your page never breaks.

## Model serving under the hood (Groq example)

1. App sends: `POST https://api.groq.com/openai/v1/chat/completions`
2. With headers: `Authorization: Bearer <key>`, `Content-Type: application/json`
3. And a JSON body: `{model, messages, temperature}`
4. Groq's fast chips (LPU) return the generated text in ~1–3s.
5. App extracts `data["choices"][0]["message"]["content"]` and shows it.

Because the request format is standard, the same few lines of `LLMClient` work
for OpenAI, Groq, Ollama, vLLM — no code changes, just new `LLM_BASE_URL` and
`LLM_MODEL`.

## Security notes (read this!)

- Keep the key **only in `.env`** — that file is gitignored and never pushed.
- Never paste the key into the repo, logs, or docs.
- If a key appears in chat/terminal by accident, **rotate it** at the provider
  and update `.env` (and your cloud deployment env vars).
- Reduce risk with a free/low-tier key because usage is light (weather chat
  answers are short).

## How to verify your setup works

Run the app, then ask a question that only a generative model can answer:

```bash
curl "http://localhost:8080/api/ask/Delhi?q=what%20is%202%20plus%202"
```

- If you get a **weather-generic fallback** answer, the LLM call failed (check
  key/model/base URL) and the rule engine answered instead.
- If you get a **direct "4"** (or a natural refusal), the LLM is working.

## Summary

- The app connects to any OpenAI-compatible model server.
- Configuration = `LLM_ENABLED`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`.
- Failures are invisible to the user (graceful fallback).
- Keys go in `.env` only, and should be rotated if ever exposed.

Next: how other programs talk to this app — **03 API Gateway & Integration**.