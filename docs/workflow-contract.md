# Workflow contract

Default flow: **ticket, Orchestrator, UX Analyst, Figma Designer, Design QA, human review.**

| Stage | Runs as | Inputs | Outputs | Remote changes |
|---|---|---|---|---|
| Sources | Main session (`design-ticket` skill) | Local ticket, pasted text, or a Linear issue read through a connected tool; its parent when the child lacks requirements; read-only Figma library evidence when connected | Source packet | None (reads only) |
| Intake | `design-orchestrator` | Source packet | Evidence ledger, specialist briefs | None |
| Understand | `ux-analyst` | Ledger and sources | Flows, acceptance criteria, state matrix, open questions | None |
| Specify | `figma-designer` | UX brief, inspected library evidence | Frame and state plan, component reuse ledger, copy | None |
| Verify | `design-qa` | Original ticket, ledger, specification | Evidence-rated scorecard, issues, checklist | None |
| Handoff | `design-orchestrator` | All outputs | Final handoff with stage record | None |
| Decide | A person | Handoff | Approve, revise or stop | None |
| Apply (opt-in) | `apply-to-figma` skill, started by a person | Approved spec, exact file, page and frame | Edits to that frame only, then QA | Authorized Figma scope only |

## Delegation

The orchestrator delegates to the three specialists itself when it can (it runs as the main thread with
`claude --agent design-team:design-orchestrator`, or as a subagent when nested delegation is enabled, which is
Claude Code's default). When delegation is not available, for example if `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`,
it returns intake only (`DELEGATION: unavailable`) and the `design-ticket` skill dispatches the specialists from the
main session, then asks the orchestrator to reconcile. No stage is ever written by a different agent and presented
as independent.

## Data contract

Every requirement is labeled `verified from source`, `inferred` or `unknown`.
QA uses `PASS (verified)`, `SPECIFIED (not visually verified)`, `FAIL` or `BLOCKED (missing evidence)`, and a
verdict of `READY FOR DESIGN REVIEW`, `REVISION REQUIRED` or `BLOCKED BY EVIDENCE`.

## Parent tickets and component evidence

- If a child ticket has no description, no acceptance criteria, or defers to its parent, the parent is read (read
  only) and cited as the source. If it cannot be read, the gap is a Blocker question, never a guess.
- The Figma designer maps every element to inspected components first. `reusable` requires evidence; anything else
  is `new component proposal, needs design-system owner approval` or `proposal / unverified`.

Human-readable instructions are not a permission system. See `docs/permissions.md` for the enforced layers.
