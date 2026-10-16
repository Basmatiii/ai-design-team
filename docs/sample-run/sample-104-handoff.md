# Sample run: SAMPLE-104 final handoff

Unedited output of validation run 7 (`docs/validation.md`): Claude Code 2.1.301, headless,
`/design-team:design-ticket examples/sample-ticket.md`. Fictional ticket and product. Dashes normalized only.

---

# SAMPLE-104 handoff: Reminder frequency (Pollen, Settings → Reminders)

**QA verdict: `REVISION REQUIRED`.** It came back twice, so this is a reviewable proposal and not an approved design.

## Stage record
| Stage | Run by | How sources were accessed |
|---|---|---|
| Source gathering | main session | `examples/sample-ticket.md` and `examples/example-project-context.md`, both read as local files |
| Library evidence | none | The ticket names no Figma file or library, so: `No library evidence supplied` |
| Intake and ledger | design-orchestrator | |
| UX analysis | ux-analyst | |
| Design spec, rev 0 and rev 1 | figma-designer | |
| QA rounds 1 and 2 | design-qa | |

The orchestrator delegated to all three specialists. I did not need to dispatch any of them myself.

Two handoff shortcuts in the orchestrator's run:
- For round 2 it condensed the designer's "Changes in response to QA" table instead of passing it verbatim. QA flagged this as issue 8.
- For the revision it did not resend the full UX output to the designer.

## Traceability
| Requirement | Acceptance criterion | Status |
|---|---|---|
| R1 selector on existing form | AC-01 | specified, not visually verified |
| R2 three options | AC-01 | specified, not visually verified |
| R3 saved value on load, default `Every week` | AC-02 | specified (see issue 4) |
| R4 future reminders only | none in the ticket | `proposal`: the analyst added AC-07, which is not designable. It is backend behavior, so QA cannot test it. |
| R5 failure keeps value, retryable error | AC-04 | specified, not visually verified. Screen-reader announcement is untested. |
| R6 no permission: view only, cannot save | AC-03 | partial, blocked on Q1-Q3 |
| R7 toggle unchanged | `proposal`: the analyst added AC-08 | holds only if Save is separate (S1). Not claimed if Save is shared (S2). |
| AC-05 LTR/RTL meaning | AC-05 | partial. Arabic copy is unavailable. |
| Component reuse, tokens, contrast | none | `BLOCKED (missing evidence)` / `unverified` |

AC-06 to AC-08 are `proposal`s from the analyst. The ticket's own list stops at AC-05.

The ticket contradicts itself. The Role line says "member who has notifications enabled", but R6 covers members without notification permission.

## Open QA issues
- **High**
  - B2 (read-only selector) is drawn as the headline permission frame. That leans toward settling Q2, and R6's wording fits B1 better. Draw B1 and B2 with equal prominence, or label B2 as adding behavior beyond R6.
  - The Tier 1 "14 frames" count doesn't match its 7 listed items. Make the count explicit.
- **Medium**
  - The helper line is called both "recommended, not optional" and R4's only UI expression. Require it, or say R4 has no UI expression.
  - R3 needs the saved value on load, but the loading frame is optional.
  - The focus order omits the permission notice.
  - A focusable `aria-disabled` Save (D2) does nothing when pressed. Specify whether it announces the reason.
  - E2's claim that the chosen value is retained is untested. Keep E1 as the baseline.
  - The condensed "Changes in response to QA" table (see above).
- **Low**
  - State that the Saving frame is deliberately left out of desktop.
  - The numeral question also affects Arabic text inside English contexts.
  - Label the "about 40%" string-expansion figure as a placeholder assumption.

## Human decisions needed
1. **Q1:** What does "notification permission" mean (OS/browser grant, in-app toggle or entitlement)? Who sees the form, and what enables permission?
2. **Q2:** Is the selector changeable without permission (B1) or read-only (B2)?
3. **Q3:** Is Save shared with the toggle (S2) or separate (S1)? If shared, how should the toggle behave under a permission block, given R7?
4. **Q5:** What is the new-account default, and is the shown default saved before the first Save?
5. **Q4:** Approved Arabic copy and numeral system, from a translator.
6. **Q13:** After a failed save and a reload, does the form show the last saved value or the failed choice?
7. **Q7:** How should "no retroactive reminders" be tested, given it is backend behavior?
8. **Also needed:**
   - A real Figma file or library.
   - Design values for contrast.
   - Desktop breakpoints.
   - Whether a loading or load-failed state is wanted.
   - Whether a success message is wanted.

## Next step
Revise or stop. Don't approve. QA's remaining issues can be fixed without new evidence, but that takes a third designer revision and QA pass, beyond the one-revision limit. Tell me if you want that extra round. Or answer Q1-Q3 first, since they decide the permission frames. I have not run `/design-team:apply-to-figma`. Only you can start it, and it should wait until the spec passes QA and a real library has been inspected.

**Changes made: None, proposal only**