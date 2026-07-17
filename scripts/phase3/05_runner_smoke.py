#!/usr/bin/env python3
"""05_runner_smoke.py — minimal end-to-end smoke test for runner.py.

1 task x 1 level x 4 conditions x 1 run = 4 generations.

Imports helpers directly from runner.py so we exercise the production
glue (config import, vLLM client, Bedrock client, prompt assembly,
run_base + run_instruct, is_truncated, _call_with_retry) without any
parallel reimplementation. The only thing this does NOT exercise is
runner.py's outer for-loop and checkpoint code.

Requires: vLLM up on :8000 AND Bedrock reachable. Run after
04_bedrock_check.sh has confirmed the environment.

Outputs:
  scripts/phase3/outputs/05/runner_smoke.json   shape-compat with runner.py
  scripts/phase3/outputs/05/prompt_<cond>.txt   assembled prompts per cond
"""
import json
import os
import sys
import time
from datetime import datetime

MINOTAUR_DIR = os.environ.get(
    "MINOTAUR_DIR", "/ocean/projects/cis260106p/dmullins/minotaur"
)
os.chdir(MINOTAUR_DIR)
sys.path.insert(0, MINOTAUR_DIR)

# Multi-family: smoke test must declare which family to exercise.
# Accepts --family <name> on argv, or MINOTAUR_FAMILY env var.
import argparse  # noqa: E402
_p = argparse.ArgumentParser()
_p.add_argument("--family", default=os.environ.get("MINOTAUR_FAMILY"),
                help="One of: llama70b, gemma31b, deepseek_v4_flash")
_args, _ = _p.parse_known_args()
if not _args.family:
    print("[05] FAIL: must pass --family <name> or set MINOTAUR_FAMILY env var")
    sys.exit(1)
os.environ["MINOTAUR_FAMILY"] = _args.family  # propagate to runner's importer

import runner  # noqa: E402  (also initializes vLLM + provider clients)

OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "outputs", "05"
)
os.makedirs(OUT_DIR, exist_ok=True)

TASK_ID = os.environ.get("SMOKE_TASK_ID", "deliberate_indifference")
LEVEL_NAME = os.environ.get("SMOKE_LEVEL", "L1_focused")

print(f"[05] task={TASK_ID} level={LEVEL_NAME}")
print(f"[05] vLLM: {runner.VLLM_BASE_URL}")
print(f"[05] bedrock region: {runner.AWS_REGION}")
print(f"[05] base model: {runner.BASE_MODEL}")
print(f"[05] instruct model: {runner.INSTRUCT_MODEL}")

corpus = runner.load_corpus()
tasks = runner.load_tasks()
exhibits = runner.load_exhibits()
ground_truth = runner.load_ground_truth()
with open(runner.LADDER_PATH) as f:
    ladder = json.load(f)

tasks_map = {t["id"]: t for t in tasks}
task = tasks_map.get(TASK_ID)
if not task:
    print(f"[05] FAIL: task {TASK_ID} not in tasks.json")
    sys.exit(1)
level = next((l for l in ladder["levels"] if l["name"] == LEVEL_NAME), None)
if not level:
    print(f"[05] FAIL: level {LEVEL_NAME} not in context_ladder.json")
    sys.exit(1)

task_truth = ground_truth.get(TASK_ID, {})
relevant_case_ids = task.get("relevant_cases", [])
relevant_exhibit_ids = task_truth.get("relevant_exhibits", [])
elements_ctx = task.get("required_elements", "")
sumf_ctx = task.get("sumf", "")
defense_ctx = task.get("defense_positions", "")
base_nudge = task["base_nudge"]
instruct_nudge = task["instruct_nudge"]
max_tokens = level.get("max_tokens", 4096)

if level["corpus_filter"] == "relevant":
    filtered_corpus = {"cases": [c for c in corpus["cases"]
                                  if c["id"] in relevant_case_ids]}
else:
    filtered_corpus = corpus
if level["exhibit_filter"] == "relevant":
    filtered_exhibits = {"exhibits": [e for e in exhibits["exhibits"]
                                        if e["id"] in relevant_exhibit_ids]}
else:
    filtered_exhibits = exhibits

all_ids = [c["id"] for c in filtered_corpus["cases"]]
corpus_ctx = runner.build_corpus_context(
    filtered_corpus, {"relevant_cases": all_ids}
)
exhibit_ctx = runner.build_exhibit_context(filtered_exhibits)
parties_ctx = runner.build_parties_context(task, level)

cross_ctx = ""
if level.get("cross_count", False):
    cross_ctx = runner.build_cross_count_elements(task, tasks_map)

bp = task["base_prompt"]
ip = task["instruct_prompt"]
for find, repl in [
    ("[CORPUS]", corpus_ctx),
    ("[EXHIBIT POOL]", exhibit_ctx),
    ("[REQUIRED ELEMENTS]", elements_ctx + cross_ctx),
    ("[SUMF]", sumf_ctx),
    ("[DEFENSE POSITIONS]", defense_ctx),
    ("[PARTIES]", parties_ctx),
]:
    bp = bp.replace(find, repl)
    ip = ip.replace(find, repl)

print(f"[05] base prompt:     {len(bp):>7} chars  (~{len(bp)//4:>6} tokens)")
print(f"[05] instruct prompt: {len(ip):>7} chars  (~{len(ip)//4:>6} tokens)")
print(f"[05] max_tokens:      {max_tokens}")


def make_runfn(cond):
    if cond == "base_alone":
        return lambda: runner.run_base(bp, max_tokens, seed=runner.SEED)
    if cond == "base_nudge":
        return lambda: runner.run_base(
            bp, max_tokens, nudge=base_nudge, seed=runner.SEED
        )
    if cond == "instruct_nudge":
        return lambda: runner.run_instruct(
            ip, max_tokens, system_msg=instruct_nudge
        )
    return lambda: runner.run_instruct(ip, max_tokens)


CONDS = ["base_alone", "base_nudge", "instruct_nudge", "instruct_alone"]
results = []
for cond in CONDS:
    print(f"\n[05] === {cond} ===")
    t0 = time.time()
    try:
        output, usage = runner._call_with_retry(make_runfn(cond))
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[05] FAIL {cond} after {elapsed:.1f}s: "
              f"{type(e).__name__}: {e}")
        results.append({
            "task_id": TASK_ID,
            "level": LEVEL_NAME,
            "condition": cond,
            "error": f"{type(e).__name__}: {e}",
            "elapsed_sec": round(elapsed, 2),
        })
        continue
    elapsed = time.time() - t0
    truncated = runner.is_truncated(output, usage, max_tokens)
    rec = {
        "task_id": TASK_ID,
        "task_name": task["name"],
        "doc_type": task.get("doc_type", "motion"),
        "level": LEVEL_NAME,
        "condition": cond,
        "run": 1,
        "output": output,
        "tokens_prompt": usage.prompt_tokens,
        "tokens_completion": usage.completion_tokens,
        "max_tokens": max_tokens,
        "truncated": truncated,
        "elapsed_sec": round(elapsed, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "model": (
            runner.BASE_MODEL if "base" in cond else runner.INSTRUCT_MODEL
        ),
        "seed": runner.SEED if "base" in cond else None,
    }
    results.append(rec)
    print(f"[05] OK   {cond}: out_tokens={usage.completion_tokens} "
          f"elapsed={elapsed:.1f}s truncated={truncated}")

out_path = os.path.join(OUT_DIR, "runner_smoke.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

for cond, prompt in [
    ("base_alone", bp),
    ("base_nudge", base_nudge + bp),
    ("instruct_nudge", ip),
    ("instruct_alone", ip),
]:
    with open(os.path.join(OUT_DIR, f"prompt_{cond}.txt"),
              "w", encoding="utf-8") as pf:
        pf.write(prompt)

ok = sum(1 for r in results if "error" not in r)
fail = len(results) - ok
expected_keys = {
    "task_id", "task_name", "doc_type", "level", "condition", "run",
    "output", "tokens_prompt", "tokens_completion", "max_tokens",
    "truncated", "elapsed_sec", "timestamp", "model", "seed",
}
schema_ok = all(
    expected_keys.issubset(set(r.keys())) for r in results if "error" not in r
)

print()
print("=" * 67)
print(f"  RUNNER SMOKE: {ok}/4 conditions OK, {fail} failed, "
      f"schema={'OK' if schema_ok else 'MISSING_KEYS'}")
print(f"  results -> {out_path}")
print(f"  prompts -> {OUT_DIR}/prompt_*.txt")
print("=" * 67)
sys.exit(0 if fail == 0 and schema_ok else 1)
