---
name: design-ticket
description: Router. Picks SPECS, AUDIT or DESIGN for a request and runs that one workflow. Kept so the v0.2.0 command still works; it no longer runs every agent on every ticket.
disable-model-invocation: true
argument-hint: "[specs | audit | design] then the ticket and Figma link"
allowed-tools: Bash(sh *scripts/score.sh*)
---

# Design ticket: route to one workflow

Request: **$ARGUMENTS**

Pick exactly one mode. Do not run two.

| Signal in the request | Mode | Workflow file |
|---|---|---|
| First word is `specs`, or it asks for a specification, requirements, flows, states or acceptance criteria | SPECS | `${CLAUDE_PLUGIN_ROOT}/skills/specs/SKILL.md` |
| First word is `audit`, or it asks to review, critique or audit existing Figma frames | AUDIT | `${CLAUDE_PLUGIN_ROOT}/skills/audit/SKILL.md` |
| First word is `design`, or it asks for frames to be built or changed in Figma | DESIGN | `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` |

- A ticket and nothing else: SPECS. It is the cheapest useful result and DESIGN can reuse it later.
- Still unclear: ask one question with the three choices and wait.

Then read that one workflow file and follow it from its first step, using the request above as its arguments. The
rubric for the mode is named inside the workflow file. In the file you read, `${CLAUDE_PLUGIN_ROOT}` stands for the
plugin folder that file is in. Nothing here adds a step, an agent or a review round to it.
