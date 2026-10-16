# design-team (Claude Code plugin)

Four agents: `design-orchestrator`, `ux-analyst`, `figma-designer`, `design-qa`.
Three person-only skills: `design-ticket`, `review-spec`, `apply-to-figma`.

## Quick test

```bash
claude plugin validate ./plugins/design-team
claude --plugin-dir ./plugins/design-team
```

Then, inside the session:

```text
/design-team:design-ticket examples/sample-ticket.md
```

Paths are relative to the folder you start Claude Code in. From an extracted plugin ZIP, start Claude Code in the
extracted folder so `examples/` resolves, or pass a full path, or paste the ticket text.

## Safety model

- The agents can only read and search (`Read, Glob, Grep`; the orchestrator can also delegate). Claude Code
  enforces these allowlists. None of them has connector tools.
- The main session gathers sources. If it has Linear or Figma connectors, block their write tools with the deny
  rules in `settings/read-only-guard.json` (release folder) or `docs/permissions.md`.
- `apply-to-figma` never runs as part of the workflow. A person starts it with an exact frame and an approved spec.
- Plugin agents ignore `hooks`, `mcpServers` and `permissionMode`, so this plugin does not use them.
