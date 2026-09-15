#!/usr/bin/env bash
set -euo pipefail
: "${CODE_ROOT:?Use scripts/container.sh}"
source "$CODE_ROOT/hybrid_rollout/robodojo/robodojo_server/runtime.sh"
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=$CODE_ROOT:$ROBODOJO_SOURCE:$ROBODOJO_SOURCE/XPolicyLab:$ROBODOJO_SOURCE/third_party/curobo
exec "$ROBODOJO_PYTHON" "$OPENWAM_REPO/scripts/smoke_sim.py" "$@"
