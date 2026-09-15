#!/usr/bin/env bash
# Called inside scripts/container.sh. One explicitly selected frozen case.
set -euo pipefail
: "${CODE_ROOT:?Use scripts/container.sh}"
export ROLLOUT_EXPERIMENT_ID=${1:?Supply a fresh experiment ID}
export ROLLOUT_CASE_ID=${2:?Supply task__variant__g0__lN}
export MAX_DECISIONS=${3:-100}
[[ "$MAX_DECISIONS" =~ ^[0-9]+$ ]] || exit 2
export ROLLOUT_EVAL_MANIFEST=$RUNTIME_ROOT/evaluation/openwam-panel60-g0.json
if [[ ! -f "$ROLLOUT_EVAL_MANIFEST" ]]; then
  "$ROBODOJO_PYTHON" -m hybrid_rollout.robodojo.evaluation --source "$ROBODOJO_SOURCE" \
    --manifest "$ROLLOUT_EVAL_MANIFEST" --freeze --panel-id openwam_panel60_g0 --eval-seed 0
else
  "$ROBODOJO_PYTHON" -m hybrid_rollout.robodojo.evaluation --source "$ROBODOJO_SOURCE" --manifest "$ROLLOUT_EVAL_MANIFEST"
fi
ROLLOUT_EVAL_MANIFEST_SHA256=$("$ROBODOJO_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["panel_sha256"])' "$ROLLOUT_EVAL_MANIFEST")
export ROLLOUT_EVAL_MANIFEST_SHA256
export ROBODOJO_TASK=${ROLLOUT_CASE_ID%%__*} ROLLOUT_REPLICA_ID=6 ROLLOUT_COUNT=1 ROLLOUT_ATTEMPT=0
export ROLLOUT_MAX_SECONDS=7200 CODEX_IMAGE_MAX_EDGE=480
exec bash "$CODE_ROOT/hybrid_rollout/robodojo/cluster_entrypoint.sh"
