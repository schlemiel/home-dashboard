from flask import Flask, jsonify, render_template
from api.admin import admin_bp
from api.bookmarks import bookmarks_bp
from api.devices import devices_bp
from api.settings import settings_bp
from services.settings_service import get_settings

app = Flask(__name__, template_folder="templates")

app.register_blueprint(bookmarks_bp, url_prefix="/api/bookmarks")
app.register_blueprint(devices_bp, url_prefix="/api/devices")
app.register_blueprint(settings_bp, url_prefix="/api/settings")
app.register_blueprint(admin_bp, url_prefix="/api/admin")

@app.route("/")
def index():
    settings = get_settings()
    title = settings.get("dashboard", {}).get("title", "Home Dashboard")
    return render_template("index.html", title=title)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    settings = get_settings()
    port = int(settings.get("dashboard", {}).get("port", 8088))
    app.run(host="0.0.0.0", port=port)
