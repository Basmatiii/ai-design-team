# Permissions: what is enforced, and by what

Written instructions shape behavior. They do not enforce it. v0.3.0 ships its guardrails inside the plugin, so they
apply as soon as the plugin is enabled, with no file to copy.

## Enforced by the plugin

| Guardrail | Mechanism | What it does |
|---|---|---|
| Linear is read-only | `hooks/hooks.json` PreToolUse + `hooks/guard.sh linear-write` | Any Linear tool that is not `get_`, `list_`, `search_` or `extract_` is denied once a `/design-team` workflow has started in the session, and always for design-team agents. New write tools are covered automatically, because the rule lists what is allowed, not what is forbidden. |
| Figma edits need the person | UserPromptSubmit + `guard.sh figma-write` | Every Figma write tool is denied until the person types `approve` (also `approved`, `approve design`). The approval lasts 120 minutes or until the next `/design-team` command, whichever comes first. `revoke` withdraws it. Wording such as "yes" or "go ahead" does not count. |
| Only the designer edits Figma | Agent allowlists + `guard.sh figma-write` | `use_figma` appears only in `figma-designer`'s `tools:`. The hook also denies Figma writes from the analyst, QA and the orchestrator even after approval. |
| No generated images or new files | `figma-designer` allowlist | The designer has reads and `use_figma`. No `generate_*`, `create_new_file`, `upload_*`. |
| One ticket at a time | `design-orchestrator` allowlist | The orchestrator agent has `get_issue` and `list_comments` only: it cannot list or search issues. Specialists have no Linear tools at all. (When the main session coordinates, this rule is prompt text: see below.) |
| Agents write only their artifacts | `guard.sh agent-scope` | design-team agents may write `.md`, `.json` and `.txt` inside `.design-team/` only. No HTML, no code, no file elsewhere in the project. They may load Figma usage skills only, and the orchestrator may run the score script only. |
| No runaway handoffs | `guard.sh dispatch` | At most 5 design-team agents started and 6 agent messages after one instruction from the person. |
| A record of what happened | PostToolUse, PostToolUseFailure, SubagentStop | `.design-team/run-ledger.tsv` logs each Figma and Linear call (tool, node id, ok or fail), each blocked attempt and each agent start and stop. The DESIGN scorecard is checked against it. |
| Workflows never start on their own | `disable-model-invocation: true` on all six skills | Only a person can start a workflow. |

Both write guards use `onFailure: block`: if the hook cannot run, the write is blocked, not allowed. If the session
cannot be identified, both guards behave as if a workflow were active.

**Scope.** The guards apply to sessions that have run a `/design-team` command, and to design-team agents. An
unrelated Claude Code session can still use your Linear and Figma connectors normally. To keep Linear read-only in
every session while the plugin is enabled, set `DESIGN_TEAM_LINEAR_LOCK=always` in your environment.

## Limits you should know

- **Hooks can be switched off above the plugin.** An organization policy (managed settings) can stop plugin hooks
  from running, and Claude Code also disables them when it cannot read the organization's settings. It then shows
  a notice that begins "Mods and hooks you set up aren't running in this session". In such a session none of the
  hook guards above are in effect: only the agent allowlists and your own permission rules remain. If you see that
  notice, add the second layer below before running DESIGN. `tests/analyze-run.py` fails any live run in which the
  hooks were not running.
- **The hook script is plain `sh`.** On Windows without Git Bash it cannot run, so Linear and Figma writes are
  blocked outright in design-team sessions (reads work). Install Git Bash to use DESIGN there.
- **Connector names.** Agent allowlists need the exact connector name. The common names for Figma and Linear are
  included; if `/mcp` shows yours under another name, run `python3 scripts/sync-connector-aliases.py --figma <name>`
  in a local clone. The hook guards do not depend on this list: they match any server whose name contains "figma"
  or "linear".
- **The main session is yours.** When you run a workflow as a slash command, the main session coordinates with
  whatever tools your session has. The hooks still stop Linear writes and unapproved Figma writes there, but
  "read one ticket only" is an instruction for the main session, not a tool limit. Starting with
  `claude --agent design-team:design-orchestrator` makes it a tool limit.
- **The approval is typed text.** The hook accepts the exact word in a prompt event. Keep the second layer below so
  that a Figma write also shows Claude Code's own confirmation.

## Second layer, in your project (recommended)

Copy the `permissions` block from `settings/read-only-guard.json` into your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "mcp__*inear*__create_*", "mcp__*inear*__update_*", "mcp__*inear*__save_*",
      "mcp__*inear*__delete_*", "mcp__*inear*__archive_*", "mcp__*inear*__remove_*", "mcp__*inear*__assign_*",
      "mcp__*igma*__create_*", "mcp__*igma*__upload_*", "mcp__*igma*__generate_*", "mcp__*igma*__send_*"
    ],
    "ask": ["mcp__*igma*__use_figma", "mcp__*igma*__update_*", "mcp__*igma*__add_*"]
  }
}
```

- Deny rules always win, in every session of that project, with or without the plugin.
- With `use_figma` under `ask`, a Figma edit needs both the typed `approve` (plugin hook) and your confirmation in
  Claude Code's own prompt. Choose "allow for this session" there to avoid a prompt per edit.
- Prefer a provider-side read-only token or scope for Linear when one is available.

## How this is tested

`python3 tests/run-static.py` feeds the guard script the same JSON Claude Code sends to hooks and checks every rule
above, including attempts to get around them (an extra `agent_type` argument, a second session id, key names inside
a script string, `..` in a path, a chained shell command). The hook matchers are run as JavaScript regular
expressions against 263 tool names: real Linear and Figma tools under five and six connector names. `tests/live/run-live.sh`
repeats the important cases in real sessions against a mock connector that logs every call it receives.
