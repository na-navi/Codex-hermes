#!/usr/bin/env python3
"""Tests for scripts/invoke-cormes.py."""

from __future__ import annotations

import json
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

    def test_doctor_accepts_no_message_and_emits_json(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            env = os.environ.copy()
            env["PATH"] = ""
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            env["CORMES_STATE_DIR"] = str(Path(home_dir) / "missing-state")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--doctor"],
                cwd=home_dir,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["tool"], "cormes-doctor")
        self.assertEqual(report["mode"], "read_only")
        self.assertIn("summary", report)
        self.assertIsInstance(report["items"], list)

    def test_normal_mode_still_requires_message(self) -> None:
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No Cormes message was provided.", result.stderr)

    def test_doctor_does_not_execute_hermes(self) -> None:
        with tempfile.TemporaryDirectory() as fake_bin, tempfile.TemporaryDirectory() as home_dir:
            argv_file = Path(home_dir) / "argv.txt"
            env = os.environ.copy()
            env["PATH"] = str(self.make_fake_hermes_bin(Path(fake_bin)))
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            env["CORMES_STATE_DIR"] = str(Path(home_dir) / "missing-state")
            env["CORMES_TEST_ARGV_FILE"] = str(argv_file)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--doctor"],
                cwd=home_dir,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertFalse(argv_file.exists())

    def test_doctor_does_not_create_model_cache_or_state_dir(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            state_dir = Path(home_dir) / "state-was-not-created"
            env = os.environ.copy()
            env["PATH"] = ""
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            env["CORMES_STATE_DIR"] = str(state_dir)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--doctor"],
                cwd=home_dir,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertFalse(state_dir.exists())
            self.assertFalse((state_dir / "default-model.txt").exists())

    def test_doctor_redacts_home_and_does_not_report_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            codex_dir = Path(home_dir) / ".codex"
            codex_dir.mkdir()
            Path(codex_dir, "config.toml").write_text("token = 'raw-secret-from-config'\n", encoding="utf-8")
            workspace = Path(home_dir) / "workspace"
            workspace.mkdir()
            env = os.environ.copy()
            env["PATH"] = ""
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            env["CORMES_STATE_DIR"] = str(Path(home_dir) / "state")
            env["CORMES_TEST_TOKEN"] = "raw-secret-from-env"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--doctor"],
                cwd=workspace,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn(home_dir, result.stdout)
        self.assertNotIn("raw-secret-from-config", result.stdout)
        self.assertNotIn("raw-secret-from-env", result.stdout)
        report = json.loads(result.stdout)
        details = "\n".join(item["detail"] for item in report["items"])
        self.assertIn("~", details)

    def test_doctor_redacts_absolute_workspace_path_outside_home(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as workspace_dir:
            env = os.environ.copy()
            env["PATH"] = ""
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--doctor"],
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn(workspace_dir, result.stdout)
        self.assertNotIn(str(ROOT), result.stdout)
        report = json.loads(result.stdout)
        cwd_item = next(item for item in report["items"] if item["key"] == "cwd")
        script_item = next(item for item in report["items"] if item["key"] == "script.path")
        self.assertEqual(cwd_item["detail"], f"<absolute-path>{os.sep}{Path(workspace_dir).name}")
        self.assertEqual(script_item["detail"], f"<absolute-path>{os.sep}{SCRIPT.name}")

    def test_doctor_health_fail_still_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            env = os.environ.copy()
            env["PATH"] = ""
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--doctor"],
                cwd=home_dir,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["summary"]["status"], "fail")
        self.assertTrue(any(item["key"] == "hermes.which" and item["status"] == "fail" for item in report["items"]))

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

    def test_home_hermes_config_path_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            config_dir = Path(home_dir, ".hermes")
            config_dir.mkdir()
            Path(config_dir, "config.yaml").write_text(
                "model:\n  provider: home-provider\n  default: home-model\n",
                encoding="utf-8",
            )
            result = self.run_wrapper(
                "-Message",
                "hello",
                extra_env={
                    "HERMES_HOME": "",
                    "LOCALAPPDATA": "",
                    "HOME": home_dir,
                    "USERPROFILE": home_dir,
                },
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=home-model", result.stdout)
        self.assertIn("PROVIDER=home-provider", result.stdout)

    def test_model_key_alias_is_used_when_default_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as hermes_home:
            Path(hermes_home, "config.yaml").write_text(
                "model:\n  provider: zai\n  model: glm-5.1\n",
                encoding="utf-8",
            )
            result = self.run_wrapper("-Message", "hello", extra_env={"HERMES_HOME": hermes_home})

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL=glm-5.1", result.stdout)
        self.assertIn("PROVIDER=zai", result.stdout)

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
