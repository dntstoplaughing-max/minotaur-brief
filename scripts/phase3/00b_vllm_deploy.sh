#!/bin/bash
# 00b_vllm_deploy.sh — launch vLLM in the foreground for an interactive
# session. Same flags as minotaur_run.job, but logs to a file and stays
# attached so you can watch startup. Background it with `&` if you want
# the shell back; otherwise use a second SSH session for the curl probe.

set -euo pipefail

PROJECT_ROOT="/ocean/projects/cis260106p/dmullins"
MODEL_PATH="${PROJECT_ROOT}/models/Llama-3.1-405B"
CONDA_ENV="minotaur"
VLLM_PORT=8000
VLLM_HOST="127.0.0.1"

OUT_DIR="$(dirname "$0")/outputs/00b"
mkdir -p "$OUT_DIR"
LOG_FILE="$OUT_DIR/vllm_$(date +%Y%m%d_%H%M%S).log"

echo "[00b] loading modules"
module purge
module load anaconda3/2024.10-1
module load cuda/12.6.1

CONDA_BASE="/opt/packages/anaconda3-2024.10-1"
# shellcheck disable=SC1091
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

echo "[00b] python: $(which python)"
echo "[00b] gpus:"
nvidia-smi --query-gpu=index,name,memory.free --format=csv

echo "[00b] launching vLLM (foreground, log -> $LOG_FILE)"
echo "[00b] from another shell on this node, verify with:"
echo "      curl -s http://${VLLM_HOST}:${VLLM_PORT}/v1/models | head"
echo ""

# Use stdbuf so the log streams in real time. Print PID before exec'ing.
( python -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_PATH}" \
    --served-model-name "meta-llama/Llama-3.1-405B" \
    --tensor-parallel-size 8 \
    --dtype bfloat16 \
    --quantization fp8 \
    --max-model-len 131072 \
    --max-num-seqs 8 \
    --gpu-memory-utilization 0.92 \
    --enforce-eager \
    --host "${VLLM_HOST}" \
    --port "${VLLM_PORT}" 2>&1 | tee "$LOG_FILE" ) &
VLLM_PID=$!
echo "[00b] vLLM pid=${VLLM_PID}"
echo "[00b] tailing log; Ctrl-C to detach (vLLM keeps running until you kill ${VLLM_PID})"
wait "$VLLM_PID"
