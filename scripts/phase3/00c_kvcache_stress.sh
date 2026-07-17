#!/bin/bash
# 00c_kvcache_stress.sh — assumes vLLM is already running on :8000.
# Builds a ~24K-token prompt from corpus.json (legal cases + key passages)
# and fires it three times at increasing max_tokens budgets to test KV-cache
# headroom under the chosen --max-model-len / --gpu-memory-utilization.

set -euo pipefail

MINOTAUR_DIR="${MINOTAUR_DIR:-/ocean/projects/cis260106p/dmullins/minotaur}"
VLLM_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
MODEL_NAME="meta-llama/Llama-3.1-405B"

OUT_DIR="$(dirname "$0")/outputs/00c"
mkdir -p "$OUT_DIR"

echo "[00c] vLLM URL: ${VLLM_URL}"
echo "[00c] checking liveness..."
if ! curl -fsS --max-time 5 "${VLLM_URL}/models" >/dev/null; then
    echo "[00c] FAIL: vLLM not reachable at ${VLLM_URL}"
    exit 1
fi
echo "[00c] vLLM is up."

# --- Build a long-context prompt --------------------------------------------
PROMPT_FILE="$OUT_DIR/long_prompt.txt"
echo "[00c] assembling ~24K-token prompt from corpus.json -> ${PROMPT_FILE}"
python3 - "$MINOTAUR_DIR/corpus.json" "$PROMPT_FILE" <<'PYEOF'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    corpus = json.load(f)

# Target ~24K tokens. Use char/4 heuristic (~96K chars) since tiktoken's
# Llama tokenizer would require an extra dependency on the compute node.
# This overshoots slightly for legal English (~3.7 chars/token), which is
# fine — we want to *stress* the cache, not undershoot it.
TARGET_CHARS = 96_000

lines = [
    "You are reviewing the following body of case law.",
    "After the corpus, summarize the doctrinal through-line in one paragraph.",
    "",
    "=== CORPUS ===",
    "",
]
total = sum(len(s) for s in lines)
for case in corpus.get("cases", []):
    block = []
    block.append(f"--- {case.get('case_name','')}, {case.get('citation','')} ---")
    block.append(f"Holding: {case.get('holding','')}")
    for i, p in enumerate(case.get("key_passages", [])):
        block.append(f"Key Passage {i+1}: \"{p}\"")
    block.append("")
    chunk = "\n".join(block) + "\n"
    if total + len(chunk) > TARGET_CHARS:
        # Pad with key passages from earlier cases to top up if we ran out
        # of corpus before hitting the target.
        break
    lines.append(chunk)
    total += len(chunk)

# If we still haven't hit the target, repeat key passages
if total < TARGET_CHARS:
    repeat_pool = []
    for case in corpus.get("cases", []):
        for p in case.get("key_passages", []):
            repeat_pool.append(f"\"{p}\" — {case.get('case_name','')}\n")
    i = 0
    while total < TARGET_CHARS and repeat_pool:
        s = repeat_pool[i % len(repeat_pool)]
        lines.append(s)
        total += len(s)
        i += 1

lines.append("")
lines.append("=== TASK ===")
lines.append("Summarize the doctrinal through-line in one paragraph.")
prompt = "\n".join(lines)
with open(dst, "w", encoding="utf-8") as f:
    f.write(prompt)
print(f"  prompt chars: {len(prompt)}")
print(f"  approx tokens (chars/4): {len(prompt)//4}")
PYEOF

PROMPT_CHARS=$(wc -c < "$PROMPT_FILE")
echo "[00c] prompt size: ${PROMPT_CHARS} chars (~$((PROMPT_CHARS / 4)) tokens)"

# --- Fire three completions at increasing max_tokens ------------------------
PASS_COUNT=0
FAIL_COUNT=0
for MT in 4096 6144 10240; do
    echo ""
    echo "[00c] === max_tokens=${MT} ==="
    REQ_FILE="$OUT_DIR/req_${MT}.json"
    RESP_FILE="$OUT_DIR/resp_${MT}.json"
    STATUS_FILE="$OUT_DIR/status_${MT}.txt"

    python3 - "$PROMPT_FILE" "$REQ_FILE" "$MT" "$MODEL_NAME" <<'PYEOF'
import json, sys
prompt_path, req_path, mt, model = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
with open(prompt_path, encoding="utf-8") as f:
    prompt = f.read()
body = {
    "model": model,
    "prompt": prompt,
    "temperature": 0.4,
    "max_tokens": mt,
    "seed": 54,
}
with open(req_path, "w", encoding="utf-8") as f:
    json.dump(body, f)
PYEOF

    START=$(date +%s)
    HTTP_CODE=$(curl -sS -o "$RESP_FILE" -w "%{http_code}" \
        --max-time 600 \
        -H "Content-Type: application/json" \
        -d @"$REQ_FILE" \
        "${VLLM_URL}/completions" || echo "000")
    END=$(date +%s)
    echo "$HTTP_CODE" > "$STATUS_FILE"
    echo "[00c] HTTP ${HTTP_CODE} in $((END - START))s"

    if [[ "$HTTP_CODE" == "200" ]]; then
        # Verify we actually got non-empty text back
        TXT_LEN=$(python3 -c "
import json,sys
try:
    d=json.load(open('$RESP_FILE'))
    t=d.get('choices',[{}])[0].get('text','') or ''
    print(len(t))
except Exception as e:
    print(0)
")
        if [[ "${TXT_LEN}" -gt 0 ]]; then
            echo "[00c] PASS max_tokens=${MT} (response chars: ${TXT_LEN})"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "[00c] FAIL max_tokens=${MT} (200 but empty completion)"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        echo "[00c] FAIL max_tokens=${MT} (HTTP ${HTTP_CODE})"
        echo "[00c] response head:"
        head -c 500 "$RESP_FILE" || true
        echo ""
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

echo ""
echo "[00c] ============================================"
echo "[00c] kvcache stress: ${PASS_COUNT} PASS, ${FAIL_COUNT} FAIL"
echo "[00c] outputs: $OUT_DIR"
echo "[00c] ============================================"
[[ "$FAIL_COUNT" -eq 0 ]] || exit 1
