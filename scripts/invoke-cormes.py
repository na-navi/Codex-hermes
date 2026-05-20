#!/usr/bin/env python
"""Invoke Hermes CLI and normalize its output for the Cormes skill."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_MODEL = "glm-5-turbo"
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
DOCTOR_ENV_OVERRIDES = [
    "CORMES_STATE_DIR",
    "CODEX_HERMES_STATE_DIR",
    "CORMES_REPO_ROOT",
    "CODEX_HERMES_REPO_ROOT",
    "HERMES_HOME",
]


class CormesArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def state_dir() -> Path:
    return Path(
        os.environ.get("CORMES_STATE_DIR")
        or os.environ.get("CODEX_HERMES_STATE_DIR")
        or Path(tempfile.gettempdir()) / "cormes"
    )


def model_cache_path() -> Path:
    return state_dir() / "default-model.txt"


def redaction_roots() -> list[str]:
    roots: list[str] = []
    for value in (os.environ.get("USERPROFILE"), os.environ.get("HOME"), str(Path.home())):
        if value and value not in roots:
            roots.append(value)
    return sorted(roots, key=len, reverse=True)


def redact_path(value: str | Path) -> str:
    text = str(value)
    try:
        normalized_text = os.path.normpath(text)
    except OSError:
        return "<unprintable-path>"

    for root in redaction_roots():
        normalized_root = os.path.normpath(root)
        text_key = os.path.normcase(normalized_text)
        root_key = os.path.normcase(normalized_root)
        if text_key == root_key:
            return "~"
        if text_key.startswith(root_key + os.sep):
            suffix = normalized_text[len(normalized_root) :].lstrip("\\/")
            return "~" + os.sep + suffix
    if os.path.isabs(normalized_text):
        name = os.path.basename(normalized_text.rstrip("\\/"))
        return f"<absolute-path>{os.sep}{name}" if name else "<absolute-path>"
    return text


def doctor_item(status: str, category: str, key: str, detail: str) -> dict[str, str]:
    return {"status": status, "category": category, "key": key, "detail": detail}


def is_readable_dir(path: Path) -> bool:
    try:
        with os.scandir(path):
            return True
    except OSError:
        return False


def add_path_item(items: list[dict[str, str]], category: str, key: str, path: Path) -> None:
    items.append(doctor_item("pass", category, key, redact_path(path)))


def add_dir_health(items: list[dict[str, str]], category: str, key: str, path: Path, missing_status: str = "warn") -> None:
    redacted = redact_path(path)
    if not path.exists():
        items.append(doctor_item(missing_status, category, key, f"{redacted} does not exist."))
        return
    if not path.is_dir():
        items.append(doctor_item("fail", category, key, f"{redacted} exists but is not a directory."))
        return
    if is_readable_dir(path):
        items.append(doctor_item("pass", category, key, f"{redacted} exists and is readable."))
    else:
        items.append(doctor_item("warn", category, key, f"{redacted} exists but was not readable."))


def which_detail(executable: str) -> tuple[str, str]:
    found = shutil.which(executable)
    if found:
        return "pass", f"Found at {redact_path(found)}."
    return "fail", f"{executable} executable was not found on PATH."


def sensitive_env_count() -> int:
    pattern = re.compile(r"(TOKEN|KEY|AUTH|SECRET)", re.IGNORECASE)
    return sum(1 for name, value in os.environ.items() if value and pattern.search(name))


def doctor_summary(items: list[dict[str, str]]) -> dict[str, str]:
    statuses = {item["status"] for item in items}
    if "fail" in statuses:
        status = "fail"
    elif "warn" in statuses:
        status = "warn"
    elif "pass" in statuses:
        status = "pass"
    else:
        status = "unknown"

    recommended_next_step = "No immediate action from the read-only doctor report."
    for item in items:
        if item["key"] == "hermes.which" and item["status"] == "fail":
            recommended_next_step = "Check Hermes CLI installation because the executable was not found on PATH."
            break
        if item["key"] == "plugin.root" and item["status"] == "fail":
            recommended_next_step = "Verify the Cormes repository or plugin installation because required plugin files are missing."
            break
        if item["key"] == "codex.home" and item["status"] == "warn":
            recommended_next_step = "Open Codex App once or verify the Codex home directory because ~/.codex was not found."
            break

    return {"status": status, "recommended_next_step": recommended_next_step}


def build_doctor_report(repo_root: Path) -> dict[str, object]:
    items: list[dict[str, str]] = []
    cwd = Path.cwd()
    codex_home = Path.home() / ".codex"
    state = state_dir()

    items.append(doctor_item("pass", "runtime", "os.platform", platform.platform()))
    items.append(doctor_item("pass", "runtime", "python.version", platform.python_version()))
    add_path_item(items, "runtime", "python.executable", Path(sys.executable))
    add_path_item(items, "runtime", "cwd", cwd)
    items.append(
        doctor_item(
            "pass",
            "runtime",
            "shell.env",
            f"SHELL={'set' if os.environ.get('SHELL') else 'unset'}; ComSpec={'set' if os.environ.get('ComSpec') else 'unset'}",
        )
    )

    node_status, node_detail = which_detail("node")
    items.append(doctor_item(node_status, "dependency", "node.which", node_detail))
    hermes_status, hermes_detail = which_detail("hermes")
    items.append(doctor_item(hermes_status, "dependency", "hermes.which", hermes_detail))

    add_path_item(items, "plugin", "script.path", SCRIPT_PATH)
    required_plugin_files = [repo_root / "scripts" / "invoke-cormes.py", repo_root / "skills" / "cormes" / "SKILL.md"]
    if all(path.exists() for path in required_plugin_files):
        items.append(doctor_item("pass", "plugin", "plugin.root", f"{redact_path(repo_root)} contains required Cormes files."))
    else:
        items.append(doctor_item("fail", "plugin", "plugin.root", f"{redact_path(repo_root)} is missing required Cormes files."))
    add_path_item(items, "plugin", "state.dir.path", state)
    add_dir_health(items, "plugin", "state.dir", state, missing_status="warn")

    for name in DOCTOR_ENV_OVERRIDES:
        value = os.environ.get(name)
        detail = f"set: {redact_path(value)}" if value else "unset"
        items.append(doctor_item("pass", "environment", name.lower(), detail))
    count = sensitive_env_count()
    detail = f"{count} sensitive-looking environment variable(s) are set; values are not reported."
    items.append(doctor_item("pass", "environment", "sensitive.values", detail))

    add_dir_health(items, "codex", "codex.home", codex_home, missing_status="warn")
    add_dir_health(items, "codex", "codex.plugins", codex_home / "plugins", missing_status="warn")
    add_dir_health(items, "codex", "codex.plugins.cormes", codex_home / "plugins" / "cormes", missing_status="warn")
    for config_name in ("config.toml", "config.json"):
        config_path = codex_home / config_name
        status = "pass" if config_path.exists() else "unknown"
        detail = f"{redact_path(config_path)} exists." if config_path.exists() else f"{redact_path(config_path)} was not found."
        items.append(doctor_item(status, "codex", f"codex.{config_name}.exists", detail))

    items.append(doctor_item("unknown", "workspace", "workspace.writeability", "Not tested because --doctor is read-only."))
    items.append(doctor_item("unknown", "codex", "sandbox.acl", "Not diagnosed because --doctor avoids definitive sandbox or ACL claims."))
    items.append(doctor_item("unknown", "privacy", "auth.session.contents", "Not inspected because --doctor does not read auth, session, or log contents."))
    items.append(doctor_item("unknown", "dependency", "hermes.runtime", "Not tested because --doctor does not execute Hermes."))

    return {
        "schema_version": 1,
        "tool": "cormes-doctor",
        "mode": "read_only",
        "summary": doctor_summary(items),
        "items": items,
    }


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


def hermes_config_paths() -> list[Path]:
    paths: list[Path] = []
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        paths.append(Path(hermes_home) / "config.yaml")

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        paths.append(Path(user_profile) / ".hermes" / "config.yaml")

    paths.append(Path.home() / ".hermes" / "config.yaml")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        paths.append(Path(local_app_data) / "hermes" / "config.yaml")

    paths.append(Path.home() / ".config" / "hermes" / "config.yaml")

    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def clean_yaml_scalar(value: str) -> str:
    value = value.strip()
    if "#" in value and not value.startswith(("'", '"')):
        value = value.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def parse_hermes_model_config(text: str) -> tuple[str | None, str]:
    in_model = False
    model_indent = 0
    values: dict[str, str] = {}

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        model_match = re.match(r"^model\s*:\s*(.*)$", line)
        if model_match:
            trailing = clean_yaml_scalar(model_match.group(1))
            if trailing and trailing != "{}":
                return None, ""
            in_model = True
            model_indent = indent
            continue

        if not in_model:
            continue

        if indent <= model_indent:
            break

        field_match = re.match(r"^\s+(default|model|provider)\s*:\s*(.*?)\s*$", line)
        if field_match:
            values[field_match.group(1)] = clean_yaml_scalar(field_match.group(2))

    return values.get("default") or values.get("model") or None, values.get("provider", "")


def read_hermes_default_model() -> tuple[str | None, str]:
    for path in hermes_config_paths():
        try:
            if not path.exists():
                continue
            model, provider = parse_hermes_model_config(path.read_text(encoding="utf-8"))
            if model:
                return model, provider
        except OSError:
            continue
    return None, ""


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
    parser = CormesArgumentParser()
    parser.add_argument("-Message", "--message")
    parser.add_argument("-Model", "--model")
    parser.add_argument("-Provider", "--provider")
    parser.add_argument("-Resume", "--resume")
    parser.add_argument("-Raw", "--raw", action="store_true")
    parser.add_argument("--doctor", action="store_true", help="Emit a read-only Cormes/Codex health snapshot as JSON.")
    parser.add_argument(
        "--repo-root",
        default=os.environ.get("CORMES_REPO_ROOT") or os.environ.get("CODEX_HERMES_REPO_ROOT"),
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

    if args.doctor:
        try:
            print(json.dumps(build_doctor_report(repo_root), ensure_ascii=False, indent=2))
            return 0
        except OSError as exc:
            print(f"Doctor report generation could not complete safely: {exc}", file=sys.stderr)
            return 2

    message = args.message or ""
    model = args.model
    provider = args.provider
    raw = args.raw

    if not args.resume:
        message, parsed_model, parsed_provider, parsed_raw = split_message_flags(message)
        model = model or parsed_model
        provider = provider or parsed_provider
        raw = raw or parsed_raw

    if not message.strip():
        raise SystemExit("No Cormes message was provided.")

    cached_model, cached_provider = read_cached_model()
    config_model, config_provider = read_hermes_default_model()
    model = model or cached_model or config_model or DEFAULT_MODEL
    provider = provider or cached_provider or (config_provider if config_model else "")
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
    env["CORMES_REPO_ROOT"] = str(repo_root)
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
