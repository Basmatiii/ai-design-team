# design-team (Claude Code plugin, v0.3.0)

Four agents: `design-orchestrator`, `ux-analyst`, `figma-designer`, `design-qa`.

| Command | Runs | Result |
|---|---|---|
| `/design-team:specs <ticket>` | UX Analyst | `.design-team/<id>/specs.md` + scorecard |
| `/design-team:audit <Figma link>` | UX Analyst | `.design-team/<id>/audit.md` + scorecard |
| `/design-team:design <ticket> <Figma target>` | Figma Designer, Design QA | approach, your `approve`, built frames, scorecard |
| `/design-team:design-ticket <request>` | routes to one of the three | |
| `/design-team:review-spec <spec> <ticket>` | Design QA, once | scorecard for an existing specification |
| `/design-team:apply-to-figma <spec> <file, page, frame>` | DESIGN from an existing specification | approval still required |

All six can only be started by a person.

## Install

```bash
claude plugin marketplace add Basmatiii/ai-design-team
claude plugin install design-team@basma-ai-tools
```

## Quick test from a clone

```bash
claude plugin validate ./plugins/design-team
claude --plugin-dir ./plugins/design-team
```

Then, inside the session: `/design-team:specs examples/sample-ticket.md`

Paths are relative to the folder you start Claude Code in. From an extracted plugin ZIP, start Claude Code in the
extracted folder so `examples/` resolves, or pass a full path, or paste the ticket text.

## Safety model

- `hooks/hooks.json` and `hooks/guard.sh` ship with the plugin: Linear writes are denied in design-team sessions,
  Figma writes are denied until the person types `approve`, and agents can write only inside `.design-team/`.
- Agent allowlists: only `figma-designer` has `use_figma`; only `design-orchestrator` can read Linear (one issue,
  no list or search); nobody has image generation, file creation or upload tools.
- `rubrics/` holds the quality rubrics and `scripts/score.sh` computes every score.
- Plugin agents ignore `hooks`, `mcpServers` and `permissionMode` in their own frontmatter, so this plugin does not
  use them there: the hooks live at plugin level.

MIT License. Copyright (c) 2026 Basma Gh.
