from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.bookmarks_service import (
    create_bookmark,
    delete_bookmark,
    import_bookmarks_from_json,
    import_bookmarks_from_netscape_html,
    list_bookmarks,
    list_categories,
    update_bookmark,
)

bookmarks_bp = Blueprint("bookmarks", __name__)


@bookmarks_bp.route("/", methods=["GET"])
def get_bookmarks():
    query = request.args.get("q", "")
    category = request.args.get("category")
    sort_by = request.args.get("sort_by", "title")
    sort_order = request.args.get("sort_order", "asc")
    favorite_raw = request.args.get("favorite")
    favorite = None

    if favorite_raw in {"true", "false"}:
        favorite = favorite_raw == "true"

    items = list_bookmarks(
        query=query,
        category=category,
        favorite=favorite,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return jsonify({"items": items, "count": len(items)})


@bookmarks_bp.route("/", methods=["POST"])
def add_bookmark():
    payload = request.get_json(silent=True) or {}
    if not payload.get("url"):
        return jsonify({"error": "Feld 'url' ist erforderlich"}), 400

    created = create_bookmark(payload)
    return jsonify(created), 201


@bookmarks_bp.route("/<bookmark_id>", methods=["PATCH"])
def patch_bookmark(bookmark_id: str):
    payload = request.get_json(silent=True) or {}
    updated = update_bookmark(bookmark_id, payload)
    if updated is None:
        return jsonify({"error": "Lesezeichen nicht gefunden"}), 404
    return jsonify(updated)


@bookmarks_bp.route("/<bookmark_id>", methods=["DELETE"])
def remove_bookmark(bookmark_id: str):
    deleted = delete_bookmark(bookmark_id)
    if not deleted:
        return jsonify({"error": "Lesezeichen nicht gefunden"}), 404
    return jsonify({"status": "deleted"})


@bookmarks_bp.route("/categories", methods=["GET"])
def categories():
    return jsonify({"categories": list_categories()})


@bookmarks_bp.route("/import", methods=["POST"])
def import_bookmarks():
    payload = request.get_json(silent=True) or {}
    import_type = payload.get("type", "json")

    if import_type == "json":
        items = payload.get("items", [])
        if not isinstance(items, list):
            return jsonify({"error": "Für JSON-Import ist ein Array in 'items' erforderlich"}), 400
        result = import_bookmarks_from_json(items)
        return jsonify({"imported": result.imported, "skipped": result.skipped})

    if import_type == "netscape-html":
        raw_html = payload.get("raw", "")
        if not isinstance(raw_html, str) or not raw_html.strip():
            return jsonify({"error": "Für HTML-Import ist 'raw' erforderlich"}), 400
        result = import_bookmarks_from_netscape_html(raw_html)
        return jsonify({"imported": result.imported, "skipped": result.skipped})

    return jsonify({"error": "Unbekannter Importtyp"}), 400
