"""Download a pinned public checkpoint; no account credentials are required."""
import argparse
import hashlib
import fcntl
import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
a.output.mkdir(parents=True,exist_ok=True)
lock = (a.output/'.download.lock').open('w')
fcntl.flock(lock,fcntl.LOCK_EX)
pin = json.loads((root/'configs/pins.json').read_text())['checkpoint']
info = HfApi(token=False).model_info(pin['repo_id'], revision=pin['revision'], files_metadata=True)
if info.sha != pin['revision']:
    raise RuntimeError('Checkpoint revision mismatch')
snapshot_download(pin['repo_id'], revision=pin['revision'], local_dir=a.output,
                  max_workers=2, token=False)
records = []
for file in info.siblings:
    path = a.output/file.rfilename
    if not path.is_file() or path.stat().st_size != file.size:
        raise RuntimeError(f'Incomplete checkpoint file: {file.rfilename}')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    digest = h.hexdigest()
    if file.lfs and digest != file.lfs.sha256:
        raise RuntimeError(f'LFS hash mismatch: {file.rfilename}')
    records.append(dict(path=file.rfilename, size=file.size, sha256=digest))
(a.output/'download-manifest.json').write_text(json.dumps(dict(**pin, files=records), indent=2))
print(json.dumps(dict(verified=True, revision=info.sha, files=len(records), output=str(a.output))))
