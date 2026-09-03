#!/usr/bin/env python3
"""Explainable Git-based entropy audit for agent-facing Markdown."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    tomllib = None


ENTRYPOINTS = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "CODEX.md", "CONTEXT.md",
    "MEMORY.md", "SKILL.md",
}
IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build",
    ".next", ".cache", "coverage", "__pycache__", ".venv", "venv",
}
AGENTIC_DIR_PARTS = {"agents", ".agents", ".claude", "skills", "prompts", "instructions"}
LINK_RE = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)")
CODE_RE = re.compile(r"`([^`\n]+)`")


@dataclass
class GitInfo:
    timestamp: int | None
    commits_after: int
    dirty: bool


def run_git(root: Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return proc.stdout if proc.returncode == 0 else None


def repo_root(path: Path) -> Path:
    result = run_git(path, "rev-parse", "--show-toplevel")
    return Path(result.strip()).resolve() if result else path.resolve()


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_config(root: Path) -> dict[str, Any]:
    config_path = root / ".ouroboros.toml"
    if not config_path.exists():
        return {}
    if tomllib is None:
        raise RuntimeError(".ouroboros.toml requires Python 3.11+")
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def excluded(path: Path, root: Path, patterns: list[str]) -> bool:
    relative = path.relative_to(root)
    return any(part in IGNORED_DIRS for part in relative.parts) or any(
        fnmatch.fnmatch(relative.as_posix(), pattern) for pattern in patterns
    )


def is_agentic(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    directories = {part.lower() for part in relative.parts[:-1]}
    posix = relative.as_posix().lower()
    return (
        path.name in ENTRYPOINTS
        or bool(directories & AGENTIC_DIR_PARTS)
        or posix.startswith(".github/instructions/")
        or posix.startswith("docs/agents/")
    )


def discover_docs(root: Path, config: dict[str, Any], requested: list[str]) -> list[Path]:
    if requested:
        docs = [(root / item).resolve() for item in requested]
        outside = []
        for path in docs:
            try:
                path.relative_to(root)
            except ValueError:
                outside.append(str(path))
        if outside:
            raise ValueError("document is outside repository: " + ", ".join(outside))
        missing = [relpath(path, root) for path in docs if not path.is_file()]
        if missing:
            raise ValueError("document not found: " + ", ".join(missing))
        return sorted(set(docs))

    discovery = config.get("discovery", {})
    excludes = list(discovery.get("exclude", []))
    docs = {
        path.resolve() for path in root.rglob("*.md")
        if not excluded(path, root, excludes) and is_agentic(path, root)
    }
    for pattern in discovery.get("include", []):
        docs.update(
            path.resolve() for path in root.glob(pattern)
            if path.is_file() and path.suffix.lower() == ".md" and not excluded(path, root, excludes)
        )
    return sorted(docs)


def strip_reference(raw: str) -> str:
    value = unquote(raw.strip()).split("#", 1)[0].split("?", 1)[0]
    if value.startswith("file://"):
        value = value[7:]
    return value.rstrip(".,:;")


def resolve_reference(raw: str, source: Path, root: Path) -> Path | None:
    value = strip_reference(raw)
    if not value or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return None
    candidate = root / value.lstrip("/") if value.startswith("/") else source.parent / value
    if not candidate.exists() and not value.startswith("/"):
        root_candidate = root / value
        if root_candidate.exists():
            candidate = root_candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def pathish(value: str) -> bool:
    if not value or any(char in value for char in "\n\t*{}<>"):
        return False
    return "/" in value or bool(re.search(r"\.[A-Za-z0-9_-]{1,12}$", value))


def references(source: Path, root: Path) -> list[Path]:
    text = source.read_text(encoding="utf-8", errors="replace")
    found = {
        resolved
        for left, right in LINK_RE.findall(text)
        if (resolved := resolve_reference(left or right, source, root)) and resolved != source
    }
    # Inline code is often an illustrative filename. Count it only when it resolves
    # to an existing local path; explicit Markdown links still surface breakage.
    for raw in CODE_RE.findall(text):
        if pathish(strip_reference(raw)):
            resolved = resolve_reference(raw, source, root)
            if resolved and resolved.exists() and resolved != source:
                found.add(resolved)
    return sorted(found)


def dirty_paths(root: Path) -> set[str]:
    output = run_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all") or ""
    values = output.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(values):
        item = values[index]
        if not item:
            break
        status, path = item[:2], item[3:]
        paths.add(path)
        if status[0] in {"R", "C"} and index + 1 < len(values):
            index += 1
            paths.add(values[index])
        index += 1
    return paths


def path_is_dirty(relative: str, dirty: set[str]) -> bool:
    prefix = relative.rstrip("/") + "/"
    return relative in dirty or any(item.startswith(prefix) for item in dirty)


def git_timestamp(root: Path, relative: str) -> int | None:
    output = run_git(root, "log", "-1", "--format=%ct", "--", relative)
    return int(output.strip()) if output and output.strip().isdigit() else None


def git_info(root: Path, path: Path, dirty: set[str], after: int | None = None) -> GitInfo:
    relative = relpath(path, root)
    timestamp = git_timestamp(root, relative)
    commits_after = 0
    if after is not None:
        output = run_git(root, "log", "--format=%ct", "--", relative) or ""
        commits_after = sum(1 for value in output.splitlines() if value.isdigit() and int(value) > after)
    return GitInfo(timestamp, commits_after, path_is_dirty(relative, dirty))


def score_label(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 40:
        return "stale"
    if score >= 15:
        return "watch"
    return "low"


def score_edge(root: Path, source: Path, target: Path, dirty: set[str]) -> dict[str, Any]:
    source_info = git_info(root, source, dirty)
    result: dict[str, Any] = {
        "source": relpath(source, root), "target": relpath(target, root), "points": {},
    }
    if not target.exists():
        result.update(score=100, label="critical", points={"missing": 100})
        return result

    target_info = git_info(root, target, dirty, source_info.timestamp)
    lag_days = 0
    if source_info.timestamp is not None and target_info.timestamp is not None:
        lag_days = max(0, (target_info.timestamp - source_info.timestamp) // 86400)
    lag_points = min(60, (lag_days // 7) * 5)
    commit_points = min(30, target_info.commits_after * 6)
    dirty_points = 10 if target_info.dirty and not source_info.dirty else 0
    points = {"lag": lag_points, "commits": commit_points, "dirty": dirty_points}
    score = min(100, sum(points.values()))
    result.update(
        score=score, label=score_label(score), points=points, lag_days=lag_days,
        commits_after_source=target_info.commits_after,
    )
    return result


def case_of(stem: str) -> str | None:
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", stem):
        return "kebab-case"
    if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", stem):
        return "snake_case"
    if re.fullmatch(r"[a-z][A-Za-z0-9]*", stem) and re.search(r"[A-Z]", stem):
        return "camelCase"
    return None


def detect_case(docs: Iterable[Path], configured: str | None, root: Path) -> tuple[str, list[dict[str, str]]]:
    candidates = [doc for doc in docs if doc.name not in ENTRYPOINTS]
    counts = Counter(case_of(doc.stem) for doc in candidates)
    counts.pop(None, None)
    convention = configured or (counts.most_common(1)[0][0] if counts else "kebab-case")
    violations = []
    for doc in candidates:
        actual = case_of(doc.stem)
        if actual != convention:
            violations.append({
                "path": relpath(doc, root), "actual": actual or "unclassified", "expected": convention,
            })
    return convention, violations


def audit(root: Path, config: dict[str, Any], requested: list[str]) -> dict[str, Any]:
    root = repo_root(root)
    docs = discover_docs(root, config, requested)
    dirty = dirty_paths(root)
    edges = [score_edge(root, doc, target, dirty) for doc in docs for target in references(doc, root)]
    by_doc = []
    for doc in docs:
        doc_edges = [edge for edge in edges if edge["source"] == relpath(doc, root)]
        by_doc.append({
            "path": relpath(doc, root), "references": len(doc_edges),
            "score": round(sum(edge["score"] for edge in doc_edges) / len(doc_edges)) if doc_edges else None,
        })
    configured_case = config.get("conventions", {}).get("markdown_case")
    if configured_case not in {None, "kebab-case", "snake_case", "camelCase"}:
        raise ValueError(f"unsupported conventions.markdown_case: {configured_case}")
    convention, violations = detect_case(docs, configured_case, root)
    overall = round(sum(edge["score"] for edge in edges) / len(edges)) if edges else 0
    return {
        "root": str(root), "git_history": run_git(root, "rev-parse", "--is-inside-work-tree") is not None,
        "convention": {"markdown_case": convention, "source": "config" if configured_case else "detected"},
        "summary": {"score": overall, "label": score_label(overall), "documents": len(docs), "edges": len(edges)},
        "documents": by_doc, "edges": sorted(edges, key=lambda item: item["score"], reverse=True),
        "case_violations": violations,
    }


def print_text(report: dict[str, Any], plan: bool = False) -> None:
    summary = report["summary"]
    print(f"Ouroboros: {summary['score']}/100 ({summary['label']})")
    print(f"Documents: {summary['documents']}  References: {summary['edges']}")
    convention = report["convention"]
    print(f"Markdown case: {convention['markdown_case']} ({convention['source']})")
    noteworthy = [edge for edge in report["edges"] if edge["score"] >= 15]
    if noteworthy:
        print("\nReview queue:")
        for edge in noteworthy:
            why = ", ".join(f"{key}={value}" for key, value in edge["points"].items() if value)
            print(f"  [{edge['score']:3}] {edge['source']} -> {edge['target']} ({why})")
    missing = [edge for edge in report["edges"] if "missing" in edge["points"]]
    if missing:
        print("\nBroken references:")
        for edge in missing:
            print(f"  {edge['source']} -> {edge['target']}")
    if report["case_violations"]:
        print("\nCase violations:")
        for item in report["case_violations"]:
            print(f"  {item['path']} ({item['actual']}; expected {item['expected']})")
    if plan:
        print("\nNon-mutating repair plan:")
        for edge in noteworthy:
            print(f"  - Review {edge['source']} against {edge['target']}; update only stale claims.")
        for item in report["case_violations"]:
            print(f"  - Consider renaming {item['path']} to {item['expected']} and repair inbound links.")
        if not noteworthy and not report["case_violations"]:
            print("  - No score-driven repairs proposed.")


def init_config(root: Path, case: str) -> int:
    path = repo_root(root) / ".ouroboros.toml"
    if path.exists():
        print(f"Refusing to overwrite {path}", file=sys.stderr)
        return 2
    path.write_text(f'[conventions]\nmarkdown_case = "{case}"\n', encoding="utf-8")
    print(f"Created {path}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for name, help_text in (("check", "report entropy"), ("plan", "report non-mutating repair suggestions")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("root", nargs="?", default=".")
        command.add_argument("--doc", action="append", default=[], help="repository-relative Markdown path")
        command.add_argument("--format", choices=("text", "json"), default="text")
    init = sub.add_parser("init", help="create .ouroboros.toml without changing documents")
    init.add_argument("root", nargs="?", default=".")
    init.add_argument("--case", choices=("kebab-case", "snake_case", "camelCase"), required=True)
    return result


def main() -> int:
    args = make_parser().parse_args()
    root = Path(args.root).resolve()
    if args.command == "init":
        return init_config(root, args.case)
    try:
        report = audit(root, load_config(repo_root(root)), args.doc)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ouroboros: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report, plan=args.command == "plan")
    return 1 if any("missing" in edge["points"] for edge in report["edges"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
