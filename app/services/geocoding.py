from app.utils.http_client import get_json


class LocationResult:
    def __init__(self, name, admin1, country_code, latitude, longitude, timezone, raw=None):
        self.name = name
        self.admin1 = admin1
        self.country_code = country_code
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone or "auto"
        self.raw = raw or {}

    def to_dict(self):
        return {
            "name": self.name,
            "state": self.admin1,
            "country_code": self.country_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
        }


def _lookup_city(city: str, india_only: bool = True) -> "LocationResult | None":
    params = {"name": city, "count": 5, "format": "json", "language": "en"}
    if india_only:
        params["countryCode"] = "IN"
    data = get_json("https://geocoding-api.open-meteo.com/v1/search", params=params)
    results = (data or {}).get("results") or []
    if not results:
        return None
    best = results[0]
    return LocationResult(
        name=best.get("name"),
        admin1=best.get("admin1"),
        country_code=best.get("country_code"),
        latitude=best.get("latitude"),
        longitude=best.get("longitude"),
        timezone=best.get("timezone"),
        raw=best,
    )


def lookup_city(city: str, india_only: bool = True) -> "LocationResult | None":
    return _lookup_city(city, india_only)


def search_cities(query: str, india_only: bool = True, limit: int = 8) -> list[dict]:
    params = {"name": query, "count": limit, "format": "json", "language": "en"}
    if india_only:
        params["countryCode"] = "IN"
    data = get_json("https://geocoding-api.open-meteo.com/v1/search", params=params)
    results = (data or {}).get("results") or []
    out = []
    for r in results:
        out.append(
            {
                "name": r.get("name"),
                "state": r.get("admin1"),
                "country_code": r.get("country_code"),
                "latitude": r.get("latitude"),
                "longitude": r.get("longitude"),
                "timezone": r.get("timezone"),
            }
        )
    return out