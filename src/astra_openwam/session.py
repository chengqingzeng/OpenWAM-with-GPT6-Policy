"""Extend the pinned simulator recorder with native EEF chunks; preserve joint corrections."""
import numpy as np
from hybrid_rollout.robodojo.robodojo_server.session import RoboDojoSession
from hybrid_rollout.robodojo.io import require, write_json
from .contract import native_chunk, native_command, trajectory


class OpenWAMSession(RoboDojoSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata.update(action_dim=16, action_horizon=32,
            action_space='absolute_EEF_environment_origin', native_action_type='ee')

    def eef_chunk_step(self, actions, **kwargs):
        require(not self.finished and not self.terminated and not self.truncated, 'Episode finished')
        require(1 <= len(actions) <= 15, 'Expected 1..15 reviewed EEF commands')
        actions = native_chunk(actions, horizon=len(actions))
        rows = []
        for action in actions:
            before = int(self.env.take_action_cnt[0])
            self.env.take_action(native_command(action))
            require(int(self.env.take_action_cnt[0]) == before+1, 'Native action must execute exactly once')
            self.step_id += 1
            ended = bool(self.env.end_flag[0])
            self.success = bool(ended and self.env.success[0])
            self.truncated = bool(ended and not self.success and self.step_id >= self.env.step_lim)
            self.terminated = bool(ended and not self.truncated)
            obs = self._observe(record=True)
            row = dict(valid=True, executed_action=action.copy(), action_space='native_EEF16',
                obs=dict(states=obs['states']), step_id=self.step_id, terminated=self.terminated,
                truncated=self.truncated, success=self.success, source=self.source,
                control_epoch=self.control_epoch, **kwargs)
            rows.append(row)
            write_json(self.episode_dir/f'action_{self.step_id-1:06d}.json',
                dict(row, executed_action=action.tolist(), obs=dict(states=obs['states'].tolist())))
            if ended:
                self._write_summary('terminal')
                break
        return dict(episode_id=self.episode_id, step_id=self.step_id, steps=rows)

    def dispatch(self, op, args):
        if op == 'robot_bases':
            self._check_identity(args['episode_id'], args['step_id'])
            return {arm:self.kinematics.root(arm) for arm in ('left','right')}
        if op in ('eef_preview', 'eef_chunk_step'):
            self._check_identity(args['episode_id'], args['step_id'])
            data = {k:v for k,v in args.items() if k not in ('episode_id','step_id')}
            if op == 'eef_preview':
                return dict(trajectory=trajectory(data['actions']), measured_fk_check=self.kinematics.check(),
                    physical_steps=0, frame='environment_origin',
                    interpretation='Native EEF targets; no speculative physics or object motion.')
            return self.eef_chunk_step(**data)
        return super().dispatch(op, args)
