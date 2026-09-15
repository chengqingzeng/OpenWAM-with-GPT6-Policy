"""Export portable tested Linux policy dependencies, excluding local editable paths."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
lines=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines()
pins=[line for line in lines if line and not line.startswith(('#','-e '))]
if any(' @ ' in line or '://' in line for line in pins):
    raise SystemExit('Unexpected URL requirement; review before exporting a portable lock')
(root/'requirements-policy.lock.txt').write_text(
    '# Tested Linux x86_64 / Python 3.11 policy environment.\n'
    '# Editable OpenWAM and this adapter are installed separately at pinned Git revisions.\n'
    '--extra-index-url https://download.pytorch.org/whl/cu128\n'+'\n'.join(sorted(pins,key=str.lower))+'\n')
print('Wrote requirements-policy.lock.txt without local paths or credentials')
