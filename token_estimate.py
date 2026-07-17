"""Token count estimation for Minotaur experiment.
Assembles full prompts for deliberate_indifference at all 4 ladder levels,
estimates token counts using word_count * 1.3 proxy.
"""
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Load all data
with open("corpus.json") as f:
    corpus = json.load(f)
with open("prompts/tasks.json") as f:
    tasks_list = json.load(f)["tasks"]
with open("prompts/context_ladder.json") as f:
    ladder = json.load(f)
with open("prompts/exhibit_pool.json") as f:
    exhibits = json.load(f)
with open("prompts/ground_truth.json") as f:
    ground_truth = json.load(f)

tasks_map = {t["id"]: t for t in tasks_list}
task = tasks_map["deliberate_indifference"]
task_truth = ground_truth["deliberate_indifference"]

# --- Helpers (mirrored from runner.py) ---

def build_corpus_context(cases_list):
    lines = []
    for c in cases_list:
        lines.append(f"--- {c['case_name']}, {c['citation']} ---")
        lines.append(f"Holding: {c['holding']}")
        for i, p in enumerate(c["key_passages"]):
            lines.append(f'Key Passage {i+1}: "{p}"')
        lines.append("")
    return "\n".join(lines)

def build_exhibit_context(exhibit_list):
    lines = []
    for ex in exhibit_list:
        lines.append(f"--- EXHIBIT {ex['id']}: {ex['name']} ({ex['date']}) ---")
        lines.append(f"From: {ex['from']} | To: {ex['to']} | Type: {ex['type']}")
        lines.append(ex["text"])
        lines.append("")
    return "\n".join(lines)

def build_cross_count_elements(task, tasks_map):
    pair_id = task.get("cross_count_pair")
    if not pair_id or pair_id not in tasks_map:
        return ""
    pair_task = tasks_map[pair_id]
    pair_elements = pair_task.get("required_elements", "")
    pair_name = pair_task.get("name", pair_id)
    return f"\n--- ALSO CONSIDER: REQUIRED ELEMENTS FOR {pair_name.upper()} ---\n{pair_elements}\n"

def word_count(text):
    return len(text.split())

def est_tokens(text):
    return int(word_count(text) * 1.3)

# --- Data references ---
relevant_case_ids = task["relevant_cases"]
relevant_exhibit_ids = task_truth["relevant_exhibits"]
elements_ctx = task["required_elements"]
sumf_ctx = task["sumf"]
defense_ctx = task.get("defense_positions", "")

print("=" * 80)
print("MINOTAUR TOKEN ESTIMATION — deliberate_indifference")
print("=" * 80)
print()

# Show component sizes first
all_corpus_ctx = build_corpus_context(corpus["cases"])
rel_corpus_ctx = build_corpus_context([c for c in corpus["cases"] if c["id"] in relevant_case_ids])
all_exhibit_ctx = build_exhibit_context(exhibits["exhibits"])
rel_exhibit_ctx = build_exhibit_context([e for e in exhibits["exhibits"] if e["id"] in relevant_exhibit_ids])

print("COMPONENT SIZES (estimated tokens via words * 1.3):")
print(f"  All corpus (31 cases):           {est_tokens(all_corpus_ctx):>7,} tokens  ({word_count(all_corpus_ctx):,} words)")
print(f"  Relevant corpus (5 cases):       {est_tokens(rel_corpus_ctx):>7,} tokens  ({word_count(rel_corpus_ctx):,} words)")
print(f"  All exhibits (38):               {est_tokens(all_exhibit_ctx):>7,} tokens  ({word_count(all_exhibit_ctx):,} words)")
print(f"  Relevant exhibits (15):          {est_tokens(rel_exhibit_ctx):>7,} tokens  ({word_count(rel_exhibit_ctx):,} words)")
print(f"  SUMF:                            {est_tokens(sumf_ctx):>7,} tokens  ({word_count(sumf_ctx):,} words)")
print(f"  Required elements:               {est_tokens(elements_ctx):>7,} tokens  ({word_count(elements_ctx):,} words)")
print(f"  Parties context (all):           {est_tokens(task['parties_context']):>7,} tokens  ({word_count(task['parties_context']):,} words)")
print(f"  Defendant context (relevant):    {est_tokens(task['defendant_context']):>7,} tokens  ({word_count(task['defendant_context']):,} words)")
print()

# --- Assemble per level ---
CONTEXT_LIMIT = 128_000

for level in ladder["levels"]:
    level_name = level["name"]
    max_tokens = level.get("max_tokens", 4096)

    # Filter corpus
    if level["corpus_filter"] == "relevant":
        filtered_cases = [c for c in corpus["cases"] if c["id"] in relevant_case_ids]
    elif level["corpus_filter"] == "none":
        filtered_cases = []
    else:  # "all"
        filtered_cases = corpus["cases"]

    # Filter exhibits
    if level["exhibit_filter"] == "relevant":
        filtered_exh = [e for e in exhibits["exhibits"] if e["id"] in relevant_exhibit_ids]
    elif level["exhibit_filter"] == "none":
        filtered_exh = []
    else:  # "all"
        filtered_exh = exhibits["exhibits"]

    # Build context strings
    corpus_ctx = build_corpus_context(filtered_cases)
    exhibit_ctx = build_exhibit_context(filtered_exh)

    # Parties
    defendants_filter = level.get("defendants_filter", "all")
    if defendants_filter == "relevant":
        parties_ctx = task.get("defendant_context", task.get("parties_context", ""))
    else:
        parties_ctx = task.get("parties_context", "")

    # Cross-count
    cross_ctx = ""
    if level.get("cross_count", False):
        cross_ctx = build_cross_count_elements(task, tasks_map)

    full_elements = elements_ctx + cross_ctx

    # Assemble base_prompt
    bp = task["base_prompt"]
    bp = bp.replace("[CORPUS]", corpus_ctx)
    bp = bp.replace("[EXHIBIT POOL]", exhibit_ctx)
    bp = bp.replace("[REQUIRED ELEMENTS]", full_elements)
    bp = bp.replace("[SUMF]", sumf_ctx)
    bp = bp.replace("[DEFENSE POSITIONS]", defense_ctx)
    bp = bp.replace("[PARTIES]", parties_ctx)

    # Assemble instruct_prompt
    ip = task["instruct_prompt"]
    ip = ip.replace("[CORPUS]", corpus_ctx)
    ip = ip.replace("[EXHIBIT POOL]", exhibit_ctx)
    ip = ip.replace("[REQUIRED ELEMENTS]", full_elements)
    ip = ip.replace("[SUMF]", sumf_ctx)
    ip = ip.replace("[DEFENSE POSITIONS]", defense_ctx)
    ip = ip.replace("[PARTIES]", parties_ctx)

    bp_tokens = est_tokens(bp)
    ip_tokens = est_tokens(ip)

    # For base conditions, nudge is prepended
    base_nudge = task["base_nudge"]
    instruct_nudge = task["instruct_nudge"]
    bp_nudge_tokens = est_tokens(base_nudge + bp)
    ip_nudge_tokens = est_tokens(ip)  # instruct_nudge goes in system_msg, separate

    print("-" * 80)
    print(f"LEVEL: {level_name}")
    print(f"  corpus_filter={level['corpus_filter']}  exhibit_filter={level['exhibit_filter']}  "
          f"defendants_filter={level.get('defendants_filter','all')}  cross_count={level.get('cross_count', False)}")
    print(f"  Cases: {len(filtered_cases)}  Exhibits: {len(filtered_exh)}")
    print()

    # 4 conditions
    conditions = {
        "base_alone":      (bp_tokens, "base_prompt only"),
        "base_nudge":      (bp_nudge_tokens, "nudge + base_prompt"),
        "instruct_alone":  (ip_tokens, "instruct_prompt only"),
        "instruct_nudge":  (ip_nudge_tokens + est_tokens(instruct_nudge),
                            "instruct_prompt + system_msg"),
    }

    for cond_name, (prompt_tok, desc) in conditions.items():
        total = prompt_tok + max_tokens
        over = total > CONTEXT_LIMIT
        status = "*** EXCEEDS 128K ***" if over else "OK"
        print(f"  {cond_name:20s}  prompt ~{prompt_tok:>7,} tok + {max_tokens:,} max_tokens = {total:>7,} total  {status}")

    print()
    # Also show the raw character and word counts for the biggest prompt variant
    biggest = max(bp_tokens, ip_tokens)
    biggest_label = "base_prompt" if bp_tokens >= ip_tokens else "instruct_prompt"
    print(f"  Largest prompt ({biggest_label}): {word_count(bp if bp_tokens >= ip_tokens else ip):,} words / "
          f"{len(bp if bp_tokens >= ip_tokens else ip):,} chars / ~{biggest:,} est. tokens")
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Model context window: 128,000 tokens")
print(f"max_tokens (generation budget): 4,096 at all levels")
print(f"Effective prompt budget: 128,000 - 4,096 = 123,904 tokens")
print()
print("The dominant cost is the exhibit pool. All 38 exhibits at L3/L4 are the")
print("binding constraint. If any level exceeds 128K, consider trimming exhibits")
print("or reducing max_tokens.")
