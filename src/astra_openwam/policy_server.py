"""Single-episode OpenWAM proposal server. Uses the official single-sample engine."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import time
import numpy as np
from .contract import native_chunk


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


class Backend:
    def __init__(self, checkpoint, seed=42):
        import torch
        from omegaconf import OmegaConf
        from openwam.deploy.server import _load_deploy_yaml, build_server_from_config
        from openwam.dataloader.robodojo_contract import arx_x5_calibration
        from openwam.dataloader.utils import poses
        from openwam.dataloader.transforms.multiview import format_prompt_for_inference

        checkpoint = Path(checkpoint).resolve()
        cfg = OmegaConf.load(checkpoint/'config.yaml')
        dl = cfg.dataloader
        if (dl.type, dl.variant, dl.embodiment, dl.action_mode, dl.num_frames) != ('robodojo','sim','arx_x5','eef',33):
            raise ValueError('Require the released RoboDojo simulation dual-X5 EEF checkpoint')
        if list(dl.unify_action_map) != ['0-9','34-43'] or not dl.multiview:
            raise ValueError('Unexpected representation or camera layout')
        weights = checkpoint/'checkpoint_step_60000.safetensors'
        manifest = json.loads((checkpoint/'download-manifest.json').read_text())
        expected = next(x['sha256'] for x in manifest['files'] if x['path']==weights.name)
        digest = sha256(weights)
        if digest != expected:
            raise ValueError('Checkpoint weight hash differs from the verified download')
        deploy = _load_deploy_yaml()
        for key, value in {'optimization.compile.enabled':False,
                'optimization.dit_cache.enabled':False, 'optimization.decode_video':False,
                'inference.inference_mode':'sync', 'inference.denoise_mode':'sync',
                'inference.denoise_steps':10}.items():
            OmegaConf.update(deploy, key, value, merge=True)
        torch.set_num_threads(8)
        torch.manual_seed(seed)
        self.server = build_server_from_config(deploy, str(checkpoint), device='cuda:0')
        self.server._init_policy()
        self.engine = self.server.engine
        if getattr(self.engine.architecture, 'binary_command_dims', ()):
            raise ValueError('RoboDojo must use continuous 0-closed/1-open grippers')
        self.poses, self.format_prompt = poses, format_prompt_for_inference
        self.calibration, self.seed, self.index = arx_x5_calibration(), seed, 0
        self.metadata = dict(checkpoint=str(checkpoint), checkpoint_sha256=digest,
            config='OpenWAM-Alpha-Sim-RoboDojo/eef20', backend='OpenWAM/PyTorch',
            config_sha256=sha256(checkpoint/'config.yaml'),
            normalization_sha256=sha256(checkpoint/'normalization_stats.npy'),
            action_horizon=32, action_dim=16, decoded_action_dim=20, model_action_dim=80,
            inferences=0, seed=seed, calibration=self.calibration,
            denoise_steps=10, denoise_mode='sync', compile=False, dit_cache=False,
            decode_video=False, gripper_semantics='continuous_0_closed_1_open',
            inference_api='official_openwam.engine.generate_single_sample')

    def state20(self, obs):
        poses, grips = [], []
        for i, arm in enumerate(('left','right')):
            c = self.calibration['arms'][arm]
            pose = np.r_[obs['eef_positions'][i], obs['eef_quaternions_wxyz'][i]].astype(float)
            if not np.isfinite(pose).all() or abs(np.linalg.norm(pose[3:])-1)>1e-4:
                raise ValueError('Invalid observed link6 pose')
            pose[3:] /= np.linalg.norm(pose[3:])
            poses.append(self.poses.env_relative_world_to_robot_base(pose,
                c['base_pos_relative_to_env_origin'], c['base_quat_wxyz']))
            grip = float(obs['states'][i*7+6])
            if not np.isfinite(grip) or not -1e-8 <= grip <= 1+1e-8:
                raise ValueError('Invalid measured gripper opening')
            grips.append(np.array([np.clip(grip,0,1)]))
        return self.poses.arms_to_eef20(poses[0],grips[0],poses[1],grips[1])

    def native_actions(self, raw):
        lp,lg,rp,rg = self.poses.eef20_to_arms(np.asarray(raw,dtype=float))
        values = []
        for arm,p,g in (('left',lp,lg),('right',rp,rg)):
            c = self.calibration['arms'][arm]
            world = self.poses.robot_base_to_env_relative_world(p,
                c['base_pos_relative_to_env_origin'], c['base_quat_wxyz'])
            values.extend((world, np.clip(g,0,1)))
        return native_chunk(np.concatenate(values,axis=-1))

    def infer(self, observation, inference_index):
        from PIL import Image
        if inference_index != self.index:
            raise ValueError('Stale or duplicate inference request')
        images = {}
        for source, target in (('cam_high','head_camera'),('cam_left_wrist','left_wrist_camera'),
                               ('cam_right_wrist','right_wrist_camera')):
            array = np.asarray(observation[source])
            if array.dtype != np.uint8 or array.ndim!=3 or array.shape[-1]!=3:
                raise ValueError('Expected original uint8 RGB camera arrays')
            images[target] = Image.fromarray(array)
        payload = dict(images=images, state=self.state20(observation).tolist(),
                       prompt=self.format_prompt(observation['instruction']))
        obs = self.server._obs_preprocessor.preprocess(payload)
        conditions = self.server._policy._build_conditions(obs)
        conditions['seed'] = self.seed
        started = time.monotonic()
        generated = self.engine.generate(conditions)
        raw = generated['actions']
        if hasattr(raw,'detach'):
            raw = raw.detach().cpu().numpy()
        raw = np.asarray(raw,dtype=np.float32)
        if raw.shape != (32,20) or not np.isfinite(raw).all():
            raise ValueError(f'Expected physical EEF20 (32,20), got {raw.shape}')
        native = self.native_actions(raw)
        result = dict(actions=native, raw_eef20=raw, inference_index=self.index,
            checkpoint_sha256=self.metadata['checkpoint_sha256'], inference_seconds=time.monotonic()-started)
        self.index += 1
        return result


def main():
    from hybrid_rollout.robodojo.robodojo_server.protocol import VERSION, receive_packet, send_packet
    p = argparse.ArgumentParser()
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--port', type=int, default=18850)
    p.add_argument('--identity-output', type=Path, required=True)
    p.add_argument('--seed',type=int,default=42)
    args = p.parse_args()
    backend = Backend(args.checkpoint,args.seed)
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind(('127.0.0.1',args.port))
        listener.listen(1)
        args.identity_output.parent.mkdir(parents=True,exist_ok=True)
        args.identity_output.write_text(json.dumps(backend.metadata,indent=2))
        print(json.dumps(dict(event='ready',port=args.port)),flush=True)
        connection,_ = listener.accept()
        with connection:
            connection.settimeout(900)
            try:
                while True:
                    request = receive_packet(connection)
                    response = dict(version=VERSION,request_id=request.get('request_id'))
                    try:
                        if request.get('version') != VERSION:
                            raise ValueError('Unsupported RPC version')
                        op = request['op']
                        if op=='metadata':
                            result=dict(backend.metadata,inferences=backend.index)
                        elif op=='infer':
                            result=backend.infer(**request.get('args',{}))
                        else:
                            raise ValueError('Unsupported policy operation')
                        send_packet(connection,dict(response,ok=True,result=result))
                    except Exception as error:
                        send_packet(connection,dict(response,ok=False,error=f'{type(error).__name__}: {error}'))
                        raise  # No silent retry or reuse after an uncertain inference.
            except (EOFError,ConnectionError):
                pass


if __name__=='__main__':
    main()
