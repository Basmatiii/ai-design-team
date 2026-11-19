#!/usr/bin/env python3
"""Measure one `claude -p --output-format stream-json --verbose` run of a design-team workflow.

Reports, from the event stream only (nothing is estimated):
  agents started by type, agent messages (resumes), turns and tokens per agent, every tool call and who made it,
  repeated reads (the same read tool with the same arguments more than once), write attempts, tool errors,
  duration and cost as Claude Code reported them.

Usage:
  python3 tests/analyze-run.py run.jsonl [more.jsonl ...] [--calls tests/out/calls.log] [--json metrics.json]
      [--max-agents N] [--max-resumes N] [--expect-file PATH_OR_GLOB] [--expect-text TEXT] [--forbid-text TEXT]
      [--no-linear-writes] [--no-figma-writes] [--quiet]

Several .jsonl files are treated as one run (for example the approach turn and the approve turn of DESIGN).
Assertion flags make the script exit 1 when they fail, so it can be used as a test."""
import collections, glob, json, os, re, sys

args = sys.argv[1:]
def opt(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default
def opts(flag):
    return [args[i + 1] for i, a in enumerate(args[:-1]) if a == flag]
VALUE_FLAGS = ('--calls', '--json', '--max-agents', '--max-resumes', '--expect-file', '--expect-text', '--forbid-text')
paths, skip = [], False
for a in args:
    if skip: skip = False; continue
    if a in VALUE_FLAGS: skip = True; continue
    if a.startswith('--'): continue
    paths.append(a)
if not paths: sys.exit(__doc__)

WRITE_TOOLS = ('Write', 'Edit', 'NotebookEdit', 'Bash')
READ_PREFIX = ('get_', 'list_', 'search_', 'extract_', 'whoami', 'download_')
def is_mcp_write(name):
    return name.startswith('mcp__') and not name.split('__')[-1].startswith(READ_PREFIX)
def server_kind(name):
    low = name.lower()
    return 'linear' if 'linear' in low else 'figma' if 'figma' in low else 'other'

last_result = {}                 # path -> the last result event of that file
agents = {}                      # tool_use_id of an Agent call -> subagent_type
owner = {}                       # tool_use_id -> who made the call
rows, errors, results, init = [], [], [], None
hooks_off = []
seen_msg = set()
turns = collections.Counter()
tokens = collections.defaultdict(collections.Counter)
models = collections.defaultdict(set)
final_text = []

for path in paths:
    for line in open(path):
        try: e = json.loads(line)
        except ValueError: continue
        t = e.get('type')
        if t == 'system' and e.get('subtype') == 'init': init = e
        if t == 'system' and 'Hooks not running' in str(e.get('content', '')): hooks_off.append(str(e['content'])[:300])
        if t == 'assistant':
            par = e.get('parent_tool_use_id')
            who = agents.get(par, 'main' if par is None else f'agent:{str(par)[-6:]}')
            msg = e.get('message', {})
            mid = msg.get('id')
            if mid not in seen_msg:          # one API response can arrive as several events: count it once
                seen_msg.add(mid); turns[who] += 1
                u = msg.get('usage') or {}
                for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                    tokens[who][k] += u.get(k) or 0
                if msg.get('model'): models[who].add(msg['model'])
            for c in msg.get('content', []):
                if c.get('type') != 'tool_use': continue
                name, inp = c['name'], c.get('input', {}) or {}
                owner[c['id']] = who
                if name in ('Agent', 'Task'): agents[c['id']] = inp.get('subagent_type', '?')
                rows.append((who, name, inp))
        if t == 'user':
            content = e.get('message', {}).get('content')
            for c in content if isinstance(content, list) else []:
                if c.get('type') == 'tool_result' and c.get('is_error'):
                    txt = c.get('content'); txt = txt if isinstance(txt, str) else json.dumps(txt)
                    errors.append((owner.get(c.get('tool_use_id'), '?'), txt[:200]))
        if t == 'result':
            results.append(e); final_text.append(str(e.get('result') or '')); last_result[path] = e

spawned = collections.Counter(agents.values())
team_spawned = sum(n for a, n in spawned.items() if a.startswith('design-team:'))
resumes = sum(1 for r in rows if r[1] == 'SendMessage')
by_tool = collections.Counter(r[1] for r in rows)
read_keys = collections.Counter(
    (r[1], json.dumps(r[2], sort_keys=True)) for r in rows
    if r[1] == 'Read' or (r[1].startswith('mcp__') and not is_mcp_write(r[1])))
repeated = {k: n for k, n in read_keys.items() if n > 1}
writes = [r for r in rows if r[1] in WRITE_TOOLS or is_mcp_write(r[1])]
linear_writes = [r for r in writes if server_kind(r[1]) == 'linear']
figma_writes = [r for r in writes if server_kind(r[1]) == 'figma']
total_tokens = collections.Counter()
for c in tokens.values(): total_tokens.update(c)
# A run with background agents emits several result events. Their durations cover only the main thread's active
# time, and total_cost_usd is cumulative within one process: take the last result of each file, never the sum.
active = sum((r.get('duration_ms') or 0) for r in results) / 1000
cost = sum((r.get('total_cost_usd') or 0) for r in last_result.values())
wall_file = os.path.join(os.path.dirname(paths[0]), 'wall-seconds.txt')
wall = sum(int(x) for x in open(wall_file).read().split()) if os.path.isfile(wall_file) else None
duration = wall if wall is not None else active
text = '\n'.join(final_text)
status = re.findall(r'STATUS:\s*(COMPLETE|PARTIAL|BLOCKED)', text)
score = re.findall(r'(\d+)/100', text)

metrics = {
    'files': paths, 'plugin_hooks_running': not hooks_off, 'duration_s': round(duration), 'duration_is_wall_clock': wall is not None, 'main_thread_active_s': round(active), 'cost_usd': round(cost, 4),
    'design_team_agents_started': team_spawned, 'agents_started_by_type': dict(spawned), 'agent_resumes': resumes,
    'turns_by_agent': dict(turns), 'tokens_by_agent': {k: dict(v) for k, v in tokens.items()},
    'tokens_total': dict(total_tokens), 'models_by_agent': {k: sorted(v) for k, v in models.items()},
    'tool_calls_total': len(rows), 'tool_calls_by_tool': dict(by_tool),
    'repeated_reads': [{'tool': k[0], 'args': k[1][:120], 'times': n} for k, n in repeated.items()],
    'figma_calls': sum(n for t, n in by_tool.items() if server_kind(t) == 'figma'),
    'linear_calls': sum(n for t, n in by_tool.items() if server_kind(t) == 'linear'),
    'write_attempts': [(r[0], r[1]) for r in writes], 'tool_errors': len(errors),
    'result_subtypes': [r.get('subtype') for r in results], 'status_lines': status, 'scores_seen': score,
}

if '--quiet' not in args:
    print('== Agents started:', dict(spawned) or 'none', '| design-team agents:', team_spawned, '| resumes (SendMessage):', resumes)
    print('== Turns by agent:', dict(turns))
    for who, c in tokens.items():
        print(f"   tokens {who.ljust(30)} in={c['input_tokens']} cache_write={c['cache_creation_input_tokens']} cache_read={c['cache_read_input_tokens']} out={c['output_tokens']} model={','.join(sorted(models[who])) or '?'}")
    print('== Tool calls:', len(rows), dict(by_tool))
    print('== Repeated reads:', metrics['repeated_reads'] or 'none')
    print('== Write or mutation attempts:', metrics['write_attempts'] or 'none')
    print('== Tool errors and denials:', errors or 'none')
    print(f"== Result: {metrics['result_subtypes']}, duration={metrics['duration_s']}s ({'wall clock' if wall is not None else 'main thread only'}), cost_usd={metrics['cost_usd']}")
    if init: print('== CLI', init.get('claude_code_version'), 'model', init.get('model'))

failed_runs = [str(r.get('result'))[:160] for r in results if r.get('is_error')]
if failed_runs:
    print('== RUN DID NOT EXECUTE:', failed_runs)
    print('   Nothing below was tested. Sign in to Claude Code (run `claude` once) and try again.')
    sys.exit(2)
fails = []
if hooks_off:
    # Without its hooks the plugin's enforcement (Linear read-only, Figma approval gate, agent lanes) is off.
    fails.append('the plugin hooks were NOT running in this session, so its guards were not in effect: ' + hooks_off[0])
calls_log = opt('--calls')
if calls_log:
    try: logged = [json.loads(l) for l in open(calls_log) if l.strip()]
    except FileNotFoundError: logged = []
    reached = [(c['server'], c['tool']) for c in logged]
    muts = [c for c in reached if not c[1].startswith(READ_PREFIX)]
    metrics['connector_calls_reached'] = reached; metrics['connector_mutations_reached'] = muts
    if '--quiet' not in args:
        print('== Connector calls that reached the mock server:', reached or 'none')
        print('== Mutations that reached a connector:', muts or 'NONE')
    if '--no-linear-writes' in args and any(s == 'linear' for s, _ in muts): fails.append('a Linear mutation reached the connector')
    if '--no-figma-writes' in args and any(s == 'figma' for s, _ in muts): fails.append('a Figma mutation reached the connector')
else:
    if '--no-linear-writes' in args and linear_writes: fails.append(f'Linear write attempted: {[r[1] for r in linear_writes]}')
    if '--no-figma-writes' in args and figma_writes: fails.append(f'Figma write attempted: {[r[1] for r in figma_writes]}')

if opt('--max-agents') is not None and team_spawned > int(opt('--max-agents')):
    fails.append(f'{team_spawned} design-team agents started, limit {opt("--max-agents")}')
if opt('--max-resumes') is not None and resumes > int(opt('--max-resumes')):
    fails.append(f'{resumes} agent resumes, limit {opt("--max-resumes")}')
for f in opts('--expect-file'):
    hits = [h for h in glob.glob(f) if os.path.isfile(h) and os.path.getsize(h) > 0]
    if not hits: fails.append(f'expected artifact missing or empty: {f}')
for s in opts('--expect-text'):
    if s.lower() not in text.lower(): fails.append(f'final reply does not contain: {s}')
for s in opts('--forbid-text'):
    if s.lower() in text.lower(): fails.append(f'final reply contains forbidden text: {s}')

metrics['assertion_failures'] = fails
if opt('--json'):
    with open(opt('--json'), 'w') as fh: json.dump(metrics, fh, indent=2)
if fails:
    print('== ASSERTIONS FAILED:'); [print('   -', f) for f in fails]; sys.exit(1)
if any(f in args for f in ('--max-agents', '--max-resumes', '--expect-file', '--expect-text', '--forbid-text', '--no-linear-writes', '--no-figma-writes')):
    print('== Assertions passed')
