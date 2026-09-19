from flask import Blueprint, current_app, render_template, request

page_bp = Blueprint("page", __name__)


@page_bp.route("/")
def index():
    featured = current_app.config.get("FEATURED_CITIES", [])
    return render_template("index.html", initial_city=featured[0] if featured else "Delhi", featured=featured)


@page_bp.route("/city/<city>")
def city_page(city):
    return render_template("index.html", initial_city=city)