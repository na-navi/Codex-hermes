# cormes

[日本語](README.md) / [English](README.en.md) / [简体中文](README.zh-CN.md)

![Cormes workflow hero](./assets/codex-hermes-hero.webp)

Experimental Codex plugin that bridges Codex App tasks to the local Hermes CLI,
then lets Codex review the returned answer before continuing.

Cormes is the Codex-side wrapper. It delegates to the external `hermes` CLI,
then treats the Hermes answer as untrusted data for Codex to review.

## Demo

![Cormes review loop demo](./assets/demo-review-loop.webp)

The demo shows the difference between plain `hermes` and Cormes: plain
Hermes returns a model answer directly, while Cormes treats that answer as
untrusted data, checks it against the local repository, and returns a reviewed
final answer.

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
$pluginRoot = "$env:USERPROFILE\.codex\plugins\cormes"
Remove-Item -Recurse -Force $pluginRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $pluginRoot | Out-Null
Copy-Item -Recurse -Force .codex-plugin, skills, commands, scripts, assets, README.md, README.en.md, README.zh-CN.md, LICENSE $pluginRoot
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
repo-local skill at `.agents/skills/cormes/SKILL.md`. That is useful while
developing the plugin, but it is not enough for other folders.

For use from other workspaces, install the plugin so Codex can load:

```text
%USERPROFILE%\.codex\plugins\cormes\skills\cormes\SKILL.md
```

## Test the Hermes Link

1. In Codex, invoke the Cormes skill with a short task from any workspace.

```text
$cormes say hello
```

2. Wait for the run to finish.
3. Confirm the output contains:
   - `MODEL=...`
   - `SESSION_ID=...`
   - `RESPONSE_BEGIN`
   - a Hermes reply after `RESPONSE_BEGIN`

If you see `Hermes CLI was not found on PATH`, the CLI is not installed or the shell cannot see it yet.
If you see no `SESSION_ID`, Hermes did not return a session marker, but the reply can still be valid.

## Doctor

`--doctor` emits a read-only JSON health snapshot for the local Codex / Cormes environment.
It does not execute Hermes, write the model cache, read config / auth / session contents, or recursively scan `.codex`.

```text
python scripts/invoke-cormes.py --doctor
```

If the report contains `fail` items but the report was emitted successfully, the process exit code is still `0`. Non-zero exits are reserved for invalid arguments or doctor itself failing to complete safely.

## Model Selection

By default, Cormes uses `model.default` / `model.provider` from Hermes `config.yaml`. You can override them at the beginning of the task text.

```text
$cormes -m glm-5.1 -p zai say hello
```

The priority order is explicit flags, the Cormes model cache, Hermes `config.yaml`, then the `glm-5-turbo` fallback.

## Compatibility

`$cormes` is the primary Codex skill invocation. Legacy `$hermes` invocation is not kept as a separate skill alias in this repository, because that would preserve the wrapper/dependency name collision.

The external CLI binary remains `hermes`. Legacy environment variables `CODEX_HERMES_STATE_DIR` and `CODEX_HERMES_REPO_ROOT` are still accepted as fallback aliases for one-way compatibility during the rename.

## Files That Matter

- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json)
- [`skills/cormes/SKILL.md`](skills/cormes/SKILL.md)
- [`.agents/skills/cormes/SKILL.md`](.agents/skills/cormes/SKILL.md)
- [`scripts/invoke-cormes.py`](scripts/invoke-cormes.py)
- [`scripts/validate-plugin.py`](scripts/validate-plugin.py)
