from __future__ import annotations

import subprocess
from typing import Any

from services.storage import ROOT_DIR


def _run_git(args: list[str]) -> dict[str, Any]:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    return {
        "ok": process.returncode == 0,
        "returncode": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip(),
    }


def git_status() -> dict[str, Any]:
    return _run_git(["status", "--short"])


def git_commit_all(message: str) -> dict[str, Any]:
    add_result = _run_git(["add", "backend/config", "data"])
    if not add_result["ok"]:
        return {"ok": False, "step": "add", "result": add_result}

    commit_result = _run_git(["commit", "-m", message])
    if not commit_result["ok"] and "nothing to commit" in commit_result["stderr"].lower():
        return {"ok": True, "step": "commit", "result": commit_result, "noop": True}

    return {
        "ok": commit_result["ok"],
        "step": "commit",
        "result": commit_result,
    }


def git_push(remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
    args = ["push", remote]
    if branch:
        args.append(branch)
    return _run_git(args)


def git_pull(remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
    args = ["pull", remote]
    if branch:
        args.append(branch)
    return _run_git(args)
