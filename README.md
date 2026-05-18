# codex-hermes

Experimental Codex plugin for delegating work to Hermes CLI models with a Codex review loop.

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
