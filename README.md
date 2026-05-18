# codex-hermes

Codex plugin port of `pi-hermes`.

This adds a `/hermes` slash command prompt for Codex. It delegates a task to the local `hermes` CLI, then makes Codex review the answer, run local checks when useful, and send up to three corrective follow-ups through `hermes --resume`.

## Requirements

- Codex with local plugin slash-command support.
- Hermes Agent CLI installed and configured as `hermes` on `PATH`.
- PowerShell, because the bundled wrapper is `scripts/invoke-hermes.ps1`.

## Usage

```text
/hermes explain this failing test
/hermes -m grok-4.3 review the current diff
/hermes -m glm-5.1 -p some-provider propose a fix for issue #12
```

The command resolves the model in this order:

1. `-m <model>` argument.
2. Cached model in `scripts/.state/default-model.txt`.
3. `grok-4.3`.

The provider is cached together with the model when supplied with `-p <provider>`.

## How It Works

`commands/hermes.md` tells Codex to:

1. Run `scripts/invoke-hermes.ps1 -Message "$ARGUMENTS"`.
2. Parse `SESSION_ID`, `MODEL`, `PROVIDER`, and the response body.
3. Review the answer locally instead of trusting it.
4. When a concrete issue is found, run `scripts/invoke-hermes.ps1 -Resume <SESSION_ID> -Message "<feedback>" -Model <MODEL>`.
5. Repeat at most three review rounds.
6. Apply or summarize the corrected result for the user.

This is intentionally not a direct TypeScript port of the pi extension. Codex plugin slash commands are prompt-driven, so the review loop lives in the command instructions and the Hermes CLI interaction is isolated in a small script.

## Files

- `.codex-plugin/plugin.json` - Codex plugin manifest.
- `commands/hermes.md` - Slash command definition.
- `.codex/commands/hermes.md` - Repo-local slash command definition for direct use from this workspace.
- `scripts/invoke-hermes.ps1` - Hermes CLI wrapper and response parser.
- `scripts/.state/default-model.txt` - local model cache, created at runtime and ignored by git.
