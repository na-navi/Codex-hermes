# codex-hermes

Mock plugin. The goal is simple: install this repo as a Codex plugin, run a Hermes task from Codex, and see a Hermes reply come back.

## What You Need

- Codex App with this repository open
- `hermes` CLI installed and available on `PATH`
- This repository cloned locally

## Install

1. Open this repository in Codex App.
2. Make sure Hermes works from a terminal first.

```text
hermes --help
```

If that command fails, fix Hermes before continuing. This plugin cannot talk to Hermes without the CLI.

3. Keep the repo root open in Codex App so the repo skill can be discovered.
4. Optional, but recommended if you want the local hook:

```text
git config core.hooksPath .githooks
```

5. Run the validator.

```text
python scripts/validate-plugin.py
```

## Test the Hermes Link

1. In Codex, invoke the Hermes skill with a short task.

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

- [`skills/hermes/SKILL.md`](/D:/data/CodexApp/Codex-hermes/skills/hermes/SKILL.md)
- [`.agents/skills/hermes/SKILL.md`](/D:/data/CodexApp/Codex-hermes/.agents/skills/hermes/SKILL.md)
- [`scripts/invoke-hermes.py`](/D:/data/CodexApp/Codex-hermes/scripts/invoke-hermes.py)
- [`scripts/validate-plugin.py`](/D:/data/CodexApp/Codex-hermes/scripts/validate-plugin.py)

