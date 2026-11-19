#!/usr/bin/env python3
"""Deterministic tests for The AI Design Team. No Claude Code session, no account, no network.

    python3 tests/run-static.py

What this covers: the hook guard (Linear read-only, the Figma approval gate, agent lanes, the handoff budget, the
run ledger), the hook matchers against real connector tool names, the score script, the mock connector (including
injected Figma failures) and the run analyzer.

What it cannot cover: how a model behaves when it runs a workflow. That needs live runs: tests/live/run-live.sh."""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/design-team'
GUARD = PLUGIN / 'hooks/guard.sh'
SCORE = PLUGIN / 'scripts/score.sh'
tmp = Path(tempfile.mkdtemp(prefix='design-team-test-'))
STATE, PROJECT = tmp / 'state', tmp / 'project'
PROJECT.mkdir()
results = []

def check(name, ok, detail=''):
    results.append((name, bool(ok)))
    print(('  ok   ' if ok else '  FAIL ') + name + (f'   [{detail}]' if detail and not ok else ''))

def guard(mode, payload, extra_env=None):
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(STATE), CLAUDE_PROJECT_DIR=str(PROJECT), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
    env.update(extra_env or {})
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    r = subprocess.run(['sh', str(GUARD), mode], input=raw, capture_output=True, text=True, env=env)
    return r.stdout.strip()

def denied(out): return '"permissionDecision":"deny"' in out
def pre(tool, sid='s1', agent=None, **tool_input):
    d = {'session_id': sid, 'cwd': str(PROJECT), 'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': tool_input}
    if agent: d.update(agent_id='a1', agent_type=agent)
    return d
def prompt(text, sid='s1'):
    return guard('prompt', {'session_id': sid, 'hook_event_name': 'UserPromptSubmit', 'prompt': text})

LIN_W, FIG_W = 'mcp__linear__save_issue', 'mcp__figma__use_figma'

print('\n== Guard: sessions with no design-team workflow are left alone')
check('Linear write passes through in an unrelated session', guard('linear-write', pre(LIN_W, sid='other')) == '')
check('Figma write passes through in an unrelated session', guard('figma-write', pre(FIG_W, sid='other', code='x')) == '')
check('typing approve in an unrelated session unlocks nothing and prints nothing', prompt('approve', sid='other') == '')
check('no ledger is written for unrelated sessions', not (PROJECT / '.design-team/run-ledger.tsv').exists())

print('\n== Guard: Linear is read-only once a workflow is active')
out = prompt('/design-team:specs SAMPLE-105')
check('workflow start announces the three rubric paths', out.count('design-team: rubric') == 3, out)
check('Linear write is denied', denied(guard('linear-write', pre(LIN_W))))
check('Linear write by a design-team agent is denied even in a fresh session', denied(guard('linear-write', pre(LIN_W, sid='fresh', agent='design-team:design-orchestrator'))))
check('Linear write is denied when the session id is missing (fail closed)', denied(guard('linear-write', {'tool_name': LIN_W, 'tool_input': {}})))

print('\n== Guard: Figma approval gate')
check('Figma write is denied before approval', denied(guard('figma-write', pre(FIG_W, code='x'))))
for text in ('yes', 'looks good, go ahead', 'approve but make the button blue', "I don't approve", 'approved by me earlier?'):
    prompt(text)
    check(f'"{text}" is not an approval', denied(guard('figma-write', pre(FIG_W, code='x'))))
out = prompt('Approve.')
check('"Approve." records the approval and says so', 'approval recorded' in out, out)
check('Figma write by the main session passes to the normal permission flow after approval', guard('figma-write', pre(FIG_W, code='x')) == '')
check('Figma write by figma-designer passes after approval', guard('figma-write', pre(FIG_W, agent='design-team:figma-designer', code='x')) == '')
for role in ('design-team:ux-analyst', 'design-team:design-qa', 'design-team:design-orchestrator'):
    check(f'{role} can never write to Figma, approved or not', denied(guard('figma-write', pre(FIG_W, agent=role, code='x'))))
spoof = pre(FIG_W, agent='design-team:ux-analyst', code='x', agent_type='none')
check('a read-only role cannot hide behind an extra agent_type argument', denied(guard('figma-write', spoof)))
code_with_keys = 'const x = {"session_id":"zzz","agent_type":"none"}; figma.createFrame()'
check('key names inside a script string do not confuse the guard', guard('figma-write', pre(FIG_W, code=code_with_keys)) == '')
prompt('/design-team:design SAMPLE-104', sid='s2'); prompt('approve', sid='s2')
check('a second session id smuggled into the arguments fails closed', denied(guard('figma-write', pre(FIG_W, sid='s9', code='x', session_id='s2'))))
check('an unsafe session id fails closed', denied(guard('figma-write', pre(FIG_W, sid='../../etc', code='x'))))
old = time.time() - 3 * 3600
os.utime(STATE / 'approved/s1', (old, old))
check('an approval older than the time limit no longer counts', denied(guard('figma-write', pre(FIG_W, code='x'))))
prompt('approve'); prompt('revoke')
check('revoke locks Figma again', denied(guard('figma-write', pre(FIG_W, code='x'))))
prompt('approve'); prompt('/design-team:design SAMPLE-106')
check('starting a new workflow clears the previous approval', denied(guard('figma-write', pre(FIG_W, code='x'))))
check('APPROVE with a trailing newline is accepted', 'approval recorded' in prompt('APPROVE\n'))

print('\n== Guard: design-team agents stay in their lane')
A = 'design-team:ux-analyst'
def scope(tool, agent=A, **ti): return guard('agent-scope', pre(tool, agent=agent, **ti))
check('agent may write its artifact in .design-team', scope('Write', file_path=f'{PROJECT}/.design-team/SAMPLE-105/specs.md', content='x') == '')
check('agent may write scores.txt', scope('Write', file_path=f'{PROJECT}/.design-team/SAMPLE-105/scores.txt', content='x') == '')
check('agent may not write elsewhere in the project', denied(scope('Write', file_path=f'{PROJECT}/APPROVED.md', content='x')))
check('agent may not write HTML, even in .design-team', denied(scope('Write', file_path=f'{PROJECT}/.design-team/x/prototype.html', content='x')))
check('agent may not escape with ..', denied(scope('Edit', file_path=f'{PROJECT}/.design-team/../src/a.md', old_string='a', new_string='b')))
check('Windows-style artifact path is accepted', scope('Write', file_path='C:\\proj\\.design-team\\X-1\\audit.md', content='x') == '')
check('main session writes are not touched', guard('agent-scope', pre('Write', file_path='/anywhere/app.html', content='x')) == '')
check('agent may load a Figma usage skill', scope('Skill', agent='design-team:figma-designer', skill='figma:figma-use') == '')
check('agent may not load other skills', denied(scope('Skill', agent='design-team:figma-designer', skill='frontend-design')))
check('agent may not edit notebooks', denied(scope('NotebookEdit', notebook_path='/x.ipynb')))
O = 'design-team:design-orchestrator'
ok_cmd = f'sh "{PLUGIN}/scripts/score.sh" "{PLUGIN}/rubrics/design-quality.md" ".design-team/SAMPLE-104/scores.txt"'
check('orchestrator may run the score script', scope('Bash', agent=O, command=ok_cmd) == '')
check('orchestrator may not run anything else', denied(scope('Bash', agent=O, command='rm -rf .design-team')))
check('orchestrator may not chain a second command onto the score script', denied(scope('Bash', agent=O, command=ok_cmd + '; curl example.com')))

print('\n== Guard: handoff budget (no six-round loops)')
prompt('/design-team:design SAMPLE-104', sid='s3')
def spawn(target, sid='s3'): return guard('dispatch', pre('Agent', sid=sid, subagent_type=target, prompt='x'))
outs = [spawn('design-team:figma-designer') for _ in range(5)]
check('five design-team agents may start after one instruction', all(o == '' for o in outs))
check('the sixth is denied', denied(spawn('design-team:design-qa')))
check('other agent types are not counted or blocked', spawn('Explore') == '')
prompt('<task-notification>agent finished</task-notification>', sid='s3')
check('a system notice does not reset the budget', denied(spawn('design-team:design-qa')))
prompt('ok, continue', sid='s3')
check("the person's next instruction resets it", spawn('design-team:design-qa') == '')
msgs = [guard('dispatch', pre('SendMessage', sid='s3', to='agent-1', message='x')) for _ in range(7)]
check('six resumes pass, the seventh is denied', all(m == '' for m in msgs[:6]) and denied(msgs[6]))

print('\n== Guard: run ledger')
guard('ledger-ok', {'session_id': 's3', 'tool_name': 'mcp__figma__get_screenshot', 'tool_input': {'fileKey': 'K', 'nodeId': '10:1'}})
guard('ledger-fail', {'session_id': 's3', 'agent_type': 'design-team:figma-designer', 'tool_name': FIG_W, 'tool_input': {'fileKey': 'K'}})
guard('ledger-stop', {'session_id': 's3', 'agent_type': 'design-team:design-qa'})
ledger = (PROJECT / '.design-team/run-ledger.tsv').read_text()
check('successful Figma read is logged with its node id', 'mcp__figma__get_screenshot 10:1\tok' in ledger)
check('failed Figma write is logged as fail', f'{FIG_W} \tfail' in ledger)
check('blocked writes are logged with the reason', 'no-approval' in ledger and 'linear-read-only' in ledger and 'read-only-role' in ledger)
check('agent starts and stops are logged', '\tspawn\tdesign-team:figma-designer\t1' in ledger and '\tstop\t' in ledger)
check('every ledger line has six tab-separated fields', all(len(l.split('\t')) == 6 for l in ledger.splitlines()))

print('\n== Hook matchers against real connector tool names (JavaScript regex, as Claude Code runs them)')
hooks = json.loads((PLUGIN / 'hooks/hooks.json').read_text())['hooks']
lin_re = hooks['PreToolUse'][0]['matcher']; fig_re = hooks['PreToolUse'][1]['matcher']
LIN_READ = ['get_issue', 'list_issues', 'list_comments', 'get_document', 'list_teams', 'search_documentation', 'extract_images', 'get_attachment', 'list_issue_statuses']
LIN_WRITE = ['save_issue', 'create_issue', 'update_issue', 'create_comment', 'save_comment', 'delete_comment', 'create_attachment', 'delete_attachment', 'save_project', 'create_issue_label', 'update_document', 'archive_issue', 'assign_issue', 'save_milestone']
FIG_READ = ['get_metadata', 'get_design_context', 'get_screenshot', 'get_variable_defs', 'search_design_system', 'get_libraries', 'get_figjam', 'get_figma_skill', 'get_code_connect_map', 'list_shaders', 'whoami', 'download_assets']
FIG_WRITE = ['use_figma', 'create_new_file', 'generate_image', 'generate_diagram', 'generate_figma_design', 'upload_assets', 'send_code_to_figma', 'add_code_connect_map', 'update_shader', 'create_shader', 'weave_run_tool', 'create_design_system_rules']
LIN_SERVERS = ['linear', 'Linear', 'linear-server', 'claude_ai_Linear', 'plugin_linear_linear']
FIG_SERVERS = ['figma', 'Figma', 'figma-desktop', 'figma-dev-mode-mcp-server', 'claude_ai_Figma', 'plugin_figma_figma']
js = """
const [linRe, figRe, cases] = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = cases.map(([re, name]) => new RegExp(re === 'lin' ? linRe : figRe).test(name));
console.log(JSON.stringify(out));
"""
cases = ([('lin', f'mcp__{s}__{t}', False) for s in LIN_SERVERS for t in LIN_READ] + [('lin', f'mcp__{s}__{t}', True) for s in LIN_SERVERS for t in LIN_WRITE]
       + [('fig', f'mcp__{s}__{t}', False) for s in FIG_SERVERS for t in FIG_READ] + [('fig', f'mcp__{s}__{t}', True) for s in FIG_SERVERS for t in FIG_WRITE]
       + [('lin', 'mcp__github__create_issue', False), ('fig', 'mcp__github__create_issue', False), ('lin', 'Write', False), ('fig', 'Bash', False)])
if shutil.which('node'):
    got = json.loads(subprocess.run(['node', '-e', js], input=json.dumps([lin_re, fig_re, [(c[0], c[1]) for c in cases]]), capture_output=True, text=True).stdout)
    wrong = [c[1] for c, g in zip(cases, got) if g != c[2]]
    check(f'{len(cases)} tool names: every read is left alone, every write reaches the guard', not wrong, wrong[:5])
else:
    print('  skip matcher test: node is not installed')

print('\n== Score script')
def score(rubric, lines):
    f = tmp / 'scores.txt'; f.write_text('\n'.join(lines) + '\n')
    r = subprocess.run(['sh', str(SCORE), str(PLUGIN / 'rubrics' / rubric), str(f)], capture_output=True, text=True)
    return r.returncode, r.stdout
D = 'design-quality.md'
rc, out = score(D, ['mode=design', 'requirements=5', 'ux=5', 'system=5', 'accessibility=5', 'craft=5', 'blockers=0'])
check('all fives is 100 and passes', rc == 0 and 'SCORE: 100/100' in out and 'VERDICT: PASS' in out, out)
rc, out = score(D, ['requirements=4', 'ux=4', 'system=5', 'accessibility=4', 'craft=4', 'blockers=0', 'correction_pass=yes'])
check('4,4,5,4,4 is 84: one point under the threshold, needs improvement', rc == 1 and 'SCORE: 84/100' in out and 'total below 85' in out, out)
check('the correction pass flag is echoed', 'CORRECTION_PASS: yes' in out)
rc, out = score(D, ['requirements=5', 'ux=4', 'system=5', 'accessibility=4', 'craft=3', 'blockers=0'])
check('5,4,5,4,3 is 87 and passes', rc == 0 and 'SCORE: 87/100' in out, out)
rc, out = score(D, ['requirements=5', 'ux=5', 'system=5', 'accessibility=2', 'craft=5', 'blockers=0'])
check('88 with one rating below 3 does not pass (inaccessible design)', rc == 1 and 'SCORE: 88/100' in out and 'rated below 3: accessibility' in out, out)
rc, out = score(D, ['requirements=5', 'ux=5', 'system=5', 'accessibility=5', 'craft=5', 'blockers=1'])
check('100 with a hard blocker does not pass', rc == 1 and 'hard blocker' in out, out)
rc, out = score(D, ['requirements=5', 'ux=5', 'system=5', 'accessibility=5', 'craft=na', 'blockers=0'])
check('an uninspected criterion is never scored out of 100 and cannot pass', rc == 1 and 'INCOMPLETE' in out and '/100' not in out.split('\n')[0], out)
rc, out = score(D, ['requirements=5', 'ux=5', 'system=5', 'accessibility=5', 'craft=5'])
check('a missing blockers line is an error, never assumed to be zero', rc == 2 and 'ERROR' in out, out)
rc, out = score(D, ['requirements=6', 'ux=5', 'system=5', 'accessibility=5', 'craft=4.5', 'blockers=0'])
check('ratings outside 0 to 5 or not whole numbers are rejected', rc == 2 and 'invalid:requirements=6' in out and 'invalid:craft=4.5' in out, out)
rc, out = score('specs-check.md', ['mode=specs', 'coverage=5', 'behavior=4', 'states=4', 'testability=4', 'blockers=0'])
check('specs check: 5,4,4,4 is 88 and passes', rc == 0 and 'SCORE: 88/100' in out, out)
rc, out = score('audit-check.md', ['mode=audit', 'evidence=na', 'scope=na', 'actionability=4', 'severity=4', 'blockers=0'])
check('audit check: uninspected scope is not scored', rc == 1 and 'INCOMPLETE' in out, out)
for r in ('design-quality.md', 'specs-check.md', 'audit-check.md'):
    check(f'.claude/rubrics/{r} matches the copy that ships in the plugin', (ROOT / '.claude/rubrics' / r).read_text() == (PLUGIN / 'rubrics' / r).read_text())

print('\n== Mock connector')
def mcp(kind, calls, env=None):
    log = tmp / f'{kind}-calls.log'
    msgs = [{'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {}}] + [
        {'jsonrpc': '2.0', 'id': i + 1, 'method': 'tools/call', 'params': {'name': n, 'arguments': a}} for i, (n, a) in enumerate(calls)]
    r = subprocess.run(['node', str(ROOT / 'tests/mock-mcp/server.mjs'), kind, str(log)], input='\n'.join(json.dumps(m) for m in msgs) + '\n',
                       capture_output=True, text=True, env=dict(os.environ, **(env or {})), timeout=20)
    return [json.loads(l)['result'] for l in r.stdout.splitlines()][1:]
if shutil.which('node'):
    res = mcp('figma', [('get_design_context', {'fileKey': 'POLLEN-DEMO', 'nodeId': '20:1'}), ('get_screenshot', {'fileKey': 'POLLEN-DEMO', 'nodeId': '10:1'}), ('use_figma', {'fileKey': 'POLLEN-DEMO', 'code': 'const f = figma.createFrame(); const g = f.clone();'}), ('use_figma', {'fileKey': 'POLLEN-DEMO', 'code': 'return figma.root.children.map(p => p.name)'}), ('get_metadata', {'fileKey': 'POLLEN-DEMO', 'nodeId': '99:2'}), ('get_metadata', {'fileKey': 'POLLEN-DEMO', 'nodeId': '99:3'})])
    check('the inaccessible fixture frame exposes its real problems (contrast, labels, target size)', all(s in res[0]['content'][0]['text'] for s in ('#BDBDBD', 'no label', '24 x 24')))
    check('a creating script gets one node per frame it makes', '99:1' in res[2]['content'][0]['text'] and '99:2' in res[2]['content'][0]['text'])
    check('a read-only script through use_figma creates nothing', 'Nothing was created' in res[3]['content'][0]['text'])
    check('a built frame reads back as a built state, and a node that was never created does not exist', 'Saving EN' in res[4]['content'][0]['text'] and 'No node 99:3' in res[5]['content'][0]['text'])
    res = mcp('figma', [('use_figma', {'fileKey': 'K', 'code': 'x'}), ('get_metadata', {'fileKey': 'K'})], env={'MOCK_FAIL': 'use_figma'})
    check('MOCK_FAIL makes use_figma return an error result while reads still work', res[0].get('isError') is True and not res[1].get('isError'))
    res = mcp('linear', [('get_issue', {'id': 'SAMPLE-107'})])
    check('SAMPLE-107 is a ticket with no requirements and no parent (missing-context case)', '"description": ""' in res[0]['content'][0]['text'] and '"parent": null' in res[0]['content'][0]['text'])
else:
    print('  skip mock connector tests: node is not installed')

print('\n== Run analyzer (on a hand-written event stream, not a real run)')
def ev(kind, **kw): return json.dumps(dict(type=kind, **kw))
def asst(mid, parent, *blocks, usage=None):
    return ev('assistant', parent_tool_use_id=parent, message={'id': mid, 'model': 'synthetic', 'usage': usage or {'input_tokens': 10, 'output_tokens': 5}, 'content': list(blocks)})
def use(i, name, **inp): return {'type': 'tool_use', 'id': i, 'name': name, 'input': inp}
stream = [
    asst('m1', None, use('t1', 'Agent', subagent_type='design-team:ux-analyst', prompt='MODE: SPECS')),
    asst('m2', 't1', use('t2', 'Read', file_path='.design-team/X/brief.md')),
    asst('m3', 't1', use('t3', 'mcp__figma__get_metadata', fileKey='K', nodeId='10:1')),
    asst('m3', 't1', use('t4', 'mcp__figma__get_metadata', fileKey='K', nodeId='10:1')),
    asst('m4', 't1', use('t5', 'Write', file_path='.design-team/X/specs.md', content='x')),
    ev('result', subtype='success', duration_ms=61000, total_cost_usd=0.12, num_turns=4, result='STATUS: COMPLETE\nOverall: 88/100'),
]
sj = tmp / 'run.jsonl'; sj.write_text('\n'.join(stream) + '\n'); mj = tmp / 'metrics.json'
r = subprocess.run([sys.executable, str(ROOT / 'tests/analyze-run.py'), str(sj), '--json', str(mj), '--max-agents', '1', '--no-figma-writes', '--expect-text', 'STATUS: COMPLETE', '--quiet'], capture_output=True, text=True)
m = json.loads(mj.read_text())
check('counts one design-team agent, 61 s, one repeated read', r.returncode == 0 and m['design_team_agents_started'] == 1 and m['duration_s'] == 61 and len(m['repeated_reads']) == 1, r.stdout + r.stderr)
check('counts turns once per API response, not once per event', m['turns_by_agent'] == {'main': 1, 'design-team:ux-analyst': 3}, m['turns_by_agent'])
r = subprocess.run([sys.executable, str(ROOT / 'tests/analyze-run.py'), str(sj), '--max-agents', '0', '--quiet'], capture_output=True, text=True)
check('fails the run when the agent limit is exceeded', r.returncode == 1)

shutil.rmtree(tmp, ignore_errors=True)
bad = [n for n, ok in results if not ok]
print(f'\n{len(results) - len(bad)} of {len(results)} checks passed')
if bad:
    print('FAILED:'); [print(' -', n) for n in bad]; sys.exit(1)
