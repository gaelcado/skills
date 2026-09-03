#!/usr/bin/env python3
"""Read CodexBar quota windows and print a privacy-safe pacing summary."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_CLI = Path("/Applications/CodexBar.app/Contents/Helpers/CodexBarCLI")
SLOTS = ("primary", "secondary", "tertiary")


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def collect_windows(entry: dict[str, Any]) -> list[dict[str, Any]]:
    usage = entry.get("usage")
    if not isinstance(usage, dict):
        return []
    windows: list[dict[str, Any]] = []
    for slot in SLOTS:
        raw = usage.get(slot)
        if isinstance(raw, dict) and isinstance(raw.get("usedPercent"), (int, float)):
            windows.append({"id": slot, "title": slot, **raw})
    extras = usage.get("extraRateWindows")
    if isinstance(extras, list):
        for index, item in enumerate(extras):
            if not isinstance(item, dict) or not isinstance(item.get("window"), dict):
                continue
            raw = item["window"]
            if not isinstance(raw.get("usedPercent"), (int, float)):
                continue
            window_id = str(item.get("id") or f"extra-{index + 1}")
            windows.append(
                {
                    "id": window_id,
                    "title": str(item.get("title") or window_id),
                    **raw,
                }
            )
    return windows


def is_paceable(window: dict[str, Any]) -> bool:
    return (
        isinstance(window.get("resetsAt"), str)
        and isinstance(window.get("windowMinutes"), (int, float))
        and float(window["windowMinutes"]) > 0
    )


def choose_window(windows: list[dict[str, Any]], requested: str) -> dict[str, Any] | None:
    if requested != "auto":
        return next((window for window in windows if window["id"] == requested), None)
    paceable = [window for window in windows if is_paceable(window)]
    if paceable:
        return max(paceable, key=lambda window: float(window["windowMinutes"]))
    return windows[0] if windows else None


def summarize(entry: dict[str, Any], requested_window: str, now: datetime) -> dict[str, Any]:
    provider = str(entry.get("provider") or "unknown")
    if isinstance(entry.get("error"), dict):
        error = entry["error"]
        return {
            "provider": provider,
            "status": "error",
            "error_kind": str(error.get("kind") or "provider_error"),
        }

    window = choose_window(collect_windows(entry), requested_window)
    if window is None:
        return {"provider": provider, "status": "no_quota_window"}

    used = clamp(float(window["usedPercent"]))
    result: dict[str, Any] = {
        "provider": provider,
        "status": "ok",
        "window": str(window["id"]),
        "window_title": str(window["title"]),
        "used_percent": round(used, 4),
        "remaining_percent": round(100.0 - used, 4),
        "resets_at": window.get("resetsAt"),
        "reset_description": window.get("resetDescription"),
    }
    if not is_paceable(window):
        result["pace_status"] = "unavailable"
        return result

    reset = parse_time(window["resetsAt"])
    if reset <= now:
        result["pace_status"] = "unavailable"
        result["data_stale"] = True
        return result
    duration_seconds = float(window["windowMinutes"]) * 60.0
    remaining_seconds = max(0.0, (reset - now).total_seconds())
    time_remaining = clamp(100.0 * remaining_seconds / duration_seconds)
    expected_used = 100.0 - time_remaining
    surplus = expected_used - used
    result.update(
        {
            "pace_status": "available",
            "time_remaining_percent": round(time_remaining, 4),
            "expected_used_percent": round(expected_used, 4),
            "surplus_percent": round(surplus, 4),
            "has_surplus": surplus > 0,
        }
    )
    return result


def load_payload(args: argparse.Namespace) -> Any:
    if args.input:
        return json.loads(Path(args.input).read_text(encoding="utf-8"))
    executable = shutil.which("codexbar")
    if executable is None and APP_CLI.is_file():
        executable = str(APP_CLI)
    if executable is None:
        raise RuntimeError(
            "CodexBar CLI is not installed; see "
            "https://github.com/steipete/CodexBar/blob/main/docs/cli.md"
        )
    completed = subprocess.run(
        [executable, "usage", "--provider", args.provider, "--format", "json"],
        capture_output=True,
        text=True,
        timeout=args.timeout,
        check=False,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = f" (exit {completed.returncode})" if completed.returncode else ""
        raise RuntimeError(f"CodexBar returned invalid JSON{detail}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="codex", help="CodexBar provider name")
    parser.add_argument("--window", default="auto", help="auto, a standard slot, or extra-window ID")
    parser.add_argument("--timeout", type=float, default=30.0, help="CodexBar timeout in seconds")
    parser.add_argument("--input", help=argparse.SUPPRESS)
    parser.add_argument("--now", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = load_payload(args)
        entries = payload if isinstance(payload, list) else [payload]
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        summaries = [summarize(entry, args.window, now) for entry in entries if isinstance(entry, dict)]
        if not summaries:
            raise RuntimeError("CodexBar returned no provider entries")
        output: Any = summaries[0] if len(summaries) == 1 else {"providers": summaries}
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if any(item.get("status") == "ok" for item in summaries) else 1
    except (OSError, ValueError, TypeError, subprocess.SubprocessError, RuntimeError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
