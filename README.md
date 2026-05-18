# codex-hermes

Experimental Codex plugin for delegating work to Hermes CLI models with a Codex review loop.

## Hermes Entry Point

- Primary Codex-facing entrypoint: [`.codex/commands/hermes.md`](/D:/data/CodexApp/Codex-hermes/.codex/commands/hermes.md)
- Legacy compatibility copy: [`commands/hermes.md`](/D:/data/CodexApp/Codex-hermes/commands/hermes.md)
- Canonical workflow: [`skills/hermes/SKILL.md`](/D:/data/CodexApp/Codex-hermes/skills/hermes/SKILL.md)

## Validate

```text
python scripts/validate-plugin.py
```

## Git Hooks

Enable the repository-managed hooks once per clone:

```text
git config core.hooksPath .githooks
```

After that, `git commit` runs `.githooks/pre-commit`, which validates the plugin structure before the commit is created.

Hook and validation automation in this repository is Python-only. Do not add `sh`, `ps1`, `bat`, or `cmd` wrappers for these paths.

See [PLANS.md](PLANS.md) for the current roadmap.
