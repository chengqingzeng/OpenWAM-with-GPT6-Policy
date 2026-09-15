"""Fetch exact public upstream revisions. Never alter an existing dirty checkout."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
pins = json.loads((ROOT/'configs/pins.json').read_text())
(ROOT/'.deps').mkdir(exist_ok=True)
for name in ('openwam', 'gpt_as_policy'):
    pin = pins[name]
    target = ROOT/'.deps'/name
    if not target.exists():
        subprocess.run(['git', 'init', str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'remote', 'add', 'origin', pin['url']], check=True)
    dirty = subprocess.check_output(['git', '-C', str(target), 'status', '--porcelain'], text=True)
    if dirty.strip():
        raise SystemExit(f'Refusing to alter dirty dependency: {target}')
    current = subprocess.run(['git', '-C', str(target), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    if current.stdout.strip() != pin['commit']:
        subprocess.run(['git', '-C', str(target), 'fetch', '--depth', '1', 'origin', pin['commit']], check=True)
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', pin['commit']], check=True)
    print(f'{name}: {pin["commit"]}')
