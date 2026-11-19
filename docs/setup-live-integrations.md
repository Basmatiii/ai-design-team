# Install, connect, test, publish

## Requirements

- Claude Code with plugin support, signed in.
- Python 3.10+ and PyYAML only for the optional static validator. Node.js only for the optional mock-connector tests.
- No external accounts for the fictional sample.

## Local test

```bash
python3 scripts/validate.py
python3 tests/run-static.py
claude plugin validate ./plugins/design-team
claude plugin validate .
claude --plugin-dir ./plugins/design-team
```

Inside the session, from the release folder:

```text
/design-team:specs examples/sample-ticket.md
```

Check that one agent ran (`ux-analyst`), that `.design-team/sample-ticket/specs.md` exists, and that the reply ends
with a scorecard.

## Live scenarios with evidence

`tests/live/run-live.sh` starts real Claude Code sessions against the mock connectors in `tests/mock-mcp/` (fictional
data, every call logged) and checks each run with `tests/analyze-run.py`. It needs a signed-in `claude`, Node.js for
the mock server, and it uses credits.

```bash
sh tests/live/run-live.sh                  # all 11 scenarios
sh tests/live/run-live.sh specs audit      # only these
python3 tests/live/summarize.py            # seconds, cost, agents, tool calls, repeated reads, tokens per scenario
```

The scenarios cover SPECS, AUDIT, DESIGN with its approval turn, missing context, a failed QA run, an inaccessible
design, failed Figma calls and low turn budgets. No real Linear or Figma workspace is touched.

## Real Linear intake

Connect a trusted Linear integration in your Claude Code environment and check which of its tools read issues and
parents. Do not assume a connection is read-only because the skill asks for read operations: add the deny rules from
`docs/permissions.md`, and prefer a provider-side read-only token or scope when available. Never commit tokens.

## Real Figma inspection and edits

Agents read only the nodes you link. For edits, run `/design-team:design` with the ticket and the exact Figma file,
page and frame. The designer shows its approach first; nothing changes until you type `approve`. Your account needs
edit access to the file. Check the result yourself afterwards: the scorecard says what was and was not verified.

If an agent reports that it has no Figma tools, your connector is registered under a name the agent allowlists do
not include. Run `/mcp` to see the name, then `python3 scripts/sync-connector-aliases.py --figma <name>` in a clone.

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

## Before publishing a fork or a new version

1. Run the validator, `tests/run-static.py` and both plugin validations; fix every warning.
2. Run `tests/live/run-live.sh` and keep the summary table in `docs/benchmark.md`.
3. Test with live Linear and Figma connections on non-sensitive data.
4. Keep the MIT notice with every copy (`LICENSE`).
5. Confirm rights to everything published. No client artifacts, tickets, links or credentials.
