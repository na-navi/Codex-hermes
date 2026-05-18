# codex-hermes

Experimental Codex plugin for delegating work to Hermes CLI models with a Codex review loop.

## Hermes Entry Point

- Primary Codex App entrypoint: [`.agents/skills/hermes/SKILL.md`](/D:/data/CodexApp/Codex-hermes/.agents/skills/hermes/SKILL.md)
- Plugin-bundled skill: [`skills/hermes/SKILL.md`](/D:/data/CodexApp/Codex-hermes/skills/hermes/SKILL.md)
- Legacy custom prompt experiment: [`.codex/commands/hermes.md`](/D:/data/CodexApp/Codex-hermes/.codex/commands/hermes.md)
- Legacy compatibility copy: [`commands/hermes.md`](/D:/data/CodexApp/Codex-hermes/commands/hermes.md)

## Invocation Note

`/hermes` is not guaranteed to exist as a native slash command in Codex App. Use `$hermes` to explicitly invoke the repo skill after Codex detects `.agents/skills/hermes/SKILL.md`.

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
