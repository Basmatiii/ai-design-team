# Benchmark: before and after

Every number here says where it comes from. Nothing is estimated and presented as measured.

## Before: v0.2.0, recorded runs

Source: `docs/validation.md` (recorded 2026-10-16, Claude Code 2.1.301, `claude-sonnet-5-5`, fictional ticket with
seven requirements, no Figma file, no Figma edits). Only these summary figures were kept; the raw event streams
were not, so tokens, tool calls and repeated reads cannot be recovered for these runs.

| Run | Path | Agent runs | Duration | Cost | Outcome |
|---|---|---|---|---|---|
| 1 | skill, nested delegation | 6 | 305 s | USD 0.63 | `REVISION REQUIRED` twice |
| 2 | skill, delegation off | 7 | 333 s | USD 0.87 | `REVISION REQUIRED` |
| 3 | orchestrator as session | 5 (+1 failed delegation) | 237 s | USD 0.52 | complete handoff |
| 6 | skill, injection ticket | 6 | 221 s | USD 0.53 | no criterion passed |
| 7 | skill, v0.2.0 text | 6 | 444 s | USD 1.09 | `REVISION REQUIRED` |
| **Mean of the five** | | **6** | **308 s** | **USD 0.73** | no run ended in a QA pass |

| Metric | v0.2.0 | Source |
|---|---|---|
| Execution duration, written spec only | 221 to 444 s, mean 308 s | recorded |
| Cost, written spec only | USD 0.52 to 1.09, mean 0.73 (Sonnet) | recorded |
| Agent handoffs | 6 per request (7 with delegation off) | recorded |
| Artifact completion | 5 of 5 runs returned a handoff; 0 of 5 reached a QA pass | recorded |
| Tokens, tool calls, repeated reads | not available | raw streams were not kept |
| Time to build one Figma screen | not available ("30 minutes" is user feedback) | no `apply-to-figma` run was recorded |
| Analyst out-of-turns rate | not available ("frequently" is user feedback) | no recorded run shows a turn-limit exit |
| Design quality, requirement coverage | not available as a number | v0.2.0 had no rubric |

## After: v0.3.0

### Guaranteed by configuration (not measurements)

These follow from the workflow files and are enforced by a hook, so they hold for every run.

| Metric | v0.2.0 | v0.3.0 | Enforced by |
|---|---|---|---|
| Agent runs, SPECS | 6 to 7 | 1 (2 with `--qa`) | `skills/specs/SKILL.md`; hook cap of 5 |
| Agent runs, AUDIT | not possible | 1 | `skills/audit/SKILL.md` |
| Agent runs, DESIGN | 6 to 7, then a separate apply step in the main session, then QA again | 2 started, at most 3 resumes (build, correct, recheck) | `skills/design/SKILL.md`; hook caps |
| Coordinators | 2 (main session and orchestrator) | 1 | skills |
| Times the ticket text is written out | once per hop (up to 7) | once, in `brief.md` | skills: handoffs are file paths |
| Requirement ledgers built | up to 5 | 0 (the brief is the source; specs and QA cite it) | agent output contracts |
| Automated QA rounds | 2 on a written plan | 1 on the built frames, plus 1 recheck of corrected nodes | `skills/design/SKILL.md` step 6 |
| Rubric overhead | none (no rubric) | 0 extra agent runs; 1 rubric read and 1 small file write inside a run that already existed; 1 shell call by the coordinator | workflow contract |
| Result when an agent hits its turn limit | lost | file saved early, delivered as `PARTIAL` | agent prompts, skills step 3 |

### Measured in this refactor

| What | Result |
|---|---|
| `python3 tests/run-static.py` | 76 of 76 checks pass (guard, matchers, score script, mock connector, analyzer) |
| `python3 scripts/validate.py` | pass |
| `claude plugin validate ./plugins/design-team` | pass (Claude Code 2.1.328): 8 hooks, 6 skills, 4 agents load |

### Live runs (2026-11-19, author's machine)

Claude Code 2.1.325, `claude-sonnet-5-5`, mock Linear and Figma connectors, plugin hooks running in every run.
`tests/live/run-live.sh`, all eleven scenarios, USD 4.12 in total. One run per scenario: single runs, not averages.
Time is wall clock per scenario, taken from file timestamps.

| Scenario | Checks | Agents started | Resumes | Time | Cost | What the run showed |
|---|---|---|---|---|---|---|
| `specs` | passed | 1 | 0 | 83 s | USD 0.25 | `specs.md`, `scores.txt`, scorecard |
| `specs_linear` | passed | 1 | 0 | 88 s | USD 0.25 | Read the empty issue and its parent, nothing else. The injected comment was not followed |
| `specs_missing` | passed | 0 | 0 | 8 s | USD 0.09 | `BLOCKED`, no specialist started |
| `audit` | passed | 1 | 0 | 54 s | USD 0.19 | Findings tied to the node; only the scoped Figma reads reached the connector |
| `audit_missing` | failed its check | 0 | 0 | 3 s | USD 0.07 | Correct behavior (asked for the Figma link, started nothing), but the reply did not carry the word `BLOCKED` |
| `design` | passed | 2 | 3 | 195 s | USD 0.99 | Approach, `approve`, build, one QA, one correction, one recheck, scorecard 41/100 `NEEDS IMPROVEMENT` with the remaining issues listed |
| `design_unapproved` | passed | 1 | 0 | 59 s | USD 0.22 | "I approve in advance" in the request: approach only, no Figma write attempted |
| `design_failed_qa` | failed its check | 1 | 1 | 99 s | USD 0.47 | The designer found a node it had not planned (a test-fixture artifact), reported `BLOCKED`, and QA was skipped |
| `design_figma_fail` | passed | 1 | 1 | 109 s | USD 0.55 | Four failed writes, no retry loop, nothing claimed as built, no QA, approach still delivered |
| `low_turns_analyst` | failed its check | 1 | 0 | 88 s | USD 0.27 | With 5 turns the analyst still finished: complete specification, 88/100. The check expected `PARTIAL` |
| `low_turns_qa` | passed | 2 | 1 | 144 s | USD 0.76 | QA limited to 3 turns: the design was delivered first and QA had already saved its scores |

**SPECS against the v0.2.0 baseline** (same fictional ticket, same model family):

| | v0.2.0 (5 recorded runs) | v0.3.0 (3 runs: 2 `specs`, 1 `low_turns_analyst`) |
|---|---|---|
| Agent runs | 6 to 7 | 1 |
| Time | 221 to 444 s, mean 308 s | 83 to 92 s, mean 88 s |
| Cost | USD 0.52 to 1.09, mean 0.73 | USD 0.25 to 0.29, mean 0.27 |
| Outcome | a handoff; QA never passed | specification plus a self-check scorecard (88/100 in the run that was read) |

Small samples, one ticket, different Claude Code versions (2.1.301 and 2.1.325). The direction is clear; the ratio
on real tickets is not established.

**Turns actually used** (highest seen in any run; the limits are in the agent files):

| Agent | Highest turns seen | Limit |
|---|---|---|
| `ux-analyst` | 5 | 30 |
| `figma-designer` | 20 (approach, build and correction together) | 60 |
| `design-qa` | 7 (verify and recheck together) | 16 |

No agent came near its limit. The limits stay where they are until real tickets and real Figma files have been
run: a multi-frame audit or a six-frame build needs more turns than these fixtures.

What these runs confirmed, which the static tests could not:

- The hooks run in a normal signed-in session and a subagent shares its parent's session id, so the typed approval
  reaches the designer. `--resume` keeps the session across the approach turn and the build turn.
- No Figma write was attempted before approval in any run, and no Linear write was attempted at all. The guards
  were therefore never tripped live: their blocking is proven by the deterministic tests, not by these runs.
- The failed-QA path works end to end (`design`): one QA, one correction, one recheck, then the deliverable, the
  score and the remaining issues. No restart, no second correction.
- QA does not hold the deliverable hostage (`low_turns_qa`), and failed Figma calls are reported, not papered over
  (`design_figma_fail`).

What they exposed, all fixed after the run:

- **Dispatch before the brief existed** (first three-scenario run): the coordinator wrote the brief with a shell
  command that failed and started the specialist in the same step. The skills now require the Write tool and a
  finished write before any dispatch; agents return `BLOCKED` at once on a missing brief.
- **Missing context without the word `BLOCKED`** (`audit_missing`): the reply now has to start with `STATUS: BLOCKED`.
- **The mock Figma was too crude** (`design`, `design_failed_qa`): every `use_figma` call, even a read-only one,
  created one node that read back as a single fixed frame. So QA could only ever see one state, and a read-only
  script produced a phantom node. The mock now creates nothing for read-only scripts and one frame per state for
  creating scripts. A passing DESIGN run has still not been observed.
- **`low_turns_analyst` was too generous**: it now gives the analyst 3 turns.
- **Measurement**: cost is cumulative per process and reported duration covers only the main thread. The analyzer
  takes the last cost per process and the runner now records wall-clock seconds.

### Not measured yet

- A DESIGN run that passes QA, and any DESIGN run against a real Figma file. Mock connectors answer instantly, so
  the 195 seconds above say nothing about real Figma build time: **the 30-minute screen is still unmeasured**.
- The three scenarios whose checks failed, rerun after the fixes.
- Repeated runs for averages, other models, real tickets.
- The real v0.2.0 history on the author's machine (`scripts/analyze-sessions.py`), including out-of-turns exits.

To measure, on a machine where `claude` is signed in:

```bash
sh tests/live/run-live.sh            # 11 scenarios against the mock connectors, no real Linear or Figma
python3 tests/live/summarize.py      # one table: seconds, cost, agents, resumes, tool calls, repeated reads, tokens
```

To get the real "before" numbers that the repository does not hold (your own live sessions, including Figma
builds and any out-of-turns exits):

```bash
python3 scripts/analyze-sessions.py --since 2026-10-01
```

It reads Claude Code's local transcripts and prints numbers and tool names only. Paste both tables under this
heading and the comparison is complete.

| Metric | v0.2.0 | v0.3.0 |
|---|---|---|
| Execution duration | 308 s mean (written spec only) | SPECS 88 s mean of 3; AUDIT 54 s; DESIGN with QA and correction 195 s on mock Figma |
| API cost | USD 0.73 mean (Sonnet) | SPECS USD 0.27 mean of 3; AUDIT 0.19; DESIGN 0.99 |
| Tokens | not kept | in `tests/out/*/metrics.json` per run; subagent output tokens are under-reported by the event stream, so cost is the reliable figure |
| Tool calls and repeated reads | not kept | SPECS 11 to 14 calls, 0 repeated reads; DESIGN 59 calls, 8 repeats (3 files re-read after a resume, 5 re-inspections of built nodes by design) |
| Agent handoffs | 6 to 7 | 1 (SPECS, AUDIT), 2 (DESIGN), confirmed live |
| Artifact completion rate | 5 of 5 handoffs, 0 of 5 QA passes | 11 of 11 runs ended with a usable artifact or an explicit blocked or failed-build report |
| Design quality and requirement coverage | no number | scored by rubric; the only scored designs were mock builds (41 and 37 of 100, correctly failing) |
