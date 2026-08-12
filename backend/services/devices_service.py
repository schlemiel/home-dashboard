from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from services.settings_service import get_settings
from services.storage import DATA_DIR, read_json, write_json

MANUAL_DEVICES_PATH = DATA_DIR / "devices.json"
DISCOVERED_DEVICES_PATH = DATA_DIR / "discovered_devices.json"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def normalize_device(raw: dict[str, Any], source: str = "manual") -> dict[str, Any]:
    return {
        "id": raw.get("id") or str(uuid4()),
        "name": str(raw.get("name", "Unbekannt")).strip() or "Unbekannt",
        "ip": str(raw.get("ip", "")).strip(),
        "mac": str(raw.get("mac", "")).strip().lower(),
        "vendor": str(raw.get("vendor", "")).strip(),
        "device_type": str(raw.get("device_type", "other")).strip() or "other",
        "icon": str(raw.get("icon", "network")).strip() or "network",
        "online": bool(raw.get("online", False)),
        "ping_ms": raw.get("ping_ms"),
        "last_seen": raw.get("last_seen") or _now_iso(),
        "source": str(raw.get("source", source)).strip() or source,
    }


def _load_manual_devices() -> list[dict[str, Any]]:
    data = read_json(MANUAL_DEVICES_PATH, [])
    if not isinstance(data, list):
        return []
    return [normalize_device(item, source="manual") for item in data if isinstance(item, dict)]


def _load_discovered_devices() -> list[dict[str, Any]]:
    data = read_json(DISCOVERED_DEVICES_PATH, [])
    if not isinstance(data, list):
        return []
    return [normalize_device(item, source="scan") for item in data if isinstance(item, dict)]


def _save_manual_devices(items: list[dict[str, Any]]) -> None:
    write_json(MANUAL_DEVICES_PATH, items)


def _save_discovered_devices(items: list[dict[str, Any]]) -> None:
    write_json(DISCOVERED_DEVICES_PATH, items)


def list_devices(include_discovered: bool = True) -> list[dict[str, Any]]:
    manual = _load_manual_devices()

    if not include_discovered:
        return manual

    discovered = _load_discovered_devices()
    merged: dict[str, dict[str, Any]] = {}

    for item in discovered + manual:
        key = item.get("mac") or item.get("ip") or item.get("id")
        merged[key] = item

    return sorted(merged.values(), key=lambda d: d.get("name", "").lower())


def add_manual_device(raw: dict[str, Any]) -> dict[str, Any]:
    items = _load_manual_devices()
    item = normalize_device(raw, source="manual")
    items.append(item)
    _save_manual_devices(items)
    return item


def replace_manual_devices(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_device(item, source="manual") for item in items if isinstance(item, dict)]
    _save_manual_devices(normalized)
    return normalized


def update_manual_device(device_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    items = _load_manual_devices()

    for idx, item in enumerate(items):
        if item.get("id") == device_id:
            merged = {**item, **patch, "id": device_id, "source": "manual"}
            items[idx] = normalize_device(merged, source="manual")
            _save_manual_devices(items)
            return items[idx]

    return None


def delete_manual_device(device_id: str) -> bool:
    items = _load_manual_devices()
    filtered = [item for item in items if item.get("id") != device_id]
    if len(filtered) == len(items):
        return False

    _save_manual_devices(filtered)
    return True


def _run_command(command: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return ""
        return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def _scan_with_arp(timeout: int) -> list[dict[str, Any]]:
    output = _run_command(["arp", "-a"], timeout=timeout)
    devices: list[dict[str, Any]] = []

    for line in output.splitlines():
        ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
        mac_match = re.search(r"(([0-9a-f]{2}:){5}[0-9a-f]{2})", line.lower())

        if not ip_match:
            continue

        ip = ip_match.group(1)
        mac = mac_match.group(1) if mac_match else ""
        devices.append(
            normalize_device(
                {
                    "name": ip,
                    "ip": ip,
                    "mac": mac,
                    "online": True,
                    "device_type": "unknown",
                },
                source="scan",
            )
        )

    return devices


def _scan_with_nmap(network_cidr: str, timeout: int) -> list[dict[str, Any]]:
    output = _run_command(["nmap", "-sn", network_cidr], timeout=timeout)
    devices: list[dict[str, Any]] = []

    current_ip = ""
    for line in output.splitlines():
        line = line.strip()

        if line.startswith("Nmap scan report for"):
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)$", line)
            current_ip = match.group(1) if match else ""
            if current_ip:
                devices.append(
                    normalize_device(
                        {
                            "name": current_ip,
                            "ip": current_ip,
                            "online": True,
                            "device_type": "unknown",
                        },
                        source="scan",
                    )
                )

        if line.startswith("MAC Address:") and devices:
            mac_match = re.search(r"(([0-9A-F]{2}:){5}[0-9A-F]{2})", line)
            if mac_match:
                devices[-1]["mac"] = mac_match.group(1).lower()

    return devices


def run_discovery_scan() -> dict[str, Any]:
    settings = get_settings()
    device_settings = settings.get("devices", {})
    network_cidr = str(device_settings.get("network_cidr", "192.168.1.0/24"))
    methods = device_settings.get("scan_methods", ["arp"])
    timeout = int(device_settings.get("scan_timeout_sec", 2))

    if not isinstance(methods, list):
        methods = ["arp"]

    discovered: list[dict[str, Any]] = []
    used_methods: list[str] = []

    if "arp" in methods:
        arp_result = _scan_with_arp(timeout=timeout)
        if arp_result:
            used_methods.append("arp")
            discovered.extend(arp_result)

    if "nmap" in methods:
        nmap_result = _scan_with_nmap(network_cidr=network_cidr, timeout=max(timeout, 5))
        if nmap_result:
            used_methods.append("nmap")
            discovered.extend(nmap_result)

    # Deduplizieren anhand MAC oder IP
    deduped: dict[str, dict[str, Any]] = {}
    for item in discovered:
        key = item.get("mac") or item.get("ip") or item.get("id")
        deduped[key] = item

    result = sorted(deduped.values(), key=lambda d: d.get("ip", ""))
    _save_discovered_devices(result)

    return {
        "methods_requested": methods,
        "methods_used": used_methods,
        "network_cidr": network_cidr,
        "count": len(result),
        "items": result,
    }
