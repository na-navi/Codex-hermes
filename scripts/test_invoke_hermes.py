#!/usr/bin/env python3
"""Tests for scripts/invoke-hermes.py."""

from __future__ import annotations

import os
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "invoke-hermes.py"
FAKE_BIN = ROOT / "scripts" / ".state" / "test-bin"
SPEC = importlib.util.spec_from_file_location("invoke_hermes", SCRIPT)
assert SPEC and SPEC.loader
invoke_hermes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(invoke_hermes)


class InvokeHermesTests(unittest.TestCase):
    def run_wrapper(self, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = str(FAKE_BIN) + os.pathsep + env.get("PATH", "")
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["CODEX_HERMES_STATE_DIR"] = str(Path(tempfile.gettempdir()) / "codex-hermes-test-state")
        if extra_env:
            env.update(extra_env)

        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_main_flow_normalizes_output_and_is_cwd_independent(self) -> None:
        result = self.run_wrapper("-Message", "hello")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=grok-4.3", result.stdout)
        self.assertIn("SESSION_ID=test-session-123", result.stdout)
        self.assertIn("RESPONSE_BEGIN", result.stdout)
        self.assertIn("日本語OK", result.stdout)

    def test_resume_flow_uses_resume_session(self) -> None:
        result = self.run_wrapper("-Message", "follow up", "-Resume", "resume-123")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("SESSION_ID=test-session-123", result.stdout)
        self.assertIn("RESPONSE_BEGIN", result.stdout)
        self.assertIn("日本語OK", result.stdout)

    def test_lowercase_session_id_is_normalized_and_filtered_from_response(self) -> None:
        output = "Hello\n\nsession_id: 20260518_141939_5b855b"
        self.assertEqual(invoke_hermes.parse_session_id(output), "20260518_141939_5b855b")
        self.assertEqual(invoke_hermes.response_block(output), "Hello")


if __name__ == "__main__":
    unittest.main()
