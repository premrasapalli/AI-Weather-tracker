import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "ai-weather-tracker-secret")

    DEBUG = _env_bool("DEBUG", False)
    TESTING = _env_bool("TESTING", False)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Open-Meteo endpoints (100% free, no API key required)
    GEOCODE_URL = os.getenv("GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")
    FORECAST_URL = os.getenv("FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
    AIR_QUALITY_URL = os.getenv("AIR_QUALITY_URL", "https://air-quality-api.open-meteo.com/v1/air-quality")

    # Request tuning
    HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))
    HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
    HTTP_BACKOFF = float(os.getenv("HTTP_BACKOFF", "0.4"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", "256"))

    # India-first behaviour
    INDIA_ONLY = _env_bool("INDIA_ONLY", True)
    DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Delhi")
    FEATURED_CITIES = [
        c.strip()
        for c in os.getenv(
            "FEATURED_CITIES",
            "Delhi,Mumbai,Bengaluru,Hyderabad,Chennai,Kolkata,Pune,Jaipur,Ahmedabad,"
            "Lucknow,Chandigarh,Surat,Kochi,Bhopal,Indore,Patna,Visakhapatnam,Nashik",
        ).split(",")
    ]

    # LLM (optional). Set LLM_API_KEY to enable generative AI enrichments.
    LLM_ENABLED = _env_bool("LLM_ENABLED", False)
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "15"))

    # Runtime
    PORT = int(os.getenv("PORT", "8080"))