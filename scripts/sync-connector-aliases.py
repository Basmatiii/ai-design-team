#!/usr/bin/env python3
"""Regenerate the `tools:` allowlist in each design-team agent from one list of connector names.

Claude Code names an MCP tool `mcp__<server>__<tool>`, and `<server>` is whatever the connector is called in a given
setup (figma, Figma, claude_ai_Figma, plugin_figma_figma and so on). Agent allowlists need the real name, so the
common ones are listed here. If `/mcp` shows your Figma or Linear connector under a different name, add it:

    python3 scripts/sync-connector-aliases.py --figma my-figma --linear my-linear

    python3 scripts/sync-connector-aliases.py --check     # exit 1 if the agent files are out of date

Only agent frontmatter is rewritten. The hook guard (hooks/hooks.json) matches any server whose name contains
"figma" or "linear", so it does not need this list."""
from pathlib import Path
import re, sys

FIGMA = ['figma', 'Figma', 'figma-desktop', 'figma-dev-mode-mcp-server', 'claude_ai_Figma', 'plugin_figma_figma']
LINEAR = ['linear', 'Linear', 'linear-server', 'claude_ai_Linear', 'plugin_linear_linear']

FIGMA_READ = ['get_metadata', 'get_design_context', 'get_screenshot', 'get_variable_defs', 'search_design_system', 'get_libraries']
FIGMA_BUILD = ['use_figma', 'get_figma_skill']   # figma-designer only; every edit still needs a typed approval
LINEAR_READ = ['get_issue', 'list_comments']     # one ticket and, when needed, its parent: no list or search tools

AGENTS = {
    'design-orchestrator': (['Agent', 'SendMessage', 'AskUserQuestion', 'Read', 'Glob', 'Grep', 'Write', 'Edit', 'Bash'], [], LINEAR_READ),
    'ux-analyst':          (['Read', 'Glob', 'Grep', 'Write', 'Edit'], FIGMA_READ, []),
    'figma-designer':      (['Read', 'Glob', 'Grep', 'Write', 'Edit', 'Skill'], FIGMA_READ + FIGMA_BUILD, []),
    'design-qa':           (['Read', 'Glob', 'Grep', 'Write', 'Edit'], FIGMA_READ, []),
}

def arg_values(flag):
    return [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == flag]

def tools_for(name, figma, linear):
    base, fig, lin = AGENTS[name]
    return base + [f'mcp__{s}__{t}' for s in figma for t in fig] + [f'mcp__{s}__{t}' for s in linear for t in lin]

def render(text, tools):
    block = 'tools:\n' + ''.join(f'  - {t}\n' for t in tools)
    out, n = re.subn(r'^tools:\n(?:  - .*\n)+', block, text, count=1, flags=re.M)
    if n != 1: raise SystemExit('no `tools:` YAML list found to replace')
    return out

def main():
    root = Path(__file__).resolve().parents[1] / 'plugins/design-team/agents'
    figma = FIGMA + [a for a in arg_values('--figma') if a not in FIGMA]
    linear = LINEAR + [a for a in arg_values('--linear') if a not in LINEAR]
    stale = []
    for name in AGENTS:
        path = root / f'{name}.md'
        old = path.read_text(); new = render(old, tools_for(name, figma, linear))
        if new != old:
            stale.append(name)
            if '--check' not in sys.argv: path.write_text(new)
    if '--check' in sys.argv:
        if stale: print('out of date:', ', '.join(stale)); sys.exit(1)
        print('agent tool lists are in sync')
    else:
        print('updated:' if stale else 'no change:', ', '.join(stale) or 'all agents')

if __name__ == '__main__':
    main()
