"""Runner: sends tasks to models across conditions, logs everything.
Pilot Run 2 — motion brief format, 4-level ladder, per-level max_tokens.
Multi-family: --family <llama70b|gemma31b|deepseek_v4_flash> selects the pair.
"""
import json, os, re, time, hashlib, argparse
from datetime import datetime
from openai import OpenAI
from config import *
from families import get_family

# --- CLI: which family to run (also accepts MINOTAUR_FAMILY env var for importers) ---
_parser = argparse.ArgumentParser()
_parser.add_argument("--family", default=os.environ.get("MINOTAUR_FAMILY"),
                     help="One of: llama70b, gemma31b, deepseek_v4_flash")
_parser.add_argument("--probe", action="store_true",
                     default=bool(os.environ.get("MINOTAUR_PROBE")),
                     help="Run probe subset: 5 tasks x L1+L4 x 4 cond x 3 runs = 120/family")
_args, _ = _parser.parse_known_args()
if not _args.family:
    raise SystemExit(
        "runner.py needs a family: pass --family <name> or set MINOTAUR_FAMILY env var. "
        "Available: llama70b, gemma31b, deepseek_v4_flash"
    )
FAMILY = get_family(_args.family)
FAMILY_NAME = _args.family
PROBE_MODE = _args.probe
# In probe mode, restrict the ladder to L1+L4 and cap runs at 3 per cell.
PROBE_LEVELS = {"L1_focused", "L4_cross_count"}
PROBE_RUNS = 3

# Override config defaults with the selected family (config.py is protected; shadow here)
BASE_MODEL = FAMILY["base_model_name"]
INSTRUCT_MODEL = FAMILY["instruct_model_id"]
INSTRUCT_PROVIDER = FAMILY["instruct_provider"]

# Bridges-2 vLLM client for base model — raw completion, no chat template
base_client = OpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)

# Instruct client setup, dispatched by provider
bedrock = None
instruct_client = None
if INSTRUCT_PROVIDER == "bedrock":
    import boto3
    from botocore.config import Config
    # max_tokens=4096 on Llama 70B Instruct occasionally exceeds the default
    # 60s read timeout. 900s gives generous headroom; 3-attempt retry covers
    # transient Bedrock blips.
    _bedrock_cfg = Config(read_timeout=900, connect_timeout=10,
                          retries={"max_attempts": 3})
    bedrock = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=_bedrock_cfg,
    )
elif INSTRUCT_PROVIDER == "together":
    instruct_client = OpenAI(
        api_key=TOGETHER_API_KEY,
        base_url=FAMILY["instruct_endpoint"],
    )
elif INSTRUCT_PROVIDER == "deepseek":
    instruct_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=FAMILY["instruct_endpoint"],
    )
else:
    raise ValueError(f"Unknown instruct_provider: {INSTRUCT_PROVIDER}")

# Family-namespaced output dirs (so families don't collide on checkpoints/prompts).
# Probe mode writes into a sibling "probe/" subtree so it never overwrites main runs.
FAMILY_RAW_DIR = os.path.join(RAW_RESULTS_DIR, FAMILY_NAME, "probe") if PROBE_MODE \
    else os.path.join(RAW_RESULTS_DIR, FAMILY_NAME)
FAMILY_PROMPT_DIR = os.path.join(PROMPT_LOG_DIR, FAMILY_NAME, "probe") if PROBE_MODE \
    else os.path.join(PROMPT_LOG_DIR, FAMILY_NAME)
if PROBE_MODE:
    print(f"[runner] PROBE MODE — levels={sorted(PROBE_LEVELS)}, runs={PROBE_RUNS}")

def load_corpus():
    with open(CORPUS_PATH) as f:
        return json.load(f)

def load_tasks():
    with open(TASKS_PATH) as f:
        return json.load(f)["tasks"]

def build_corpus_context(corpus, task):
    """Build the corpus string injected into [CORPUS] placeholder."""
    relevant = [c for c in corpus["cases"] if c["id"] in task["relevant_cases"]]
    lines = []
    for c in relevant:
        lines.append(f"--- {c['case_name']}, {c['citation']} ---")
        lines.append(f"Holding: {c['holding']}")
        for i, p in enumerate(c["key_passages"]):
            lines.append(f"Key Passage {i+1}: \"{p}\"")
        lines.append("")
    return "\n".join(lines)

def load_exhibits():
    with open(EXHIBIT_POOL_PATH) as f:
        return json.load(f)

def load_ground_truth():
    with open(GROUND_TRUTH_PATH) as f:
        return json.load(f)

def build_exhibit_context(exhibits):
    """Build the exhibit pool string injected into [EXHIBIT POOL] placeholder."""
    lines = []
    for ex in exhibits["exhibits"]:
        lines.append(f"--- EXHIBIT {ex['id']}: {ex['name']} ({ex['date']}) ---")
        lines.append(f"From: {ex['from']} | To: {ex['to']} | Type: {ex['type']}")
        lines.append(ex["text"])
        lines.append("")
    return "\n".join(lines)

def build_parties_context(task, level):
    """Build the parties block, filtering defendants by level.
    'relevant' → only this count's defendants. 'all' → full defendant list.
    """
    defendants_filter = level.get("defendants_filter", "all")
    if defendants_filter == "relevant":
        return task.get("defendant_context", task.get("parties_context", ""))
    else:  # "all"
        return task.get("parties_context", "")

def build_cross_count_elements(task, tasks_map):
    """At L4, inject the required elements from the paired count.
    Returns the paired count's element list, or empty string if no pair.
    """
    pair_id = task.get("cross_count_pair")
    if not pair_id or pair_id not in tasks_map:
        return ""
    pair_task = tasks_map[pair_id]
    pair_elements = pair_task.get("required_elements", "")
    pair_name = pair_task.get("name", pair_id)
    return f"\n--- ALSO CONSIDER: REQUIRED ELEMENTS FOR {pair_name.upper()} ---\n{pair_elements}\n"

def log_prompt(task_id, level_name, cond_name, run_i, prompt_text, system_msg=None):
    """Log the full assembled prompt for reproducibility."""
    os.makedirs(FAMILY_PROMPT_DIR, exist_ok=True)
    entry = {
        "family": FAMILY_NAME,
        "task_id": task_id,
        "level": level_name,
        "condition": cond_name,
        "run": run_i,
        "seed": SEED,
        "temperature": TEMPERATURE,
        "prompt": prompt_text,
        "system_msg": system_msg,
        "prompt_hash": hashlib.sha256(prompt_text.encode()).hexdigest()[:16],
        "timestamp": datetime.utcnow().isoformat(),
    }
    fname = f"{FAMILY_PROMPT_DIR}/{task_id}_{level_name}_{cond_name}_run{run_i:02d}.json"
    with open(fname, "w") as f:
        json.dump(entry, f, indent=2)

def run_base(prompt, max_tokens, nudge="", seed=SEED):
    """Base model via Bridges-2 vLLM: true pre-training checkpoint, no alignment, no chat template."""
    full_prompt = nudge + prompt
    # Use completions endpoint (not chat) — raw completion mode
    resp = base_client.completions.create(
        model=BASE_MODEL,
        prompt=full_prompt,
        temperature=TEMPERATURE,
        max_tokens=max_tokens,
        seed=seed,
    )
    return resp.choices[0].text, resp.usage

def run_instruct(prompt, max_tokens, system_msg=None, seed=None):
    """Instruct model dispatcher — routes to the family's provider."""
    if INSTRUCT_PROVIDER == "bedrock":
        return _run_instruct_bedrock(prompt, max_tokens, system_msg)
    return _run_instruct_openai_compat(prompt, max_tokens, system_msg, seed=seed)


def _run_instruct_bedrock(prompt, max_tokens, system_msg=None):
    """Bedrock Converse: Llama 3.1 70B Instruct. Bedrock has no seed parameter."""
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    system_list = [{"text": system_msg}] if system_msg else []
    resp = bedrock.converse(
        modelId=INSTRUCT_MODEL,
        messages=messages,
        system=system_list,
        inferenceConfig={"temperature": TEMPERATURE, "maxTokens": max_tokens},
    )
    output_text = resp["output"]["message"]["content"][0]["text"]
    u = resp["usage"]

    class Usage:
        def __init__(self, raw):
            self.prompt_tokens = raw["inputTokens"]
            self.completion_tokens = raw["outputTokens"]

    return output_text, Usage(u)


def _run_instruct_openai_compat(prompt, max_tokens, system_msg=None, seed=None):
    """OpenAI-compatible chat: Together (Gemma 3 27B IT) and DeepSeek (V3.1)."""
    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": INSTRUCT_MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
    }
    if FAMILY.get("instruct_supports_seed") and seed is not None:
        kwargs["seed"] = seed

    resp = instruct_client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content, resp.usage

def is_truncated(output, usage, max_tokens):
    """Detect whether the output was cut off at the token budget.
    True if completion tokens >= max_tokens - 10 (buffer for tokenizer variance)
    AND output doesn't end with a sentence-ending character.
    """
    at_limit = usage.completion_tokens >= (max_tokens - 10)
    no_ending = not output.rstrip().endswith(("." , "?", "!", '"', ")"))
    return at_limit and no_ending

def _call_with_retry(fn, max_attempts=3, backoff=5):
    """Retry wrapper with exponential backoff for transient API errors."""
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            wait = backoff * (2 ** attempt)
            print(f"  [retry {attempt+1}/{max_attempts}, waiting {wait}s] {e}")
            time.sleep(wait)


def run_experiment():
    """Pilot Run 2: 5 tasks × 4 levels × 4 conditions × 10 runs = 800 generations.
    Levels defined in context_ladder.json with per-level max_tokens.
    Motion brief format with SUMFs, parties context, cross-count injection.
    """
    corpus = load_corpus()
    tasks = load_tasks()
    exhibits = load_exhibits()
    ground_truth = load_ground_truth()

    # Build tasks lookup for cross-count pairing
    tasks_map = {t["id"]: t for t in tasks}

    with open(LADDER_PATH) as f:
        ladder = json.load(f)

    os.makedirs(FAMILY_RAW_DIR, exist_ok=True)

    # --- Resume from latest checkpoint if present (per-family) ---
    # Checkpoints live under FAMILY_RAW_DIR so families never collide.
    results = []
    completed_keys = set()
    ckpts = sorted(
        f for f in os.listdir(FAMILY_RAW_DIR)
        if f.startswith("checkpoint_") and f.endswith(".json")
    )
    if ckpts:
        latest = ckpts[-1]
        try:
            with open(os.path.join(FAMILY_RAW_DIR, latest)) as f:
                results = json.load(f)
            completed_keys = {
                (r["task_id"], r["level"], r["condition"], r["run"])
                for r in results
            }
            print(f"[resume] loaded {len(results)} prior generations from {latest}")
            print(f"[resume] {len(completed_keys)} cells already completed; skipping those")
        except Exception as e:
            print(f"[resume] WARN: failed to load {latest}: {e}; starting fresh")
            results = []
            completed_keys = set()

    for task in tasks:
        task_id = task["id"]
        task_truth = ground_truth.get(task_id, {})
        relevant_case_ids = task.get("relevant_cases", [])
        relevant_exhibit_ids = task_truth.get("relevant_exhibits", [])
        elements_ctx = task.get("required_elements", "")
        sumf_ctx = task.get("sumf", "")
        defense_ctx = task.get("defense_positions", "")
        base_nudge = task["base_nudge"]
        instruct_nudge = task["instruct_nudge"]

        for level in ladder["levels"]:
            level_name = level["name"]
            if PROBE_MODE and level_name not in PROBE_LEVELS:
                continue  # probe restricts to L1 + L4
            max_tokens = level.get("max_tokens", 4096)

            # ── Filter corpus by level ──
            if level["corpus_filter"] == "relevant":
                filtered_corpus = {"cases": [c for c in corpus["cases"]
                                              if c["id"] in relevant_case_ids]}
            else:  # "all"
                filtered_corpus = corpus

            # ── Filter exhibits by level ──
            if level["exhibit_filter"] == "relevant":
                filtered_exhibits = {"exhibits": [e for e in exhibits["exhibits"]
                                                   if e["id"] in relevant_exhibit_ids]}
            else:  # "all"
                filtered_exhibits = exhibits

            # ── Build context strings ──
            all_ids = [c["id"] for c in filtered_corpus["cases"]]
            corpus_ctx = build_corpus_context(filtered_corpus, {"relevant_cases": all_ids})
            exhibit_ctx = build_exhibit_context(filtered_exhibits)
            parties_ctx = build_parties_context(task, level)

            # ── Cross-count injection (L4 only) ──
            cross_ctx = ""
            if level.get("cross_count", False):
                cross_ctx = build_cross_count_elements(task, tasks_map)

            # ── Build prompts ──
            bp = task["base_prompt"]
            ip = task["instruct_prompt"]

            # Inject placeholders
            bp = bp.replace("[CORPUS]", corpus_ctx)
            ip = ip.replace("[CORPUS]", corpus_ctx)
            bp = bp.replace("[EXHIBIT POOL]", exhibit_ctx)
            ip = ip.replace("[EXHIBIT POOL]", exhibit_ctx)
            bp = bp.replace("[REQUIRED ELEMENTS]", elements_ctx + cross_ctx)
            ip = ip.replace("[REQUIRED ELEMENTS]", elements_ctx + cross_ctx)
            bp = bp.replace("[SUMF]", sumf_ctx)
            ip = ip.replace("[SUMF]", sumf_ctx)
            bp = bp.replace("[DEFENSE POSITIONS]", defense_ctx)
            ip = ip.replace("[DEFENSE POSITIONS]", defense_ctx)
            bp = bp.replace("[PARTIES]", parties_ctx)
            ip = ip.replace("[PARTIES]", parties_ctx)

            runs_this_run = PROBE_RUNS if PROBE_MODE else RUNS_PER_CONDITION
            levels_this_run = len(PROBE_LEVELS) if PROBE_MODE else len(ladder["levels"])
            total_expected = len(tasks) * levels_this_run * 4 * runs_this_run
            for cond_name in ["base_alone", "base_nudge", "instruct_nudge", "instruct_alone"]:
                for run_i in range(runs_this_run):
                    run_seed = SEED + run_i  # Per-run seed for reproducible variance
                    if (task_id, level_name, cond_name, run_i + 1) in completed_keys:
                        continue  # already in checkpoint, skip silently
                    print(f"  {task_id} | {level_name} | {cond_name} | run {run_i+1}/{runs_this_run} | seed={run_seed}")
                    t0 = time.time()

                    if cond_name == "base_alone":
                        run_fn = lambda _bp=bp, _s=run_seed: run_base(_bp, max_tokens, seed=_s)
                    elif cond_name == "base_nudge":
                        run_fn = lambda _bp=bp, _bn=base_nudge, _s=run_seed: run_base(_bp, max_tokens, nudge=_bn, seed=_s)
                    elif cond_name == "instruct_nudge":
                        run_fn = lambda _ip=ip, _ins=instruct_nudge, _s=run_seed: run_instruct(_ip, max_tokens, system_msg=_ins, seed=_s)
                    else:  # instruct_alone
                        run_fn = lambda _ip=ip, _s=run_seed: run_instruct(_ip, max_tokens, seed=_s)

                    try:
                        output, usage = _call_with_retry(run_fn)
                    except Exception as e:
                        print(f"  [FAILED] {task_id} | {level_name} | {cond_name} | run {run_i+1}: {e}")
                        continue
                    elapsed = time.time() - t0
                    truncated = is_truncated(output, usage, max_tokens)

                    # Log full assembled prompt for reproducibility
                    prompt_to_log = bp if "base" in cond_name else ip
                    sys_msg_to_log = instruct_nudge if cond_name == "instruct_nudge" else None
                    if cond_name == "base_nudge":
                        prompt_to_log = base_nudge + prompt_to_log
                    log_prompt(task_id, level_name, cond_name, run_i + 1, prompt_to_log, sys_msg_to_log)

                    seed_to_log = run_seed if (
                        "base" in cond_name or FAMILY.get("instruct_supports_seed")
                    ) else None
                    results.append({
                        "family": FAMILY_NAME,
                        "task_id": task_id,
                        "task_name": task["name"],
                        "doc_type": task.get("doc_type", "motion"),
                        "level": level_name,
                        "condition": cond_name,
                        "run": run_i + 1,
                        "output": output,
                        "tokens_prompt": usage.prompt_tokens,
                        "tokens_completion": usage.completion_tokens,
                        "max_tokens": max_tokens,
                        "truncated": truncated,
                        "elapsed_sec": round(elapsed, 2),
                        "timestamp": datetime.utcnow().isoformat(),
                        "model": BASE_MODEL if "base" in cond_name else INSTRUCT_MODEL,
                        "seed": seed_to_log,
                    })
                    # Progressive save every 50 generations — insurance against crash
                    if len(results) % 50 == 0:
                        ckpt = f"{FAMILY_RAW_DIR}/checkpoint_{len(results):04d}.json"
                        with open(ckpt, "w") as ck:
                            json.dump(results, ck)
                        print(f"  [checkpoint] {len(results)}/{total_expected} saved → {ckpt}")

    # Save
    outfile = f"{FAMILY_RAW_DIR}/run_{FAMILY_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} generations to {outfile}")
    return results

if __name__ == "__main__":
    run_experiment()