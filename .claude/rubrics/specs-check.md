# Specs quality check (SPECS mode)

<!-- weights: coverage=40 behavior=25 states=25 testability=10 threshold=85 floor=3 -->

A small self-check the `ux-analyst` runs once, at the end of its own run, on the specification it just wrote.
It is not independent QA and must be labeled `self-check` in the scorecard. No extra agent is started for it.
Nothing visual is scored here: a specification has no visual result to inspect.

Weighted total = SUM(weight * rating / 5), out of 100. **Pass** = 85 or more, no rating below 3, no hard blocker.
Scale: 5 fully meets, 4 minor gaps, 3 acceptable with noticeable gaps, 2 significant gaps, 1 mostly fails, 0 absent.

## Criteria

### coverage: requirements coverage (40%)
- 5: every requirement and acceptance criterion in the brief appears in the specification with its source.
- 3: all core requirements covered; one or two secondary ones missing or left without a source.
- 1: a core requirement is missing or changed.
- Evidence: the count `covered / total` and the ids that are missing.

### behavior: flows and interaction behavior (25%)
- 5: the main flow is numbered start to end and every interaction says what the user does and what the system does.
- 3: the main flow is complete; some interactions are described only as outcomes.
- 1: no usable flow.
- Evidence: the flow section and any step without a system response.

### states: states, edge cases and accessibility (25%)
- 5: every state that applies to this ticket is specified, plus keyboard, focus, labels and error association.
- 3: the main states are covered; one applicable state or one accessibility point is missing.
- 1: happy path only.
- Evidence: the list of applicable states marked specified or missing. States that do not apply are not gaps.

### testability: acceptance criteria quality (10%)
- 5: every acceptance criterion is an observable outcome a tester could check without asking a question.
- 3: most are testable; a few are vague.
- 1: criteria restate the requirement without an observable outcome.
- Evidence: the ids of any vague criteria.

## Hard blockers

1. A core requirement from the ticket is missing or contradicted.
2. An assumption is presented as a fact (anything not in the source must be labeled `assumption`).
3. A component, token or screen is described as existing without having been inspected.
4. The ticket could not be read and the specification was written anyway.

## Scores file

`.design-team/<id>/scores.txt`:

```text
mode=specs
coverage=5
behavior=4
states=4
testability=4
blockers=0
```

List at most three improvements. If Figma frames were linked but could not be read, say so in the scorecard: the
check still runs on the text, and the specification must mark those parts `not inspected`.
