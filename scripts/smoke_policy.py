"""Offline policy/coordinate proof on a recorded native observation. No simulation steps."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from astra_openwam.policy_server import Backend

p=argparse.ArgumentParser()
p.add_argument('--checkpoint',type=Path,required=True)
p.add_argument('--observation',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
with np.load(a.observation,allow_pickle=False) as archive:
    obs={key:archive[key] for key in archive.files}
obs['instruction']=str(obs['instruction'].item())
started=time.monotonic()
backend=Backend(a.checkpoint)
load_seconds=time.monotonic()-started
# A stationary physical EEF20 proposal must round-trip to the measured world poses.
state=backend.state20(obs)
stationary=backend.native_actions(np.repeat(state[None],32,axis=0))
for i,o in ((0,0),(1,8)):
    np.testing.assert_allclose(stationary[0,o:o+3],obs['eef_positions'][i],atol=1e-6)
    actual=stationary[0,o+3:o+7]; measured=obs['eef_quaternions_wxyz'][i]
    assert abs(abs(float(np.dot(actual,measured)))-1)<1e-5
records=[]
for i in range(2):
    torch.cuda.reset_peak_memory_stats()
    result=backend.infer(obs,i)
    torch.cuda.synchronize()
    np.savez_compressed(a.output/f'proposal_{i}.npz',actions=result['actions'],raw_eef20=result['raw_eef20'])
    records.append(dict(inference_seconds=result['inference_seconds'],
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        native_shape=list(result['actions'].shape),raw_shape=list(result['raw_eef20'].shape)))
report=dict(metadata=backend.metadata,load_seconds=load_seconds,coordinate_roundtrip_passed=True,
    gpu=torch.cuda.get_device_name(),gpu_total_bytes=torch.cuda.get_device_properties(0).total_memory,torch_version=torch.__version__,inferences=records,
    scope='Two offline proposals on one recorded observation; no Astra call, no simulator actions, not a success-rate result')
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
