from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.devices_service import (
    add_manual_device,
    delete_manual_device,
    list_devices as list_devices_service,
    run_discovery_scan,
    update_manual_device,
)

devices_bp = Blueprint("devices", __name__)


@devices_bp.route("/", methods=["GET"])
def list_devices():
    include_discovered_raw = request.args.get("include_discovered", "true").lower()
    include_discovered = include_discovered_raw != "false"
    items = list_devices_service(include_discovered=include_discovered)
    return jsonify({"devices": items, "count": len(items)})


@devices_bp.route("/", methods=["POST"])
def create_device():
    payload = request.get_json(silent=True) or {}
    created = add_manual_device(payload)
    return jsonify(created), 201


@devices_bp.route("/<device_id>", methods=["PATCH"])
def patch_device(device_id: str):
    payload = request.get_json(silent=True) or {}
    updated = update_manual_device(device_id, payload)
    if updated is None:
        return jsonify({"error": "Gerät nicht gefunden"}), 404
    return jsonify(updated)


@devices_bp.route("/<device_id>", methods=["DELETE"])
def remove_device(device_id: str):
    deleted = delete_manual_device(device_id)
    if not deleted:
        return jsonify({"error": "Gerät nicht gefunden"}), 404
    return jsonify({"status": "deleted"})


@devices_bp.route("/scan", methods=["POST"])
def scan_devices():
    result = run_discovery_scan()
    return jsonify(result)
