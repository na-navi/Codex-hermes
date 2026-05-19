#!/usr/bin/env python3
"""Tests for scripts/invoke-cormes.py."""

from __future__ import annotations

import os
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "invoke-cormes.py"
SPEC = importlib.util.spec_from_file_location("invoke_cormes", SCRIPT)
assert SPEC and SPEC.loader
invoke_cormes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(invoke_cormes)


class InvokeCormesTests(unittest.TestCase):
    def make_fake_hermes_bin(self, directory: Path) -> Path:
        script = directory / "fake_hermes.py"
        script.write_text(
            "\n".join(
                [
                    "print('Query: test')",
                    "print('Initializing agent...')",
                    "print('╭─ Hermes ─╮')",
                    "print('    日本語OK')",
                    "print('    line2')",
                    "print('╰────────╯')",
                    "print('Session:        test-session-123')",
                ]
            ),
            encoding="utf-8",
        )

        if os.name == "nt":
            launcher = directory / "hermes.cmd"
            launcher.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
        else:
            launcher = directory / "hermes"
            launcher.write_text(f'#! /bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
            launcher.chmod(0o755)

        return directory

    def run_wrapper(self, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as fake_bin:
            env = os.environ.copy()
            env["PATH"] = str(self.make_fake_hermes_bin(Path(fake_bin))) + os.pathsep + env.get("PATH", "")
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["CORMES_STATE_DIR"] = str(Path(tempfile.gettempdir()) / "cormes-test-state")
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
        self.assertEqual(invoke_cormes.parse_session_id(output), "20260518_141939_5b855b")
        self.assertEqual(invoke_cormes.response_block(output), "Hello")

    def test_legacy_state_dir_env_is_still_supported(self) -> None:
        env = {"CORMES_STATE_DIR": "", "CODEX_HERMES_STATE_DIR": str(Path(tempfile.gettempdir()) / "legacy-cormes-state")}
        result = self.run_wrapper("-Message", "hello", extra_env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("RESPONSE_BEGIN", result.stdout)

    def test_legacy_repo_root_env_is_still_supported(self) -> None:
        env = {"CORMES_REPO_ROOT": "", "CODEX_HERMES_REPO_ROOT": str(ROOT)}
        result = self.run_wrapper("-Message", "hello", extra_env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("RESPONSE_BEGIN", result.stdout)


if __name__ == "__main__":
    unittest.main()
