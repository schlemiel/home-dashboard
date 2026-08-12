from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.settings_service import (
    get_settings as get_settings_service,
    set_module_enabled,
    update_settings,
)

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/", methods=["GET"])
def get_settings():
    return jsonify(get_settings_service())


@settings_bp.route("/", methods=["PATCH"])
def patch_settings():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Ungültiger Payload"}), 400
    updated = update_settings(payload)
    return jsonify(updated)


@settings_bp.route("/modules/<module_name>", methods=["PATCH"])
def toggle_module(module_name: str):
    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled", False))
    updated = set_module_enabled(module_name=module_name, enabled=enabled)
    return jsonify(updated)
