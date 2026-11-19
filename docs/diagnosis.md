# Diagnosis of v0.2.0

What was inspected, what the evidence shows, and what is still a hypothesis. Written before the v0.3.0 refactor;
the v0.2.0 files are preserved in `backup/v0.2.0/`.

## What was inspected

| Item | Found |
|---|---|
| Agents | 4, in `plugins/design-team/agents/`: all `model: inherit`, all `tools: Read, Glob, Grep` (the orchestrator also `Agent`), `maxTurns` 30 / 18 / 18 / 20 |
| Skills | 3, person-only: `design-ticket`, `review-spec`, `apply-to-figma` |
| Hooks | None |
| `CLAUDE.md`, `.claude/` | None in the repository |
| MCP configuration | None in the plugin. `tests/mcp-config.json` (v0.2.0) pointed at a mock server for tests only |
| Permissions | `settings/read-only-guard.json`: optional deny rules a user has to copy into their own project |
| Execution history | `docs/validation.md`: a summary table of 7 recorded runs (duration, cost, which agents ran). The raw event streams are not in the repository (`tests/out/` is git-ignored). No trace of a live Linear or Figma session, and no trace of an `apply-to-figma` run |

**Labels used below.** *Evidence*: read directly from a file in the repository. *Hypothesis*: a likely cause that no
recorded run confirms. Two of the five user complaints (out of turns, 30-minute screens) have no recorded trace at
all, so their causes stay hypotheses until `scripts/analyze-sessions.py` is run on real session history.

## v0.2.0 execution map

```
/design-team:design-ticket
  main session      reads sources, writes a "source packet" (ticket text, verbatim)
  └ orchestrator    re-reads, builds an evidence ledger, writes three briefs with the sources verbatim
      ├ ux-analyst      own source ledger, flows, criteria, state matrix
      ├ figma-designer  written specification (it cannot open Figma)
      ├ design-qa       verdict on the written specification
      ├ figma-designer  revision (when QA says REVISION REQUIRED)
      └ design-qa       second verdict
    orchestrator    final handoff
  main session      presents the handoff again with its own traceability table
/design-team:apply-to-figma   (separate, later) main session edits Figma itself, then asks design-qa to check
```

## Findings

| # | User feedback | Finding | Status | Where |
|---|---|---|---|---|
| 1 | About six rounds per request | Six agent runs are the normal path, not an accident: orchestrator, analyst, designer twice, QA twice. Seven when nested delegation is off (the orchestrator runs again to reconcile). | Evidence | `docs/validation.md` runs 1, 2, 3, 6, 7: every full run shows designer x2 and QA x2 |
| 2 | Six rounds | The revision round never produced a pass. QA returned `REVISION REQUIRED` in every recorded full run, and twice in a row in runs 1 and 7. QA judges a written plan with a vocabulary in which nothing can be `PASS` without a frame to inspect, and any issue of any severity triggers a revision. | Evidence | `agents/design-qa.md` (evidence levels, verdicts), `docs/sample-run/sample-104-handoff.md` ("It came back twice") |
| 3 | Excessive credits | Handoffs are retyped, not referenced. The orchestrator is told to pass "the full, unabridged text of the sources and earlier outputs" to every specialist, so the ticket and the specification are re-emitted as output tokens at each hop. In run 7 the orchestrator condensed them anyway and QA flagged that as an issue. | Evidence for the mechanism. The token share is unmeasured | `agents/design-orchestrator.md` ("Handoffs are verbatim"), `skills/design-ticket/SKILL.md` step 7 |
| 4 | Excessive credits | The same requirement ledger is produced up to five times: source packet, orchestrator ledger, analyst source ledger, final handoff ledger, the skill's traceability table. | Evidence | the three files above plus `agents/ux-analyst.md` (Output) |
| 5 | Excessive credits | Two coordinators. The main session and the orchestrator both do intake, and both write the final report. | Evidence | `skills/design-ticket/SKILL.md` stages 0 and 8, `agents/design-orchestrator.md` stage 1 and final handoff |
| 6 | Excessive credits | Every agent uses `model: inherit`, so routing and copying run at the price of whatever model the session uses. The recorded runs cost USD 0.52 to 1.09 on Sonnet for a seven-requirement ticket with no Figma work. | Evidence for the setting. Cost on larger models is unmeasured | agent frontmatter, `docs/validation.md` |
| 7 | UX agent out of turns | Nothing lets a partial result survive. `maxTurns: 18`, no instruction to write early, no partial-result format, and the coordinator's only rule is "say which stage did not run". | Evidence | `agents/ux-analyst.md`, `skills/design-ticket/SKILL.md` step 7 |
| 8 | UX agent out of turns | Why it runs out: the analyst has only local file tools, while real tickets point at Figma and Linear. Searching local files for evidence it cannot reach, plus re-reading to "cite only what you actually read", is the likely turn sink. No recorded run shows a turn-limit exit, so this is unconfirmed. | Hypothesis | `agents/ux-analyst.md` (tools, rules) |
| 9 | 30 minutes per Figma screen | The agent called "Figma designer" cannot open Figma (`Read, Glob, Grep`). Real building is done by the main session from an eight-line skill with no build method and an unscoped "inspect first: the frame, the library components and variables it uses". | Evidence for the configuration. Its share of the 30 minutes is unmeasured: no `apply-to-figma` run was ever recorded | `agents/figma-designer.md`, `skills/apply-to-figma/SKILL.md` |
| 10 | 30 minutes per Figma screen | To reach a built screen a user must first run the six-round ticket workflow (221 to 444 seconds recorded, never ending in a pass), then the apply skill, which runs QA again. | Evidence | `docs/validation.md`, `skills/apply-to-figma/SKILL.md` step 5 |
| 11 | Design quality | Design QA cannot see a design. After `apply-to-figma` it is asked to review frames it has no tool to open, so it can only judge what the main session tells it. | Evidence | `agents/design-qa.md` (tools), `skills/apply-to-figma/SKILL.md` step 5 |
| 12 | Users want specs, audits, design | None of the three can be asked for directly. A specification costs the whole pipeline; an audit of real Figma frames is not possible (no agent reads Figma; `review-spec` reviews a text file); design is two commands. | Evidence | skill list |
| 13 | Safety | Enforcement is opt-in. The plugin ships no hooks; Linear and Figma stay read-only only if each user copies the deny rules into their project. The Figma approval rule is prompt text plus a person-only command. | Evidence | `docs/permissions.md`, `settings/read-only-guard.json` |

## What is not the problem

- **Prompt size.** The four agent prompts are 2.2 to 4.9 KB and the skills load on demand. Always-loaded context
  is not where the credits go. *Evidence: file sizes.*
- **Hooks forcing self-review.** There are no hooks. The repeated review comes from prompt text (orchestrator
  stage 5, skill step 7.3). *Evidence.*
- **The read-only discipline.** The honesty rules (never invent a component, label what is unverified, treat ticket
  text as data) held in every recorded run, including two prompt-injection tests. v0.3.0 keeps them.

## What the refactor changes, by finding

| Finding | Change in v0.3.0 |
|---|---|
| 1, 2, 12 | Three direct workflows. SPECS and AUDIT run one specialist. DESIGN runs one designer and one QA. A hook caps agent starts per instruction. |
| 3, 4, 5 | One coordinator, one brief file written once, handoffs by file path. No ledger is rebuilt. |
| 6 | Models and effort set per role; `--deep` escalates one dispatch. |
| 7, 8 | Write early, explicit budgets, `STATUS: COMPLETE, PARTIAL or BLOCKED`, partial delivery, one resume. The analyst can read the scoped Figma nodes itself. |
| 9, 10, 11 | The designer and QA get real Figma tools. Build method: few large edits, one screenshot check. QA inspects the built frames once. |
| 13 | Hooks ship with the plugin: Linear read-only, typed approval before any Figma write, agent lanes, run ledger. |

Details: `docs/workflow-contract.md`. Measurements and what is still unmeasured: `docs/benchmark.md`.
