import hashlib
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from astra_openwam.contract import native_chunk, native_command, trajectory, check_calibration
from astra_openwam.client import OpenWAMClient
from astra_openwam.session import OpenWAMSession
from astra_openwam.recording_io import savez_record
from hybrid_rollout.robodojo.robodojo_server.client import validate_dual_response
from conftest import ROOT, RUNTIME


def chunk():
    a = np.zeros((32,16),np.float32)
    a[:,3] = a[:,11] = 1
    a[:,7] = .25
    a[:,15] = .75
    return a


def test_gate_and_correction_code_preserved():
    for file in ('gate_assessment.py','validation.py','action_edit_kinematics.py','kinematics.py'):
        path = 'hybrid_rollout/robodojo/robodojo_server/'+file
        assert (RUNTIME/path).read_bytes() == (ROOT/'.deps/gpt_as_policy'/path).read_bytes()
    p = trajectory(chunk())[0]
    req = dict(request_id='fresh',current_eef=p,student_eef_trajectory=trajectory(chunk()))
    response = dict(request_id='fresh',reason='Observed missed grasp',mode='eef',steps=5,
                    target={arm:dict(p[arm]) for arm in ('left','right')})
    validate_dual_response(response,req)
    response['target']['left']['position'] = [.051,0,0]
    with pytest.raises(ValueError,match='5 cm'):
        validate_dual_response(response,req)
    response.update(mode='student',steps=16)
    with pytest.raises(ValueError,match='1..15'):
        validate_dual_response(response,req)


def test_native_actions_cannot_be_joint_commands():
    a = chunk()
    command = native_command(a[0])
    assert set(command) == {'left_ee_pose','right_ee_pose','left_ee_joint_state','right_ee_joint_state'}
    assert command['left_ee_joint_state'][0] == .25
    assert trajectory(a)[0]['right']['gripper_opening'] == .75
    for bad in (np.zeros((50,14)),np.full((32,16),np.nan),a*2):
        with pytest.raises(ValueError): native_chunk(bad)


def test_calibration_rejects_frame_drift_and_accepts_quaternion_sign():
    q = np.array([2**-.5,0,0,2**-.5])
    root = np.eye(4)
    root[:3,:3] = Rotation.from_quat(np.roll(q,-1)).as_matrix()
    root[:3,3] = [.3,-.45,.765]
    calibration = dict(arms={arm:dict(base_pos_relative_to_env_origin=root[:3,3],base_quat_wxyz=-q)
                            for arm in ('left','right')})
    check_calibration(dict(left=root,right=root),calibration)
    rounded = root.copy()
    rounded[:3,:3] = Rotation.from_euler('z',.00030194).as_matrix() @ root[:3,:3]
    check_calibration(dict(left=rounded,right=rounded),calibration)
    rounded[:3,:3] = Rotation.from_euler('z',.002).as_matrix() @ root[:3,:3]
    with pytest.raises(ValueError,match='calibration'):
        check_calibration(dict(left=rounded,right=root),calibration)
    bad = root.copy(); bad[0,3] += .01
    with pytest.raises(ValueError,match='calibration'):
        check_calibration(dict(left=bad,right=root),calibration)


def test_policy_identity_and_original_recording(tmp_path):
    a = chunk()
    class RPC:
        def __init__(self,*args,**kwargs): self.index=0
        def request(self,op,**kwargs):
            if op=='metadata': return dict(checkpoint=str(tmp_path),checkpoint_sha256='hash',
                backend='OpenWAM/PyTorch',action_horizon=32,action_dim=16,decoded_action_dim=20,inferences=0)
            return dict(actions=a,raw_eef20=np.ones((32,20)),checkpoint_sha256='hash',inference_index=self.index)
        def close(self): pass
    client = OpenWAMClient(0,tmp_path,client_cls=RPC)
    obs = {key:np.zeros((3,4,3),np.uint8) for key in ('cam_high','cam_left_wrist','cam_right_wrist')}
    obs.update(states=np.zeros(14),eef_positions=np.zeros((2,3)),eef_quaternions_wxyz=np.tile([1,0,0,0],(2,1)))
    client.infer(obs,tmp_path/'proposal.npz')
    with np.load(tmp_path/'proposal.npz') as saved:
        assert saved['raw_actions'].shape == (32,20)
        assert saved['actions'].shape == (32,16)
        np.testing.assert_array_equal(saved['cam_high'],obs['cam_high'])
    with pytest.raises(ValueError,match='sequence'):
        client.infer(obs,tmp_path/'duplicate.npz')
    assert not (tmp_path/'duplicate.npz').exists()


def test_native_prefix_exactly_once_and_stale_request_rejected(tmp_path):
    class Env:
        take_action_cnt=[0]; end_flag=[False]; success=[False]; step_lim=10
        def take_action(self,command):
            assert 'left_ee_pose' in command and 'left_arm_joint_state' not in command
            self.take_action_cnt[0]+=1
            self.end_flag[0]=self.take_action_cnt[0]==2
            self.success[0]=self.end_flag[0]
    session = OpenWAMSession.__new__(OpenWAMSession)
    session.env=Env(); session.step_id=0; session.episode_id='fresh'; session.poisoned=False
    session.finished=session.terminated=session.truncated=False
    session.source='student'; session.control_epoch=0; session.episode_dir=tmp_path
    session._observe=lambda **kwargs:dict(states=np.zeros(14))
    session._write_summary=lambda reason:None
    with pytest.raises(ValueError):
        session.dispatch('eef_chunk_step',dict(episode_id='old',step_id=0,actions=chunk()[:3]))
    assert session.env.take_action_cnt[0]==0
    result=session.dispatch('eef_chunk_step',dict(episode_id='fresh',step_id=0,actions=chunk()[:3]))
    assert len(result['steps'])==2 and result['step_id']==2 and session.success
    assert result['steps'][0]['executed_action'].shape==(16,)
    assert result['steps'][0]['obs']['states'].shape==(14,)


def test_lossless_recording(tmp_path,monkeypatch):
    arrays=dict(image=np.arange(72,dtype=np.uint8).reshape(4,6,3),state=np.arange(14,dtype=np.float32),instruction='Move blocks')
    for level in ('1','6'):
        monkeypatch.setenv('ROBODOJO_RECORD_COMPRESSION',level)
        savez_record(tmp_path/(level+'.npz'),**arrays)
        with np.load(tmp_path/(level+'.npz'),allow_pickle=False) as saved:
            for key,value in arrays.items(): np.testing.assert_array_equal(saved[key],value)


def test_mixed_command_recording_keeps_dimensions_and_gripper_indices(tmp_path):
    import json
    from hybrid_rollout.robodojo.robodojo_server.debug_recorder import DecisionTimeline
    from hybrid_rollout.robodojo.robodojo_server.video_panel import gripper_change
    def save(name,value): (tmp_path/name).write_text(json.dumps(value))
    save('run.json',dict(evaluation_method='openwam_plus_gpt',action_horizon=32,action_dim=16))
    records=[]
    for i,mode in enumerate(('student','eef')):
        records.append(dict(decision=i,start_tick=i,end_tick=i+1,executed_steps=1,response=dict(mode=mode,steps=1)))
        np.savez(tmp_path/f'proposal_{i:03d}.npz',actions=chunk(),raw_actions=np.ones((32,20)))
        action=chunk()[:1] if mode=='student' else np.zeros((1,14))
        if mode=='eef': action[0,[6,13]]=[.8,.9]
        np.savez(tmp_path/f'execution_{i:03d}.npz',actions=action,states=np.zeros((1,14)))
    save('history.json',records)
    timeline=DecisionTimeline(tmp_path)
    student,correction=timeline.segments
    assert np.asarray(student['delta_vs_openwam_prefix']).shape==(1,16)
    assert not student['numeric_action_changed']
    assert correction['delta_vs_openwam_prefix']==[] and correction['codex_override']
    assert 'L 0.25→0.80' in gripper_change(correction,0)
    assert 'R 0.75→0.90' in gripper_change(correction,0)
    assert timeline.at(1)[0]['decision']==0 and timeline.at(2)[0]['decision']==1
