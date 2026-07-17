"""Scorer: runs gates on all results, aggregates metrics, outputs tables.
Pilot Run 2 — G3a/G3b split, truncated field, level×condition breakdown.
Updated for bundled measurements in corrected gates.py.
"""
import json, os, csv, re
from collections import defaultdict
from gates import run_gates
from config import *

# ─── PATH 1: Post-Hoc Output Metrics (zero API cost) ────────────

# Alignment overhead patterns — regex lists for token categorization
HEDGING_PATTERNS = [
    r'\bit could be argued\b', r'\barguably\b', r'\bit appears that\b',
    r'\bit seems that\b', r'\bpotentially\b', r'\bpossibly\b',
    r'\bmay suggest\b', r'\bmight indicate\b', r'\bcould potentially\b',
    r'\bone could argue\b', r'\bit is possible that\b',
    r'\blikely\b(?!\s+(?:to succeed|establishes|demonstrates|shows))',
    r'\bperhaps\b', r'\bconceivably\b',
]
META_COMMENTARY_PATTERNS = [
    r'\bI should note\b', r'\bit(?:\x27|\')s important to (?:note|consider|recognize)\b',
    r'\bI would like to\b', r'\blet me (?:address|analyze|examine|consider)\b',
    r'\bbefore (?:addressing|analyzing|turning to)\b',
    r'\bin this (?:section|analysis|brief|motion)\b.*?\bI will\b',
    r'\bI(?:\x27|\')ll now\b', r'\bturning (?:now )?to\b',
    r'\bas (?:discussed|noted|mentioned) (?:above|below|earlier)\b',
]
BALANCED_ANALYSIS_PATTERNS = [
    r'\bon the other hand\b', r'\bdefendants? (?:may|might|could) argue\b',
    r'\bthere are counterarguments\b', r'\bto be fair\b',
    r'\bboth sides\b', r'\bbalancing (?:the )?(?:interests|considerations)\b',
    r'\bthe court (?:must|should|will need to) weigh\b',
    r'\breasonable minds (?:could|may) differ\b',
    r'\backnowledg(?:e|ing) (?:that )?(?:the )?(?:defense|defendants?)\b',
    r'\bwhile (?:the )?defendants?\b.*\bhave a point\b',
]
DISCLAIMER_PATTERNS = [
    r'\bthis is not legal advice\b', r'\bnot a lawyer\b',
    r'\bshould consult\b', r'\bseek (?:legal )?(?:advice|counsel)\b',
    r'\bfor informational purposes\b', r'\bdisclaimer\b',
    r'\bcannot provide legal\b', r'\bnot intended as\b',
]
PREAMBLE_PATTERNS = [
    r'^(?:I(?:\x27|\')ll|I will|Let me|Here is|Based on|Below is|The following)',
    r'^(?:I(?:\x27|\')m drafting|I(?:\x27|\')m going to|Sure|Certainly|Of course)',
    r'^(?:Thank you for|I understand|You(?:\x27|\')ve asked)',
]
# First substantive legal claim indicators
SUBSTANTIVE_CLAIM_PATTERNS = [
    r'\bExhibit [A-Z]', r'\bEx\.\s*[A-Z]',
    r'\b\d+\s+U\.S\.C\.', r'\b\d+\s+(?:U\.S\.|F\.\d+d?|A\.\d+d?)\s+\d+',
    r'\b(?:Plaintiff|Defendant)s?\s+(?:establish|demonstrat|show|prov|fail)',
    r'\bgenuine (?:dispute|issue)\b', r'\bsummary judgment\b',
    r'\bdeliberate indifference\b', r'\bretaliation\b',
    r'\baccommodation\b', r'\bfraud\b', r'\bconspiracy\b',
]


def _count_pattern_tokens(text, patterns):
    """Count approximate token weight of all pattern matches in text."""
    matches = 0
    token_count = 0
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            matches += 1
            token_count += len(m.group().split())
    return matches, token_count


def _find_first_substantive_token(text):
    """Find the character offset of the first substantive legal claim."""
    for p in SUBSTANTIVE_CLAIM_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            prefix = text[:m.start()]
            return m.start(), len(prefix.split())
    return len(text), len(text.split())


def compute_output_metrics(output, ground_truth_task=None):
    """Path 1: Zero-cost post-hoc metrics computed on raw output text."""
    words = output.split()
    total_words = len(words)
    if total_words == 0:
        return _empty_output_metrics()

    hedge_n, hedge_tok = _count_pattern_tokens(output, HEDGING_PATTERNS)
    meta_n, meta_tok = _count_pattern_tokens(output, META_COMMENTARY_PATTERNS)
    balanced_n, balanced_tok = _count_pattern_tokens(output, BALANCED_ANALYSIS_PATTERNS)
    disclaimer_n, disclaimer_tok = _count_pattern_tokens(output, DISCLAIMER_PATTERNS)

    overhead_matches = hedge_n + meta_n + balanced_n + disclaimer_n
    overhead_tokens = hedge_tok + meta_tok + balanced_tok + disclaimer_tok
    alignment_overhead_rate = overhead_tokens / total_words if total_words else 0

    first_claim_char, first_claim_tokens = _find_first_substantive_token(output)

    para_match = re.search(r'^\s*\d+\.', output, re.MULTILINE)
    tokens_to_first_para = len(output[:para_match.start()].split()) if para_match else total_words

    substantive_tokens = total_words - overhead_tokens
    substantive_density = substantive_tokens / total_words if total_words else 0

    words_lower = [w.lower().strip('.,;:!\'"()[]{}') for w in words if w.strip()]
    unique_words = set(words_lower)
    type_token_ratio = len(unique_words) / len(words_lower) if words_lower else 0

    sentences = re.split(r'[.!?]+', output)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    sent_lengths = [len(s.split()) for s in sentences]
    if len(sent_lengths) > 1:
        mean_sent_len = sum(sent_lengths) / len(sent_lengths)
        sent_len_variance = sum((l - mean_sent_len) ** 2 for l in sent_lengths) / (len(sent_lengths) - 1)
    else:
        mean_sent_len = sent_lengths[0] if sent_lengths else 0
        sent_len_variance = 0

    all_exhibit_pattern = r'(?:Exhibit|Ex\.?)\s*([A-Z]-?[0-9A-Z]*(?:-[0-9A-Z]+)?)'
    all_mentions = set(m.upper() for m in re.findall(all_exhibit_pattern, output))
    from gates import KNOWN_EXHIBITS
    for ex_id in KNOWN_EXHIBITS:
        if len(ex_id) == 1:
            if re.search(r'(?:Exhibit|Ex\.?)\s*' + ex_id + r'\b', output):
                all_mentions.add(ex_id)
            elif re.search(r'[([,;]\s*' + ex_id + r'\s*[)\],;.]', output):
                all_mentions.add(ex_id)
        else:
            if re.search(r'\b' + re.escape(ex_id) + r'\b', output):
                all_mentions.add(ex_id)
    total_exhibits_mentioned = len(all_mentions)

    gratuitous_mentions = 0
    if ground_truth_task:
        relevant = set(ground_truth_task.get("relevant_exhibits", []))
        gratuitous_mentions = len(all_mentions - relevant)

    return {
        "hedge_count": hedge_n,
        "meta_commentary_count": meta_n,
        "balanced_analysis_count": balanced_n,
        "disclaimer_count": disclaimer_n,
        "overhead_matches": overhead_matches,
        "overhead_tokens": overhead_tokens,
        "alignment_overhead_rate": round(alignment_overhead_rate, 4),
        "tokens_to_first_claim": first_claim_tokens,
        "tokens_to_first_paragraph_number": tokens_to_first_para,
        "total_words": total_words,
        "substantive_tokens": substantive_tokens,
        "substantive_density": round(substantive_density, 4),
        "type_token_ratio": round(type_token_ratio, 4),
        "unique_word_count": len(unique_words),
        "mean_sentence_length": round(mean_sent_len, 1),
        "sentence_length_variance": round(sent_len_variance, 1),
        "total_exhibits_mentioned": total_exhibits_mentioned,
        "exhibits_mentioned_list": sorted(all_mentions),
        "gratuitous_mentions": gratuitous_mentions,
    }


def _empty_output_metrics():
    return {
        "hedge_count": 0, "meta_commentary_count": 0,
        "balanced_analysis_count": 0, "disclaimer_count": 0,
        "overhead_matches": 0, "overhead_tokens": 0,
        "alignment_overhead_rate": 0, "tokens_to_first_claim": 0,
        "tokens_to_first_paragraph_number": 0,
        "total_words": 0, "substantive_tokens": 0, "substantive_density": 0,
        "type_token_ratio": 0, "unique_word_count": 0,
        "mean_sentence_length": 0, "sentence_length_variance": 0,
        "total_exhibits_mentioned": 0, "exhibits_mentioned_list": [],
        "gratuitous_mentions": 0,
    }
# ─── Inter-Run Variance (Measurement D) ──────────────────────

def compute_interrun_variance(scored_results):
    """Measurement D: Per-run variance within each (task, level, condition) cell."""
    from itertools import combinations

    groups = defaultdict(list)
    for s in scored_results:
        groups[(s["task_id"], s["level"], s["condition"])].append(s)

    variance_results = {}
    for key, items in groups.items():
        n = len(items)
        if n < 2:
            variance_results[key] = {
                "n_runs": n, "mean_jaccard_exhibits": None,
                "length_std": None, "overhead_rate_std": None,
                "ceiling_advocacy": None, "floor_advocacy": None,
            }
            continue

        exhibit_sets = []
        for item in items:
            exh_list = item.get("exhibits_mentioned_list", [])
            if isinstance(exh_list, str):
                try: exh_list = json.loads(exh_list)
                except: exh_list = []
            exhibit_sets.append(set(exh_list))

        jaccard_scores = []
        for (a, b) in combinations(range(n), 2):
            sa, sb = exhibit_sets[a], exhibit_sets[b]
            union = sa | sb
            inter = sa & sb
            if union:
                jaccard_scores.append(len(inter) / len(union))
        mean_jaccard = sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0

        lengths = [item.get("total_words", 0) for item in items]
        mean_len = sum(lengths) / n
        length_std = (sum((l - mean_len) ** 2 for l in lengths) / (n - 1)) ** 0.5

        overheads = [item.get("alignment_overhead_rate", 0) for item in items]
        mean_oh = sum(overheads) / n
        oh_std = (sum((o - mean_oh) ** 2 for o in overheads) / (n - 1)) ** 0.5

        adv_scores = [item.get("advocacy_composite") or 0 for item in items]

        variance_results[key] = {
            "n_runs": n,
            "mean_jaccard_exhibits": round(mean_jaccard, 3),
            "length_std": round(length_std, 1),
            "overhead_rate_std": round(oh_std, 4),
            "ceiling_advocacy": round(max(adv_scores), 2),
            "floor_advocacy": round(min(adv_scores), 2),
        }
    return variance_results


def compute_nudge_effect_sizes(scored_results):
    """Nudge effect size: Cohen's d between nudge and no-nudge conditions."""
    metrics = [
        "citations_verified", "citations_fabricated", "citation_density",
        "advocacy_composite", "exhibit_precision", "exhibit_recall",
        "alignment_overhead_rate", "per_case_accuracy", "quality_composite",
        "hallucination_count", "standard_identification",
    ]

    def cohens_d(group_a, group_b, metric):
        vals_a = [s.get(metric) or 0 for s in group_a]
        vals_b = [s.get(metric) or 0 for s in group_b]
        n_a, n_b = len(vals_a), len(vals_b)
        if n_a < 2 or n_b < 2:
            return None
        mean_a, mean_b = sum(vals_a) / n_a, sum(vals_b) / n_b
        var_a = sum((x - mean_a) ** 2 for x in vals_a) / (n_a - 1)
        var_b = sum((x - mean_b) ** 2 for x in vals_b) / (n_b - 1)
        pooled = (((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)) ** 0.5
        return round((mean_b - mean_a) / pooled, 3) if pooled else 0.0

    groups = defaultdict(list)
    for s in scored_results:
        groups[s["condition"]].append(s)
    results = {}
    for model, (no_nudge, with_nudge) in [
        ("base", ("base_alone", "base_nudge")),
        ("instruct", ("instruct_alone", "instruct_nudge")),
    ]:
        a, b = groups.get(no_nudge, []), groups.get(with_nudge, [])
        results[model] = {m: cohens_d(a, b, m) for m in metrics}
    return results


def load_results(results_file):
    with open(results_file) as f:
        return json.load(f)
# ─── SCORE ALL ───────────────────────────────────────────────

def score_all(results, corpus, run_judge=True):
    """Run gates on every generation. Returns scored results.
    Updated for bundled measurements (corrected gates.py).

    run_judge=False skips the LLM judge calls — useful for fast deterministic
    rescoring after methodology changes (e.g. adding family-specific regex
    patterns).
    """
    tasks_map = {}
    with open(TASKS_PATH) as f:
        for t in json.load(f)["tasks"]:
            tasks_map[t["id"]] = t

    ground_truth = {}
    if os.path.exists(GROUND_TRUTH_PATH):
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

    exhibits = {}
    if os.path.exists(EXHIBIT_POOL_PATH):
        with open(EXHIBIT_POOL_PATH) as f:
            exhibits = json.load(f)

    scored = []
    for r in results:
        task = tasks_map[r["task_id"]]
        truncated = r.get("truncated", False)
        gate_report = run_gates(
            r["output"], task, corpus, ground_truth,
            exhibits=exhibits, run_judge=run_judge, truncated=truncated,
        )
        gt_task = ground_truth.get(r["task_id"], {})
        output_metrics = compute_output_metrics(r["output"], gt_task)

        # Per-case citation accuracy
        relevant_ids = set(task.get("relevant_cases", []))
        cited_ids = set()
        for c in gate_report["citations"]["details"]:
            if c["status"] == "verified" and c.get("matched_case"):
                for cc in corpus["cases"]:
                    if cc["case_name"] == c["matched_case"]:
                        cited_ids.add(cc["id"])
                        break
        per_case_acc = len(cited_ids & relevant_ids) / max(len(relevant_ids), 1)

        scored.append({
            **r,
            "gate_report": gate_report,
            **output_metrics,
            # Flat metrics for CSV
            "citations_total": gate_report["citations"]["total"],
            "citations_verified": gate_report["citations"]["verified"],
            "citations_fabricated": gate_report["citations"]["fabricated"],
            "quotes_total": gate_report["quotes"]["total"],
            "quotes_verified": gate_report["quotes"]["verified"],
            "quotes_fabricated": gate_report["quotes"]["fabricated"],
            "exhibit_precision": gate_report["exhibits"]["precision"],
            "exhibit_recall": gate_report["exhibits"]["recall"],
            "exhibits_cited": gate_report["exhibits"]["total_cited"],
            "exhibit_false_pos": len(gate_report["exhibits"]["false_positives"]),
            "exhibit_false_neg": len(gate_report["exhibits"]["false_negatives"]),
            # Bundle A: Writing Quality — zealous advocacy keys
            "positional_discipline": gate_report["advocacy"].get("positional_discipline"),
            "role_integrity": gate_report["advocacy"].get("role_integrity"),
            "adverse_treatment": gate_report["advocacy"].get("adverse_treatment"),
            "advocacy_composite": gate_report["advocacy"].get("advocacy_composite"),
            "role_break": gate_report["advocacy"].get("role_break"),
            "both_sides_count": gate_report["advocacy"].get("both_sides_count"),
            "writing_quality_agreement": gate_report["advocacy"].get("writing_quality_agreement"),
            # Gates 7-8: Element Mapping & Framing
            "gate7_element_accuracy": gate_report["judge"].get("gate7_element_accuracy"),
            "gate8_framing_accuracy": gate_report["judge"].get("gate8_framing_accuracy"),
            "wrong_count_framing": gate_report["judge"].get("wrong_count_framing"),
            "wrong_count_instances": gate_report["judge"].get("wrong_count_instances"),
            "legal_accuracy_agreement": gate_report["judge"].get("legal_accuracy_agreement"),
            # Bundle A: Evidence Utilization (via evidence_quality key)
            "exhibit_deployment": gate_report.get("evidence_quality", {}).get("exhibit_deployment"),
            "legal_authority_use": gate_report.get("evidence_quality", {}).get("legal_authority_use"),
            "element_targeting": gate_report.get("evidence_quality", {}).get("element_targeting"),
            "evidence_composite": gate_report.get("evidence_quality", {}).get("evidence_composite"),
            "quality_composite": gate_report.get("evidence_quality", {}).get("quality_composite"),
            "defense_adoption_rate": gate_report.get("evidence_quality", {}).get("defense_adoption_rate"),
            # Citation breakdown
            "statute_citations": gate_report["citations"].get("statute_citations", 0),
            "case_citations": gate_report["citations"].get("case_citations", 0),
            "citation_density": round(gate_report["citations"]["total"] / max(output_metrics.get("total_words", 1), 1) * 1000, 2),
            "per_case_accuracy": round(per_case_acc, 3),
            "token_cost_per_cite": round(r.get("tokens_completion", 0) / max(gate_report["citations"]["verified"], 1), 1),
            "tokens_to_first_paragraph_number": output_metrics.get("tokens_to_first_paragraph_number", 0),
            # SUMF compliance
            "sumf_applicable": gate_report.get("sumf", {}).get("sumf_applicable", False),
            "sumf_score": gate_report.get("sumf", {}).get("sumf_score"),
            # Legal standard accuracy (from bundled measurements)
            "standard_identification": gate_report.get("legal_standard", {}).get("standard_identification"),
            "standard_application": gate_report.get("legal_standard", {}).get("standard_application"),
            "element_completeness": gate_report.get("legal_standard", {}).get("element_completeness"),
            # Hallucinated facts (from bundled measurements)
            "hallucination_count": gate_report.get("hallucination", {}).get("hallucination_count"),
            "hallucination_severity": gate_report.get("hallucination", {}).get("severity"),
            # FIX: single bundled_agreement replaces 3 separate agreement keys
            "bundled_agreement": gate_report.get("bundled_agreement"),
            # Core fields
            "gate_pass": gate_report["gate_pass"],
            "gate3a_pass": gate_report["completeness"]["gate3a_pass"],
            "truncated": truncated,
            "completeness_pass": gate_report["completeness"]["gate_pass"],
            "is_refusal": gate_report["completeness"]["is_refusal"],
        })
    return scored
# ─── AGGREGATION ─────────────────────────────────────────────

def aggregate_by_condition(scored):
    """Group metrics by condition for comparison table."""
    groups = defaultdict(list)
    for s in scored:
        groups[s["condition"]].append(s)

    summary = {}
    for condition, items in groups.items():
        n = len(items)
        non_truncated = [i for i in items if not i["truncated"]]
        n_nt = len(non_truncated) or 1
        summary[condition] = {
            "n": n,
            "gate_pass_rate": sum(1 for i in items if i["gate_pass"]) / n,
            "avg_fabricated_citations": sum(i["citations_fabricated"] for i in items) / n,
            "avg_verified_citations": sum(i["citations_verified"] for i in items) / n,
            "avg_fabricated_quotes": sum(i["quotes_fabricated"] for i in items) / n,
            "avg_exhibit_precision": sum(i["exhibit_precision"] or 0 for i in items) / n,
            "avg_exhibit_recall": sum(i["exhibit_recall"] or 0 for i in items) / n,
            "avg_exhibit_false_pos": sum(i["exhibit_false_pos"] for i in items) / n,
            "avg_positional_discipline": sum(i.get("positional_discipline") or 0 for i in items) / n,
            "avg_role_integrity": sum(i.get("role_integrity") or 0 for i in items) / n,
            "avg_adverse_treatment": sum(i.get("adverse_treatment") or 0 for i in items) / n,
            "avg_advocacy_composite": sum(i.get("advocacy_composite") or 0 for i in items) / n,
            "avg_both_sides": sum(i.get("both_sides_count") or 0 for i in items) / n,
            "role_break_rate": sum(1 for i in items if i.get("role_break")) / n,
            "avg_gate7_element": sum(i.get("gate7_element_accuracy") or 0 for i in items) / n,
            "avg_gate8_framing": sum(i.get("gate8_framing_accuracy") or 0 for i in items) / n,
            "gate3a_pass_rate": sum(1 for i in items if i["gate3a_pass"]) / n,
            "truncation_rate": sum(1 for i in items if i["truncated"]) / n,
            "refusal_rate": sum(1 for i in items if i["is_refusal"]) / n,
            "avg_overhead_rate": sum(i.get("alignment_overhead_rate", 0) for i in items) / n,
            "avg_tokens_to_first_claim": sum(i.get("tokens_to_first_claim", 0) for i in items) / n,
            "avg_ttr": sum(i.get("type_token_ratio", 0) for i in items) / n,
            "avg_substantive_density": sum(i.get("substantive_density", 0) for i in items) / n,
            "avg_sent_len_var": sum(i.get("sentence_length_variance", 0) for i in items) / n,
            "avg_exhibits_mentioned": sum(i.get("total_exhibits_mentioned", 0) for i in items) / n,
            "avg_gratuitous": sum(i.get("gratuitous_mentions", 0) for i in items) / n,
            "avg_exhibit_deployment": sum(i.get("exhibit_deployment") or 0 for i in items) / n,
            "avg_legal_authority_use": sum(i.get("legal_authority_use") or 0 for i in items) / n,
            "avg_element_targeting": sum(i.get("element_targeting") or 0 for i in items) / n,
            "avg_quality_composite": sum(i.get("quality_composite") or 0 for i in items) / n,
            "avg_defense_adoption": sum(i.get("defense_adoption_rate") or 0 for i in items) / n,
            "avg_citation_density": sum(i.get("citation_density") or 0 for i in items) / n,
            "avg_per_case_accuracy": sum(i.get("per_case_accuracy") or 0 for i in items) / n,
            "avg_token_cost_per_cite": sum(i.get("token_cost_per_cite") or 0 for i in items) / n,
            "avg_preamble_tokens": sum(i.get("tokens_to_first_paragraph_number") or 0 for i in items) / n,
            "avg_statute_cites": sum(i.get("statute_citations") or 0 for i in items) / n,
            "avg_case_cites": sum(i.get("case_citations") or 0 for i in items) / n,
            "avg_standard_id": sum(i.get("standard_identification") or 0 for i in items) / n,
            "avg_standard_app": sum(i.get("standard_application") or 0 for i in items) / n,
            "avg_element_completeness": sum(i.get("element_completeness") or 0 for i in items) / n,
            "avg_hallucination_count": sum(i.get("hallucination_count") or 0 for i in items) / n,
            "avg_hallucination_severity": sum(i.get("hallucination_severity") or 0 for i in items) / n,
            # FIX: bundled agreement
            "avg_bundled_agreement": sum(i.get("bundled_agreement") or 0 for i in items) / n,
        }
    return summary


def aggregate_by_level_condition(scored):
    """Group metrics by (level, condition) for the ladder analysis."""
    groups = defaultdict(list)
    for s in scored:
        groups[(s["level"], s["condition"])].append(s)

    levels = sorted(set(k[0] for k in groups))
    conditions = ["base_alone", "base_nudge", "instruct_nudge", "instruct_alone"]

    rows = []
    for level in levels:
        for cond in conditions:
            items = groups.get((level, cond), [])
            if not items:
                continue
            n = len(items)
            non_truncated = [i for i in items if not i["truncated"]]
            n_nt = len(non_truncated) or 1
            rows.append({
                "level": level, "condition": cond, "n": n,
                "gate_pass_rate": sum(1 for i in items if i["gate_pass"]) / n,
                "avg_fabricated": sum(i["citations_fabricated"] for i in items) / n,
                "avg_exhibit_precision": sum(i["exhibit_precision"] or 0 for i in items) / n,
                "avg_exhibit_recall": sum(i["exhibit_recall"] or 0 for i in items) / n,
                "avg_exhibit_fp": sum(i["exhibit_false_pos"] for i in items) / n,
                "avg_advocacy_composite": sum(i.get("advocacy_composite") or 0 for i in items) / n,
                "avg_both_sides": sum(i.get("both_sides_count") or 0 for i in items) / n,
                "gate3a_pass_rate": sum(1 for i in items if i["gate3a_pass"]) / n,
                    "truncation_rate": sum(1 for i in items if i["truncated"]) / n,
                "refusal_rate": sum(1 for i in items if i["is_refusal"]) / n,
            })
    return rows


def aggregate_by_task_level_condition(scored):
    """Group metrics by (task_id, level, condition) for full 5x4x4 table."""
    groups = defaultdict(list)
    for s in scored:
        groups[(s["task_id"], s["level"], s["condition"])].append(s)

    tasks = sorted(set(k[0] for k in groups))
    levels = sorted(set(k[1] for k in groups))
    conditions = ["base_alone", "base_nudge", "instruct_nudge", "instruct_alone"]

    rows = []
    for task in tasks:
        for level in levels:
            for cond in conditions:
                items = groups.get((task, level, cond), [])
                if not items:
                    continue
                n = len(items)
                non_truncated = [i for i in items if not i["truncated"]]
                n_nt = len(non_truncated) or 1
                wcf_items = [i for i in items if i.get("wrong_count_framing") is not None]
                n_wcf = len(wcf_items) or 1
                rows.append({
                    "task_id": task, "level": level, "condition": cond, "n": n,
                    "gate_pass_rate": sum(1 for i in items if i["gate_pass"]) / n,
                    "avg_fabricated": sum(i["citations_fabricated"] for i in items) / n,
                    "avg_exhibit_precision": sum(i["exhibit_precision"] or 0 for i in items) / n,
                    "avg_exhibit_recall": sum(i["exhibit_recall"] or 0 for i in items) / n,
                    "avg_exhibit_fp": sum(i["exhibit_false_pos"] for i in items) / n,
                    "avg_advocacy_composite": sum(i.get("advocacy_composite") or 0 for i in items) / n,
                    "avg_both_sides": sum(i.get("both_sides_count") or 0 for i in items) / n,
                    "avg_gate7_element": sum(i.get("gate7_element_accuracy") or 0 for i in items) / n,
                    "avg_gate8_framing": sum(i.get("gate8_framing_accuracy") or 0 for i in items) / n,
                    "wrong_count_framing_rate": sum(1 for i in wcf_items if i.get("wrong_count_framing")) / n_wcf,
                    "avg_wrong_count_instances": sum(i.get("wrong_count_instances") or 0 for i in items) / n,
                    "gate3a_pass_rate": sum(1 for i in items if i["gate3a_pass"]) / n,
                            "truncation_rate": sum(1 for i in items if i["truncated"]) / n,
                    "refusal_rate": sum(1 for i in items if i["is_refusal"]) / n,
                })
    return rows
# ─── CSV EXPORT ──────────────────────────────────────────────

def export_csv(scored, outpath):
    """Export flat CSV for analysis."""
    fields = [
        "task_id", "level", "condition", "run", "model",
        "citations_total", "citations_verified", "citations_fabricated",
        "quotes_total", "quotes_verified", "quotes_fabricated",
        "exhibits_cited", "exhibit_precision", "exhibit_recall",
        "exhibit_false_pos", "exhibit_false_neg",
        "positional_discipline", "role_integrity", "adverse_treatment",
        "advocacy_composite", "role_break", "both_sides_count", "writing_quality_agreement",
        "gate7_element_accuracy", "gate8_framing_accuracy",
        "wrong_count_framing", "wrong_count_instances",
        "legal_accuracy_agreement",
        # Path 1: Output metrics
        "hedge_count", "meta_commentary_count", "balanced_analysis_count",
        "disclaimer_count", "overhead_matches", "overhead_tokens",
        "alignment_overhead_rate", "tokens_to_first_claim",
        "total_words", "substantive_tokens", "substantive_density",
        "type_token_ratio", "unique_word_count",
        "mean_sentence_length", "sentence_length_variance",
        "total_exhibits_mentioned", "gratuitous_mentions",
        # Bundle A: Evidence Utilization
        "exhibit_deployment", "legal_authority_use", "element_targeting",
        "evidence_composite", "quality_composite", "defense_adoption_rate",
        # New measurements
        "statute_citations", "case_citations", "citation_density",
        "per_case_accuracy", "token_cost_per_cite",
        "tokens_to_first_paragraph_number",
        "sumf_applicable", "sumf_score",
        "standard_identification", "standard_application", "element_completeness",
        "hallucination_count", "hallucination_severity",
        # FIX: single bundled_agreement
        "bundled_agreement",
        # Core fields
        "gate_pass", "gate3a_pass", "truncated",
        "completeness_pass", "is_refusal",
        "tokens_prompt", "tokens_completion", "max_tokens",
    ]
    with open(outpath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(scored)
    print(f"Exported {len(scored)} rows to {outpath}")
# ─── MAIN ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, glob, argparse
    _p = argparse.ArgumentParser()
    _p.add_argument("--family", required=True,
                    help="One of: llama70b, gemma31b, deepseek_v4_flash")
    _p.add_argument("--no-judge", action="store_true",
                    help="Skip LLM judge calls — deterministic-only rescoring")
    _p.add_argument("--probe", action="store_true",
                    help="Read from results/raw/<family>/probe/ instead of main")
    _args, _ = _p.parse_known_args()
    FAMILY_NAME = _args.family
    RUN_JUDGE = not _args.no_judge

    corpus = json.load(open(CORPUS_PATH))
    sub = "probe" if _args.probe else ""
    family_raw_dir = os.path.join(RAW_RESULTS_DIR, FAMILY_NAME, sub) if sub \
        else os.path.join(RAW_RESULTS_DIR, FAMILY_NAME)
    family_scored_dir = os.path.join(SCORED_RESULTS_DIR, FAMILY_NAME, sub) if sub \
        else os.path.join(SCORED_RESULTS_DIR, FAMILY_NAME)
    raw_files = sorted(
        f for f in glob.glob(f"{family_raw_dir}/*.json")
        if not os.path.basename(f).startswith("checkpoint_")
    )
    if not raw_files:
        print(f"No raw results found in {family_raw_dir}. Run runner.py --family {FAMILY_NAME} first.")
        sys.exit(1)
    print(f"[scorer] family={FAMILY_NAME} run_judge={RUN_JUDGE} probe={_args.probe}")
    results = load_results(raw_files[-1])
    scored = score_all(results, corpus, run_judge=RUN_JUDGE)

    # Save scored JSON
    os.makedirs(family_scored_dir, exist_ok=True)
    scored_file = f"{family_scored_dir}/scored_{os.path.basename(raw_files[-1])}"
    with open(scored_file, "w") as f:
        json.dump(scored, f, indent=2)
    export_csv(scored, scored_file.replace(".json", ".csv"))

    # Condition-level summary
    summary = aggregate_by_condition(scored)
    for cond, m in summary.items():
        print(f"\n=== {cond} (n={m['n']}) ===")
        print(f"  Gate pass rate:     {m['gate_pass_rate']:.1%}")
        print(f"  G3a (no refusal):   {m['gate3a_pass_rate']:.1%}")
        print(f"  Truncation rate:    {m['truncation_rate']:.1%}")
        print(f"  Avg fabricated:     {m['avg_fabricated_citations']:.2f} citations")
        print(f"  Exhibit precision:  {m['avg_exhibit_precision']:.1%}")
        print(f"  Exhibit recall:     {m['avg_exhibit_recall']:.1%}")
        print(f"  Avg exhibit FP:     {m['avg_exhibit_false_pos']:.1f}")
        print(f"  Advocacy composite: {m['avg_advocacy_composite']:.2f}/5")
        print(f"    Positional disc:  {m['avg_positional_discipline']:.2f}/5")
        print(f"    Role integrity:   {m['avg_role_integrity']:.2f}/5")
        print(f"    Adverse treat:    {m['avg_adverse_treatment']:.2f}/5")
        print(f"  Both-sides count:   {m['avg_both_sides']:.1f}")
        print(f"  Role break rate:    {m['role_break_rate']:.1%}")
        print(f"  Gate 7 (element):   {m['avg_gate7_element']:.1%}")
        print(f"  Gate 8 (framing):   {m['avg_gate8_framing']:.1%}")
        print(f"  Refusal rate:       {m['refusal_rate']:.1%}")
        print(f"  --- Path 1: Output Metrics ---")
        print(f"  Overhead rate:      {m['avg_overhead_rate']:.2%}")
        print(f"  Tokens to 1st claim:{m['avg_tokens_to_first_claim']:.0f}")
        print(f"  Type-token ratio:   {m['avg_ttr']:.3f}")
        print(f"  Substantive dens:   {m['avg_substantive_density']:.2%}")
        print(f"  Sent len variance:  {m['avg_sent_len_var']:.1f}")
        print(f"  Exhibits mentioned: {m['avg_exhibits_mentioned']:.1f}")
        print(f"  Gratuitous exh:     {m['avg_gratuitous']:.1f}")
        print(f"  --- Bundle A: Evidence Utilization ---")
        print(f"  Exhibit deployment: {m['avg_exhibit_deployment']:.2f}/5")
        print(f"  Legal authority:    {m['avg_legal_authority_use']:.2f}/5")
        print(f"  Element targeting:  {m['avg_element_targeting']:.2f}/5")
        print(f"  Quality composite:  {m['avg_quality_composite']:.2f}/5")
        print(f"  Defense adoption:   {m['avg_defense_adoption']:.2f}")
        print(f"  --- Bundled Measurements ---")
        print(f"  Citation density:   {m['avg_citation_density']:.1f}/1k words")
        print(f"  Per-case accuracy:  {m['avg_per_case_accuracy']:.1%}")
        print(f"  Token cost/cite:    {m['avg_token_cost_per_cite']:.0f}")
        print(f"  Preamble tokens:    {m['avg_preamble_tokens']:.0f}")
        print(f"  Statute cites:      {m['avg_statute_cites']:.1f}")
        print(f"  Case cites:         {m['avg_case_cites']:.1f}")
        print(f"  Std identification: {m['avg_standard_id']:.2f}/5")
        print(f"  Std application:    {m['avg_standard_app']:.2f}/5")
        print(f"  Element complete:   {m['avg_element_completeness']:.1%}")
        print(f"  Hallucinations:     {m['avg_hallucination_count']:.1f}")
        print(f"  Halluc. severity:   {m['avg_hallucination_severity']:.2f}/5")
        print(f"  Bundled agreement:  {m['avg_bundled_agreement']:.1%}")

    # Nudge Effect Sizes (Cohen's d)
    nudge_d = compute_nudge_effect_sizes(scored)
    print("\n" + "=" * 90)
    print("NUDGE EFFECT SIZES (Cohen's d: positive = nudge helped)")
    print("=" * 90)
    for model, effects in nudge_d.items():
        print(f"\n  {model.upper()}:")
        for metric, d in effects.items():
            label = "negligible" if d is None else (
                "negligible" if abs(d) < 0.2 else
                "small" if abs(d) < 0.5 else
                "medium" if abs(d) < 0.8 else "LARGE")
            print(f"    {metric:<30} d={d or 0:>7.3f}  ({label})")

    # Level x Condition breakdown
    print("\n" + "=" * 110)
    print("LEVEL x CONDITION BREAKDOWN")
    print("=" * 110)
    lc_rows = aggregate_by_level_condition(scored)
    prev_level = None
    for row in lc_rows:
        if prev_level and row["level"] != prev_level:
            print()
        prev_level = row["level"]
        print(f"{row['level']:<20} {row['condition']:<20} {row['n']:>4} "
              f"{row['gate_pass_rate']:>5.0%} "
              f"{row['gate3a_pass_rate']:>4.0%} "
              f""
              f"{row['truncation_rate']:>5.0%} "
              f"{row['avg_fabricated']:>5.2f} "
              f"{row['avg_exhibit_precision']:>5.1%} "
              f"{row['avg_exhibit_recall']:>5.1%} "
              f"{row['avg_exhibit_fp']:>5.1f} "
              f"{row['avg_advocacy_composite']:>5.2f} "
              f"{row['avg_both_sides']:>5.1f} "
              f"{row['refusal_rate']:>6.0%}")

    # Task x Level x Condition breakdown
    print("\n" + "=" * 130)
    print("TASK x LEVEL x CONDITION BREAKDOWN")
    print("=" * 130)
    tlc_rows = aggregate_by_task_level_condition(scored)
    prev_task = None
    for row in tlc_rows:
        if prev_task and row["task_id"] != prev_task:
            print()
        prev_task = row["task_id"]
        print(f"{row['task_id']:<22} {row['level']:<18} {row['condition']:<18} {row['n']:>3} "
              f"{row['gate_pass_rate']:>5.0%} "
              f"{row['avg_fabricated']:>5.2f} "
              f"{row['avg_exhibit_precision']:>5.1%} "
              f"{row['avg_exhibit_recall']:>5.1%} "
              f"{row['avg_exhibit_fp']:>4.1f} "
              f"{row['avg_advocacy_composite']:>5.2f} "
              f"{row['avg_gate7_element']:>5.1%} "
              f"{row['avg_gate8_framing']:>5.1%} "
              f"{row['wrong_count_framing_rate']:>4.0%} "
              f"{row['avg_wrong_count_instances']:>4.1f}")

    # Inter-Run Variance
    variance = compute_interrun_variance(scored)
    print("\n" + "=" * 120)
    print("INTER-RUN VARIANCE")
    print("=" * 120)
    for (task_id, level, cond), v in sorted(variance.items()):
        print(f"{task_id:<22} {level:<18} {cond:<18} {v['n_runs']:>3} "
              f"{v['mean_jaccard_exhibits'] or 0:>8.3f} "
              f"{v['length_std'] or 0:>8.1f} "
              f"{v['overhead_rate_std'] or 0:>8.4f} "
              f"{v['ceiling_advocacy'] or 0:>6.2f} "
              f"{v['floor_advocacy'] or 0:>6.2f}")