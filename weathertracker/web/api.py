from flask import Blueprint, jsonify, request

from weathertracker.services.geocoding import search_cities
from weathertracker.services.assistant import ask_city, get_weather_bundle
from weathertracker.services.weather import clear_cache

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/search")
def search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"success": False, "error": "Query too short", "results": []}), 400
    try:
        results = search_cities(query)
        return jsonify({"success": True, "results": results})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc), "results": []}), 502


@api_bp.route("/weather/<city>")
def weather(city):
    bundle = get_weather_bundle(city)
    return jsonify({"success": True, **bundle})


@api_bp.route("/ask/<city>")
def ask(city):
    question = (request.args.get("q") or "").strip()
    if not question:
        return jsonify({"success": False, "error": "Missing question"}), 400
    from flask import current_app

    llm = current_app.extensions["llm"]
    bundle = get_weather_bundle(city)
    answer = ask_city(llm, bundle, question)
    return jsonify({"success": True, "city": bundle["city"], "answer": answer, "llm_enabled": llm.enabled})


@api_bp.route("/cache/clear", methods=["POST"])
def purge_cache():
    clear_cache()
    return jsonify({"success": True, "message": "cache cleared"})