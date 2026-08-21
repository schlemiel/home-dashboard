from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

TOPOLOGY_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "storage_topology.sh"


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, separator, raw_value = line.partition(":")
            if separator:
                parts = raw_value.strip().split()
                if parts and parts[0].isdigit():
                    values[key] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1] == "kB" else 1)
    except (OSError, UnicodeError):
        return {}
    return values


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def _device_uuid(source: str) -> str:
    try:
        result = subprocess.run(
            ["lsblk", "-no", "UUID", source],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")


def _storage_topology() -> list[dict[str, str]]:
    if not TOPOLOGY_SCRIPT.exists():
        return []
    try:
        result = subprocess.run(
            [str(TOPOLOGY_SCRIPT), "--json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        payload = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _block_device_for(source: str) -> dict[str, str]:
    fallback = {
        "name": Path(source).name or source,
        "type": "unknown",
        "transport": "n/a",
        "device_size": "",
    }
    try:
        result = subprocess.run(
            ["lsblk", "-P", "-o", "NAME,PATH,TYPE,TRAN,SIZE,MOUNTPOINT", source],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return fallback
    if not result.stdout.strip():
        return fallback
    try:
        values = {
            key: value
            for token in shlex.split(result.stdout.splitlines()[0])
            for key, value in [token.split("=", 1)]
        }
    except ValueError:
        return fallback
    return {
        "name": values.get("NAME", "") or fallback["name"],
        "type": values.get("TYPE", "") or fallback["type"],
        "transport": values.get("TRAN", "") or fallback["transport"],
        "device_size": values.get("SIZE", "") or fallback["device_size"],
    }


def _mounts() -> list[dict[str, Any]]:
    mounts: list[dict[str, Any]] = []
    try:
        lines = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return mounts

    seen: set[str] = set()
    for line in lines:
        try:
            source, target, filesystem, options, *_ = shlex.split(line)
        except ValueError:
            continue
        if (
            target in seen
            or not source.startswith("/dev/")
            or source.startswith(("/dev/loop", "/dev/ram", "/dev/zram"))
            or not os.path.exists(target)
        ):
            continue
        seen.add(target)
        usage = shutil.disk_usage(target)
        device = _block_device_for(source)
        mounts.append({
            "source": source,
            "uuid": _device_uuid(source),
            **device,
            "mountpoint": target,
            "filesystem": filesystem,
            "options": options,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total": _format_bytes(usage.total),
            "used": _format_bytes(usage.used),
            "free": _format_bytes(usage.free),
            "used_percent": round((usage.used / usage.total) * 100, 1) if usage.total else 0,
        })
    return sorted(mounts, key=lambda item: item["mountpoint"])


def get_system_overview() -> dict[str, Any]:
    memory = _read_meminfo()
    total_memory = memory.get("MemTotal", 0)
    available_memory = memory.get("MemAvailable", memory.get("MemFree", 0))
    used_memory = max(total_memory - available_memory, 0)
    try:
        load_average = os.getloadavg()
    except OSError:
        load_average = (0.0, 0.0, 0.0)

    return {
        "hostname": os.uname().nodename,
        "cpu_count": os.cpu_count() or 0,
        "load_average": [round(value, 2) for value in load_average],
        "memory": {
            "total_bytes": total_memory,
            "used_bytes": used_memory,
            "available_bytes": available_memory,
            "total": _format_bytes(total_memory),
            "used": _format_bytes(used_memory),
            "available": _format_bytes(available_memory),
            "used_percent": round((used_memory / total_memory) * 100, 1) if total_memory else 0,
        },
        "mounts": _mounts(),
        "storage_topology": _storage_topology(),
    }