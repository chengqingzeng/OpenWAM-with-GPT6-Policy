#!/usr/bin/env bash
set -euo pipefail
export RUNTIME_ROOT=/mnt/rollout/robodojo_mixed_control ROLLOUT_SHARED_ROOT=/mnt/rollout/robodojo_mixed_control
export ROBODOJO_PYTHON=/root/miniconda3/envs/RoboDojo/bin/python
export CODE_ROOT
CODE_ROOT=$("$ROBODOJO_PYTHON" "$OPENWAM_REPO/scripts/build_runtime.py")
export ROBODOJO_SOURCE=/workspace/RoboDojo
"$ROBODOJO_PYTHON" - "$OPENWAM_REPO/configs/pins.json" "$ROBODOJO_SOURCE" <<'PY_CHECK'
import json,subprocess,sys
expected=json.load(open(sys.argv[1]))['robodojo']['commit']
actual=subprocess.check_output(['git','-C',sys.argv[2],'rev-parse','HEAD'],text=True).strip()
assert actual==expected, 'RoboDojo source differs from the pinned experiment'
PY_CHECK
export OPENWAM_SOURCE=$OPENWAM_REPO/.deps/openwam OPENWAM_PYTHON=$OPENWAM_REPO/.venv/bin/python
export CHECKPOINT=$RUNTIME_ROOT/checkpoints/OpenWAM-Alpha-Sim-RoboDojo
export CODEX_BIN=$ROBODOJO_BASE/tools/codex-0.153.4/bin/codex
export PATH=$ROBODOJO_BASE/tools/codex-0.153.4/codex-path:$PATH
export ROLLOUT_EVALUATION_METHOD=openwam_plus_gpt
export POLICY_GPU=0 SIM_GPU=0 POLICY_PORT=18850 SIM_PORT=19513
export OPENWAM_POLICY_SEED=42 ROBODOJO_RECORD_COMPRESSION=1
export TASK_ROOT=$RUNTIME_ROOT DAGGER_NVIDIA_RUNTIME=$RUNTIME_ROOT/graphics/runtime DAGGER_SYSROOT=/
export HF_HOME=$RUNTIME_ROOT/cache/huggingface
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$CODE_ROOT
mkdir -p "$DAGGER_NVIDIA_RUNTIME" "$HF_HOME"
driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n 1)
for file in "/usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.$driver_version" /usr/share/vulkan/icd.d/nvidia_icd.json /usr/share/glvnd/egl_vendor.d/10_nvidia.json; do
  test -f "$file"
  ln -sfn "$file" "$DAGGER_NVIDIA_RUNTIME/$(basename "$file")"
done
export VK_DRIVER_FILES=$DAGGER_NVIDIA_RUNTIME/nvidia_icd.json
exec "$@"
