"""Gunicorn config; binds to the port configured in config/settings.json."""
from services.settings_service import get_settings

_settings = get_settings()
_port = int(_settings.get("dashboard", {}).get("port", 8088))

bind = f"0.0.0.0:{_port}"
workers = 2
threads = 4
timeout = 60
accesslog = "-"
errorlog = "-"
