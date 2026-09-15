"""Native dual-X5 pose commands: [L xyz,wxyz,opening; R xyz,wxyz,opening]."""
import numpy as np
from scipy.spatial.transform import Rotation

HORIZON = 32
NATIVE_DIM = 16


def check_calibration(actual, calibration):
    """Compare the measured robot roots with the checkpoint's fixed sim frames."""
    for arm in ('left', 'right'):
        root = np.asarray(actual[arm], float)
        c = calibration['arms'][arm]
        expected = Rotation.from_quat(np.roll(c['base_quat_wxyz'], -1)).as_matrix()
        if root.shape != (4,4) or not np.isfinite(root).all():
            raise ValueError('Invalid measured robot base')
        position_error = np.linalg.norm(root[:3,3]-c['base_pos_relative_to_env_origin'])
        angle_error = Rotation.from_matrix(root[:3,:3] @ expected.T).magnitude()
        if position_error > 1e-4 or angle_error > 1e-4:
            raise ValueError(f'{arm} robot base differs from the checkpoint calibration')


def native_chunk(value, *, horizon=HORIZON):
    a = np.asarray(value, dtype=np.float32)
    if a.shape != (horizon, NATIVE_DIM) or not np.isfinite(a).all():
        raise ValueError(f'Expected finite ({horizon}, {NATIVE_DIM}) native EEF chunk')
    for offset in (0, 8):
        norms = np.linalg.norm(a[:, offset+3:offset+7], axis=1)
        if not np.allclose(norms, 1, rtol=0, atol=1e-4):
            raise ValueError('Native targets require unit wxyz quaternions')
        grip = a[:, offset+7]
        if np.any((grip < 0) | (grip > 1)):
            raise ValueError('Gripper opening must be in [0,1]')
    return a


def native_command(row):
    row = native_chunk(np.asarray(row)[None], horizon=1)[0]
    return {key: value for arm, offset in (('left', 0), ('right', 8))
            for key, value in ((f'{arm}_ee_pose', row[offset:offset+7].copy()),
                               (f'{arm}_ee_joint_state', row[offset+7:offset+8].copy()))}


def trajectory(actions):
    a = native_chunk(actions)
    return [dict(index=i, **{arm: dict(position=row[o:o+3].tolist(),
        quaternion_wxyz=row[o+3:o+7].tolist(), frame='environment_origin', link='link6',
        gripper_closed=bool(row[o+7] < .5), gripper_opening=float(row[o+7]))
        for arm, o in (('left', 0), ('right', 8))}) for i, row in enumerate(a)]


def diagnostics(actions):
    a = native_chunk(actions)
    arms = {}
    for arm, o in (('left', 0), ('right', 8)):
        rotations = Rotation.from_quat(a[:, [o+4, o+5, o+6, o+3]])
        angular = (rotations[1:]*rotations[:-1].inv()).magnitude()
        arms[arm] = dict(max_successive_position_m=float(np.linalg.norm(np.diff(a[:,o:o+3], axis=0), axis=1).max()),
            max_successive_rotation_rad=float(angular.max()),
            gripper_opening_min=float(a[:,o+7].min()), gripper_opening_max=float(a[:,o+7].max()))
    return dict(shape=list(a.shape), finite=True, action_space='absolute_EEF_environment_origin',
        quaternion_order='wxyz', arms=arms,
        interpretation='Target diagnostics only; neither safety verdict nor predicted object motion.')
