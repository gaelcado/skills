#!/usr/bin/env python3
"""Manage Afterburner's persistent, agent-neutral task notepad."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def store_path() -> Path:
    override = os.environ.get("AFTERBURNER_NOTEPAD")
    if override:
        return Path(override).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".local" / "share"
    return base / "afterburner" / "notepad.json"


def empty_store() -> dict[str, Any]:
    return {"version": 1, "next_id": 1, "tasks": []}


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_store()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("unsupported notepad format")
    if not isinstance(payload.get("next_id"), int) or not isinstance(payload.get("tasks"), list):
        raise ValueError("invalid notepad structure")
    return payload


def save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".notepad-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def add_task(payload: dict[str, Any], task: str, repo: str | None, notes: str | None) -> dict[str, Any]:
    item = {
        "id": payload["next_id"],
        "task": task.strip(),
        "repo": str(Path(repo).expanduser().resolve()) if repo else None,
        "notes": notes.strip() if notes else None,
        "status": "queued",
        "created_at": now_iso(),
        "completed_at": None,
    }
    if not item["task"]:
        raise ValueError("task cannot be empty")
    payload["tasks"].append(item)
    payload["next_id"] += 1
    return item


def find_task(payload: dict[str, Any], task_id: int) -> dict[str, Any]:
    for item in payload["tasks"]:
        if item.get("id") == task_id:
            return item
    raise ValueError(f"task {task_id} not found")


def render_text(items: list[dict[str, Any]]) -> None:
    if not items:
        print("Afterburner notepad is empty.")
        return
    for item in items:
        marker = "x" if item["status"] == "done" else " "
        repo = f"  repo={item['repo']}" if item.get("repo") else ""
        print(f"[{marker}] {item['id']}: {item['task']}{repo}")
        if item.get("notes"):
            print(f"    {item['notes']}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="command", required=True)

    add = subcommands.add_parser("add", help="queue a task")
    add.add_argument("task")
    add.add_argument("--repo", help="repository associated with the task")
    add.add_argument("--notes", help="optional execution context")

    listing = subcommands.add_parser("list", help="list queued tasks")
    listing.add_argument("--all", action="store_true", help="include completed tasks")
    listing.add_argument("--format", choices=("text", "json"), default="text")

    done = subcommands.add_parser("done", help="mark a task complete")
    done.add_argument("id", type=int)
    return result


def main() -> int:
    args = parser().parse_args()
    path = store_path()
    try:
        payload = load(path)
        if args.command == "add":
            item = add_task(payload, args.task, args.repo, args.notes)
            save(path, payload)
            print(json.dumps(item, indent=2, sort_keys=True))
        elif args.command == "done":
            item = find_task(payload, args.id)
            item["status"] = "done"
            item["completed_at"] = now_iso()
            save(path, payload)
            print(f"Completed task {item['id']}: {item['task']}")
        else:
            items = payload["tasks"] if args.all else [
                item for item in payload["tasks"] if item.get("status") == "queued"
            ]
            if args.format == "json":
                print(json.dumps({"path": str(path), "tasks": items}, indent=2, sort_keys=True))
            else:
                render_text(items)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"afterburner notepad: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
