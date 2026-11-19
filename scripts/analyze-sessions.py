#!/usr/bin/env python3
"""Measure past design-team runs from Claude Code's own session transcripts on this computer.

Claude Code keeps a transcript of every session under ~/.claude/projects/<project>/<session>.jsonl, and of every
subagent under <session>/subagents/agent-<id>.jsonl (kept for about 30 days by default). This script reads them,
finds the sessions that used the design team, and reports what actually happened: how long each took, how many
agents ran, tool calls, repeated reads, tokens, and any sign that an agent ran out of turns.

    python3 scripts/analyze-sessions.py                    # every project
    python3 scripts/analyze-sessions.py --since 2026-10-01 # only sessions that started on or after that day
    python3 scripts/analyze-sessions.py --csv runs.csv     # also write one row per session

It only reads. It prints numbers and tool names, never ticket text, prompts or file contents, so the output is safe
to share. Transcript format is not a public contract and changes between Claude Code versions: the script skips
what it does not recognize and says how many lines it skipped, instead of guessing."""
import collections, csv, json, re, sys
from datetime import datetime
from pathlib import Path

args = sys.argv[1:]
def opt(flag, default=None): return args[args.index(flag) + 1] if flag in args else default
base = Path(opt('--dir', str(Path.home() / '.claude/projects')))
since = opt('--since')
OUT_OF_TURNS = re.compile(r'(max(imum)?[ _-]?turns|out of turns|turn limit|ran out of (its )?turns)', re.I)
READ_PREFIX = ('get_', 'list_', 'search_', 'extract_', 'whoami', 'download_')

def parse_time(s):
    try: return datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except (ValueError, TypeError): return None

def read(path):
    """Yield (event, None) for parsed lines and (None, 1) for unreadable ones."""
    try:
        with open(path, errors='ignore') as fh:
            for line in fh:
                try: yield json.loads(line), None
                except ValueError: yield None, 1
    except OSError:
        return

def scan(session_file):
    s = dict(file=session_file, team=False, commands=collections.Counter(), spawned=collections.Counter(), resumes=0,
             tools=collections.Counter(), reads=collections.Counter(), tokens=collections.Counter(), models=set(),
             out_of_turns=0, skipped=0, start=None, end=None, cost=None, seen=set(), subagent_files=0)
    files = [session_file] + sorted((session_file.parent / session_file.stem / 'subagents').glob('agent-*.jsonl'))
    s['subagent_files'] = len(files) - 1
    for f in files:
        for e, bad in read(f):
            if bad: s['skipped'] += 1; continue
            if not isinstance(e, dict): continue
            ts = parse_time(e.get('timestamp'))
            if ts:
                s['start'] = min(s['start'], ts) if s['start'] else ts
                s['end'] = max(s['end'], ts) if s['end'] else ts
            if e.get('type') == 'cost-state' and isinstance(e.get('totalCostUSD'), (int, float)): s['cost'] = e['totalCostUSD']
            msg = e.get('message') if isinstance(e.get('message'), dict) else {}
            content = msg.get('content')
            if e.get('type') == 'user':
                texts = [content] if isinstance(content, str) else [c.get('text') or c.get('content') for c in content or [] if isinstance(c, dict)]
                for t in texts:
                    t = t if isinstance(t, str) else json.dumps(t) if t else ''
                    for cmd in re.findall(r'/design-team:([a-z-]+)', t[:400]): s['commands'][cmd] += 1; s['team'] = True
                    if 'design-team' in str(f) or s['team']:
                        if OUT_OF_TURNS.search(t[-600:]) or OUT_OF_TURNS.search(t[:600]): s['out_of_turns'] += 1
            if e.get('type') == 'assistant':
                mid = msg.get('id')
                if mid and mid not in s['seen']:
                    s['seen'].add(mid); u = msg.get('usage') or {}
                    for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                        s['tokens'][k] += u.get(k) or 0
                    if msg.get('model') and not str(msg['model']).startswith('<'): s['models'].add(msg['model'])
                for c in content if isinstance(content, list) else []:
                    if not isinstance(c, dict) or c.get('type') != 'tool_use': continue
                    name, inp = c.get('name', '?'), c.get('input') or {}
                    s['tools'][name] += 1
                    if name in ('Agent', 'Task'):
                        st = str(inp.get('subagent_type', '?')); s['spawned'][st] += 1
                        if st.startswith('design-team:'): s['team'] = True
                    if name == 'SendMessage': s['resumes'] += 1
                    if name == 'Read' or (name.startswith('mcp__') and name.split('__')[-1].startswith(READ_PREFIX)):
                        s['reads'][(name, json.dumps(inp, sort_keys=True))] += 1
    return s

sessions = []
for f in sorted(base.glob('*/*.jsonl')):
    s = scan(f)
    if not s['team']: continue
    if since and s['start'] and s['start'].date().isoformat() < since: continue
    sessions.append(s)

if not sessions:
    sys.exit(f'No design-team sessions found under {base}. Transcripts are kept for a limited time, and only on the computer that ran them.')

rows = []
for s in sessions:
    team = sum(n for a, n in s['spawned'].items() if a.startswith('design-team:'))
    figma = sum(n for t, n in s['tools'].items() if 'figma' in t.lower())
    linear = sum(n for t, n in s['tools'].items() if 'linear' in t.lower())
    figma_writes = sum(n for t, n in s['tools'].items() if 'figma' in t.lower() and not t.split('__')[-1].startswith(READ_PREFIX))
    repeated = sum(n - 1 for n in s['reads'].values() if n > 1)
    minutes = round((s['end'] - s['start']).total_seconds() / 60, 1) if s['start'] and s['end'] else None
    rows.append(dict(
        date=s['start'].date().isoformat() if s['start'] else '?', session=s['file'].stem[:8],
        commands=' '.join(f'{k}x{v}' for k, v in s['commands'].items()) or '(agent only)',
        wall_minutes=minutes, design_team_agents=team,
        by_agent=' '.join(f"{a.split(':')[-1]}x{n}" for a, n in sorted(s['spawned'].items()) if a.startswith('design-team:')),
        resumes=s['resumes'], tool_calls=sum(s['tools'].values()), figma_calls=figma, figma_writes=figma_writes, linear_calls=linear,
        repeated_reads=repeated, out_of_turns_mentions=s['out_of_turns'],
        input_tokens=s['tokens']['input_tokens'] + s['tokens']['cache_creation_input_tokens'], cache_read_tokens=s['tokens']['cache_read_input_tokens'],
        output_tokens=s['tokens']['output_tokens'], cost_usd=s['cost'], models=' '.join(sorted(s['models'])), unreadable_lines=s['skipped']))

cols = list(rows[0])
print('| ' + ' | '.join(cols) + ' |'); print('|' + '---|' * len(cols))
for r in rows: print('| ' + ' | '.join('' if r[c] is None else str(r[c]) for c in cols) + ' |')
n = len(rows)
def avg(k):
    v = [r[k] for r in rows if isinstance(r[k], (int, float))]
    return round(sum(v) / len(v), 1) if v else 'n/a'
print(f'\n{n} design-team sessions. Averages per session: {avg("design_team_agents")} design-team agents, {avg("wall_minutes")} wall-clock minutes, '
      f'{avg("tool_calls")} tool calls, {avg("figma_calls")} Figma calls, {avg("repeated_reads")} repeated reads, {avg("output_tokens")} output tokens.')
print(f'Sessions with an out-of-turns mention: {sum(1 for r in rows if r["out_of_turns_mentions"])} of {n}.')
print('Notes: wall-clock minutes run from the first to the last transcript line, so they include time spent waiting for you. '
      'A session can hold several requests: divide by the command counts. cost_usd is present only when the transcript recorded it.')
if opt('--csv'):
    with open(opt('--csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print('wrote', opt('--csv'))
