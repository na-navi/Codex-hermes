#!/usr/bin/env python
"""Invoke Hermes CLI and normalize its output for the Codex Hermes skill."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_MODEL = "grok-4.3"
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]


def state_dir() -> Path:
    return Path(os.environ.get("CODEX_HERMES_STATE_DIR") or Path(tempfile.gettempdir()) / "codex-hermes")


def model_cache_path() -> Path:
    return state_dir() / "default-model.txt"


def read_cached_model() -> tuple[str | None, str]:
    path = model_cache_path()
    if not path.exists():
        return None, ""

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None, ""

    model, sep, provider = raw.partition("|")
    return model, provider if sep else ""


def write_cached_model(model: str, provider: str) -> None:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    value = f"{model}|{provider}" if provider else model
    model_cache_path().write_text(value, encoding="utf-8")


def split_message_flags(text: str) -> tuple[str, str | None, str | None, bool]:
    tokens = shlex.split(text, posix=False)
    remaining: list[str] = []
    model = None
    provider = None
    raw = False
    i = 0

    while i < len(tokens):
        token = tokens[i].strip("\"'")
        if token == "-m" and i + 1 < len(tokens):
            model = tokens[i + 1].strip("\"'")
            i += 2
        elif token == "-p" and i + 1 < len(tokens):
            provider = tokens[i + 1].strip("\"'")
            i += 2
        elif token == "--raw":
            raw = True
            i += 1
        else:
            remaining.append(tokens[i].strip("\"'"))
            i += 1

    return " ".join(remaining).strip(), model, provider, raw


def response_block(output: str) -> str:
    block = re.search(r"(?m)^\s*╭─[^\r\n]*╮\r?\n([\s\S]*?)^\s*╰─", output)
    if block:
        lines = block.group(1).splitlines()
        return "\n".join(re.sub(r"^\s{4}", "", line) for line in lines).strip()

    skip_patterns = [
        r"^Query:",
        r"^Initializing",
        r"^──+$",
        r"^Resume this",
        r"^\s+hermes --resume",
        r"^Session:\s",
        r"^session_id:\s",
        r"^Duration:\s",
        r"^Messages:\s",
        r"^\s*╭─",
        r"^\s*╰─",
    ]
    skip_re = re.compile("|".join(f"(?:{pattern})" for pattern in skip_patterns))
    filtered = [line for line in output.splitlines() if not skip_re.search(line)]
    text = "\n".join(filtered).strip()
    return text or output.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-Message", "--message", required=True)
    parser.add_argument("-Model", "--model")
    parser.add_argument("-Provider", "--provider")
    parser.add_argument("-Resume", "--resume")
    parser.add_argument("-Raw", "--raw", action="store_true")
    parser.add_argument(
        "--repo-root",
        default=os.environ.get("CODEX_HERMES_REPO_ROOT"),
        help="Override the repository root used for repo-local state and relative lookups.",
    )
    return parser.parse_args()


def parse_session_id(output: str) -> str | None:
    session_line = re.search(r"(?im)^(?:Session|session_id):\s*(\S+)", output)
    if session_line:
        return session_line.group(1)

    resume_match = re.search(r"hermes --resume (\S+)", output)
    if resume_match:
        return resume_match.group(1)

    return None


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    message = args.message
    model = args.model
    provider = args.provider
    raw = args.raw

    if not args.resume:
        message, parsed_model, parsed_provider, parsed_raw = split_message_flags(message)
        model = model or parsed_model
        provider = provider or parsed_provider
        raw = raw or parsed_raw

    if not message.strip():
        raise SystemExit("No Hermes message was provided.")

    cached_model, cached_provider = read_cached_model()
    model = model or cached_model or DEFAULT_MODEL
    provider = provider or cached_provider
    write_cached_model(model, provider or "")

    hermes = shutil.which("hermes")
    if not hermes:
        raise SystemExit("Hermes CLI was not found on PATH. Install and configure the `hermes` command first.")

    if args.resume:
        command = [hermes, "-z", message, "-m", model, "--resume", args.resume]
    else:
        command = [hermes, "chat", "-q", message, "-Q", "-m", model]

    if provider:
        command.extend(["--provider", provider])

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["CODEX_HERMES_REPO_ROOT"] = str(repo_root)

    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    text_output = (completed.stdout + completed.stderr).rstrip()
    if completed.returncode != 0:
        raise SystemExit(f"Hermes CLI failed with exit code {completed.returncode}:\n{text_output}")

    session_id = parse_session_id(text_output)
    if not session_id and args.resume:
        session_id = args.resume

    response = text_output if raw else response_block(text_output)
    print(f"MODEL={model}")
    if provider:
        print(f"PROVIDER={provider}")
    if session_id:
        print(f"SESSION_ID={session_id}")
    print("RESPONSE_BEGIN")
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
