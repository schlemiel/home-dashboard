from flask import Blueprint, jsonify

from services.system_service import get_system_overview

system_bp = Blueprint("system", __name__)


@system_bp.route("/", methods=["GET"])
def system_overview():
    return jsonify(get_system_overview())