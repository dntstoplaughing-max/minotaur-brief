#!/bin/bash
# 02_base_format_probe.sh — base model (no instruct prefix) on Count I,
# Level 1 context, no nudge. 3 generations saved as gen_1.txt..gen_3.txt
# under outputs/02/ for manual review.
#
# This rebuilds the prompt by mirroring runner.py:build_corpus_context /
# build_exhibit_context / build_parties_context — same placeholder
# replacements, no nudge, no instruct system message.

set -euo pipefail

MINOTAUR_DIR="${MINOTAUR_DIR:-/ocean/projects/cis260106p/dmullins/minotaur}"
VLLM_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
MODEL_NAME="meta-llama/Llama-3.1-405B"

TASK_ID="deliberate_indifference"
LEVEL_NAME="L1_focused"
N_RUNS=3
SEED_BASE=54
TEMPERATURE=0.4
MAX_TOKENS=4096

OUT_DIR="$(dirname "$0")/outputs/02"
mkdir -p "$OUT_DIR"

echo "[02] task=${TASK_ID} level=${LEVEL_NAME} runs=${N_RUNS}"
echo "[02] vLLM URL: ${VLLM_URL}"
if ! curl -fsS --max-time 5 "${VLLM_URL}/models" >/dev/null; then
    echo "[02] FAIL: vLLM not reachable at ${VLLM_URL}"
    exit 1
fi

# --- Build the assembled base prompt ---------------------------------------
PROMPT_FILE="$OUT_DIR/assembled_prompt.txt"
echo "[02] assembling base prompt -> ${PROMPT_FILE}"
python3 - "$MINOTAUR_DIR" "$TASK_ID" "$LEVEL_NAME" "$PROMPT_FILE" <<'PYEOF'
import json, os, sys
root, task_id, level_name, dst = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

def load(p):
    with open(os.path.join(root, p)) as f:
        return json.load(f)

corpus = load("corpus.json")
tasks  = load("prompts/tasks.json")["tasks"]
ladder = load("prompts/context_ladder.json")
exhibits = load("prompts/exhibit_pool.json")
ground_truth = load("prompts/ground_truth.json")

task = next(t for t in tasks if t["id"] == task_id)
level = next(l for l in ladder["levels"] if l["name"] == level_name)
truth = ground_truth.get(task_id, {})

relevant_case_ids = task.get("relevant_cases", [])
relevant_exhibit_ids = truth.get("relevant_exhibits", [])

# Filter corpus and exhibits per the level config
if level["corpus_filter"] == "relevant":
    cases = [c for c in corpus["cases"] if c["id"] in relevant_case_ids]
else:
    cases = corpus["cases"]
if level["exhibit_filter"] == "relevant":
    exs = [e for e in exhibits["exhibits"] if e["id"] in relevant_exhibit_ids]
else:
    exs = exhibits["exhibits"]

# Replicate runner.build_corpus_context
corpus_lines = []
for c in cases:
    corpus_lines.append(f"--- {c['case_name']}, {c['citation']} ---")
    corpus_lines.append(f"Holding: {c['holding']}")
    for i, p in enumerate(c.get("key_passages", [])):
        corpus_lines.append(f"Key Passage {i+1}: \"{p}\"")
    corpus_lines.append("")
corpus_ctx = "\n".join(corpus_lines)

# Replicate runner.build_exhibit_context
ex_lines = []
for ex in exs:
    ex_lines.append(f"--- EXHIBIT {ex['id']}: {ex['name']} ({ex['date']}) ---")
    ex_lines.append(f"From: {ex['from']} | To: {ex['to']} | Type: {ex['type']}")
    ex_lines.append(ex["text"])
    ex_lines.append("")
exhibit_ctx = "\n".join(ex_lines)

# Replicate runner.build_parties_context
parties_ctx = (task.get("defendant_context", task.get("parties_context", ""))
               if level.get("defendants_filter", "all") == "relevant"
               else task.get("parties_context", ""))

# L1 has cross_count=False, so no cross_ctx
elements_ctx = task.get("required_elements", "")
sumf_ctx = task.get("sumf", "")
defense_ctx = task.get("defense_positions", "")

bp = task["base_prompt"]
bp = bp.replace("[CORPUS]", corpus_ctx)
bp = bp.replace("[EXHIBIT POOL]", exhibit_ctx)
bp = bp.replace("[REQUIRED ELEMENTS]", elements_ctx)
bp = bp.replace("[SUMF]", sumf_ctx)
bp = bp.replace("[DEFENSE POSITIONS]", defense_ctx)
bp = bp.replace("[PARTIES]", parties_ctx)

with open(dst, "w", encoding="utf-8") as f:
    f.write(bp)
print(f"  prompt chars: {len(bp)}  approx tokens (chars/4): {len(bp)//4}")
PYEOF

PROMPT_CHARS=$(wc -c < "$PROMPT_FILE")
echo "[02] prompt size: ${PROMPT_CHARS} chars"

# --- Fire N_RUNS generations -----------------------------------------------
for i in $(seq 1 "$N_RUNS"); do
    SEED=$((SEED_BASE + i - 1))
    REQ_FILE="$OUT_DIR/req_${i}.json"
    RESP_FILE="$OUT_DIR/resp_${i}.json"
    OUT_TXT="$OUT_DIR/gen_${i}.txt"

    echo ""
    echo "[02] === run ${i}/${N_RUNS} (seed=${SEED}) ==="

    python3 - "$PROMPT_FILE" "$REQ_FILE" "$SEED" "$MODEL_NAME" "$TEMPERATURE" "$MAX_TOKENS" <<'PYEOF'
import json, sys
prompt_path, req_path, seed, model, temp, mt = sys.argv[1:7]
with open(prompt_path, encoding="utf-8") as f:
    prompt = f.read()
body = {
    "model": model,
    "prompt": prompt,
    "temperature": float(temp),
    "max_tokens": int(mt),
    "seed": int(seed),
}
with open(req_path, "w", encoding="utf-8") as f:
    json.dump(body, f)
PYEOF

    START=$(date +%s)
    HTTP_CODE=$(curl -sS -o "$RESP_FILE" -w "%{http_code}" \
        --max-time 900 \
        -H "Content-Type: application/json" \
        -d @"$REQ_FILE" \
        "${VLLM_URL}/completions" || echo "000")
    END=$(date +%s)
    echo "[02] HTTP ${HTTP_CODE} in $((END - START))s"

    if [[ "$HTTP_CODE" != "200" ]]; then
        echo "[02] FAIL run ${i} (HTTP ${HTTP_CODE})"
        head -c 500 "$RESP_FILE" || true
        echo ""
        continue
    fi

    python3 - "$RESP_FILE" "$OUT_TXT" <<'PYEOF'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    d = json.load(f)
text = d.get("choices", [{}])[0].get("text", "") or ""
with open(dst, "w", encoding="utf-8") as f:
    f.write(text)
print(f"  saved {len(text)} chars -> {dst}")
PYEOF
done

echo ""
echo "[02] outputs: $OUT_DIR"
ls -la "$OUT_DIR"
