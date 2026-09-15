"""Fresh identified policy proposals over lossless loopback RPC; never retry."""
from pathlib import Path
import time
import uuid
import numpy as np
from .contract import native_chunk


class OpenWAMClient:
    def __init__(self, port, checkpoint, client_cls=None):
        if client_cls is None:
            from hybrid_rollout.robodojo.robodojo_server.protocol import RPCClient
            client_cls = RPCClient
        self.client = client_cls('127.0.0.1', port, timeout=900)
        self.metadata = self.client.request('metadata')
        self.index = 0
        m = self.metadata
        if not (m.get('checkpoint') == str(Path(checkpoint).resolve()) and
                m.get('checkpoint_sha256') and m.get('backend') == 'OpenWAM/PyTorch' and
                m.get('action_horizon') == 32 and m.get('action_dim') == 16 and
                m.get('decoded_action_dim') == 20 and m.get('inferences') == 0):
            self.close()
            raise ValueError('Fresh identified OpenWAM RoboDojo policy server required')

    def infer(self, observation, output):
        started = time.monotonic()
        result = self.client.request('infer', observation=observation, inference_index=self.index)
        if (result.get('checkpoint_sha256') != self.metadata['checkpoint_sha256'] or
                result.get('inference_index') != self.index):
            raise ValueError('Policy identity or inference sequence mismatch')
        actions = native_chunk(result['actions'])
        raw = np.asarray(result['raw_eef20'], np.float32)
        if raw.shape != (32,20) or not np.isfinite(raw).all():
            raise ValueError('Expected the original finite EEF20 proposal')
        np.savez_compressed(output, raw_actions=raw, actions=actions,
            **{k: observation[k] for k in ('cam_high','cam_left_wrist','cam_right_wrist','states',
                                         'eef_positions','eef_quaternions_wxyz')})
        self.index += 1
        return actions, dict(prediction_id=uuid.uuid4().hex, inference_index=self.index-1,
            inference_seconds=time.monotonic()-started, action_space='absolute_EEF_environment_origin',
            proposal_space='EEF20_per_arm_base', model_horizon=32)

    def close(self):
        self.client.close()
