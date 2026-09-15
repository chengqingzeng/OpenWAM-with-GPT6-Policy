"""Native Isaac EE/joint compatibility check, with no model calls or benchmark score."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import numpy as np
from astra_openwam.contract import check_calibration
from hybrid_rollout.robodojo.robodojo_server.protocol import RPCClient

output=Path(sys.argv[1]).resolve()
output.mkdir(parents=True,exist_ok=False)
port=19514
log_path=output/'server.log'
client=None
# The standalone official contract imports NumPy only. Avoid importing training packages into Isaac.
spec=importlib.util.spec_from_file_location('robodojo_contract',Path(os.environ['OPENWAM_SOURCE'])/'openwam/dataloader/robodojo_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
with log_path.open('w') as log:
    process=subprocess.Popen([sys.executable,'-m','hybrid_rollout.robodojo.robodojo_server.server',
        '--task','build_tower','--eval-seed','0','--port',str(port),'--output',str(output/'native')],
        cwd=output,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        deadline=time.monotonic()+900
        while '"event": "ready"' not in log_path.read_text(errors='replace'):
            if process.poll() is not None: raise RuntimeError(f'Simulator exited; see {log_path}')
            if time.monotonic()>deadline: raise TimeoutError('Simulator startup timeout')
            time.sleep(2)
        client=RPCClient('127.0.0.1',port)
        identity=client.request('reset',seed=0,source='student',policy_version='native-EE-infrastructure-smoke')
        def request(op,tick=0,**kwargs):
            return client.request(op,episode_id=identity['episode_id'],step_id=tick,**kwargs)
        bases=request('robot_bases')
        check_calibration(bases,contract.arx_x5_calibration())
        obs=request('teacher_observation')
        np.savez_compressed(output/'initial_observation.npz',**obs)
        row=np.concatenate([np.r_[obs['eef_positions'][i],obs['eef_quaternions_wxyz'][i],obs['states'][7*i+6]] for i in (0,1)])
        preview=request('eef_preview',actions=np.repeat(row[None],32,axis=0))
        native=request('eef_chunk_step',actions=row[None])
        assert native['step_id']==1 and len(native['steps'])==1
        obs_after=request('teacher_observation',1)
        targets={arm:dict(position=obs_after['eef_positions'][i].tolist(),
            quaternion_wxyz=obs_after['eef_quaternions_wxyz'][i].tolist(),gripper_closed=bool(obs_after['states'][7*i+6]<.5),
            gripper_opening=float(obs_after['states'][7*i+6])) for i,arm in enumerate(('left','right'))}
        joint=request('eef_joint_target',1,targets=targets)
        correction=request('chunk_step',1,actions=np.asarray(joint['action'])[None])
        assert correction['step_id']==2 and len(correction['steps'])==1
        final=request('finish_pilot',2,reason='infrastructure_smoke')
        report=dict(status='passed',model_calls=0,native_ee_steps=1,bounded_dls_steps=1,
            calibration_checked=True,fk_check=preview['measured_fk_check'],
            native_action_shape=list(np.asarray(native['steps'][0]['executed_action']).shape),
            correction_shape=list(np.asarray(correction['steps'][0]['executed_action']).shape),
            control_dt=final['control_dt'],cameras={k:list(obs[k].shape) for k in ('cam_high','cam_left_wrist','cam_right_wrist')},
            benchmark_result=False)
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:
        if client: client.close()
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
