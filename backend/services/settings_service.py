from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.storage import CONFIG_DIR, read_json, write_json

SETTINGS_PATH = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "dashboard": {
        "title": "Udos Home Dashboard",
        "port": 8088,
        "location": "Borken",
    },
    "modules": {
        "bookmarks": True,
        "devices": True,
        "weather": False,
        "calendar": False,
        "paperless": False,
        "docker": False,
        "proxmox": False,
        "music": False,
        "recipes": False,
    },
    "bookmarks": {
        "default_sort_by": "title",
        "default_sort_order": "asc",
        "categories": ["Server", "Cloud", "Medien", "Tools"],
    },
    "devices": {
        "network_cidr": "192.168.1.0/24",
        "scan_methods": ["arp"],
        "scan_timeout_sec": 2,
        "auto_scan_on_load": False,
    },
    "git": {
        "auto_commit_json_changes": False,
        "default_commit_message": "chore(dashboard): update data files",
        "remote": "origin",
        "branch": "main",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def get_settings() -> dict[str, Any]:
    loaded = read_json(SETTINGS_PATH, {})
    if not isinstance(loaded, dict):
        loaded = {}
    merged = _deep_merge(DEFAULT_SETTINGS, loaded)

    if merged != loaded:
        write_json(SETTINGS_PATH, merged)

    return merged


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    current = get_settings()
    updated = _deep_merge(current, patch)
    write_json(SETTINGS_PATH, updated)
    return updated


def set_module_enabled(module_name: str, enabled: bool) -> dict[str, Any]:
    settings = get_settings()
    settings.setdefault("modules", {})[module_name] = enabled
    write_json(SETTINGS_PATH, settings)
    return settings
