"""Render the native cuRobo path template in an isolated robot-asset copy."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

base,runtime=map(Path,sys.argv[1:])
source=base/'cache/robodojo-data/Assets/Robots/x5'
target=runtime/'robot-assets/x5'
if not target.exists():
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,target)
template=(source/'curobo_tmp.yml').read_text()
# Exactly the substitutions used by RoboDojo utils/update_embodiment_config_path.py.
rendered=template.replace('${ASSETS_PATH}','/workspace/RoboDojo').replace('$ASSETS_PATH','/workspace/RoboDojo')
config=target/'curobo.yml'
if config.exists() and config.read_text()!=rendered:
    raise SystemExit('Existing generated cuRobo config differs; use a fresh runtime')
config.write_text(rendered)
manifest=dict(source_template_sha256=hashlib.sha256(template.encode()).hexdigest(),
    rendered_sha256=hashlib.sha256(rendered.encode()).hexdigest(),
    substitution_only=True,robot_parameters_changed=False)
(runtime/'robot-assets/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
