import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_runtime',ROOT/'scripts/build_runtime.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RUNTIME = module.build()
sys.path.insert(0,str(RUNTIME))
