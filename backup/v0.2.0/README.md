# Backup: The AI Design Team v0.2.0

A frozen copy of the configuration as it was before the v0.3.0 refactor, taken from commit `bb14c8c`
("Docs: record live Linear and Figma testing by the author"). Nothing in this folder is loaded by Claude Code:
it sits outside `plugins/design-team/`, so the marketplace and `--plugin-dir` ignore it.

| Path | What it is |
|---|---|
| `agents/` | The four v0.2.0 agent definitions (all `model: inherit`, tools `Read, Glob, Grep`) |
| `skills/` | `design-ticket`, `review-spec`, `apply-to-figma` as shipped in v0.2.0 |
| `settings/read-only-guard.json` | The v0.2.0 optional deny rules |
| `docs/` | The v0.2.0 workflow contract, permissions page and validation record |
| `plugin.json` | The v0.2.0 manifest |

## Restore

```bash
git checkout bb14c8c -- plugins/design-team settings docs
```

Or copy `agents/` and `skills/` from this folder over `plugins/design-team/` and remove `plugins/design-team/hooks/`.

Why the refactor happened and what the evidence was: `docs/diagnosis.md`.
