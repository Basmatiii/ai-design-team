# Audit quality check (AUDIT mode)

<!-- weights: evidence=35 scope=25 actionability=25 severity=15 threshold=85 floor=3 -->

A small self-check the `ux-analyst` runs once, at the end of its own run, on the audit it just wrote. It rates the
**audit**, not the audited design: the design's own problems are the audit's findings. It is labeled `self-check`
in the scorecard and starts no extra agent.

Weighted total = SUM(weight * rating / 5), out of 100. **Pass** = 85 or more, no rating below 3, no hard blocker.
Scale: 5 fully meets, 4 minor gaps, 3 acceptable with noticeable gaps, 2 significant gaps, 1 mostly fails, 0 absent.

## Criteria

### evidence: evidence behind each finding (35%)
- 5: every finding cites the node id it was observed on and what was inspected (screenshot, metadata, variables).
- 3: most findings cite a node; a few are general observations.
- 1: findings are generic best-practice statements with no node behind them.
- Evidence: the count `findings with a node id / total findings`.

### scope: coverage of the requested scope (25%)
- 5: every frame in the requested scope was inspected, and nothing outside it was read.
- 3: most frames inspected; the rest are listed as `not inspected` with the reason.
- 1: a small part of the scope was inspected and the audit does not say so.
- Evidence: the list of frames, each marked inspected or not inspected.

### actionability: actionable recommendations (25%)
- 5: every finding has a specific change, where to make it, and the reason.
- 3: recommendations exist but several are vague ("improve hierarchy").
- 1: findings without recommendations.
- Evidence: the ids of findings without a specific change.

### severity: severity calibration (15%)
- 5: every finding has a severity that follows the definitions (Critical, High, Medium, Low) and preferences are
  not reported as findings.
- 3: severities assigned; a few look inflated or deflated.
- 1: no severities, or everything is High.
- Evidence: the severity counts.

## Hard blockers

1. A finding about a frame that was not inspected.
2. A fabricated node id, component name, measurement or contrast value.
3. The Figma scope could not be read and findings were written anyway.
4. Any attempt to edit Figma during an audit.

## Scores file

`.design-team/<id>/scores.txt`:

```text
mode=audit
evidence=5
scope=4
actionability=4
severity=4
blockers=0
```

If the scope could not be inspected at all, do not score: write `evidence=na` and `scope=na`, return
`STATUS: BLOCKED`, and list what is needed. An uninspected design is never rated.
