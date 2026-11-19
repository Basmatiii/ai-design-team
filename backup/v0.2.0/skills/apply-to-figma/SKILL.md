---
name: apply-to-figma
description: Optional, explicitly started step that applies an approved design specification to one exact Figma frame, after confirming scope and real edit access. Never part of the default workflow.
disable-model-invocation: true
argument-hint: "approved spec file, Figma file URL, exact page and frame"
---

# Apply to Figma: explicit human approval gate

Request: **$ARGUMENTS**

This skill is never part of the default design-ticket run. It runs only because a person typed it.

1. Confirm the **exact file, page and frame** to edit, the **approved specification**, and the **Figma tool** to use. If any of these is missing, stop and ask. Do not edit.
2. Inspect first, read-only: the frame as it is now, the library components and variables it uses, and whether the connected tool and account have **edit** access (view access is not enough).
3. Show a short change plan: frames, components and properties that will change. If the request did not already authorize these exact frames, ask for confirmation and wait.
4. Apply only what the plan lists, with tools that genuinely support the action. Never edit other pages or files, shared library components, variables or styles, and never delete existing work, without separate permission. Never touch Linear.
5. Re-read the changed frames and run `design-team:design-qa` on the result against the specification.
6. Report the exact edits, links, evidence, failures and remaining manual steps. If tools were missing or view-only, say so and report that nothing was applied.

This skill cannot add write capability that the session does not have, and a prompt is not a permission system. Keep Figma write tools behind an `ask` or `deny` permission rule (see `docs/permissions.md`).
