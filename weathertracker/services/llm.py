"""Optional LLM enrichment layer.

Works with any OpenAI-compatible chat endpoint (OpenAI, Groq, Together,
Ollama, LM Studio, vLLM...). When no API key is configured the app falls
back to the deterministic InsightGenerator — fully free and offline-safe.
"""

import json
import logging

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=15.0):
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or "gpt-4o-mini"
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        if not self.enabled:
            raise RuntimeError("LLM not enabled (missing API key)")
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


def enrich_briefing(llm: LLMClient, context: dict, briefing: str) -> str:
    """Ask the LLM to polish a weather briefing given live telemetry context."""
    if not llm.enabled:
        return briefing
    compact = {
        "city": context.get("city"),
        "state": context.get("state"),
        "temp_c": context.get("temp_c"),
        "condition": context.get("condition"),
        "humidity_pct": context.get("humidity_pct"),
        "wind_kmh": context.get("wind_kmh"),
        "aqi": context.get("aqi"),
        "today_max": context.get("today_max"),
        "today_min": context.get("today_min"),
        "txn": context.get("txn"),
    }
    system = (
        "You are a concise weather-report meteorologist for India. "
        "Return ONLY a short, fluent, 2-3 sentence briefing (no markdown, no preamble)."
    )
    user = (
        f"Live telemetry: {json.dumps(compact)}.\n"
        f"Vehicle: {briefing}\nWrite a tighter, more natural version."
    )
    try:
        return llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        ).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM enrichment failed, using engine briefing: %s", exc)
        return briefing


def answer_question(llm: LLMClient, question: str, context: dict) -> str:
    """Answer an open-ended question about the city using live context."""
    if not llm.enabled:
        return _fallback_answer(question, context)
    compact = {
        "city": context.get("city"),
        "state": context.get("state"),
        "temp_c": context.get("temp_c"),
        "feels_like_c": context.get("feels_like_c"),
        "condition": context.get("condition"),
        "humidity_pct": context.get("humidity_pct"),
        "pressure_hpa": context.get("pressure_hpa"),
        "wind_kmh": context.get("wind_kmh"),
        "cloud_pct": context.get("cloud_pct"),
        "aqi": context.get("aqi"),
        "today_max": context.get("today_max"),
        "today_min": context.get("today_min"),
        "sunrise": context.get("sunrise"),
        "sunset": context.get("sunset"),
        "forecast": context.get("forecast"),
    }
    system = (
        "You are an intelligent weather assistant for India. Use ONLY the provided "
        "telemetry to answer. Be accurate, helpful and brief (max 5 sentences)."
    )
    user = f"Telemetry for {context.get('city')}: {json.dumps(compact)}\nQuestion: {question}"
    try:
        return llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM question failed, using rule fallback: %s", exc)
        return _fallback_answer(question, context)


def _fallback_answer(question: str, ctx: dict) -> str:
    q = question.lower()
    city = ctx.get("city")
    days = (ctx.get("forecast") or {}).get("days") or []

    # 7-day outlook
    if "week" in q or "next" in q or "forecast" in q:
        if not days:
            return f"A 7-day forecast is not available for {city} right now."
        hottest = max(days, key=lambda d: d["tmax"])
        rainiest = max(days, key=lambda d: d.get("precip_prob") or 0)
        line = f"The week ahead in {city} peaks at {hottest['tmax']}°C on {hottest['date']} "
        if (rainiest.get("precip_prob") or 0) > 50:
            line += f"with rain most likely on {rainiest['date']} ({rainiest['precip_prob']}%)."
        else:
            line += "with little to no rain expected."
        return line
    if "tomorrow" in q:
        if len(days) < 2:
            return f"No forecast available for tomorrow in {city}."
        d = days[1]
        rain = d.get("precip_prob") or 0
        return (
            f"Tomorrow in {city}: {d['condition']}, {d['tmin']}–{d['tmax']}°C, "
            f"rain chance {rain}%."
        )
    if "rain" in q or "umbrella" in q:
        likely = (ctx.get("forecast") or {}).get("today_rain")
        if likely:
            return f"Yes — rain is expected today in {city} with a {likely}% chance. Carry an umbrella."
        return f"No significant rain expected today in {city}. Enjoy the dry weather."
    if "wear" in q or "cloth" in q or "dress" in q or "clothe" in q:
        temp = ctx.get("temp_c") or 0
        if temp >= 35:
            tip = "Light cotton clothes and a hat — it's hot."
        elif temp <= 20:
            tip = "Carry a light jacket or sweater."
        else:
            tip = "Comfortable light clothing works well."
        if (ctx.get("forecast") or {}).get("today_rain"):
            tip += " Also bring an umbrella for the chance of rain."
        return f"For {city} right now ({temp}°C): {tip}"
    if "health" in q or "exercise" in q or "jog" in q or "run" in q or "walk" in q:
        tip = f"It's {ctx.get('temp_c')}°C (feels like {ctx.get('feels_like_c')}°C). "
        if ctx.get("aqi") and ctx.get("aqi") > 150:
            tip += "Air quality is poor — prefer indoor exercise or early morning."
        elif ctx.get("temp_c", 0) >= 35:
            tip += "Best to exercise early morning or evening."
        else:
            tip += "Good time for outdoor activity."
        return tip
    if "air" in q or "pollut" in q or "aqi" in q or "breath" in q:
        aqi = ctx.get("aqi")
        if aqi is None:
            return "Air quality data is not available right now for this city."
        level = (
            "Good"
            if aqi <= 50
            else "Satisfactory"
            if aqi <= 100
            else "Moderate"
            if aqi <= 200
            else "Poor"
            if aqi <= 300
            else "Very Poor"
            if aqi <= 400
            else "Severe"
        )
        return f"Air quality in {city} is {level} (AQI {aqi}). {'Limit outdoor exercise.' if aqi > 200 else 'Generally fine for normal activity.'}"
    if "hot" in q or "temp" in q or "warm" in q:
        return (
            f"In {city} it is currently {ctx.get('temp_c')}°C "
            f"(feels like {ctx.get('feels_like_c')}°C). Today's range is "
            f"{ctx.get('today_min')}–{ctx.get('today_max')}°C."
        )
    if "wind" in q:
        return f"Winds in {city} are currently {ctx.get('wind_kmh')} km/h."
    if "humidity" in q or "humid" in q:
        return f"Relative humidity in {city} is {ctx.get('humidity_pct')}%."
    if "cloud" in q or "sky" in q:
        return f"Sky condition: {ctx.get('condition')} with {ctx.get('cloud_pct')}% cloud cover."
    return (
        f"In {city} right now it's {ctx.get('temp_c')}°C with {ctx.get('condition')}, "
        f"AQI {ctx.get('aqi') or 'n/a'}. Ask me about rain, tomorrow's weather, the week "
        f"ahead, what to wear, indoor exercise, air quality, wind or humidity."
    )
