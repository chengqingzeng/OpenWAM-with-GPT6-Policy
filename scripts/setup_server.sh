#!/usr/bin/env bash
# Isolated Linux policy environment; never install into the RoboDojo/Isaac env.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
python_bin=python3.11
runtime=''
wait_for=''
while (($#)); do
  case "$1" in
    --python) python_bin=$2; shift 2 ;;
    --runtime) runtime=$2; shift 2 ;;
    --wait-for) wait_for=$2; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
: "${runtime:?Supply --runtime outside the Git checkout}"
mkdir -p "$runtime"
if [[ -n "$wait_for" ]]; then
  echo 'Waiting for the existing measurement to finish before downloads/install.'
  while true; do
    state=$("$python_bin" -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' "$wait_for")
    case "$state" in
      running) sleep 30 ;;
      completed|failed) break ;;
      *) echo "Unknown measurement state: $state" >&2; exit 2 ;;
    esac
  done
fi
date -u +%FT%TZ > "$runtime/setup.started"
"$python_bin" "$repo/scripts/bootstrap_sources.py"
if [[ ! -x "$repo/.venv/bin/python" ]]; then
  "$python_bin" -m venv "$repo/.venv"
fi
py="$repo/.venv/bin/python"
"$py" -m pip install --upgrade pip setuptools wheel packaging ninja
"$py" -m pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
  --index-url https://download.pytorch.org/whl/cu128
requirements=()
[[ ! -f "$repo/requirements-policy.lock.txt" ]] || requirements=(-r "$repo/requirements-policy.lock.txt")
if command -v nvcc >/dev/null || [[ -x "${CUDA_HOME:-/usr/local/cuda}/bin/nvcc" ]]; then
  DS_BUILD_OPS=0 "$py" -m pip install --no-build-isolation "${requirements[@]}" -e "$repo/.deps/openwam" -e "$repo[dev]"
else
  : "${ROBODOJO_BASE:?DeepSpeed metadata requires nvcc; set ROBODOJO_BASE to reuse the existing CUDA 12.8 container}"
  OPENWAM_RUNTIME="$runtime" bash "$repo/scripts/container.sh" env CUDA_HOME=/usr/local/cuda DS_BUILD_OPS=0 \
    "$py" -m pip install --no-build-isolation "${requirements[@]}" -e "$repo/.deps/openwam" -e "$repo[dev]"
fi
# Select the compatible wheel on the host too (the Isaac container has newer glibc).
"$py" -m pip install --force-reinstall --no-deps --only-binary=:all: cryptography==50.0.1
"$py" -m pip check
"$py" -m pip freeze > "$runtime/policy-environment.freeze.txt"
"$py" "$repo/scripts/download_checkpoint.py" \
  --output "$runtime/checkpoints/OpenWAM-Alpha-Sim-RoboDojo"
date -u +%FT%TZ > "$runtime/setup.completed"
echo 'Policy environment and pinned checkpoint ready; no GPU inference launched.'
