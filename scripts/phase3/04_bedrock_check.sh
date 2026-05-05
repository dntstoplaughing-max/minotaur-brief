#!/bin/bash
# 04_bedrock_check.sh — confirm AWS Bedrock credentials and network egress
# from the compute node by sending a 50-token completion to the instruct
# model configured in config.py.
#
# Reads INSTRUCT_MODEL, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# directly from config.py — no separate copy of the credentials.

set -euo pipefail

MINOTAUR_DIR="${MINOTAUR_DIR:-/ocean/projects/cis260106p/dmullins/minotaur}"
CONDA_ENV="minotaur"

OUT_DIR="$(dirname "$0")/outputs/04"
mkdir -p "$OUT_DIR"
RESP_FILE="$OUT_DIR/bedrock_response.txt"

echo "[04] activating conda env"
module purge 2>/dev/null || true
module load anaconda3/2024.10-1 2>/dev/null || true
CONDA_BASE="$(conda info --base 2>/dev/null || echo "${ANACONDA3_ROOT:-/opt/packages/anaconda3}")"
# shellcheck disable=SC1091
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

cd "$MINOTAUR_DIR"

echo "[04] calling Bedrock with a 50-token trivia probe..."
python3 - <<PYEOF | tee "$RESP_FILE"
import sys, traceback
try:
    from config import (
        INSTRUCT_MODEL, AWS_REGION,
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    )
except Exception as e:
    print(f"[04] FAIL: could not import from config.py: {e}")
    sys.exit(1)

import boto3
client = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

print(f"[04] region={AWS_REGION}  model={INSTRUCT_MODEL}")
try:
    resp = client.converse(
        modelId=INSTRUCT_MODEL,
        messages=[{"role": "user",
                   "content": [{"text": "Reply with exactly: 'Bedrock OK'."}]}],
        inferenceConfig={"temperature": 0.0, "maxTokens": 50},
    )
    text = resp["output"]["message"]["content"][0]["text"]
    usage = resp.get("usage", {})
    print(f"[04] response text: {text!r}")
    print(f"[04] usage: in={usage.get('inputTokens')} out={usage.get('outputTokens')}")
    print("[04] PASS: Bedrock reachable, credentials valid.")
except Exception as e:
    print(f"[04] FAIL: Bedrock call raised {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(2)
PYEOF
