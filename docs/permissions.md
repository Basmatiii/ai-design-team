# Permissions: keep Linear read-only and Figma edits explicit

Written instructions shape behavior. They do not enforce it. This toolkit puts each guardrail where Claude Code can
actually hold it.

## What is enforced by the toolkit itself

| Guardrail | Where it lives | Enforced by |
|---|---|---|
| The four agents can only read and search | `tools:` in each agent's frontmatter (`Read, Glob, Grep`, plus `Agent` for the orchestrator) | Claude Code's tool allowlist |
| The agents have no connector access | No `mcp__` tools in any agent's `tools:` list | Claude Code's tool allowlist |
| The workflow skills never start on their own | `disable-model-invocation: true` on all three skills | Claude Code: only a person can invoke them |

Plugin agents cannot carry `hooks`, `mcpServers` or `permissionMode` (Claude Code ignores those fields in plugin
agents for security reasons), so the toolkit does not rely on them.

## What you enforce in your project

The **main session** that runs `/design-team:design-ticket` can see whatever connectors you have connected. If your
Linear or Figma connector exposes write tools, block them with deny rules. Copy the `permissions` block from
`settings/read-only-guard.json` into your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "mcp__*inear*__create_*", "mcp__*inear*__update_*", "mcp__*inear*__save_*",
      "mcp__*inear*__delete_*", "mcp__*inear*__archive_*", "mcp__*inear*__remove_*", "mcp__*inear*__assign_*",
      "mcp__*igma*__use_figma", "mcp__*igma*__create_*", "mcp__*igma*__upload_*",
      "mcp__*igma*__generate_*", "mcp__*igma*__send_*", "mcp__*igma*__add_*", "mcp__*igma*__update_*"
    ]
  }
}
```

- Deny rules accept globs in the tool-name position and always win over allow rules.
- `*inear*` and `*igma*` match a server however you named it (`linear`, `Linear`, `claude_ai_Linear`).
- Connector tool names change. Run `/mcp`, list your servers' tools and add any write tool these patterns miss.
- Prefer a provider-side read-only token or scope for Linear when one is available. Two layers are better than one.

## When you do want Figma edits

`/design-team:apply-to-figma` needs a Figma write tool. For that session only, move the Figma entries from `deny`
to `ask`, so every write still shows you a confirmation:

```json
{ "permissions": { "ask": ["mcp__*igma*__use_figma"] } }
```

Keep the Linear entries in `deny`.

## How this was tested

See `docs/validation.md`. The guard was tested against a mock Linear and Figma server
(`tests/mock-mcp/`) that logs every call it receives: with the guard, a direct request to change an issue never
reached the server; without it, the same request did.
