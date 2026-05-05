"""pairwise.py — Pairwise LLM-as-judge with six bias controls.
Run after scorer.py. Compares base vs instruct outputs within each
(task, level, run) triple using position-randomized, format-stripped,
decomposed judging with chain-of-thought rationales.

Bias controls implemented:
  1. Position randomization (A/B swap with tracking)
  2. Length-controlled analysis (stratified by length ratio)
  3. Format-blind judging (markdown/formatting stripped before comparison)
  4. Decomposed judging (axes aligned with Gates 6-9)
  5. Inter-rater agreement (Opus 4.6 + GPT-4o as cross-family judges)
  6. Chain-of-thought rationale extraction (auditable reasoning)

Usage:
  python pairwise.py                              # run all pairwise comparisons
  python pairwise.py --sample 50                   # run on 50 random pairs
  python pairwise.py --audit                       # print rationales for spot-check
  python pairwise.py results/scored/scored_run_*.json
"""
import json, os, re, random, csv, sys
from collections import defaultdict
from datetime import datetime
from openai import OpenAI
import anthropic
from config import *

# ─── CONFIGURATION ──────────────────────────────────────────────────

PRIMARY_JUDGE = JUDGE_MODEL           # Anthropic API (Opus)
SECONDARY_JUDGE = "gpt-4o"            # IAA cross-family check (OpenAI direct)

IAA_SAMPLE_RATE = 0.15  # 15% of pairs get dual-judged for inter-rater agreement
NUM_PASSES = 1          # single pass per judge (n=10 runs provides variance)
HOLISTIC_JUDGE = JUDGE_MODEL          # holistic zealous advocacy judge

PAIRWISE_RESULTS_DIR = "results/pairwise"


# ─── CONTROL 3: FORMAT STRIPPING ────────────────────────────────────────────

def strip_formatting(text):
    """Remove markdown, bullet points, headers, structural markers.
    Preserves legal content: citations, exhibit refs, quotations.
    """
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[a-z]\)\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\([a-z]\)\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()


# ─── CONTROL 4: DECOMPOSED PAIRWISE PROMPT ───────────────────────────────────

DECOMPOSED_PAIRWISE_PROMPT = """You are comparing two legal briefs written for the SAME task.
Both briefs attempt a {doc_type} for {task_name}.

IMPORTANT: Do NOT prefer a response merely because it is longer, more
verbose, or more heavily formatted. Evaluate SUBSTANCE, not presentation.

BRIEF A:
{brief_a}

BRIEF B:
{brief_b}

Evaluate on FIVE axes (for each, choose A, B, or TIE):

1. CITATION QUALITY: Which brief cites case law more precisely, with
   named-case analogies drawing specific factual parallels rather than
   citing cases for propositions only? (legal_authority_use)

2. EXHIBIT USAGE: Which brief better anchors each factual assertion to
   a specific exhibit, front-loading evidence rather than asserting
   then supporting later? (exhibit_deployment, element_targeting)

3. POSITIONAL DISCIPLINE: Which brief maintains pure plaintiff advocacy
   throughout — no hedging, no both-sides framing, no volunteering
   weaknesses? Do NOT penalize directness or reward balance.
   (positional_discipline, adverse_treatment)

4. ELEMENT TARGETING: Which brief organizes argument around the legal
   elements of the claim and assigns evidence to each element more
   systematically? (element_targeting, framing_accuracy)

5. ROLE INTEGRITY: Which reads more like a real filed document by a
   plaintiff's attorney — attorney voice, no register breaks, no
   AI-flavored qualifications? (role_integrity)

For each axis: winner (A/B/TIE), confidence (1-5), reasoning (1-2 sentences).
Then: OVERALL winner (A/B/TIE), holistic, weighted toward exhibit usage + positional discipline.

Return ONLY valid JSON."""


# ─── CONTROL 4b: HOLISTIC ZEALOUS ADVOCACY PROMPT ──────────────────────────
# Single Opus 4.6 call per pair. No self-consistency — one pass, holistic.
# Asks the gold-standard question: which brief better serves its litigation
# objective? Used as a calibration check against the decomposed axes.

HOLISTIC_ZEALOUS_PROMPT = """You are a senior litigator evaluating two legal briefs written for the SAME task.

TASK: {doc_type} on behalf of the PLAINTIFF
Count/claim: {task_name}
Objective: {objective}

Both briefs had access to the same exhibits and case law.
Your only question: which brief does a BETTER JOB as a ZEALOUS ADVOCATE
for the plaintiff, given the materials available?

Zealous advocacy means:
- Advancing the plaintiff's position on every element, without hedging
- Deploying available evidence at maximum effectiveness
- Arguing like a skilled attorney who intends to win, not to be balanced

Do NOT prefer a brief merely because it is longer or more verbose.
Do NOT penalize directness or one-sidedness — that is the goal.

BRIEF A:
{brief_a}

BRIEF B:
{brief_b}

Return ONLY valid JSON with keys:
"winner": "A", "B", or "TIE"
"margin": "clear", "moderate", or "narrow"
"reasoning": one sentence explaining the decisive factor
"""


# ─── JUDGE CLIENTS ──────────────────────────────────────────────────────

def get_primary_client():
    """Primary judge via Anthropic API (Opus)."""
    if not hasattr(get_primary_client, "_c"):
        get_primary_client._c = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
        )
    return get_primary_client._c

def get_secondary_client():
    """IAA cross-family judge via OpenAI (GPT-4o)."""
    if not hasattr(get_secondary_client, "_c"):
        get_secondary_client._c = OpenAI(
            api_key=OPENAI_API_KEY,
        )
    return get_secondary_client._c

def _permissive_json_parse(raw):
    raw = raw.strip()
    try: return json.loads(raw)
    except json.JSONDecodeError: pass
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if fence:
        try: return json.loads(fence.group(1).strip())
        except: pass
    brace = re.search(r'(\{[\s\S]*\})', raw)
    if brace:
        try: return json.loads(brace.group(1))
        except: pass
    raise json.JSONDecodeError("No valid JSON", raw, 0)


def run_holistic_pairwise(output_a, output_b, task_name, doc_type,
                          client, strip_fmt=True):
    """Single Opus 4.6 holistic zealous advocacy comparison.
    One pass only. Returns dict with winner (de-anonymized), margin, reasoning.
    """
    if strip_fmt:
        brief_a = strip_formatting(output_a)[:10000]
        brief_b = strip_formatting(output_b)[:10000]
    else:
        brief_a = output_a[:10000]
        brief_b = output_b[:10000]

    swapped = random.random() < 0.5
    if swapped:
        brief_a, brief_b = brief_b, brief_a
    position_map = {
        "A": "output_b" if swapped else "output_a",
        "B": "output_a" if swapped else "output_b",
    }
    objective = (
        "defeat defendant's motion for summary judgment"
        if doc_type == "opposition"
        else "obtain partial summary judgment"
    )
    prompt = HOLISTIC_ZEALOUS_PROMPT.format(
        doc_type=(
            "Opposition to Motion for Summary Judgment"
            if doc_type == "opposition"
            else "Motion for Partial Summary Judgment"
        ),
        task_name=task_name,
        objective=objective,
        brief_a=brief_a,
        brief_b=brief_b,
    )
    try:
        if isinstance(client, anthropic.Anthropic):
            resp = client.messages.create(
                model=HOLISTIC_JUDGE,
                system="You are a senior litigator. Evaluate zealous advocacy. "
                       "Return only valid JSON.",
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=256,
            )
            raw_text = resp.content[0].text
        else:
            resp = client.chat.completions.create(
                model=SECONDARY_JUDGE,
                messages=[
                    {"role": "system", "content":
                     "You are a senior litigator. Evaluate zealous advocacy. "
                     "Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=256,
            )
            raw_text = resp.choices[0].message.content
        result = _permissive_json_parse(raw_text)
        raw_winner = result.get("winner", "TIE")
        real_winner = (
            "TIE" if raw_winner == "TIE"
            else position_map.get(raw_winner, "TIE")
        )
        judge_used = HOLISTIC_JUDGE if isinstance(client, anthropic.Anthropic) else SECONDARY_JUDGE
        return {
            "winner": real_winner,
            "margin": result.get("margin", ""),
            "reasoning": result.get("reasoning", ""),
            "swapped": swapped,
            "judge_model": judge_used,
        }
    except Exception as e:
        print(f"  Holistic judge error: {e}")
        return None


# ─── CORE PAIRWISE EVALUATION ──────────────────────────────────────────────

def run_single_pairwise(
    output_a, output_b, task_name, doc_type,
    judge_model, client, strip_fmt=True,
):
    """Run one pairwise comparison with all controls active.
    Returns (result_dict, position_map) where position_map tracks
    which condition was A vs B for de-anonymization.
    """
    # Control 3: Format stripping
    if strip_fmt:
        brief_a = strip_formatting(output_a)
        brief_b = strip_formatting(output_b)
    else:
        brief_a, brief_b = output_a, output_b

    brief_a = brief_a[:10000]
    brief_b = brief_b[:10000]

    # Control 1: Position randomization — track which condition lands in slot A vs B
    swapped = random.random() < 0.5
    if swapped:
        brief_a, brief_b = brief_b, brief_a
    position_map = {
        "A": "output_b" if swapped else "output_a",
        "B": "output_a" if swapped else "output_b",
    }

    prompt = DECOMPOSED_PAIRWISE_PROMPT.format(
        doc_type=doc_type, task_name=task_name,
        brief_a=brief_a, brief_b=brief_b,
    )

    pass_results = []
    for _ in range(NUM_PASSES):
        try:
            if isinstance(client, anthropic.Anthropic):
                resp = client.messages.create(
                    model=judge_model,
                    system="You are a precise legal evaluator. "
                           "Compare two briefs on five axes. Return only valid JSON.",
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1024,
                )
                raw_text = resp.content[0].text
            else:
                resp = client.chat.completions.create(
                    model=judge_model,
                    messages=[
                        {"role": "system", "content":
                         "You are a precise legal evaluator. "
                         "Compare two briefs on five axes. Return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1024,
                )
                raw_text = resp.choices[0].message.content
            pass_results.append(
                _permissive_json_parse(raw_text)
            )
        except Exception as e:
            print(f"  Judge error ({judge_model}): {e}")

    if not pass_results:
        return None, position_map

    AXES = ["citation_quality", "exhibit_usage", "positional_discipline",
            "element_targeting", "role_integrity"]

    def _deanon(w):
        """Map A/B back to the real condition (output_a / output_b / TIE)."""
        return "TIE" if w == "TIE" else position_map.get(w, "TIE")

    def _maj(vals):
        vals = [v for v in vals if v]
        return max(set(vals), key=vals.count) if vals else "TIE"

    def _avg(vals):
        vals = [v for v in vals if isinstance(v, (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None

    axis_results = {}
    for ax in AXES:
        winners = [
            p.get(ax, {}).get("winner") if isinstance(p.get(ax), dict)
            else p.get(f"{ax}_winner")
            for p in pass_results
        ]
        confs = [
            p.get(ax, {}).get("confidence") if isinstance(p.get(ax), dict)
            else p.get(f"{ax}_confidence")
            for p in pass_results
        ]
        axis_results[ax] = {
            "winner": _deanon(_maj(winners)),
            "confidence": _avg(confs),
        }

    overall_votes = [
        p.get("overall", {}).get("winner") if isinstance(p.get("overall"), dict)
        else (p.get("overall_winner") or p.get("OVERALL_WINNER"))
        for p in pass_results
    ]
    # Control 6: Chain-of-thought rationale (first valid pass)
    rationale = next(
        (p.get("reasoning", "") for p in pass_results if p.get("reasoning")), ""
    )

    return {
        "overall_winner": _deanon(_maj(overall_votes)),
        "swapped": swapped,
        "position_map": position_map,
        "axes": axis_results,
        "rationale": rationale,
        "agreement": round(len(pass_results) / NUM_PASSES, 2),
        "judge_model": judge_model,
    }, position_map
# ─── CONTROL 2: LENGTH STRATIFICATION ────────────────────────────────────────

def length_bucket(output_a, output_b):
    """Bin pair by word-count ratio for Control 2 (length-controlled analysis).
    Buckets: balanced (<1.25×), moderate (1.25–1.75×), large (>1.75×).
    """
    la, lb = len(output_a.split()), len(output_b.split())
    if la == 0 or lb == 0:
        return "unknown"
    ratio = max(la, lb) / min(la, lb)
    if ratio < 1.25:
        return "balanced"
    elif ratio < 1.75:
        return "moderate"
    return "large"


# ─── PAIR BUILDER ─────────────────────────────────────────────────────────────

def build_pairs(results):
    """Build (base, instruct) pairs within each (task, level, run) triple.
    Comparisons: base_alone vs instruct_alone, base_nudge vs instruct_nudge.
    """
    index = defaultdict(dict)
    for r in results:
        key = (r["task_id"], r["level"], r["run"])
        index[key][r["condition"]] = r

    pairs = []
    for (task_id, level, run), conds in index.items():
        for base_c, inst_c in [
            ("base_alone", "instruct_alone"),
            ("base_nudge", "instruct_nudge"),
        ]:
            if base_c in conds and inst_c in conds:
                pairs.append({
                    "task_id": task_id,
                    "task_name": conds[base_c].get("task_name", task_id),
                    "level": level,
                    "run": run,
                    "comparison": f"{base_c}_vs_{inst_c}",
                    "doc_type": conds[base_c].get("doc_type", "motion"),
                    "output_a": conds[base_c]["output"],   # a = base
                    "output_b": conds[inst_c]["output"],   # b = instruct
                    "len_bucket": length_bucket(
                        conds[base_c]["output"], conds[inst_c]["output"]
                    ),
                })
    return pairs


# ─── MAIN EVALUATION LOOP ─────────────────────────────────────────────────────

def run_pairwise(results_file=None, sample=None, audit=False):
    """Run all pairwise comparisons with all six bias controls active.
    Applies IAA_SAMPLE_RATE (15%) dual-judging with Claude as cross-family judge.
    """
    import glob
    if results_file is None:
        files = sorted(glob.glob("results/scored/scored_*.json"))
        if not files:
            print("No scored results found. Run scorer.py first.")
            return []
        results_file = files[-1]

    print(f"Loading: {results_file}")
    with open(results_file) as f:
        results = json.load(f)

    pairs = build_pairs(results)
    print(f"Built {len(pairs)} pairs from {len(results)} generations")

    if sample:
        pairs = random.sample(pairs, min(sample, len(pairs)))
        print(f"Sampled down to {len(pairs)} pairs")

    # Control 5: Flag 15% of pairs for IAA dual-judging (Claude)
    iaa_idx = set(random.sample(
        range(len(pairs)), max(1, int(len(pairs) * IAA_SAMPLE_RATE))
    ))

    os.makedirs(PAIRWISE_RESULTS_DIR, exist_ok=True)
    pairwise_results = []
    primary_client = get_primary_client()
    secondary_client = get_secondary_client()

    for i, pair in enumerate(pairs):
        print(f"  [{i+1}/{len(pairs)}] "
              f"{pair['task_id']} | {pair['level']} | "
              f"run {pair['run']} | {pair['comparison']} "
              f"[{pair['len_bucket']}]")

        # Holistic zealous advocacy judgment (Opus 4.6, one pass)
        holistic_result = run_holistic_pairwise(
            pair["output_a"], pair["output_b"],
            pair["task_name"],
            pair.get("doc_type", "motion"),
            client=primary_client,  # Opus 4.6 is now primary
        )

        primary_result, _ = run_single_pairwise(
            pair["output_a"], pair["output_b"],
            pair["task_name"], pair.get("doc_type", "motion"),
            judge_model=PRIMARY_JUDGE,
            client=primary_client,
        )

        # Control 5: IAA — cross-family judge on sampled pairs
        iaa_result = None
        if i in iaa_idx:
            print(f"    [IAA] Running cross-family judge ({SECONDARY_JUDGE})")
            iaa_result, _ = run_single_pairwise(
                pair["output_a"], pair["output_b"],
                pair["task_name"], pair.get("doc_type", "motion"),
                judge_model=SECONDARY_JUDGE,
                client=secondary_client,
                strip_fmt=True,
            )

        iaa_agreement = None
        if primary_result and iaa_result:
            iaa_agreement = (
                primary_result["overall_winner"]
                == iaa_result["overall_winner"]
            )

        # Check holistic vs decomposed agreement
        holistic_decomposed_agree = None
        if primary_result and holistic_result:
            holistic_decomposed_agree = (
                primary_result["overall_winner"]
                == holistic_result["winner"]
            )

        row = {
            **pair,
            "output_a": None,   # strip raw outputs to keep file small
            "output_b": None,
            "primary": primary_result,
            "iaa": iaa_result,
            "iaa_agreement": iaa_agreement,
            "holistic": holistic_result,
            "holistic_decomposed_agree": holistic_decomposed_agree,
        }
        pairwise_results.append(row)

        if audit and primary_result:
            print(f"    Rationale: {primary_result.get('rationale', '')[:200]}")

    # Save JSON
    outfile = (
        f"{PAIRWISE_RESULTS_DIR}/"
        f"pairwise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(outfile, "w") as f:
        json.dump(pairwise_results, f, indent=2)
    print(f"\nSaved {len(pairwise_results)} pairwise results to {outfile}")

    export_pairwise_csv(pairwise_results, outfile.replace(".json", ".csv"))
    print_pairwise_summary(pairwise_results)
    return pairwise_results


# ─── AGGREGATION ──────────────────────────────────────────────────────────────

def print_pairwise_summary(results):
    """Print win rates by axis, by level, by comparison type, and IAA rate."""
    AXES = ["citation_quality", "exhibit_usage", "positional_discipline",
            "element_targeting", "role_integrity"]

    def win_rate(rows, winner_key="overall_winner", condition="output_a"):
        """Fraction where condition won (output_a = base)."""
        valid = [r for r in rows if r.get("primary")]
        if not valid:
            return None
        wins = sum(
            1 for r in valid
            if r["primary"].get(winner_key) == condition
        )
        ties = sum(
            1 for r in valid
            if r["primary"].get(winner_key) == "TIE"
        )
        return {
            "base_win": round(wins / len(valid), 3),
            "tie": round(ties / len(valid), 3),
            "instruct_win": round(
                (len(valid) - wins - ties) / len(valid), 3
            ),
            "n": len(valid),
        }

    print("\n" + "=" * 80)
    print("PAIRWISE SUMMARY — Overall")
    print("=" * 80)
    overall = win_rate(results)
    if overall:
        print(f"  Base wins:    {overall['base_win']:.1%}  (n={overall['n']})")
        print(f"  Ties:         {overall['tie']:.1%}")
        print(f"  Instruct wins:{overall['instruct_win']:.1%}")

    print("\n── By Axis ──")
    for ax in AXES:
        valid = [r for r in results if r.get("primary")]
        base_w = sum(
            1 for r in valid
            if r["primary"].get("axes", {}).get(ax, {}).get("winner")
            == "output_a"
        )
        ties = sum(
            1 for r in valid
            if r["primary"].get("axes", {}).get(ax, {}).get("winner")
            == "TIE"
        )
        n = len(valid) or 1
        print(f"  {ax:<26} base={base_w/n:.1%}  tie={ties/n:.1%}  "
              f"instruct={(n-base_w-ties)/n:.1%}")

    print("\n── By Level ──")
    for level in ["L1_focused", "L2_exhibit_noise", "L3_full_noise", "L4_cross_count"]:
        lvl_rows = [r for r in results if r["level"] == level]
        wr = win_rate(lvl_rows)
        if wr:
            print(f"  {level}: base={wr['base_win']:.1%}  "
                  f"tie={wr['tie']:.1%}  "
                  f"instruct={wr['instruct_win']:.1%}  (n={wr['n']})")

    print("\n── By Comparison ──")
    for cmp in ["base_alone_vs_instruct_alone", "base_nudge_vs_instruct_nudge"]:
        cmp_rows = [r for r in results if r.get("comparison") == cmp]
        wr = win_rate(cmp_rows)
        if wr:
            print(f"  {cmp}: base={wr['base_win']:.1%}  "
                  f"instruct={wr['instruct_win']:.1%}  (n={wr['n']})")

    # Holistic zealous advocacy report
    h_rows = [r for r in results if r.get("holistic")]
    if h_rows:
        h_base = sum(
            1 for r in h_rows
            if r["holistic"].get("winner") == "output_a"
        )
        h_ties = sum(
            1 for r in h_rows
            if r["holistic"].get("winner") == "TIE"
        )
        h_n = len(h_rows)
        print(f"\n\u2500\u2500 Holistic Zealous Advocacy (Opus 4.6, n={h_n}) \u2500\u2500")
        print(f"  Base wins:    {h_base/h_n:.1%}")
        print(f"  Ties:         {h_ties/h_n:.1%}")
        print(f"  Instruct wins:{(h_n-h_base-h_ties)/h_n:.1%}")
        # Margin breakdown
        for margin in ["clear", "moderate", "narrow"]:
            m_rows = [r for r in h_rows
                      if r["holistic"].get("margin") == margin]
            if m_rows:
                m_base = sum(
                    1 for r in m_rows
                    if r["holistic"].get("winner") == "output_a"
                )
                print(f"    {margin:<10}: base={m_base/len(m_rows):.1%}  "
                      f"(n={len(m_rows)})")
        # Agreement with decomposed overall
        agree_rows = [r for r in h_rows
                      if r.get("holistic_decomposed_agree") is not None]
        if agree_rows:
            agree_rate = sum(
                1 for r in agree_rows
                if r["holistic_decomposed_agree"]
            ) / len(agree_rows)
            print(f"  Holistic/decomposed agreement: {agree_rate:.1%}  "
                  f"(n={len(agree_rows)})")

    # IAA report
    iaa_rows = [r for r in results if r.get("iaa") is not None]
    if iaa_rows:
        agree = sum(1 for r in iaa_rows if r.get("iaa_agreement"))
        print(f"\n── IAA (cross-family, n={len(iaa_rows)}) ──")
        print(f"  Agreement rate: {agree/len(iaa_rows):.1%}")

    # Control 2: Length bucket breakdown
    print("\n── By Length Bucket ──")
    for bucket in ["balanced", "moderate", "large"]:
        b_rows = [r for r in results if r.get("len_bucket") == bucket]
        wr = win_rate(b_rows)
        if wr:
            print(f"  {bucket:<10}: base={wr['base_win']:.1%}  "
                  f"instruct={wr['instruct_win']:.1%}  (n={wr['n']})")


# ─── CSV EXPORT ───────────────────────────────────────────────────────────────

def export_pairwise_csv(results, outpath):
    """Export flat CSV with one row per pair."""
    AXES = ["citation_quality", "exhibit_usage", "positional_discipline",
            "element_targeting", "role_integrity"]

    fields = (
        ["task_id", "task_name", "level", "run", "comparison",
         "len_bucket", "overall_winner", "swapped", "agreement",
         "iaa_agreement", "holistic_winner", "holistic_margin",
         "holistic_decomposed_agree"]
        + [f"{ax}_winner" for ax in AXES]
        + [f"{ax}_confidence" for ax in AXES]
        + ["iaa_overall_winner", "holistic_reasoning", "rationale"]
    )

    rows = []
    for r in results:
        p = r.get("primary") or {}
        iaa = r.get("iaa") or {}
        row = {
            "task_id": r["task_id"],
            "task_name": r.get("task_name", ""),
            "level": r["level"],
            "run": r["run"],
            "comparison": r.get("comparison", ""),
            "len_bucket": r.get("len_bucket", ""),
            "overall_winner": p.get("overall_winner", ""),
            "swapped": p.get("swapped", ""),
            "agreement": p.get("agreement", ""),
            "iaa_agreement": r.get("iaa_agreement", ""),
            "iaa_overall_winner": iaa.get("overall_winner", ""),
            "holistic_winner": (r.get("holistic") or {}).get("winner", ""),
            "holistic_margin": (r.get("holistic") or {}).get("margin", ""),
            "holistic_decomposed_agree": r.get("holistic_decomposed_agree", ""),
            "holistic_reasoning": (r.get("holistic") or {}).get("reasoning", "")[:300],
            "rationale": p.get("rationale", "")[:300],
        }
        for ax in AXES:
            ax_data = p.get("axes", {}).get(ax, {})
            row[f"{ax}_winner"] = ax_data.get("winner", "")
            row[f"{ax}_confidence"] = ax_data.get("confidence", "")
        rows.append(row)

    with open(outpath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} rows to {outpath}")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pairwise LLM-as-judge")
    parser.add_argument("results_file", nargs="?", default=None,
                        help="Path to scored JSON (default: latest in results/scored/)")
    parser.add_argument("--sample", type=int, default=None,
                        help="Run on N random pairs instead of all")
    parser.add_argument("--audit", action="store_true",
                        help="Print rationales for spot-check")
    args = parser.parse_args()
    run_pairwise(
        results_file=args.results_file,
        sample=args.sample,
        audit=args.audit,
    )