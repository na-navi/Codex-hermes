# codex-hermes

## About

Experimental Codex plugin for delegating tasks to the local Hermes Agent CLI, with Codex reviewing the returned answer before using it.

Suggested GitHub repository About text:

```text
Experimental Codex plugin for delegating tasks to Hermes Agent CLI.
```

## Development Status

This project is still in development.

### What works today

- Codex can call the local `hermes` CLI through `scripts/invoke-hermes.ps1`.
- Hermes can answer prompts when run with the required filesystem permissions.
- Codex can review Hermes responses and continue a Hermes session with corrective follow-up prompts.

### What does not work yet

- `/hermes` is not currently recognized by Codex as a visible slash command.
- The repository contains command prompt definitions, but the plugin is not yet being surfaced as a command skill in Codex.

In other words, the Hermes conversation path works, but plugin command discovery is not solved yet.

## Goal

`codex-hermes` is intended to provide a `/hermes` command for Codex:

```text
/hermes explain this failing test
/hermes -m grok-4.3 review the current diff
/hermes -m glm-5.1 -p some-provider propose a fix for issue #12
```

The command should:

1. Send the user task to Hermes.
2. Parse the Hermes session ID, model, provider, and response.
3. Treat the Hermes response as untrusted.
4. Let Codex review the answer against local repo context.
5. Send focused follow-up feedback to Hermes when needed.
6. Return a reviewed final answer to the user.

## Current Manual Path

Until slash command discovery is fixed, the wrapper can be run directly:

```powershell
scripts/invoke-hermes.ps1 -Message "test"
```

On sandboxed Codex runs, Hermes may need escalation because it writes to its own home and log directories outside the workspace, such as:

```text
%LOCALAPPDATA%\hermes\logs\agent.log
```

The command prompt definition now records this rule:

- full access: run Hermes normally
- `auto_review`: request escalation before running Hermes

## Requirements

- Hermes Agent CLI installed and configured as `hermes` on `PATH`.
- PowerShell, because the wrapper is `scripts/invoke-hermes.ps1`.
- A Codex plugin/slash-command loading mechanism that can discover this repository's command definition.

## Files

- `.codex-plugin/plugin.json` - Codex plugin manifest.
- `commands/hermes.md` - Canonical slash command definition for the plugin and GitHub review.
- `.codex/commands/hermes.md` - Repo-local mirror for direct use from this workspace.
- `scripts/invoke-hermes.ps1` - Hermes CLI wrapper and response parser.
- `scripts/.state/default-model.txt` - local model cache, created at runtime and ignored by git.

Keep behavior rules in `commands/hermes.md` first, then mirror the same content into `.codex/commands/hermes.md` when local slash-command support needs it. The `.codex` copy is committed, but it is treated as runtime compatibility rather than the source of truth.

## Known Issue: Command Discovery

The main open problem is that `/hermes` does not appear as a Codex slash command.

Current suspicion:

- `.codex-plugin/plugin.json` has plugin metadata.
- `commands/hermes.md` exists.
- Codex may require an additional manifest field or marketplace/plugin registration step to expose command prompts.

Next investigation:

1. Confirm the official Codex plugin schema for slash commands.
2. Check whether `commands/` is auto-discovered or must be declared.
3. Add the required manifest field if one exists.
4. Decide whether `.codex/commands/hermes.md` is still needed after plugin discovery works.
