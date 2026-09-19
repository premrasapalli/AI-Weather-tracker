import os

from flask import Flask, jsonify, render_template, request

from app.config import Config
from app.services.llm import LLMClient
from app.services.assistant import CityServiceError
from app.utils.logging_config import setup_logging


def create_app(config: Config | None = None) -> Flask:
    setup_logging((config or Config()).LOG_LEVEL)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )
    app.config.from_object(config or Config())

    llm = LLMClient(
        base_url=app.config["LLM_BASE_URL"],
        api_key=app.config["LLM_API_KEY"],
        model=app.config["LLM_MODEL"],
        timeout=app.config["LLM_TIMEOUT"],
    )
    app.extensions["llm"] = llm

    from app.web import api_bp, page_bp

    app.register_blueprint(page_bp)
    app.register_blueprint(api_bp)

    register_error_handlers(app)
    register_template_helpers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CityServiceError)
    def handle_city_error(exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": str(exc), "success": False}), exc.status_code
        return render_template("error.html", code=exc.status_code, message=str(exc)), exc.status_code

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found", "success": False}), 404
        return render_template("error.html", code=404, message="Page not found"), 404

    @app.errorhandler(500)
    def server_error(_):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error", "success": False}), 500
        return render_template("error.html", code=500, message="Something went wrong"), 500


def register_template_helpers(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        return {"app_name": "AI Weather Tracker", "year": "2026"}