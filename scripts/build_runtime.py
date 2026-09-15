"""Build an immutable, hashed runtime from pinned sources and the reviewable patch."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build():
    pins = json.loads((ROOT/'configs/pins.json').read_text())
    source = ROOT/'.deps/gpt_as_policy'
    for name in ('gpt_as_policy', 'openwam'):
        dep = ROOT/'.deps'/name
        head = subprocess.check_output(['git','-C',str(dep),'rev-parse','HEAD'],text=True).strip()
        dirty = subprocess.check_output(['git','-C',str(dep),'status','--porcelain'],text=True).strip()
        if head != pins[name]['commit'] or dirty:
            raise SystemExit(f'Pinned clean checkout required: {dep}')
    inputs = [ROOT/'patches/openwam-runtime.patch', ROOT/'configs/pins.json',
              ROOT/'configs/experiment.yaml',*sorted(p for p in (ROOT/'scripts').iterdir() if p.suffix in ('.py','.sh') and not p.name.startswith('.')),ROOT/'LICENSE',*sorted((ROOT/'licenses').glob('*')),*sorted((ROOT/'src').rglob('*.py'))]
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    identity = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    parent = ROOT/'.runtime'
    parent.mkdir(exist_ok=True)
    target = parent/identity[:16]
    if target.exists():
        manifest = json.loads((target/'source_manifest.json').read_text())
        for name,digest in manifest['files'].items():
            if hashlib.sha256((target/name).read_bytes()).hexdigest() != digest:
                raise SystemExit(f'Generated runtime was modified: {name}')
        return target
    with tempfile.TemporaryDirectory(dir=parent,prefix='build-') as temp:
        staging = Path(temp)/'src'
        staging.mkdir()
        shutil.copytree(source/'hybrid_rollout',staging/'hybrid_rollout',
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        subprocess.run(['patch','--batch','-p1','-i',str(ROOT/'patches/openwam-runtime.patch')],
                       cwd=staging,check=True,stdout=subprocess.DEVNULL)
        shutil.copytree(ROOT/'src/astra_openwam',staging/'astra_openwam',
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(ROOT/'licenses',staging/'licenses')
        shutil.copytree(ROOT/'scripts',staging/'integration_scripts',ignore=shutil.ignore_patterns('__pycache__','._*'))
        shutil.copytree(ROOT/'configs',staging/'integration_configs')
        shutil.copyfile(ROOT/'LICENSE',staging/'LICENSE')
        files = {str(p.relative_to(staging)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(staging.rglob('*')) if p.is_file()}
        (staging/'source_manifest.json').write_text(json.dumps(dict(
            schema='astra_openwam.source.v1',identity=identity,pins=pins,inputs=hashes,files=files),indent=2)+'\n')
        staging.rename(target)
    return target


if __name__ == '__main__':
    print(build())
