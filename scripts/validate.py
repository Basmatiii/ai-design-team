#!/usr/bin/env python3
"""Static release checks for The AI Design Team. Run from anywhere: python3 scripts/validate.py
Checks structure, manifests, agent tool boundaries, model and turn settings, skill invocation gates, hook wiring,
rubrics, example sync, house style and leaks.
Optional: a local, git-ignored `.release-denylist` (one regex per line) for private names that must never ship.
This does not run Claude Code. Deterministic behavior tests: tests/run-static.py. Live runs: tests/live/run-live.sh."""
from pathlib import Path
import json, re, subprocess, sys
try:
    import yaml
except ImportError:
    sys.exit('Install PyYAML first: pip install pyyaml')

root = Path(__file__).resolve().parents[1]
plugin = root / 'plugins/design-team'
fails = []
def check(ok, msg):
    if not ok: fails.append(msg)
def front(path):
    t = path.read_text(); check(t.startswith('---\n'), f'{path}: missing frontmatter')
    return yaml.safe_load(t.split('---', 2)[1]) or {}

# manifests
market = json.loads((root / '.claude-plugin/marketplace.json').read_text())
manifest = json.loads((plugin / '.claude-plugin/plugin.json').read_text())
check(market['plugins'][0]['name'] == manifest['name'], 'marketplace and plugin names differ')
check(market['plugins'][0].get('version') == manifest.get('version'), 'marketplace and plugin versions differ')
check(manifest.get('license') == 'MIT' and market['plugins'][0].get('license') == 'MIT', 'license must be MIT in both manifests')
check((root / market['plugins'][0]['source']).is_dir(), 'marketplace source path missing')

# agents: explicit allowlists, one lane each
BUILTIN = {
    'design-orchestrator': {'Agent', 'SendMessage', 'AskUserQuestion', 'Read', 'Glob', 'Grep', 'Write', 'Edit', 'Bash'},
    'ux-analyst': {'Read', 'Glob', 'Grep', 'Write', 'Edit'},
    'figma-designer': {'Read', 'Glob', 'Grep', 'Write', 'Edit', 'Skill'},
    'design-qa': {'Read', 'Glob', 'Grep', 'Write', 'Edit'},
}
MODELS = {'design-orchestrator': 'haiku', 'ux-analyst': 'sonnet', 'figma-designer': 'sonnet', 'design-qa': 'sonnet'}
READ = ('get_', 'list_', 'search_')
for n, builtin in BUILTIN.items():
    meta = front(plugin / 'agents' / f'{n}.md')
    check(meta.get('name') == n and meta.get('description'), f'{n}: name/description')
    tools = meta.get('tools') or []
    check(isinstance(tools, list) and tools, f'{n}: tools must be an explicit YAML list')
    plain = {t for t in tools if not t.startswith('mcp__')}; mcp = [t for t in tools if t.startswith('mcp__')]
    check(plain == builtin, f'{n}: built-in tools must be exactly {sorted(builtin)}, got {sorted(plain)}')
    check(not any('*' in t for t in mcp), f'{n}: connector tools must be named one by one, no wildcards')
    writes = [t for t in mcp if not t.split('__')[-1].startswith(READ)]
    if n == 'figma-designer':
        check(all(t.endswith('__use_figma') for t in writes), f'{n}: the only write tool allowed is use_figma, got {writes}')
        check(any(t.endswith('__use_figma') for t in mcp), f'{n}: needs use_figma to build')
    else:
        check(not writes, f'{n}: read-only role lists a write tool: {writes}')
    linear = [t for t in mcp if 'inear' in t]
    check(not linear or n == 'design-orchestrator', f'{n}: only the orchestrator reads Linear')
    check(all(t.split('__')[-1] in ('get_issue', 'list_comments') for t in linear), f'{n}: Linear access is limited to get_issue and list_comments')
    check(meta.get('model') == MODELS[n], f'{n}: model should be {MODELS[n]} (docs/workflow-contract.md explains the choice)')
    check(meta.get('effort') in ('low', 'medium', 'high'), f'{n}: effort must be low, medium or high')
    check(isinstance(meta.get('maxTurns'), int) and 8 <= meta['maxTurns'] <= 60, f'{n}: maxTurns must be set between 8 and 60')
    check(not any(k in meta for k in ('hooks', 'mcpServers', 'permissionMode')), f'{n}: uses fields plugin agents ignore')
    body = (plugin / 'agents' / f'{n}.md').read_text().split('---', 2)[2]
    check(len(body) < 6000, f'{n}: prompt body is {len(body)} characters; keep always-loaded prompts under 6000')
r = subprocess.run([sys.executable, str(root / 'scripts/sync-connector-aliases.py'), '--check'], capture_output=True, text=True)
check(r.returncode == 0, 'agent tool lists are out of date: run scripts/sync-connector-aliases.py')

# skills: only a person can start them; one brief template; no pipeline language from v0.2.0
SKILLS = ['specs', 'audit', 'design', 'design-ticket', 'review-spec', 'apply-to-figma']
check(sorted(p.name for p in (plugin / 'skills').iterdir() if p.is_dir()) == sorted(SKILLS), 'unexpected skill folders')
briefs = set()
for n in SKILLS:
    path = plugin / 'skills' / n / 'SKILL.md'; meta = front(path); text = path.read_text()
    check(meta.get('name') == n and meta.get('disable-model-invocation') is True, f'{n}: must set disable-model-invocation: true')
    check('unabridged' not in text and 'verbatim: pass each specialist' not in text, f'{n}: handoffs pass file paths, not pasted text')
    if n in ('specs', 'audit', 'design'):
        m = re.search(r'<!-- brief-template:start -->(.*?)<!-- brief-template:end -->', text, re.S)
        check(bool(m), f'{n}: brief template block missing'); briefs.add(m.group(1) if m else n)
        check('scripts/score.sh' in text and 'Scorecard' in text, f'{n}: must end with the scripted scorecard')
        check('Missing context' in text and 'STATUS: BLOCKED' in text, f'{n}: must define what happens when context is missing')
check(len(briefs) == 1, 'the brief template differs between the specs, audit and design skills')
design = (plugin / 'skills/design/SKILL.md').read_text()
check('End your turn' in design and 'approve' in design, 'design: approval gate missing')
check('At most one correction pass' in design, 'design: the single correction pass rule is missing')
check('Deliver before QA' in design, 'design: the deliverable must be returned before QA')

# hooks and scripts
hooks = json.loads((plugin / 'hooks/hooks.json').read_text())['hooks']
pre = {h['hooks'][0]['args'][1]: h for h in hooks['PreToolUse']}
check({'linear-write', 'figma-write', 'agent-scope', 'dispatch'} <= set(pre), 'hooks.json: a PreToolUse guard is missing')
for k in ('linear-write', 'figma-write'):
    check(pre.get(k, {}).get('hooks', [{}])[0].get('onFailure') == 'block', f'hooks.json: {k} must fail closed (onFailure: block)')
check('UserPromptSubmit' in hooks, 'hooks.json: the approval hook is missing')
for s in ('hooks/guard.sh', 'scripts/score.sh'):
    check(subprocess.run(['sh', '-n', str(plugin / s)]).returncode == 0, f'{s}: shell syntax error')

# rubrics: weights add up, project copy in sync
for r in ('design-quality', 'specs-check', 'audit-check'):
    text = (plugin / 'rubrics' / f'{r}.md').read_text()
    m = re.search(r'<!-- weights: (.*?) -->', text)
    check(bool(m), f'rubrics/{r}.md: weights line missing')
    if m:
        kv = dict(x.split('=') for x in m.group(1).split())
        check(sum(int(v) for k, v in kv.items() if k not in ('threshold', 'floor')) == 100, f'rubrics/{r}.md: weights must add up to 100')
        check(kv.get('threshold') == '85' and kv.get('floor') == '3', f'rubrics/{r}.md: threshold 85 and floor 3 expected')
    copy = root / '.claude/rubrics' / f'{r}.md'
    check(copy.is_file() and copy.read_text() == text, f'.claude/rubrics/{r}.md differs from the plugin copy')
dq = (plugin / 'rubrics/design-quality.md').read_text()
check('requirements=25 ux=25 system=20 accessibility=20 craft=10' in dq, 'design-quality weights must be 25/25/20/20/10')

# examples bundled in the plugin match the release copy
pe, re_ = plugin / 'examples', root / 'examples'
names = sorted(p.name for p in pe.glob('*.md'))
check(names == sorted(p.name for p in re_.glob('*.md')), 'examples/ and plugins/design-team/examples/ list different files')
for n in names: check((pe / n).read_text() == (re_ / n).read_text(), f'examples/{n} differs from the plugin copy')

# required files
for f in ['README.md', 'CHANGELOG.md', 'LICENSE', 'plugins/design-team/LICENSE', 'docs/licensing.md', 'docs/permissions.md', 'docs/workflow-contract.md',
          'docs/validation.md', 'docs/diagnosis.md', 'docs/benchmark.md', 'docs/setup-live-integrations.md', 'settings/read-only-guard.json',
          'tests/mock-mcp/server.mjs', 'tests/run-static.py', 'tests/live/run-live.sh', 'backup/v0.2.0/README.md']:
    check((root / f).is_file(), f'missing {f}')
json.loads((root / 'settings/read-only-guard.json').read_text())

# house style and leak checks on everything that ships
SHIP = [p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and 'out' not in p.parts and '.design-team' not in p.parts
        and p.suffix in ('.md', '.json', '.py', '.mjs', '.txt', '.sh') and p.name != '.release-denylist']
SECRET = re.compile(r'(sk-ant-[A-Za-z0-9_-]{10,}|lin_api_[A-Za-z0-9]{10,}|figd_[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|[a-z]{20}\.supabase\.co|-----BEGIN [A-Z ]*PRIVATE KEY)')
deny_file = root / '.release-denylist'
deny = [re.compile(l.strip()) for l in deny_file.read_text().splitlines() if l.strip() and not l.startswith('#')] if deny_file.exists() else []
for p in SHIP:
    t = p.read_text(errors='ignore')
    check(chr(0x2014) not in t and chr(0x2013) not in t, f'{p.relative_to(root)}: em or en dash (house style)')
    check(not SECRET.search(t), f'{p.relative_to(root)}: looks like a credential or private project URL')
    for d in deny: check(not d.search(t), f'{p.relative_to(root)}: matches a private denylist entry')

if fails:
    print('FAIL'); [print(' -', f) for f in fails]; sys.exit(1)
print(f'PASS: manifests, 4 agents with explicit allowlists, 6 person-only skills, hooks, 3 rubrics, examples in sync, {len(SHIP)} files style- and leak-checked'
      + (f', {len(deny)} private denylist patterns' if deny else ''))
print('Behavior: python3 tests/run-static.py (deterministic) and tests/live/run-live.sh (live, needs Claude Code).')
