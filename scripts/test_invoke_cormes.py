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
                    "import os",
                    "import sys",
                    "argv_file = os.environ.get('CORMES_TEST_ARGV_FILE')",
                    "if argv_file:",
                    "    open(argv_file, 'w', encoding='utf-8').write('\\n'.join(sys.argv[1:]))",
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
        result, _ = self.run_wrapper_with_argv(*args, extra_env=extra_env)
        return result

    def run_wrapper_with_argv(
        self, *args: str, extra_env: dict[str, str] | None = None
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as fake_bin, tempfile.TemporaryDirectory() as state_dir:
            env = os.environ.copy()
            env["PATH"] = str(self.make_fake_hermes_bin(Path(fake_bin))) + os.pathsep + env.get("PATH", "")
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["CORMES_STATE_DIR"] = state_dir
            env["HERMES_HOME"] = str(Path(state_dir) / "missing-hermes-home")
            env["LOCALAPPDATA"] = str(Path(state_dir) / "local-app-data")
            env["HOME"] = state_dir
            env["USERPROFILE"] = state_dir
            argv_file = Path(state_dir) / "argv.txt"
            env["CORMES_TEST_ARGV_FILE"] = str(argv_file)
            if extra_env:
                env.update(extra_env)

            result = subprocess.run(
                [sys.executable, str(SCRIPT), *args],
                cwd=tempfile.gettempdir(),
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            argv = argv_file.read_text(encoding="utf-8").splitlines() if argv_file.exists() else []
            return result, argv

    def test_main_flow_normalizes_output_and_is_cwd_independent(self) -> None:
        result = self.run_wrapper("-Message", "hello")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=glm-5-turbo", result.stdout)
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

    def test_hermes_config_default_model_and_provider_are_used(self) -> None:
        with tempfile.TemporaryDirectory() as hermes_home:
            Path(hermes_home, "config.yaml").write_text(
                "model:\n  provider: zai\n  default: glm-5.1\n",
                encoding="utf-8",
            )
            result, argv = self.run_wrapper_with_argv("-Message", "hello", extra_env={"HERMES_HOME": hermes_home})

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=glm-5.1", result.stdout)
        self.assertIn("PROVIDER=zai", result.stdout)
        self.assertIn("-m", argv)
        self.assertIn("glm-5.1", argv)
        self.assertIn("--provider", argv)
        self.assertIn("zai", argv)

    def test_missing_or_empty_config_falls_back_to_hardcoded_default(self) -> None:
        with tempfile.TemporaryDirectory() as hermes_home:
            Path(hermes_home, "config.yaml").write_text("model:\n  default: ''\n", encoding="utf-8")
            result = self.run_wrapper("-Message", "hello", extra_env={"HERMES_HOME": hermes_home})

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=glm-5-turbo", result.stdout)

    def test_malformed_config_falls_back_to_hardcoded_default(self) -> None:
        with tempfile.TemporaryDirectory() as hermes_home:
            Path(hermes_home, "config.yaml").write_text("model: [\n", encoding="utf-8")
            result = self.run_wrapper("-Message", "hello", extra_env={"HERMES_HOME": hermes_home})

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=glm-5-turbo", result.stdout)

    def test_cached_model_takes_priority_over_hermes_config(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as hermes_home:
            Path(state_dir, "default-model.txt").write_text("cached-model|cached-provider", encoding="utf-8")
            Path(hermes_home, "config.yaml").write_text(
                "model:\n  provider: config-provider\n  default: config-model\n",
                encoding="utf-8",
            )
            result = self.run_wrapper(
                "-Message",
                "hello",
                extra_env={"CORMES_STATE_DIR": state_dir, "HERMES_HOME": hermes_home},
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=cached-model", result.stdout)
        self.assertIn("PROVIDER=cached-provider", result.stdout)

    def test_cli_model_and_provider_take_priority(self) -> None:
        with tempfile.TemporaryDirectory() as hermes_home:
            Path(hermes_home, "config.yaml").write_text(
                "model:\n  provider: config-provider\n  default: config-model\n",
                encoding="utf-8",
            )
            result, argv = self.run_wrapper_with_argv(
                "-Message",
                "hello",
                "-Model",
                "cli-model",
                "-Provider",
                "cli-provider",
                extra_env={"HERMES_HOME": hermes_home},
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=cli-model", result.stdout)
        self.assertIn("PROVIDER=cli-provider", result.stdout)
        self.assertIn("cli-model", argv)
        self.assertIn("cli-provider", argv)

    def test_message_model_and_provider_flags_take_priority(self) -> None:
        with tempfile.TemporaryDirectory() as hermes_home:
            Path(hermes_home, "config.yaml").write_text(
                "model:\n  provider: config-provider\n  default: config-model\n",
                encoding="utf-8",
            )
            result, argv = self.run_wrapper_with_argv(
                "-Message",
                "-m message-model -p message-provider hello",
                extra_env={"HERMES_HOME": hermes_home},
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=message-model", result.stdout)
        self.assertIn("PROVIDER=message-provider", result.stdout)
        self.assertIn("message-model", argv)
        self.assertIn("message-provider", argv)


if __name__ == "__main__":
    unittest.main()
