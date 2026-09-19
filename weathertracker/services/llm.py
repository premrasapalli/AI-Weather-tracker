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
        return llm.chat([{"role": "system", "content": system}, {"role": "user", "content": user}]).strip()
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
    if "rain" in q or "umbrella" in q:
        likely = (ctx.get("forecast") or {}).get("today_rain")
        if likely:
            return f"Yes — rain is expected today in {ctx.get('city')} with a {likely}% chance. Carry an umbrella."
        return f"No significant rain expected today in {ctx.get('city')}. Enjoy the dry weather."
    if "hot" in q or "temp" in q or "warm" in q:
        return (
            f"In {ctx.get('city')} it is currently {ctx.get('temp_c')}°C "
            f"(feels like {ctx.get('feels_like_c')}°C). Today's range is "
            f"{ctx.get('today_min')}–{ctx.get('today_max')}°C."
        )
    if "air" in q or "pollut" in q or "aqi" in q or "breath" in q:
        aqi = ctx.get("aqi")
        if aqi is None:
            return "Air quality data is not available right now for this city."
        level = "Good" if aqi <= 50 else "Satisfactory" if aqi <= 100 else "Moderate" if aqi <= 200 else "Poor" if aqi <= 300 else "Very Poor" if aqi <= 400 else "Severe"
        return f"Air quality in {ctx.get('city')} is {level} (AQI {aqi}). {'Limit outdoor exercise.' if aqi > 200 else 'Generally fine for normal activity.'}"
    if "wind" in q:
        return f"Winds in {ctx.get('city')} are currently {ctx.get('wind_kmh')} km/h."
    if "humidity" in q or "humid" in q:
        return f"Relative humidity in {ctx.get('city')} is {ctx.get('humidity_pct')}%."
    if "cloud" in q or "sky" in q:
        return f"Sky condition: {ctx.get('condition')} with {ctx.get('cloud_pct')}% cloud cover."
    return (
        f"In {ctx.get('city')} right now it's {ctx.get('temp_c')}°C with {ctx.get('condition')}, "
        f"AQI {ctx.get('aqi') or 'n/a'}. Ask me about rain, temperature, air quality, wind or humidity."
    )