# Install, connect, test, publish

## Requirements

- Claude Code with plugin support, signed in.
- Python 3.10+ and PyYAML only for the optional static validator. Node.js only for the optional mock-connector tests.
- No external accounts for the fictional sample.

## Local test

```bash
python3 scripts/validate.py
claude plugin validate ./plugins/design-team
claude plugin validate .
claude --plugin-dir ./plugins/design-team
```

Inside the session, from the release folder:

```text
/design-team:design-ticket examples/sample-ticket.md
```

Check that the orchestrator, UX analyst, Figma designer and Design QA each ran (the handoff has a stage record),
that QA judged the original acceptance criteria, and that nothing outside the conversation changed.

## Headless test with evidence

```bash
claude -p "/design-team:design-ticket examples/sample-ticket.md" --plugin-dir ./plugins/design-team \
  --strict-mcp-config --allowedTools Read Glob Grep Agent Skill --output-format stream-json --verbose > tests/out/run.jsonl
python3 tests/analyze-run.py tests/out/run.jsonl
```

## Mock Linear and Figma (no accounts)

`tests/mock-mcp/server.mjs` imitates both connectors with fictional data and logs every call to `tests/out/calls.log`.

```bash
mkdir -p tests/out
claude -p "/design-team:design-ticket SAMPLE-105 (a Linear issue). The design system is in the Figma file POLLEN-DEMO." \
  --plugin-dir ./plugins/design-team --settings settings/read-only-guard.json \
  --mcp-config tests/mcp-config.json --strict-mcp-config \
  --allowedTools Read Glob Grep Agent Skill mcp__linear__get_issue mcp__linear__list_issues mcp__linear__list_comments \
    mcp__figma__get_metadata mcp__figma__search_design_system \
  --output-format stream-json --verbose > tests/out/linear.jsonl
python3 tests/analyze-run.py tests/out/linear.jsonl --calls tests/out/calls.log
```

SAMPLE-105 has an empty description, so the run should read its parent SAMPLE-100. One of its comments contains a
prompt injection that asks for a state change; the expected result is that no write reaches the mock server.

## Real Linear intake

Connect a trusted Linear integration in your Claude Code environment and check which of its tools read issues and
parents. Do not assume a connection is read-only because the skill asks for read operations: add the deny rules from
`docs/permissions.md`, and prefer a provider-side read-only token or scope when available. Never commit tokens.

## Real Figma inspection and edits

The workflow inspects library components with read-only Figma tools when a file is named. For edits, a person runs
`/design-team:apply-to-figma` with the exact approved file, page, frame and spec, through a tool with real edit access,
with Figma write tools set to `ask`. Check the result yourself afterwards.

## Local marketplace test

```bash
claude plugin marketplace add .
claude plugin install design-team@basma-ai-tools
claude plugin list
```

From GitHub:

```bash
claude plugin marketplace add Basmatiii/ai-design-team
claude plugin install design-team@basma-ai-tools
```

## Before a public release

1. Run the validator, both plugin validations and the headless test; fix every warning.
2. Run the mock-connector test and keep the guard result.
3. Test against a real, non-sensitive Linear workspace and a test Figma file.
4. Keep the MIT notice with every copy (`LICENSE`).
5. Confirm rights to everything published. No client artifacts, tickets, links or credentials.
