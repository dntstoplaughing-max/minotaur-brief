#!/usr/bin/env python3
"""07_cross_family_probe.py — Phase 1 of the methodology probe.

Instruct-side subset of the full probe matrix:
  5 tasks x 2 levels (L1 + L4) x 2 conds (instruct_alone, instruct_nudge)
  x 3 runs x 3 families = 180 generations.

Goal: see how the three families' instruct outputs compare BEFORE the
base side comes online. Tells us:
  - Cross-family regex transfer (do HEDGING/META/etc. patterns hit similar rates?)
  - Refusal style differences across alignment recipes
  - Within-cell variance at n=3
  - Whether the nudge has a comparable effect across families

Does NOT need base models downloaded — instruct APIs only.

Outputs:
  scripts/phase3/outputs/07/<family>/<task>_<level>_<cond>_run<N>.txt
  scripts/phase3/outputs/07/probe_results.json     all generations + metadata
  scripts/phase3/outputs/07/regex_summary.txt      per-family hit rates per category

Cost: ~180 calls x ~$0.005 each = ~$1.
Time: ~20-30 min if sequential, less if running parallel families.
"""
import json
import os
import re
import sys
import time
from datetime import datetime

MINOTAUR_DIR = os.environ.get(
    "MINOTAUR_DIR",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
os.chdir(MINOTAUR_DIR)
sys.path.insert(0, MINOTAUR_DIR)

from config import (
    TEMPERATURE, CORPUS_PATH, TASKS_PATH, LADDER_PATH,
    EXHIBIT_POOL_PATH, GROUND_TRUTH_PATH, SEED,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION,
)
try:
    from config import TOGETHER_API_KEY
except ImportError:
    TOGETHER_API_KEY = None
try:
    from config import DEEPSEEK_API_KEY
except ImportError:
    DEEPSEEK_API_KEY = None

from families import FAMILIES
from scorer import (
    HEDGING_PATTERNS, META_COMMENTARY_PATTERNS,
    BALANCED_ANALYSIS_PATTERNS, DISCLAIMER_PATTERNS, PREAMBLE_PATTERNS,
    _count_pattern_tokens,
)

OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "outputs", "07"
)
os.makedirs(OUT_DIR, exist_ok=True)

# --- Probe matrix ---
PROBE_LEVELS = ["L1_focused", "L4_cross_count"]
PROBE_CONDS = ["instruct_alone", "instruct_nudge"]
RUNS = 3

# --- Load data ---
with open(CORPUS_PATH) as f:
    corpus = json.load(f)
with open(TASKS_PATH) as f:
    tasks_all = json.load(f)["tasks"]
with open(EXHIBIT_POOL_PATH) as f:
    exhibits = json.load(f)
with open(GROUND_TRUTH_PATH) as f:
    ground_truth = json.load(f)
with open(LADDER_PATH) as f:
    ladder = json.load(f)

tasks_map = {t["id"]: t for t in tasks_all}
levels_map = {l["name"]: l for l in ladder["levels"]}

print(f"[07] PROBE MATRIX: {len(tasks_all)} tasks x {len(PROBE_LEVELS)} levels x "
      f"{len(PROBE_CONDS)} conds x {RUNS} runs x {len(FAMILIES)} families = "
      f"{len(tasks_all) * len(PROBE_LEVELS) * len(PROBE_CONDS) * RUNS * len(FAMILIES)} calls")


# --- Prompt assembly (lifted from runner.py to avoid module-level family lock) ---
def build_corpus_context(cases_list):
    lines = []
    for c in cases_list:
        lines.append(f"--- {c['case_name']}, {c['citation']} ---")
        lines.append(f"Holding: {c['holding']}")
        for i, p in enumerate(c["key_passages"]):
            lines.append(f"Key Passage {i+1}: \"{p}\"")
        lines.append("")
    return "\n".join(lines)


def build_exhibit_context(exh_list):
    lines = []
    for ex in exh_list:
        lines.append(f"--- EXHIBIT {ex['id']}: {ex['name']} ({ex['date']}) ---")
        lines.append(f"From: {ex['from']} | To: {ex['to']} | Type: {ex['type']}")
        lines.append(ex["text"])
        lines.append("")
    return "\n".join(lines)


def build_parties_context(task, level):
    df = level.get("defendants_filter", "all")
    if df == "relevant":
        return task.get("defendant_context", task.get("parties_context", ""))
    return task.get("parties_context", "")


def build_cross_count_elements(task):
    pair_id = task.get("cross_count_pair")
    if not pair_id or pair_id not in tasks_map:
        return ""
    pair_task = tasks_map[pair_id]
    pair_elements = pair_task.get("required_elements", "")
    pair_name = pair_task.get("name", pair_id)
    return (f"\n--- ALSO CONSIDER: REQUIRED ELEMENTS FOR "
            f"{pair_name.upper()} ---\n{pair_elements}\n")


def assemble_prompt(task, level):
    """Build the instruct prompt for a (task, level)."""
    task_truth = ground_truth.get(task["id"], {})
    relevant_case_ids = task.get("relevant_cases", [])
    relevant_exhibit_ids = task_truth.get("relevant_exhibits", [])

    if level["corpus_filter"] == "relevant":
        f_cases = [c for c in corpus["cases"] if c["id"] in relevant_case_ids]
    else:
        f_cases = corpus["cases"]
    if level["exhibit_filter"] == "relevant":
        f_exh = [e for e in exhibits["exhibits"]
                 if e["id"] in relevant_exhibit_ids]
    else:
        f_exh = exhibits["exhibits"]

    cross_ctx = build_cross_count_elements(task) if level.get("cross_count") else ""
    elements_ctx = task.get("required_elements", "")
    sumf_ctx = task.get("sumf", "")
    defense_ctx = task.get("defense_positions", "")
    parties_ctx = build_parties_context(task, level)
    corpus_ctx = build_corpus_context(f_cases)
    exhibit_ctx = build_exhibit_context(f_exh)

    ip = task["instruct_prompt"]
    for find, repl in [
        ("[CORPUS]", corpus_ctx),
        ("[EXHIBIT POOL]", exhibit_ctx),
        ("[REQUIRED ELEMENTS]", elements_ctx + cross_ctx),
        ("[SUMF]", sumf_ctx),
        ("[DEFENSE POSITIONS]", defense_ctx),
        ("[PARTIES]", parties_ctx),
    ]:
        ip = ip.replace(find, repl)
    return ip


# --- Provider calls ---
_bedrock = None
def call_bedrock(model_id, prompt, max_tok, system_msg=None):
    global _bedrock
    if _bedrock is None:
        import boto3
        from botocore.config import Config
        # Llama 70B Instruct with max_tokens=4096 occasionally exceeds the
        # default 60s read timeout. 900s gives generous headroom.
        cfg = Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 3})
        _bedrock = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=cfg,
        )
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    system_list = [{"text": system_msg}] if system_msg else []
    resp = _bedrock.converse(
        modelId=model_id,
        messages=messages,
        system=system_list,
        inferenceConfig={"temperature": TEMPERATURE, "maxTokens": max_tok},
    )
    return resp["output"]["message"]["content"][0]["text"], resp["usage"]


_openai_clients = {}
def call_openai_compat(api_key, base_url, model_id, prompt, max_tok, system_msg=None, seed=None):
    from openai import OpenAI
    key = (api_key, base_url)
    if key not in _openai_clients:
        _openai_clients[key] = OpenAI(api_key=api_key, base_url=base_url)
    client = _openai_clients[key]
    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})
    kwargs = {
        "model": model_id,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": max_tok,
    }
    if seed is not None:
        kwargs["seed"] = seed
    resp = client.chat.completions.create(**kwargs)
    usage = {
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
    }
    return resp.choices[0].message.content, usage


def call_family(fam, prompt, max_tok, system_msg=None, seed=None):
    provider = fam["instruct_provider"]
    model_id = fam["instruct_model_id"]
    if provider == "bedrock":
        text, usage = call_bedrock(model_id, prompt, max_tok, system_msg)
        return text, {"input_tokens": usage.get("inputTokens"),
                      "output_tokens": usage.get("outputTokens")}
    if provider == "together":
        if not TOGETHER_API_KEY:
            raise RuntimeError("TOGETHER_API_KEY missing in config.py")
        return call_openai_compat(
            TOGETHER_API_KEY, fam["instruct_endpoint"], model_id,
            prompt, max_tok, system_msg, seed,
        )
    if provider == "deepseek":
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY missing in config.py")
        return call_openai_compat(
            DEEPSEEK_API_KEY, fam["instruct_endpoint"], model_id,
            prompt, max_tok, system_msg, seed,
        )
    raise ValueError(f"unknown provider {provider}")


# --- Run probe matrix ---
records = []
total_calls = 0
expected = len(tasks_all) * len(PROBE_LEVELS) * len(PROBE_CONDS) * RUNS * len(FAMILIES)

for fname, fam in FAMILIES.items():
    fam_dir = os.path.join(OUT_DIR, fname)
    os.makedirs(fam_dir, exist_ok=True)
    print(f"\n[07] === FAMILY: {fname} ({fam['instruct_provider']}) ===")
    for task in tasks_all:
        task_id = task["id"]
        instruct_nudge = task.get("instruct_nudge", "")
        for level_name in PROBE_LEVELS:
            level = levels_map[level_name]
            max_tok = level.get("max_tokens", 4096)
            ip = assemble_prompt(task, level)
            for cond in PROBE_CONDS:
                system_msg = instruct_nudge if cond == "instruct_nudge" else None
                for run_i in range(RUNS):
                    total_calls += 1
                    run_seed = SEED + run_i
                    label = f"{task_id}_{level_name}_{cond}_run{run_i+1:02d}"
                    print(f"  [{total_calls}/{expected}] {fname} | {label}")
                    t0 = time.time()
                    try:
                        text, usage = call_family(
                            fam, ip, max_tok,
                            system_msg=system_msg, seed=run_seed,
                        )
                    except Exception as e:
                        elapsed = time.time() - t0
                        print(f"    FAIL ({elapsed:.1f}s): {type(e).__name__}: {e}")
                        records.append({
                            "family": fname, "task_id": task_id,
                            "level": level_name, "condition": cond,
                            "run": run_i + 1, "seed": run_seed,
                            "error": f"{type(e).__name__}: {e}",
                            "elapsed_sec": round(elapsed, 2),
                        })
                        continue
                    elapsed = time.time() - t0
                    out_path = os.path.join(fam_dir, f"{label}.txt")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    records.append({
                        "family": fname, "task_id": task_id,
                        "level": level_name, "condition": cond,
                        "run": run_i + 1, "seed": run_seed,
                        "output": text,
                        "input_tokens": usage.get("input_tokens"),
                        "output_tokens": usage.get("output_tokens"),
                        "elapsed_sec": round(elapsed, 2),
                        "timestamp": datetime.utcnow().isoformat(),
                        "model": fam["instruct_model_id"],
                        "provider": fam["instruct_provider"],
                    })
                    print(f"    OK  out={usage.get('output_tokens')} tok, {elapsed:.1f}s")

# --- Save raw records ---
results_path = os.path.join(OUT_DIR, "probe_results.json")
with open(results_path, "w") as f:
    json.dump(records, f, indent=2)
print(f"\n[07] Saved {len(records)} records to {results_path}")

# --- Regex hit summary per family per category ---
CATEGORIES = [
    ("hedging", HEDGING_PATTERNS),
    ("meta_commentary", META_COMMENTARY_PATTERNS),
    ("balanced_analysis", BALANCED_ANALYSIS_PATTERNS),
    ("disclaimer", DISCLAIMER_PATTERNS),
    ("preamble", PREAMBLE_PATTERNS),
]

per_family = {fname: {"records": [r for r in records
                                  if r.get("family") == fname and "output" in r]}
              for fname in FAMILIES}

print("\n" + "=" * 100)
print("REGEX HIT SUMMARY (per family, mean per output)")
print("=" * 100)
fam_names = list(FAMILIES.keys())
header = f"{'category':<22}" + "".join(f"{f:>26}" for f in fam_names)
print(header)
print("-" * len(header))
table_rows = [header, "-" * len(header)]

for cat_name, patterns in CATEGORIES:
    row = f"{cat_name:<22}"
    for fname in fam_names:
        recs = per_family[fname]["records"]
        n = len(recs)
        if n == 0:
            row += f"{'(no data)':>26}"
            continue
        total_matches = 0
        total_tokens = 0
        total_words = 0
        for r in recs:
            text = r["output"]
            m, t = _count_pattern_tokens(text, patterns)
            total_matches += m
            total_tokens += t
            total_words += len(text.split())
        mean_matches = total_matches / n
        rate_pct = (total_tokens / total_words * 100) if total_words else 0
        row += f"  {mean_matches:>5.2f} hits ({rate_pct:>5.2f}%)"
    print(row)
    table_rows.append(row)

# Mean output length per family
print("-" * len(header))
row = f"{'mean_words':<22}"
for fname in fam_names:
    recs = per_family[fname]["records"]
    if recs:
        mean_w = sum(len(r["output"].split()) for r in recs) / len(recs)
        row += f"{mean_w:>26.0f}"
    else:
        row += f"{'(no data)':>26}"
print(row)
table_rows.append(row)

# Refusal-pattern probe
REFUSAL_HINTS = [
    r"\bI (?:cannot|can\x27t|am unable|won\x27t)\b",
    r"\bI(?:\x27m)? (?:not able to|sorry|unable to)\b",
    r"\bI must decline\b",
    r"\bunable to (?:assist|help|provide)\b",
    r"\bagainst my (?:guidelines|programming)\b",
    r"\bnot able to (?:produce|generate|provide)\b",
]
row = f"{'refusal_hint_rate':<22}"
for fname in fam_names:
    recs = per_family[fname]["records"]
    if not recs:
        row += f"{'(no data)':>26}"
        continue
    n_refused = 0
    for r in recs:
        text = r["output"][:500]  # only check opening
        for p in REFUSAL_HINTS:
            if re.search(p, text, re.IGNORECASE):
                n_refused += 1
                break
    pct = n_refused / len(recs) * 100
    row += f"{n_refused}/{len(recs)} ({pct:>4.1f}%)".rjust(26)
print(row)
table_rows.append(row)

with open(os.path.join(OUT_DIR, "regex_summary.txt"), "w") as f:
    f.write("\n".join(table_rows) + "\n")

print(f"\n[07] regex summary -> {OUT_DIR}/regex_summary.txt")
print(f"[07] per-output texts -> {OUT_DIR}/<family>/*.txt")
print("\n[07] DONE — read 3-6 outputs per family side-by-side to confirm regex transfer.")
