# SAMPLE-104: Add reminder frequency to a notification settings form

**Status:** Fictional demo ticket. No relation to any actual client or product.
**Product:** Pollen, a fictional gardening journal application.
**Surface:** Settings → Reminders.
**Role:** Signed-in member who has notifications enabled.
**Parent reference:** `example-project-context.md` (included with this demo).

## User story

As a member, I want to choose how often the app reminds me to water my plants so I can avoid duplicate reminders.

## Requirements

- R1: Add a `Reminder frequency` selector to the existing Reminders settings form.
- R2: Options are `Every day`, `Every 2 days`, and `Every week`.
- R3: Show the current saved value when the page loads. Existing accounts default to `Every week` if unset.
- R4: Saving updates the selection for future reminders; no retroactive reminders are created.
- R5: If saving fails, keep the user's selected value visible and show a retryable error.
- R6: Members without notification permission can view the setting but cannot save until permission is enabled.
- R7: Existing notification toggle remains unchanged.

## Acceptance criteria

- AC-01: A signed-in, enabled member can see and select one of the three frequencies.
- AC-02: The saved frequency is displayed on subsequent visits.
- AC-03: The permission-disabled state is visible and correctly explains why Save is unavailable.
- AC-04: Save failures are announced accessibly and allow retry without losing the chosen value.
- AC-05: Both LTR and RTL layouts retain label/value meaning, especially numeric options.

## Out of scope

- Notification delivery backend, push permission prompts, email channel settings, scheduler frequency logic.

## Known gaps / questions

- No existing Figma file, tokens or component IDs are supplied here. Reuse claims must remain **unverified** until a real library is inspected.
- Exact API state names and error codes are not supplied; do not make them up.
