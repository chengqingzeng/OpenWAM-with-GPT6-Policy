"""Keep the baseline gate/recording; route the student through native EEF commands."""
from hybrid_rollout.robodojo.robodojo_server.client import RoboDojoTools
from .contract import check_calibration
from hybrid_rollout.robodojo.io import write_json


class OpenWAMTools(RoboDojoTools):
    def infer(self, **arguments):
        checks = check_calibration(self._rpc('robot_bases'), self.student.metadata['calibration'])
        write_json(self.output/'base_calibration_check.json', checks)
        return super().infer(**arguments)

    def _rpc(self, op, **kwargs):
        if op == 'fk_preview':
            op = 'eef_preview'
        elif op == 'chunk_step' and 'student_prediction_id' in kwargs:
            op = 'eef_chunk_step'
        return super()._rpc(op, **kwargs)

    def gripper_history(self, executed):
        # Student commands are native EEF16. GPT corrections retain joint14.
        indices = (7,15) if executed.shape[-1] == 16 else (6,13)
        return [{arm: bool(row[i] < .5) for arm,i in zip(('left','right'),indices)} for row in executed]
