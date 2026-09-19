# 00 — Introduction (For Everyone)

> Read this first. It explains what this project is in plain English — no coding
> knowledge needed. The later documents go deeper, step by step.

## What is this?

**AI Weather Tracker** is a website that:

1. Shows you the **current weather** for cities across India (temperature,
   humidity, wind, clouds, and more).
2. Shows you the **7-day forecast** (high/low temps, rain chance, UV, sunrise/sunset).
3. Shows you the **air quality** (how clean or polluted the air is right now).
4. Has a built-in **AI assistant** you can chat with:

   > "Will it rain tomorrow?" → the assistant answers using real weather data.
   >
   > "What should I wear today?" → it gives a clothing tip based on temperature.
   >
   > "Is it safe to jog right now?" → it warns you if the air quality is bad.

## Have you used a weather app before?

Great — then you already know what this does. Think of a typical phone weather
app (like Google Weather or AccuWeather), but with two extras:

- A focus on **Indian cities** and **Indian air quality guidance**.
- A **chat with the weather** — you can *ask questions* instead of just reading.

## The important part: it is FREE

- The weather information comes from a free service called **Open-Meteo**
  (public weather data — no cost).
- The AI assistant has **two brains**:
  - **Brain 1 (always on, free):** a set of smart rules that turn weather numbers
    into helpful answers. Works offline, no key, no cost.
  - **Brain 2 (optional):** a real AI model (like the ones from Groq or OpenAI) that
    answers more creatively. This one needs a key from the provider — you add it in
    a settings file if you want it. If it's not available, the app quietly uses
    Brain 1 instead. Nothing breaks.

> In simple words: **the app works perfectly with zero accounts and zero money.**
> Turning on the fancy AI model is an optional upgrade.

## Why is there a "chat with AI"?

Two reasons:

- **Understanding weather is hard.** "AQI 160" sounds like nothing — but the
  assistant tells you what it *means* ("air quality is unhealthy for sensitive
  groups, prefer indoor exercise").
- **Decisions are personal.** Instead of reading a number, you ask "should I go
  for a run tonight?" and get a practical answer.

## What do you need to get started?

| You need | Why | Cost |
|----------|-----|------|
| A computer with any browser | To open the website | — |
| Something to run the code (Python, or Docker) | To start the app on your machine | Free download |
| An internet connection | To fetch live weather data | Your normal internet |
| An AI key (optional) | For the creative AI answers | Sometimes free tier |

That's it. So in this document, we show you the very first steps.

## Try it

There are three easy ways:

**Way 1 — Already live on the internet (no setup)**
Open this link in your browser:
[https://ai-weather-tracker.onrender.com](https://ai-weather-tracker.onrender.com)
Pick a city, read the weather, and ask the assistant a question.

**Way 2 — Run it on your own computer with Python**

```bash
git clone https://github.com/premrasapalli/AI-Weather-tracker.git
cd AI-Weather-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8080 in your browser.

**Way 3 — Run it with Docker (in a container)**

```bash
docker compose up --build
```

Then open http://localhost:8080.

All three ways show the **exact same app**.

If any step is confusing, jump ahead to `07-troubleshooting.md` — it explains
common problems in everyday language.

## What's inside this documentation series?

We wrote 11 documents (numbered 00 to 10) that go from *simple* to *advanced*.

| Doc | Level | What you will learn |
|-----|-------|---------------------|
| **00 — this file** | Everyone | What the app is, and how to use it |
| **01 — Architecture** | Beginner | How the pieces fit together, like a kitchen recipe |
| **02 — LLM & Model Serving** | Intermediate | What "the AI brain" is, and how it is connected |
| **03 — API Gateway & Integration** | Intermediate | How other apps can talk to this one |
| **04 — Deployment & Prerequisites** | Intermediate | Putting the app on the internet for real |
| **05 — CI/CD Pipeline** | Advanced | Automatic testing and shipping robots |
| **06 — Implementation Guide** | Advanced | A guided walk through every folder and file |
| **07 — Troubleshooting** | Everyone | Fix the most common things that go wrong |
| **08 — Cost & Operations** | Advanced | What it costs, how to watch it, how to keep it healthy |

Reading order: start here, then go to **01**, and move forward in number order.

If you only want the plain-English version, read **00**, **01**, and **07**.
The rest are for people who want to build or modify the app themselves.

### One more sentence for context

This project started as a simple idea — *make a weather app for India with AI* —
and grew into a clean, well-organized, free-to-run system with an assistant, a
REST API, automatic testing, and cloud deployment. As you read on, you will see
each part of that system, from the simplest screen to the smartest layer.

Ready? Continue to **01 — Architecture**.