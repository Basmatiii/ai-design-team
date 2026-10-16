# The AI Design Team (v0.2.0, preview)

**Four specialized agents. One smarter design workflow.**

A Claude Code plugin for product designers. A ticket goes in; a research-backed UX brief, a Figma-ready design
specification and an independent QA review come out, and a person makes the decision. Nothing in Linear or Figma
changes unless that person starts a separate, explicit step.

```
ticket > Orchestrator > UX Analyst > Figma Designer > Design QA > human review
```

| Agent | Job | Tools |
|---|---|---|
| `design-orchestrator` | Builds the evidence ledger, delegates, reconciles one handoff | Agent, Read, Glob, Grep |
| `ux-analyst` | Flows, numbered acceptance criteria, state matrix, open questions | Read, Glob, Grep |
| `figma-designer` | Figma-ready frame plan; reuses only inspected components | Read, Glob, Grep |
| `design-qa` | Evidence-rated review against the original ticket; refuses imaginary passes | Read, Glob, Grep |

| Skill | What it does |
|---|---|
| `/design-team:design-ticket` | Runs the whole workflow on a file, pasted text or a Linear issue (read only) |
| `/design-team:review-spec` | Runs Design QA alone on an existing spec |
| `/design-team:apply-to-figma` | Opt-in: applies an approved spec to one exact Figma frame, after confirmation |

All three skills can only be started by a person (`disable-model-invocation: true`).

## Try it

Requires Claude Code with plugin support. No accounts are needed for the fictional sample.

```bash
python3 scripts/validate.py                  # static checks (needs PyYAML)
claude plugin validate ./plugins/design-team
claude --plugin-dir ./plugins/design-team
```

Inside the session, from this folder:

```text
/design-team:design-ticket examples/sample-ticket.md
```

Or run the orchestrator as the main session, which then delegates to the three specialists itself:

```bash
claude --plugin-dir ./plugins/design-team --agent design-team:design-orchestrator
```

## Using your own tickets and library

- **Linear**: connect a Linear integration in your Claude Code session and pass an issue ID or URL. The skill reads
  the issue, and its parent when the child lacks requirements, with read operations only.
- **Figma**: connect a Figma integration and name the file. The skill lists existing components with read-only tools
  before the designer proposes anything.
- **Enforce it**: copy `settings/read-only-guard.json` into your project's `.claude/settings.json`. Deny rules are
  enforced by Claude Code; instructions alone are not. Details in `docs/permissions.md`.

## What is in the folder

- `plugins/design-team/`: the plugin (manifest, four agents, three skills, bundled examples)
- `.claude-plugin/marketplace.json`: marketplace catalog for a future public repository
- `examples/`: fictional Pollen tickets, project context and library inventory
- `settings/read-only-guard.json`: permission rules that block Linear and Figma writes
- `tests/`: a mock Linear and Figma server that logs every call, and a run analyzer
- `docs/`: workflow contract, permissions, live integrations, validation record, licensing
- `scripts/validate.py`: static release checks

## Status

Tested with Claude Code 2.1.301 on fictional data, including delegation, parent-ticket investigation, library
inspection and the read-only guard against a mock connector. Not yet tested against real Linear or Figma
workspaces, and no time savings are claimed. See `docs/validation.md`.

Independent project by Basma Gh, not endorsed by Anthropic, Figma or Linear. All rights reserved until a
publication license is chosen (`docs/licensing.md`).
