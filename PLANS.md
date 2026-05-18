# Plans

A `/hermes` slash command for Codex that delegates tasks to the local Hermes CLI, then has Codex review the response and send up to three corrective feedback rounds.

```
/hermes explain this failing test
/hermes -m grok-4.3 review the current diff
/hermes -m glm-5.1 -p some-provider propose a fix for issue #12
```

## Done

- `scripts/invoke-hermes.ps1` can call Hermes CLI
- Parses session ID / model / provider / response body
- Command prompt enforces "do not trust Hermes output"

## Not done

- **`/hermes` is not recognized as a Codex slash command** (command discovery unresolved — this must be fixed first)

## Files

- `.codex-plugin/plugin.json` — Plugin manifest
- `commands/hermes.md` — Command definition (canonical)
- `.codex/commands/hermes.md` — Command definition (local Codex copy, identical content)
- `scripts/invoke-hermes.ps1` — Hermes CLI wrapper
