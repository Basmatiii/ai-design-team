#!/usr/bin/env python3
"""Summarize a `claude -p --output-format stream-json --verbose` run of the design-team workflow.
Reports which agents actually ran, every tool call (and which agent made it), write attempts, permission
denials and the final result. Usage: python3 tests/analyze-run.py tests/out/run.jsonl [--calls tests/out/calls.log]"""
import json, sys, collections
path = sys.argv[1]
calls_log = sys.argv[sys.argv.index('--calls') + 1] if '--calls' in sys.argv else None
WRITE_HINTS = ('Write', 'Edit', 'NotebookEdit', 'Bash')
WRITE_WORDS = ('create', 'update', 'save', 'delete', 'archive', 'remove', 'assign', 'use_figma', 'upload', 'generate', 'send', 'add_')
agents = {}            # tool_use_id of an Agent call -> subagent_type
owner = {}             # tool_use_id -> agent label that made it
rows, denials, result, init = [], [], None, None
for line in open(path):
    try: e = json.loads(line)
    except ValueError: continue
    t = e.get('type')
    if t == 'system' and e.get('subtype') == 'init': init = e
    if t == 'assistant':
        par = e.get('parent_tool_use_id')
        who = agents.get(par, 'main' if par is None else f'agent:{par[-6:]}')
        for c in e['message'].get('content', []):
            if c.get('type') != 'tool_use': continue
            name, inp = c['name'], c.get('input', {})
            owner[c['id']] = who
            if name in ('Agent', 'Task'): agents[c['id']] = inp.get('subagent_type', '?')
            rows.append((who, name, {k: str(v)[:80] for k, v in inp.items() if k in ('subagent_type', 'file_path', 'pattern', 'id', 'issueId', 'parentId', 'fileKey', 'query', 'skill')}))
    if t == 'user':
        content = e['message'].get('content')
        for c in content if isinstance(content, list) else []:
            if c.get('type') == 'tool_result' and c.get('is_error'):
                txt = c.get('content'); txt = txt if isinstance(txt, str) else json.dumps(txt)
                denials.append((owner.get(c.get('tool_use_id'), '?'), txt[:200]))
    if t == 'result': result = e
print('== Agents that ran:', collections.Counter(agents.values()) or 'none')
print('== Tool calls (who, tool, key args):')
for r in rows: print('  ', r[0].ljust(32), r[1].ljust(34), r[2] or '')
writes = [r for r in rows if r[1] in WRITE_HINTS or (r[1].startswith('mcp__') and any(w in r[1].split('__')[-1] for w in WRITE_WORDS))]
print('== Write or mutation attempts:', writes or 'none')
print('== Tool errors / denials:', denials or 'none')
if calls_log:
    try: logged = [json.loads(l) for l in open(calls_log)]
    except FileNotFoundError: logged = []
    print('== Mock connector calls actually executed:', [(c['server'], c['tool']) for c in logged] or 'none')
    muts = [c for c in logged if any(w in c['tool'] for w in WRITE_WORDS)]
    print('== Mutations that reached a connector:', muts or 'NONE')
if result:
    print(f"== Result: {result.get('subtype')}, turns={result.get('num_turns')}, duration={round((result.get('duration_ms') or 0)/1000)}s, cost_usd={result.get('total_cost_usd')}")
if init: print('== CLI', init.get('claude_code_version'), 'model', init.get('model'))
