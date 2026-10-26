#!/usr/bin/env python3
"""Generate local plugin packages/config previews, never install or change host policy."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.execution import Executor


def generate(work, python):
    executable = Path(python).expanduser().resolve(strict=True)
    if not executable.is_file(): raise ValueError('Select a real Python interpreter')
    entry = str(work.repo_root / 'scripts/serve_plugin.py')
    servers, plugins = {}, []
    for kind in ('email', 'browser'):
        name = 'career-' + kind
        server = {'type': 'stdio', 'command': str(executable),
                  'args': [entry, kind, '--data-dir', str(work.data_dir), '--actor', work.actor]}
        servers[name] = server
        target = work.inside('configured-plugins/' + name)
        target.mkdir(parents=True, exist_ok=True)
        manifest = {'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
                    'name': name, 'version': '0.1.0',
                    'description': 'Local ' + kind + ' application tools by DUYTRUYENTHONG; requires reviewed scope.'}
        for filename, value in [('plugin.json', manifest), ('mcp.json',
                {'$schema': 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json', 'mcpServers': {name: server}})]:
            work.atomic_text('configured-plugins/' + name + '/' + filename, json.dumps(value, indent=2))
        plugins.append({'name': name, 'source': {'source': 'local', 'path': './' + name},
                        'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'})
    work.atomic_text('configured-plugins/.agents/plugins/marketplace.json', json.dumps(
        {'name': 'career-kit-local', 'interface': {'displayName': 'Vietnam Career Agent Kit'}, 'plugins': plugins}, indent=2))
    work.atomic_text('configured-plugins/mcp-servers.example.json', json.dumps({'mcpServers': servers}, indent=2))
    lines = []
    for name, server in servers.items():
        lines.extend(['[mcp_servers.' + name + ']', 'command = ' + json.dumps(server['command']),
                      'args = ' + json.dumps(server['args']), ''])
    work.atomic_text('configured-plugins/codex.example.toml', '\n'.join(lines))
    return {'packages': [str(work.inside('configured-plugins/' + n)) for n in servers],
            'host_settings_changed': False, 'installed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--actor', default='local-user')
    args = parser.parse_args()
    print(json.dumps(generate(Executor(args.data_dir, actor=args.actor), args.python), indent=2))


if __name__ == '__main__': main()
