#!/usr/bin/env python3
"""Tests for Afterburner's task notepad."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("notepad.py")


class NotepadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = Path(self.temporary.name) / "notepad.json"
        self.environment = {**os.environ, "AFTERBURNER_NOTEPAD": str(self.store)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_add_list_and_complete(self) -> None:
        added = self.run_cli("add", "Audit dependency boundaries", "--repo", self.temporary.name)
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertEqual(json.loads(added.stdout)["id"], 1)

        queued = self.run_cli("list", "--format", "json")
        self.assertEqual(len(json.loads(queued.stdout)["tasks"]), 1)

        completed = self.run_cli("done", "1")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(self.run_cli("list", "--format", "json").stdout)["tasks"], [])
        all_tasks = json.loads(self.run_cli("list", "--all", "--format", "json").stdout)["tasks"]
        self.assertEqual(all_tasks[0]["status"], "done")

    def test_rejects_empty_task_and_preserves_ids(self) -> None:
        empty = self.run_cli("add", "   ")
        self.assertEqual(empty.returncode, 2)
        added = json.loads(self.run_cli("add", "Useful task").stdout)
        self.assertEqual(added["id"], 1)


if __name__ == "__main__":
    unittest.main()
