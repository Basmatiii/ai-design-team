# Workflow contract (v0.3.0)

Three workflows, each started by a person, each with a fixed maximum of agent runs.

| Command | Result | Agents | Figma | Linear |
|---|---|---|---|---|
| `/design-team:specs <ticket>` | `.design-team/<id>/specs.md` + scorecard | 1: `ux-analyst` (`--qa` adds one `design-qa` review) | read, scoped | read, one ticket |
| `/design-team:audit <Figma link>` | `.design-team/<id>/audit.md` + scorecard | 1: `ux-analyst` | read, requested scope only | optional read |
| `/design-team:design <ticket> <Figma target>` | built frames, `approach.md`, `build.md`, `qa.md` + scorecard | 2: `figma-designer`, `design-qa` | read, then write **after the person types `approve`** | read, one ticket |

Also: `/design-team:design-ticket` routes a free-form request to one of the three, `/design-team:review-spec`
runs QA once on an existing specification, `/design-team:apply-to-figma` enters DESIGN with a specification you
already have. `claude --agent design-team:design-orchestrator` runs the same workflows with the orchestrator as the
session, on a small model.

## Who does what

| Role | Job | Model, effort, turn limit | Tools enforced by its allowlist |
|---|---|---|---|
| Coordinator (the session running the skill, or `design-orchestrator`) | Route, read the ticket once, write `brief.md`, start one specialist per stage, relay, run the score script | orchestrator agent: `haiku`, low, 24 | Linear `get_issue` and `list_comments` only; no Figma |
| `ux-analyst` | SPECS and AUDIT, with one self-check | `sonnet`, high, 30 | Figma reads; files only in `.design-team/` |
| `figma-designer` | DESIGN: approach, build, one correction | `sonnet`, high, 60 | Figma reads + `use_figma`; a Figma usage skill; files only in `.design-team/` |
| `design-qa` | One evidence-based evaluation of the built frames, one recheck | `sonnet`, medium, 16 | Figma reads; files only in `.design-team/` |

`--deep` on a command runs that one specialist dispatch on `opus`. Use it for a hard problem, not by default.

The turn limits are ceilings, not targets. In the first live runs (fictional ticket, mock connectors) the analyst
used at most 5 turns, the designer 20 across approach, build and correction, and QA 7 across verify and recheck.
The limits leave room for real multi-frame work and will be tightened only after runs on real tickets and files
(`docs/benchmark.md`).

## One brief, written once

The coordinator reads the ticket once and writes `.design-team/<id>/brief.md`: goal, requirements and acceptance
criteria copied verbatim, out of scope, Figma file and node ids, gaps, and any instructions found inside the sources
(quoted, not followed). Specialists get the **path**. Nothing is pasted from one agent to the next, and no agent
rebuilds a requirement ledger. Figma is read by the specialist that needs it, scoped to the nodes in the brief.

## DESIGN, step by step

```
1 intake + brief            coordinator
2 approach (read-only)      figma-designer      inspects the real file, finds reusable components
3 APPROVAL GATE             the person types: approve          <- nothing is written to Figma before this
4 build                     figma-designer (resumed, same context)
  deliverable returned      frames + links + build.md          <- before QA, whatever QA says later
5 verify, once              design-qa           screenshots and metadata of the built frames, scores.txt
6 correction, at most once  figma-designer (resumed), then design-qa (resumed) rechecks only those nodes
7 scorecard                 coordinator runs scripts/score.sh
```

## Quality rubric

| Mode | Rubric | Scored by | When |
|---|---|---|---|
| DESIGN | `rubrics/design-quality.md`: requirements 25, UX and interactions 25, design-system consistency 20, accessibility and states 20, visual craftsmanship 10 | `design-qa`, independently | Once, on the finished frames |
| SPECS | `rubrics/specs-check.md`: coverage 40, behavior 25, states 25, testability 10 | `ux-analyst`, self-check | Once, inside its own run |
| AUDIT | `rubrics/audit-check.md`: evidence 35, scope 25, actionability 25, severity 15 (rates the audit, not the design) | `ux-analyst`, self-check | Once, inside its own run |

- Each criterion is rated 0 to 5 with anchors and one line of evidence. Weighted total = SUM(weight * rating / 5).
- **Pass** = 85 or more, no rating below 3, no unresolved hard blocker.
- **Hard blockers** fail a result whatever the number: a critical usability or accessibility failure, a materially
  unmet requirement, fabricated component usage, an unverified Figma claim, an unauthorized edit.
- **No evidence, no number.** A criterion that could not be inspected is `na`. A result with any `na` is reported as
  incomplete, never out of 100, and cannot pass. An audit whose scope could not be read is not scored at all.
- **Deterministic totals.** Agents write ratings to `scores.txt`; `scripts/score.sh` computes the total and the
  verdict from the weights line inside the rubric file. No agent adds numbers up.
- **A project can override a rubric** by placing a file with the same name in `.claude/rubrics/`. The plugin hook
  resolves the path when a workflow starts, so no agent spends a turn looking for it.
- The rubric adds **no agent run** to SPECS or AUDIT and no extra round to DESIGN: QA ran once before the rubric
  existed in this design, and it still runs once.

## Limits on rework

- One QA pass. At most one correction pass, on a list of at most five items, each the smallest change that clears a
  blocker or lifts a rating below 3. One recheck of those nodes only.
- Never a restart of the workflow, never a redesign for a minor issue.
- If the result still fails, the person gets the deliverable, the score, the blockers and the exact remaining issues.
- The plugin hook stops a session that starts more than 5 design-team agents or sends more than 6 agent messages
  after one instruction (`DESIGN_TEAM_MAX_SPAWNS`, `DESIGN_TEAM_MAX_RESUMES`).

## Partial results

Every specialist writes its file early and keeps it usable, and ends with `STATUS: COMPLETE`, `PARTIAL` or
`BLOCKED`. Since Claude Code 2.1.246 a subagent that reaches its turn limit returns its output marked partial. The
coordinator then delivers the saved file as `PARTIAL` with the missing parts listed; it resumes the specialist once
only when no file was saved. Missing context is `BLOCKED` with the missing input named: no specialist is started.

## Scorecard

Every workflow ends with the same block: overall score out of 100, pass or needs improvement, the criterion
ratings with their evidence, hard blockers, at most three improvements, the artifact paths, Figma links only for
nodes a tool call in this run actually read or built, whether the correction pass was used, and how many agents ran.

Human-readable instructions are not a permission system. See `docs/permissions.md` for the enforced layers.
