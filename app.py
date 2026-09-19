from weathertracker import create_app

app = create_app()

if __name__ == "__main__":
    port = int(app.config.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))  # noqa: S104 - web server binds all interfaces
