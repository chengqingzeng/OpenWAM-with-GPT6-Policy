#!/usr/bin/env bash
# Reuse a verified RoboDojo image, assets and managed Codex profiles.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
: "${ROBODOJO_BASE:?Set the existing RoboDojo deployment directory}"
: "${OPENWAM_RUNTIME:?Set an isolated runtime directory outside this checkout}"
[[ "$ROBODOJO_BASE" = /* && "$OPENWAM_RUNTIME" = /* ]] || exit 2
[[ "$OPENWAM_RUNTIME" != "$ROBODOJO_BASE" ]] || { echo 'Use an isolated runtime' >&2; exit 2; }
for input in "$ROBODOJO_BASE/deployment/seccomp-codex.json" "$ROBODOJO_BASE/cache/robodojo-data/Assets" \
  "$ROBODOJO_BASE/private/auth_profiles" "$repo/.venv/bin/python"; do
  [[ -e "$input" ]] || { echo "Missing input: $input" >&2; exit 2; }
done
mkdir -p "$OPENWAM_RUNTIME/cache/isaac-kit/"{data,cache,logs} "$OPENWAM_RUNTIME/private/auth_profiles" "$OPENWAM_RUNTIME/container-home"
# Reuse downloaded Isaac extension caches in an isolated writable container home.
if [[ -d "$ROBODOJO_BASE/container-home/.local/share/ov" && ! -e "$OPENWAM_RUNTIME/container-home/.local/share/ov" ]]; then
  mkdir -p "$OPENWAM_RUNTIME/container-home/.local/share"
  cp -a "$ROBODOJO_BASE/container-home/.local/share/ov" "$OPENWAM_RUNTIME/container-home/.local/share/ov"
fi
chmod 700 "$OPENWAM_RUNTIME/private" "$OPENWAM_RUNTIME/private/auth_profiles"
proxy_env=()
for name in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy; do
  [[ -z "${!name:-}" ]] || proxy_env+=(--env "$name=${!name}")
done
exec sudo docker run --rm --gpus all --network host --shm-size 16g \
  --user "$(id -u):$(id -g)" \
  --security-opt "seccomp=$ROBODOJO_BASE/deployment/seccomp-codex.json" \
  --security-opt apparmor=unconfined --env NVIDIA_DRIVER_CAPABILITIES=all \
  "${proxy_env[@]}" --env NO_PROXY=localhost,127.0.0.1 --env no_proxy=localhost,127.0.0.1 \
  --env "OPENWAM_REPO=$repo" --env "ROBODOJO_BASE=$ROBODOJO_BASE" \
  --env "ROLLOUT_AUTH_PROFILE=${ROLLOUT_AUTH_PROFILE:-codex_a_2}" \
  --mount "type=bind,src=$OPENWAM_RUNTIME/container-home,dst=/home/ubuntu" \
  --mount "type=bind,src=$repo,dst=$repo" \
  --mount "type=bind,src=$OPENWAM_RUNTIME,dst=/mnt/rollout/openwam_gpt6" \
  --mount "type=bind,src=$ROBODOJO_BASE,dst=$ROBODOJO_BASE,readonly" \
  --mount "type=bind,src=$ROBODOJO_BASE/private/auth_profiles,dst=/mnt/rollout/openwam_gpt6/private/auth_profiles" \
  --mount "type=bind,src=$OPENWAM_RUNTIME/cache/isaac-kit/data,dst=/root/miniconda3/envs/RoboDojo/lib/python3.11/site-packages/isaacsim/kit/data" \
  --mount "type=bind,src=$OPENWAM_RUNTIME/cache/isaac-kit/cache,dst=/root/miniconda3/envs/RoboDojo/lib/python3.11/site-packages/isaacsim/kit/cache" \
  --mount "type=bind,src=$OPENWAM_RUNTIME/cache/isaac-kit/logs,dst=/root/miniconda3/envs/RoboDojo/lib/python3.11/site-packages/isaacsim/kit/logs" \
  --mount "type=bind,src=${UV_PYTHON_ROOT:-/home/ubuntu/.local/share/uv/python},dst=${UV_PYTHON_ROOT:-/home/ubuntu/.local/share/uv/python},readonly" \
  --mount "type=bind,src=$ROBODOJO_BASE/cache/robodojo-data/Assets,dst=/workspace/RoboDojo/Assets,readonly" \
  --mount "type=bind,src=$ROBODOJO_BASE/src/RoboDojo/.git,dst=/workspace/RoboDojo/.git,readonly" \
  "${ROBODOJO_IMAGE:-robodojo-repro-runtime:ee67a14}" \
  bash "$repo/scripts/container_env.sh" "$@"
