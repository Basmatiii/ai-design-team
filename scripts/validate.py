#!/usr/bin/env python3
"""Static release checks for The AI Design Team. Run from anywhere: python3 scripts/validate.py
Checks structure, manifests, agent tool boundaries, skill invocation gates, example sync, house style and leaks.
Optional: a local, git-ignored `.release-denylist` (one regex per line) for private names that must never ship.
This does not run Claude Code; see docs/validation.md for the runtime tests."""
from pathlib import Path
import json, re, sys
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
check((root / market['plugins'][0]['source']).is_dir(), 'marketplace source path missing')

# agents: read-only tools only, no connectors, orchestrator alone may delegate
READ = {'Read', 'Glob', 'Grep'}
for n in ['design-orchestrator', 'ux-analyst', 'figma-designer', 'design-qa']:
    meta = front(plugin / 'agents' / f'{n}.md')
    check(meta.get('name') == n and meta.get('description'), f'{n}: name/description')
    tools = {t.strip() for t in str(meta.get('tools', '')).split(',') if t.strip()}
    allowed = READ | ({'Agent'} if n == 'design-orchestrator' else set())
    check(tools and tools <= allowed, f'{n}: tools must be a subset of {sorted(allowed)}, got {sorted(tools)}')
    check(not any(k in meta for k in ('hooks', 'mcpServers', 'permissionMode')), f'{n}: uses fields plugin agents ignore')

# skills: only a person can start them
for n in ['design-ticket', 'apply-to-figma', 'review-spec']:
    meta = front(plugin / 'skills' / n / 'SKILL.md')
    check(meta.get('name') == n and meta.get('disable-model-invocation') is True, f'{n}: must set disable-model-invocation: true')

# examples bundled in the plugin match the release copy
pe, re_ = plugin / 'examples', root / 'examples'
names = sorted(p.name for p in pe.glob('*.md'))
check(names == sorted(p.name for p in re_.glob('*.md')), 'examples/ and plugins/design-team/examples/ list different files')
for n in names: check((pe / n).read_text() == (re_ / n).read_text(), f'examples/{n} differs from the plugin copy')

# required docs
for f in ['README.md', 'docs/licensing.md', 'docs/permissions.md', 'docs/workflow-contract.md', 'docs/validation.md',
          'docs/setup-live-integrations.md', 'settings/read-only-guard.json', 'tests/mock-mcp/server.mjs']:
    check((root / f).is_file(), f'missing {f}')
json.loads((root / 'settings/read-only-guard.json').read_text())

# house style and leak checks on everything that ships
SHIP = [p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and 'out' not in p.parts
        and p.suffix in ('.md', '.json', '.py', '.mjs', '.txt') and p.name != '.release-denylist']
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
print(f'PASS: manifests, 4 read-only agents, 3 person-only skills, examples in sync, {len(SHIP)} files style- and leak-checked'
      + (f', {len(deny)} private denylist patterns' if deny else ''))
print('Runtime behavior (Claude Code, delegation, connectors) is covered separately in docs/validation.md.')
