# codex-hermes

Languages: English | [日本語](README.ja.md) | [简体中文](README.zh-CN.md)

Experimental Codex plugin that bridges Codex App tasks to the local Hermes CLI,
then lets Codex review the returned answer before continuing.

The goal is simple: install this repo as a Codex plugin, run a Hermes task from
any Codex workspace, and see a Hermes reply come back.

## Latest Release

- [v0.1.2 - Public metadata cleanup for installable-first distribution](https://github.com/na-navi/Codex-hermes/releases/tag/v0.1.2)
- [v0.1.1 - Initial verified Codex App <-> Hermes CLI bridge](https://github.com/na-navi/Codex-hermes/releases/tag/v0.1.1)
- No binary or bundle is attached yet; use the repository source directly.

## What You Need

- Codex App
- `hermes` CLI installed and available on `PATH`
- This repository cloned locally

## Install

1. Make sure Hermes works from a terminal first.

```text
hermes --help
```

If that command fails, fix Hermes before continuing. This plugin cannot talk to Hermes without the CLI.

2. Install the plugin into your Codex plugin directory.

```powershell
$pluginRoot = "$env:USERPROFILE\.codex\plugins\codex-hermes"
New-Item -ItemType Directory -Force -Path $pluginRoot | Out-Null
Copy-Item -Recurse -Force .codex-plugin, skills, commands, scripts, README.md, LICENSE $pluginRoot
```

3. Restart Codex App, or open a new thread, so the plugin skill list is refreshed.

4. Run the validator from this repository.

```text
python scripts/validate-plugin.py
```

5. Optional, but recommended for development in this repository:

```text
git config core.hooksPath .githooks
```

## Development Mode

When this repository is the active Codex workspace, Codex can also discover the
repo-local skill at `.agents/skills/hermes/SKILL.md`. That is useful while
developing the plugin, but it is not enough for other folders.

For use from other workspaces, install the plugin so Codex can load:

```text
%USERPROFILE%\.codex\plugins\codex-hermes\skills\hermes\SKILL.md
```

## Test the Hermes Link

1. In Codex, invoke the Hermes skill with a short task from any workspace.

```text
$hermes say hello
```

2. Wait for the run to finish.
3. Confirm the output contains:
   - `MODEL=...`
   - `SESSION_ID=...`
   - `RESPONSE_BEGIN`
   - a Hermes reply after `RESPONSE_BEGIN`

If you see `Hermes CLI was not found on PATH`, the CLI is not installed or the shell cannot see it yet.
If you see no `SESSION_ID`, Hermes did not return a session marker, but the reply can still be valid.

## Files That Matter

- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json)
- [`skills/hermes/SKILL.md`](skills/hermes/SKILL.md)
- [`.agents/skills/hermes/SKILL.md`](.agents/skills/hermes/SKILL.md)
- [`scripts/invoke-hermes.py`](scripts/invoke-hermes.py)
- [`scripts/validate-plugin.py`](scripts/validate-plugin.py)

