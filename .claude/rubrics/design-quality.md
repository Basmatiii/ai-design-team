# Design quality rubric (DESIGN mode)

<!-- weights: requirements=25 ux=25 system=20 accessibility=20 craft=10 threshold=85 floor=3 -->

Used once per design, by `design-qa`, on the finished Figma result. The designer builds to these criteria but does
not score itself. `scripts/score.sh` reads the weights line above, so this file is the single source of truth.

Weighted total = SUM(weight * rating / 5), out of 100.
**Pass** = total of 85 or more, no rating below 3, and no unresolved hard blocker.

## Evidence rule

A rating counts only with evidence you inspected in this run: a screenshot you took, node metadata or design
context you read (cite the node id), a variable or component search result, or a quoted requirement from the brief.

- No evidence inspected for a criterion: write `na`, never a number. A design with any `na` cannot pass.
- Never rate from the designer's description, the approach document or memory.
- One line of evidence per rating is enough. Do not write essays.

## Scale

| Rating | Meaning |
|---|---|
| 5 | Fully meets the criterion. Nothing to fix. |
| 4 | Meets it, with minor issues that do not affect the user's task. |
| 3 | Acceptable. Noticeable gaps, none of them blocking. |
| 2 | Significant gaps. A user or a developer would be misled or slowed down. |
| 1 | Mostly fails the criterion. |
| 0 | Absent, or contradicts the source. |

## Criteria

### requirements: requirements coverage (25%)
- 5: every requirement and acceptance criterion in the brief maps to a visible element or state in the built frames.
- 3: all core requirements are present; one or two secondary ones are missing or only partly shown.
- 1: a core requirement is missing or contradicted.
- Evidence: requirement id next to the node id that satisfies it.

### ux: UX and interactions (25%)
- 5: the primary task is obvious, the reading order and action hierarchy support it, and the flow has no dead ends.
- 3: the task can be completed, with friction: an unclear primary action, an extra step, weak feedback.
- 1: a user cannot tell what to do next, or the flow breaks.
- Evidence: the screenshot plus the step where the friction happens.

### system: design-system consistency (20%)
- 5: every element that has a library component is an instance of it; colors, type and spacing use variables or styles.
- 3: mostly instances; a few detached layers or hard-coded values.
- 1: mostly hand-drawn layers where library components exist.
- Evidence: instance and variable usage read from metadata or design context. A component named in the report that is
  not found in the frame or the library is a hard blocker, not a low score.

### accessibility: accessibility and states (20%)
- 5: the states the brief calls for exist (for example empty, loading, error, disabled, focus); text contrast and
  target sizes meet WCAG 2.2 AA where they can be measured from real values; controls have visible labels.
- 3: the main states exist; one applicable state or one measurable accessibility point is missing.
- 1: only the happy path is drawn, or a measured contrast or target size clearly fails.
- Evidence: the state frames by node id; contrast only from real color values, otherwise say `contrast not measurable`.
- Only states that apply to this ticket count. Do not penalize a state the brief rules out.

### craft: visual craftsmanship (10%)
- 5: consistent spacing rhythm and alignment, auto layout throughout, clear layer names, no clipped or overlapping content.
- 3: tidy overall; a few misalignments or one frame without auto layout.
- 1: visibly uneven spacing, overlaps, or clipped text.
- Evidence: the screenshot. No screenshot means `na`.

## Hard blockers

Any one of these blocks a pass whatever the number says. Count the unresolved ones in `blockers=`.

1. A critical usability failure: the user cannot complete the primary task.
2. A critical accessibility failure: for example a required control with no label, or measured text contrast far below AA.
3. A materially unmet requirement: a core requirement or acceptance criterion is missing or contradicted.
4. Fabricated component usage: a component, variant, token or library that was reported as used and does not exist.
5. An unverified Figma claim: something reported as built, changed or visually checked with no successful tool result
   behind it (check `.design-team/run-ledger.tsv` when it exists).
6. An unauthorized edit: a change outside the approved frames, or any Figma write that was attempted before approval.

## Scores file

Write `.design-team/<id>/scores.txt`, one `key=value` per line, nothing else:

```text
mode=design
requirements=4
ux=4
system=5
accessibility=3
craft=4
blockers=0
correction_pass=no
```

## Improvements

List at most three, most valuable first, each as: what to change, where (node id), why. Minor issues never justify a
redesign: name the smallest change that fixes the issue.
