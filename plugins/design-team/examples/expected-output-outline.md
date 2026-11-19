# Expected outcome: an outline, not a generated transcript

What a correct run on `sample-ticket.md` should contain in v0.3.0. Real runs are recorded in `docs/validation.md`
of the repository once they exist.

## `/design-team:specs examples/sample-ticket.md`

- Agents run: 1 (`ux-analyst`). No orchestrator hop, no designer, no QA.
- `.design-team/sample-ticket/brief.md`: R1 to R7 and AC-01 to AC-05 copied verbatim, `Figma: none linked`, and the
  ticket's contradiction noted under gaps (the Role line says notifications are enabled; R6 covers members without
  permission).
- `.design-team/sample-ticket/specs.md`: user goal and business goal, assumptions labeled as such, a requirement
  challenge for the R6 contradiction, numbered flow, states (load, changed, saved, permission disabled, save failure
  and retry), accessibility, AC-01 to AC-05 kept with their ids and any additions labeled `proposed`.
- Component and contrast statements marked `not inspected`: the ticket supplies no Figma file.
- Scorecard: a specs self-check out of 100 computed by `scripts/score.sh`, at most three improvements, the open
  questions. `Linear: read-only, unchanged. Figma: unchanged.`

## `/design-team:audit <link to a frame>`

- Agents run: 1 (`ux-analyst`). Only the linked frames are read.
- `audit.md`: each frame marked inspected or not inspected, findings with node id, severity, recommended change and
  rationale, at most 12.
- Scorecard rates the audit (evidence, scope, actionability, severity). Nothing is scored if the scope could not be read.

## `/design-team:design <ticket> <Figma file and target>`

- Turn 1: `approach.md` (what and where, frames, component reuse table with names returned by the library search,
  decisions needed) and the line `Reply approve to apply this to Figma`. No Figma write has happened.
- After `approve`: frames built by `figma-designer`, `build.md` listing node ids, links and screenshots taken. The
  frames and links are reported before QA.
- `design-qa` once: `qa.md` and `scores.txt`, ratings with evidence, `na` for anything it could not inspect.
- At most one correction pass and one recheck. Scorecard with `Correction pass used: yes or no`.
- Without a Figma file: `STATUS: BLOCKED`, naming the missing file and target. Nothing is invented.
