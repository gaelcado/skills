#!/usr/bin/env python3
"""Deterministic tests for read_quota.py."""

from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("read_quota.py")
SPEC = importlib.util.spec_from_file_location("read_quota", MODULE_PATH)
assert SPEC and SPEC.loader
read_quota = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(read_quota)


class ReadQuotaTests(unittest.TestCase):
    NOW = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)

    def test_auto_chooses_longest_paceable_window_and_calculates_surplus(self) -> None:
        entry = {
            "provider": "example",
            "usage": {
                "primary": {
                    "usedPercent": 30,
                    "resetsAt": "2026-01-05T18:00:00Z",
                    "windowMinutes": 720,
                },
                "secondary": {
                    "usedPercent": 40,
                    "resetsAt": "2026-01-08T12:00:00Z",
                    "windowMinutes": 10080,
                },
            },
        }
        result = read_quota.summarize(entry, "auto", self.NOW)
        self.assertEqual(result["window"], "secondary")
        self.assertEqual(result["time_remaining_percent"], 42.8571)
        self.assertEqual(result["surplus_percent"], 17.1429)
        self.assertTrue(result["has_surplus"])

    def test_unbounded_window_never_claims_surplus(self) -> None:
        entry = {"provider": "example", "usage": {"primary": {"usedPercent": 12}}}
        result = read_quota.summarize(entry, "auto", self.NOW)
        self.assertEqual(result["pace_status"], "unavailable")
        self.assertNotIn("surplus_percent", result)

    def test_provider_error_does_not_echo_message(self) -> None:
        entry = {
            "provider": "example",
            "error": {"kind": "auth", "message": "secret account detail"},
        }
        result = read_quota.summarize(entry, "auto", self.NOW)
        self.assertEqual(result, {"provider": "example", "status": "error", "error_kind": "auth"})

    def test_expired_window_never_claims_surplus(self) -> None:
        entry = {
            "provider": "example",
            "usage": {
                "primary": {
                    "usedPercent": 10,
                    "resetsAt": "2026-01-05T11:00:00Z",
                    "windowMinutes": 300,
                }
            },
        }
        result = read_quota.summarize(entry, "auto", self.NOW)
        self.assertEqual(result["pace_status"], "unavailable")
        self.assertTrue(result["data_stale"])
        self.assertNotIn("surplus_percent", result)

    def test_named_extra_window_is_supported(self) -> None:
        entry = {
            "provider": "example",
            "usage": {
                "extraRateWindows": [
                    {
                        "id": "monthly",
                        "title": "Monthly",
                        "window": {
                            "usedPercent": 80,
                            "resetsAt": "2026-01-20T12:00:00Z",
                            "windowMinutes": 43200,
                        },
                    }
                ]
            },
        }
        result = read_quota.summarize(entry, "monthly", self.NOW)
        self.assertEqual(result["window"], "monthly")
        self.assertFalse(result["has_surplus"])

    def test_missing_codexbar_points_to_installation_guide(self) -> None:
        args = SimpleNamespace(input=None, provider="codex", timeout=1)
        with (
            patch.object(read_quota.shutil, "which", return_value=None),
            patch.object(read_quota, "APP_CLI", Path("/missing/CodexBarCLI")),
        ):
            with self.assertRaisesRegex(RuntimeError, r"github\.com/steipete/CodexBar/.*/cli\.md"):
                read_quota.load_payload(args)


if __name__ == "__main__":
    unittest.main()
