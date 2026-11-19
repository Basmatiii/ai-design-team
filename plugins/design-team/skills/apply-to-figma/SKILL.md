---
name: apply-to-figma
description: Applies an already written specification to an exact Figma location through the DESIGN workflow. The approach is still shown first and the person still has to type approve before anything changes.
disable-model-invocation: true
argument-hint: "specification file, Figma file URL, exact page and frame"
allowed-tools: Bash(sh *scripts/score.sh*)
---

# Apply to Figma

Request: **$ARGUMENTS**

This is the DESIGN workflow with a specification you already have. Read
`${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` and follow it from step 1 (in that file `${CLAUDE_PLUGIN_ROOT}` stands for the plugin folder it is in), with two
differences:

1. Add `SPEC: <path of the specification>` to the designer's dispatch, and name that path in the brief under
   "Constraints and context".
2. If the exact file, page and frame are not all given, stop and ask. Do not pick a location.

Starting this command is not an approval. The approval gate in step 3 of the DESIGN workflow still applies: the
person types `approve` after seeing the approach, and the plugin hook denies every Figma write before that.
