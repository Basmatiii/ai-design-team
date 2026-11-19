---
name: review-spec
description: Runs the independent Design QA agent once on an existing written specification, against its ticket, with the specs quality check. Review only, one pass, no revision loop.
disable-model-invocation: true
argument-hint: "specification file, then the ticket file or Linear issue id"
allowed-tools: Bash(sh *scripts/score.sh*)
---

# Review spec

Review input: **$ARGUMENTS**

1. Do not read the files yourself. Rubric path: use the `design-team: rubric specs-check = <path>` line the plugin added to this prompt. If there is no
such line, use `${CLAUDE_PLUGIN_ROOT}/rubrics/specs-check.md`.
2. Start `design-team:design-qa` once:

   ```text
   MODE: REVIEW
   SPEC: <specification path>
   TICKET: <ticket or brief path>
   RUBRIC: <specs-check rubric path>
   ```

   For a Linear issue, first write the brief as in `/design-team:specs` step 1 (one read-only issue read) and pass
   the brief path as `TICKET`.
3. Run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/score.sh" "<rubric path>" "<scores.txt path QA returned>"` and present
   the scorecard: overall score, pass or needs improvement, criterion ratings with evidence, hard blockers, at most
   three improvements, the artifact paths. One pass: no revision, no second review.
4. Review only. Nothing is edited in the specification, in Figma or in Linear.
