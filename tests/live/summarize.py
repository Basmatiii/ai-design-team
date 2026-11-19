#!/usr/bin/env python3
"""Print one comparison table from the metrics.json files that tests/live/run-live.sh wrote.
Usage: python3 tests/live/summarize.py [tests/out]"""
import json, sys
from pathlib import Path
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'out')
rows = []
for f in sorted(out.glob('*/metrics.json')):
    m = json.loads(f.read_text()); t = m.get('tokens_total', {})
    rows.append((f.parent.name, m.get('duration_s'), m.get('cost_usd'), m.get('design_team_agents_started'), m.get('agent_resumes'),
                 m.get('tool_calls_total'), len(m.get('repeated_reads', [])), t.get('input_tokens', 0) + t.get('cache_creation_input_tokens', 0),
                 t.get('cache_read_input_tokens', 0), t.get('output_tokens', 0), 'yes' if not m.get('assertion_failures') else 'NO'))
if not rows: sys.exit(f'no metrics.json under {out}: run tests/live/run-live.sh first')
head = ('scenario', 'seconds', 'cost usd', 'agents', 'resumes', 'tool calls', 'repeated reads', 'input tok', 'cache read tok', 'output tok', 'checks passed')
print('| ' + ' | '.join(head) + ' |'); print('|' + '---|' * len(head))
for r in rows: print('| ' + ' | '.join(str(x) for x in r) + ' |')
