# The AI Design Team (v0.3.0)

**Four specialized agents. Three direct workflows. One approval before anything changes in Figma.**

A Claude Code plugin for product designers. Ask for what you actually need, and only the agents that produce it run.

| You want | Command | What runs | What you get |
|---|---|---|---|
| A UX specification | `/design-team:specs <ticket>` | 1 agent: UX Analyst | `specs.md`: goal, assumptions, flows, interaction behavior, states, edge cases, accessibility, acceptance criteria |
| A UX audit of existing frames | `/design-team:audit <Figma link>` | 1 agent: UX Analyst | `audit.md`: findings tied to node ids, severity, recommended change, rationale |
| Actual design in Figma | `/design-team:design <ticket> <Figma target>` | 2 agents: Figma Designer, Design QA | An approach to approve, then editable frames built from your library, checked once |

Every workflow ends with a short, evidence-based **scorecard** out of 100. Linear is never written to. Figma is
written to only by the designer, and only after you type `approve`.

```
specs    ticket > brief > UX Analyst > scorecard
audit    Figma scope > brief > UX Analyst > scorecard
design   ticket > brief > Figma Designer (approach) > YOU: approve > Figma Designer (build) > Design QA (once) > scorecard
```

| Agent | Job | Model | Can touch |
|---|---|---|---|
| `design-orchestrator` | Routes a request to one workflow and coordinates it | `haiku` | Linear: read one issue. Figma: nothing |
| `ux-analyst` | Specifications and audits, with one self-check | `sonnet` | Figma: read the scoped nodes |
| `figma-designer` | Inspects the real file, proposes, builds after approval | `sonnet` | Figma: read, and `use_figma` after approval |
| `design-qa` | One evidence-based evaluation of the finished design | `sonnet` | Figma: read |

Other commands: `/design-team:design-ticket` (routes a free-form request to one of the three),
`/design-team:review-spec` (QA on an existing specification), `/design-team:apply-to-figma` (DESIGN from a
specification you already have). Add `--deep` to run the specialist on `opus` for a hard problem.

## Install

Requires Claude Code 2.1.246 or later with plugin support.

```bash
claude plugin marketplace add Basmatiii/ai-design-team
claude plugin install design-team@basma-ai-tools
```

Or inside Claude Code: `/plugin marketplace add Basmatiii/ai-design-team`, then `/plugin install design-team@basma-ai-tools`.

## Try it on the fictional ticket

```bash
git clone https://github.com/Basmatiii/ai-design-team
cd ai-design-team
claude --plugin-dir ./plugins/design-team
```

Then run `/design-team:specs examples/sample-ticket.md`. Artifacts land in `.design-team/sample-ticket/`.

## Using your own tickets and files

- **Linear**: connect a Linear integration and pass an issue id or URL. One issue is read, plus its parent only when
  the issue has no requirements of its own.
- **Figma**: connect the Figma integration and paste a link to the frame, section or page. Agents read only the
  nodes you point at, never a whole file unless you ask for it.
- **Connector names**: agents are allowed the common Figma and Linear connector names. If `/mcp` shows yours under
  another name, see `scripts/sync-connector-aliases.py`.
- **Artifacts** are written to `.design-team/<ticket id>/` in the folder you start Claude Code in. Add
  `.design-team/` to your project's `.gitignore` if you do not want them committed.

## Quality rubric

| Mode | Criteria (weight) | Scored by |
|---|---|---|
| DESIGN | Requirements coverage 25, UX and interactions 25, design-system consistency 20, accessibility and states 20, visual craftsmanship 10 | Design QA, once, on the built frames |
| SPECS | Coverage 40, flows and behavior 25, states and accessibility 25, testable criteria 10 | UX Analyst self-check |
| AUDIT | Evidence 35, scope 25, actionability 25, severity 15 | UX Analyst self-check |

Ratings are 0 to 5 with written anchors and one line of evidence each. Pass is 85 or more, no rating below 3, and
no hard blocker (a critical usability or accessibility failure, a materially unmet requirement, fabricated
component usage, an unverified Figma claim, an unauthorized edit). What was not inspected is `na`, never a number.
Totals come from `scripts/score.sh`, not from a model. To change a rubric for one project, copy it from
`plugins/design-team/rubrics/` to `.claude/rubrics/` in that project and edit it there.

## Guardrails that are enforced, not just written

The plugin ships hooks (`plugins/design-team/hooks/`), active as soon as it is enabled:

- Linear write tools are denied in any session that runs a design-team workflow.
- Figma write tools are denied until you type `approve`, and always for the analyst, QA and the orchestrator.
- design-team agents can write only `.md`, `.json` and `.txt` files inside `.design-team/`.
- At most 5 agents start after one instruction: a six-round loop cannot happen.
- Every Figma and Linear call is logged to `.design-team/run-ledger.tsv`.

Details and limits: `docs/permissions.md`.

## Work on the plugin

```bash
python3 scripts/validate.py                  # static checks (needs PyYAML)
python3 tests/run-static.py                  # 76 deterministic checks, no account needed
claude plugin validate ./plugins/design-team
sh tests/live/run-live.sh                    # 11 live scenarios on mock connectors (uses credits)
python3 scripts/analyze-sessions.py          # measure your own past runs from local transcripts
```

## What is in the folder

- `plugins/design-team/`: the plugin (manifest, four agents, six skills, hooks, rubrics, score script, examples)
- `.claude/rubrics/`: the same rubrics at the project-override path, kept in sync
- `docs/`: diagnosis of v0.2.0, workflow contract, permissions, benchmark, validation record, setup, licensing
- `tests/`: deterministic tests, live scenarios, the mock Linear and Figma server, the run analyzer
- `scripts/`: validator, connector-name sync, session-history analyzer
- `settings/read-only-guard.json`: optional second permission layer for your project
- `backup/v0.2.0/`: the previous agents, skills and settings, unchanged
- `examples/`: fictional Pollen tickets, project context and library inventory

## Status

v0.3.0 restructures the team after user feedback on v0.2.0 (about six agent rounds per request, high credit use,
the UX agent running out of turns, slow Figma screens). In the first live runs on the fictional sample ticket, a
specification took one agent, about 88 seconds and USD 0.27, against six agents, 308 seconds and USD 0.73 for
v0.2.0. Those are a handful of single runs on mock connectors: real tickets, real Figma files and a design that
passes QA are still to be measured. `docs/benchmark.md` has every number and its source.

Independent project by Basma Gh, not endorsed by Anthropic, Figma or Linear. Released under the MIT License
(`LICENSE`).
