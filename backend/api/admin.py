from __future__ import annotations

from flask import Blueprint, jsonify, request

from services import gitops
from services.bookmarks_service import load_bookmarks, save_bookmarks
from services.devices_service import list_devices, replace_manual_devices
from services.settings_service import get_settings, update_settings

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/status", methods=["GET"])
def admin_status():
    return jsonify(
        {
            "status": "ok",
            "git": gitops.git_status(),
            "settings": get_settings(),
            "devices_count": len(list_devices()),
        }
    )


@admin_bp.route("/git/commit", methods=["POST"])
def git_commit():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "chore(dashboard): update settings and data"))
    result = gitops.git_commit_all(message=message)
    return jsonify(result), 200 if result.get("ok") else 500


@admin_bp.route("/git/push", methods=["POST"])
def git_push():
    payload = request.get_json(silent=True) or {}
    remote = str(payload.get("remote", "origin"))
    branch = payload.get("branch")
    result = gitops.git_push(remote=remote, branch=branch)
    return jsonify(result), 200 if result.get("ok") else 500


@admin_bp.route("/git/pull", methods=["POST"])
def git_pull():
    payload = request.get_json(silent=True) or {}
    remote = str(payload.get("remote", "origin"))
    branch = payload.get("branch")
    result = gitops.git_pull(remote=remote, branch=branch)
    return jsonify(result), 200 if result.get("ok") else 500


@admin_bp.route("/backup/export", methods=["GET"])
def backup_export():
    return jsonify(
        {
            "settings": get_settings(),
            "bookmarks": load_bookmarks(),
            "devices": list_devices(include_discovered=False),
        }
    )


@admin_bp.route("/backup/restore", methods=["POST"])
def backup_restore():
    payload = request.get_json(silent=True) or {}

    if not isinstance(payload, dict):
        return jsonify({"error": "Ungültiger Payload"}), 400

    if "settings" in payload and isinstance(payload["settings"], dict):
        update_settings(payload["settings"])

    if "bookmarks" in payload and isinstance(payload["bookmarks"], list):
        save_bookmarks(payload["bookmarks"])

    if "devices" in payload and isinstance(payload["devices"], list):
        replace_manual_devices(payload["devices"])

    return jsonify({"status": "restored"})
