#!/bin/bash
# verify_model.sh — read-only integrity check for Llama-3.1-405B on Bridges-2.
# Idempotent. No deletes, no moves. Run on the login node.

set -uo pipefail

MODEL_DIR="${MODEL_DIR:-/ocean/projects/cis260106p/dmullins/models/Llama-3.1-405B}"
MIN_GB=750
MAX_GB=820

REQUIRED_FILES=(
    "config.json"
    "tokenizer.json"
    "tokenizer_config.json"
    "generation_config.json"
    "model.safetensors.index.json"
)

FAIL=0
WARN=0

print_section() {
    echo ""
    echo "==================================================================="
    echo "  $1"
    echo "==================================================================="
}

# --- 1. Directory exists ----------------------------------------------------
print_section "1) Model directory check"
if [[ ! -d "$MODEL_DIR" ]]; then
    echo "FAIL: model directory does not exist: $MODEL_DIR"
    echo ""
    echo "==================================================================="
    echo "  SUMMARY: FAIL (model directory missing)"
    echo "==================================================================="
    exit 1
fi
echo "OK: directory exists -> $MODEL_DIR"

# --- 2. List safetensors with sizes; flag zero-byte ------------------------
print_section "2) safetensors files"
SAFETENSORS=()
while IFS= read -r -d '' f; do
    SAFETENSORS+=("$f")
done < <(find "$MODEL_DIR" -maxdepth 1 -type f -name "*.safetensors" -print0 | sort -z)

if [[ ${#SAFETENSORS[@]} -eq 0 ]]; then
    echo "FAIL: no .safetensors files found in $MODEL_DIR"
    FAIL=1
else
    echo "Found ${#SAFETENSORS[@]} .safetensors files:"
    ZERO_BYTE=0
    for f in "${SAFETENSORS[@]}"; do
        SIZE_BYTES=$(stat -c %s "$f" 2>/dev/null || stat -f %z "$f" 2>/dev/null)
        SIZE_HUMAN=$(numfmt --to=iec --suffix=B "$SIZE_BYTES" 2>/dev/null || echo "${SIZE_BYTES}B")
        if [[ "$SIZE_BYTES" -eq 0 ]]; then
            echo "  ZERO-BYTE: $(basename "$f")"
            ZERO_BYTE=$((ZERO_BYTE + 1))
            FAIL=1
        else
            printf "  %s  %s\n" "$SIZE_HUMAN" "$(basename "$f")"
        fi
    done
    if [[ $ZERO_BYTE -gt 0 ]]; then
        echo "FAIL: $ZERO_BYTE zero-byte shard(s) detected"
    fi
fi

# --- 3. Total size in GB ----------------------------------------------------
print_section "3) Total size check (expected ${MIN_GB}-${MAX_GB} GB)"
TOTAL_BYTES=0
for f in "${SAFETENSORS[@]}"; do
    SIZE_BYTES=$(stat -c %s "$f" 2>/dev/null || stat -f %z "$f" 2>/dev/null)
    TOTAL_BYTES=$((TOTAL_BYTES + SIZE_BYTES))
done
TOTAL_GB=$(awk "BEGIN { printf \"%.2f\", $TOTAL_BYTES / (1024*1024*1024) }")
echo "Total .safetensors size: ${TOTAL_GB} GB"
RANGE_OK=$(awk -v g="$TOTAL_GB" -v lo="$MIN_GB" -v hi="$MAX_GB" \
    'BEGIN { print (g >= lo && g <= hi) ? "yes" : "no" }')
if [[ "$RANGE_OK" == "yes" ]]; then
    echo "OK: within expected range"
else
    echo "WARN: ${TOTAL_GB} GB is outside expected ${MIN_GB}-${MAX_GB} GB range"
    WARN=1
fi

# --- 4. Required files present ---------------------------------------------
print_section "4) Required config/tokenizer files"
for fn in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$MODEL_DIR/$fn" ]]; then
        echo "  OK   $fn"
    else
        echo "  MISS $fn"
        FAIL=1
    fi
done

# --- 5. Verify shard manifest matches disk ---------------------------------
print_section "5) Shard manifest cross-check"
INDEX_PATH="$MODEL_DIR/model.safetensors.index.json"
if [[ ! -f "$INDEX_PATH" ]]; then
    echo "SKIP: model.safetensors.index.json not present"
else
    python3 - "$INDEX_PATH" "$MODEL_DIR" <<'PYEOF'
import json, os, sys
index_path, model_dir = sys.argv[1], sys.argv[2]
with open(index_path) as f:
    idx = json.load(f)
weight_map = idx.get("weight_map", {})
referenced = sorted(set(weight_map.values()))
missing = []
for shard in referenced:
    full = os.path.join(model_dir, shard)
    if not os.path.isfile(full) or os.path.getsize(full) == 0:
        missing.append(shard)
print(f"  manifest references {len(referenced)} shard files "
      f"covering {len(weight_map)} tensors")
if missing:
    print(f"  FAIL: {len(missing)} referenced shard(s) missing or empty:")
    for m in missing[:10]:
        print(f"    - {m}")
    if len(missing) > 10:
        print(f"    ... and {len(missing) - 10} more")
    sys.exit(2)
else:
    print("  OK: every referenced shard is present and non-empty")
    sys.exit(0)
PYEOF
    PYRC=$?
    if [[ $PYRC -ne 0 ]]; then
        FAIL=1
    fi
fi

# --- Summary ---------------------------------------------------------------
print_section "SUMMARY"
if [[ $FAIL -eq 0 && $WARN -eq 0 ]]; then
    echo "PASS: model directory looks complete and within size bounds."
    exit 0
elif [[ $FAIL -eq 0 ]]; then
    echo "PASS WITH WARNINGS: required files present, but see WARN above."
    exit 0
else
    echo "FAIL: one or more critical checks failed. See output above."
    exit 1
fi
