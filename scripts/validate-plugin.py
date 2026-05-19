#!/usr/bin/env python3
"""Validate the cormes plugin structure and common publication issues."""

from __future__ import annotations

import json
import re
import sys
from filecmp import cmp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXIT_CODE = 0
SKILL_NAME = "cormes"
PLUGIN_NAME = "cormes"


def pass_(message: str) -> None:
    print(f"  [PASS] {message}")


def fail(message: str) -> None:
    global EXIT_CODE
    print(f"  [FAIL] {message}")
    EXIT_CODE = 1


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_plugin_json() -> None:
    section(".codex-plugin/plugin.json")
    plugin_path = ROOT / ".codex-plugin" / "plugin.json"
    if not plugin_path.exists():
        fail(f"plugin.json not found at {plugin_path}")
        return

    pass_("plugin.json exists")
    try:
        plugin = json.loads(read_text(plugin_path))
    except Exception as exc:  # noqa: BLE001 - validation should report any parse failure.
        fail(f"plugin.json parse error: {exc}")
        return

    pass_("plugin.json is valid JSON")

    if plugin.get("name") == PLUGIN_NAME:
        pass_(f"name: {PLUGIN_NAME}")
    elif plugin.get("name"):
        fail(f"name is {plugin['name']!r}, expected {PLUGIN_NAME!r}")
    else:
        fail("name is missing")

    if plugin.get("version"):
        pass_(f"version: {plugin['version']}")
    else:
        fail("version is missing")

    if plugin.get("description"):
        pass_("description present")
    else:
        fail("description is missing")

    skills = plugin.get("skills")
    if skills == "./skills/":
        pass_("skills: ./skills/")
    elif skills:
        fail(f"skills is {skills!r}, expected './skills/'")
    else:
        fail("skills field is missing")

    interface = plugin.get("interface")
    if isinstance(interface, dict) and interface.get("displayName"):
        pass_(f"interface.displayName: {interface['displayName']}")
    else:
        fail("interface.displayName is missing")

    if isinstance(interface, dict) and interface.get("capabilities"):
        pass_(f"interface.capabilities: {', '.join(interface['capabilities'])}")
    else:
        fail("interface.capabilities is missing")


def validate_skill() -> None:
    section("skills/cormes/SKILL.md")
    skill_path = ROOT / "skills" / "cormes" / "SKILL.md"
    if not skill_path.exists():
        fail(f"SKILL.md not found at {skill_path}")
        return

    pass_("SKILL.md exists")
    content = read_text(skill_path)
    match = re.search(r"\A---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        fail("No YAML frontmatter (--- ... ---) found")
        return

    pass_("YAML frontmatter found")
    frontmatter = match.group(1)

    name_match = re.search(r"^name:\s*(\S+)", frontmatter, re.MULTILINE)
    if not name_match:
        fail("name field missing in frontmatter")
    elif name_match.group(1) == SKILL_NAME:
        pass_(f"name: {SKILL_NAME}")
    else:
        fail(f"name is {name_match.group(1)!r}, expected {SKILL_NAME!r}")

    if re.search(r"^description:\s*", frontmatter, re.MULTILINE):
        pass_("description field present")
    else:
        fail("description field missing in frontmatter")


def validate_repo_skill() -> None:
    section(".agents/skills/cormes/SKILL.md")
    skill_path = ROOT / ".agents" / "skills" / "cormes" / "SKILL.md"
    if not skill_path.exists():
        fail(f"Repo skill not found at {skill_path}")
        return

    pass_("repo SKILL.md exists")
    content = read_text(skill_path)
    match = re.search(r"\A---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        fail("No YAML frontmatter (--- ... ---) found")
        return

    pass_("YAML frontmatter found")
    frontmatter = match.group(1)

    name_match = re.search(r"^name:\s*(\S+)", frontmatter, re.MULTILINE)
    if not name_match:
        fail("name field missing in frontmatter")
    elif name_match.group(1) == SKILL_NAME:
        pass_(f"name: {SKILL_NAME}")
    else:
        fail(f"name is {name_match.group(1)!r}, expected {SKILL_NAME!r}")

    if re.search(r"^description:\s*", frontmatter, re.MULTILINE):
        pass_("description field present")
    else:
        fail("description field missing in frontmatter")


def validate_wrapper() -> None:
    section("scripts/invoke-cormes.py")
    wrapper_path = ROOT / "scripts" / "invoke-cormes.py"
    if wrapper_path.exists():
        pass_("invoke-cormes.py exists")
    else:
        fail(f"invoke-cormes.py not found at {wrapper_path}")


def validate_command_copies() -> None:
    section("commands/cormes.md copies")
    root_command = ROOT / "commands" / "cormes.md"
    codex_command = ROOT / ".codex" / "commands" / "cormes.md"

    if root_command.exists():
        pass_("commands/cormes.md exists")
    else:
        fail(f"commands/cormes.md not found at {root_command}")

    if codex_command.exists():
        pass_(".codex/commands/cormes.md exists")
    else:
        fail(f".codex/commands/cormes.md not found at {codex_command}")

    if root_command.exists() and codex_command.exists():
        if cmp(root_command, codex_command, shallow=False):
            pass_("legacy command copies are identical")
        else:
            fail("commands/cormes.md and .codex/commands/cormes.md differ")


def scan_privacy_and_secrets() -> None:
    section("privacy & secret scan")
    scan_paths = [
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        ".agents/skills/cormes/SKILL.md",
        "skills/cormes/SKILL.md",
        "commands/cormes.md",
        ".codex/commands/cormes.md",
        ".env.example",
        ".githooks/pre-commit",
        "scripts/invoke-cormes.py",
        "README.md",
        "README.en.md",
        "README.ja.md",
        "README.zh-CN.md",
        "PLANS.md",
    ]
    token_pattern = re.compile(
        r"(api[_-]?key|api[_-]?secret|access[_-]?token|bearer)\s*[:=]\s*[\"']?\w{20,}",
        re.IGNORECASE,
    )
    gh_token_pattern = re.compile(r"gh[op]_[A-Za-z0-9]{20,}")
    user_path_pattern = re.compile(r"C:\\Users\\([^\\]+)\\.*?(?:\s|$)")

    found_issue = False
    for rel_path in scan_paths:
        path = ROOT / rel_path
        if not path.exists():
            continue

        text = read_text(path)
        for match in user_path_pattern.finditer(text):
            fail(f"{rel_path} contains hardcoded username {match.group(1)!r}")
            found_issue = True

        if token_pattern.search(text):
            fail(f"{rel_path} may contain a secret/token")
            found_issue = True

        if gh_token_pattern.search(text):
            fail(f"{rel_path} may contain a GitHub token")
            found_issue = True

    if not found_issue:
        pass_("No hardcoded usernames, secrets, or tokens found in tracked files")


def main() -> int:
    print("Validating cormes plugin...")
    print(f"Root: {ROOT}")
    validate_plugin_json()
    validate_skill()
    validate_repo_skill()
    validate_wrapper()
    validate_command_copies()
    scan_privacy_and_secrets()

    print("\n================================")
    if EXIT_CODE == 0:
        print("RESULT: PASS")
    else:
        print(f"RESULT: FAIL (exit code {EXIT_CODE})")
    print("================================")
    return EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
