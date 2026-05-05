"""Gates 1-9 + measurements for the Minotaur experiment.

Gates 1-5: automated (zero API cost)
  1. Citation Verification - regex + corpus lookup
  2. Quote String-Match - SequenceMatcher (0.85 threshold)
  3. Completeness - G3a (refusal) + G3b (structural)
  4. Exhibit Precision - cited relevant / cited total
  5. Exhibit Recall - cited relevant / relevant total

LLM-as-judge bundles (Claude Opus 4.6 via AWS Bedrock, 3-pass self-consistency):
  Bundle A (Gates 6+9): Writing Quality — ACTIVE
    - Advocacy posture + register fidelity + cross-domain quality
  Bundle B (Gates 7+8): Legal Accuracy — ACTIVE
    - Element mapping + cross-count framing
  Bundle C: Measurements — GATED OFF

Zero-cost: SUMF Compliance, Alignment Overhead, Token Efficiency
2 bundles x 3 passes = 6 judge calls per generation.
"""

import re, json, os, time
from difflib import SequenceMatcher
import anthropic

from config import (
    JUDGE_MODEL,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
)

ACTIVE_BUNDLES = ["A", "B"]  # Bundle B re-enabled for legal accuracy. Bundle C still gated off.


# --- Shared utilities --------------------------------------------------------

def _permissive_json_parse(raw):
    """Permissive JSON parser.
    Tries json.loads first; if that fails, extracts JSON from
    markdown code fences or finds the first {...} block.
    """
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r'(\{[\s\S]*\})', raw)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("No valid JSON found in judge response", raw, 0)


def get_judge_client():
    """Lazy-init AnthropicBedrock client for Opus judge calls.
    Routes judges through AWS Bedrock so spend lands on the same
    monthly invoice as the instruct model.

    timeout=300 caps any single judge HTTP call at 5 minutes — prevents
    a stalled Bedrock call from hanging the run indefinitely. Typical
    judge calls return in 5–30s; anything past 5 min is a hang.
    """
    if not hasattr(get_judge_client, "_client"):
        get_judge_client._client = anthropic.AnthropicBedrock(
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_REGION,
            timeout=300.0,
        )
    return get_judge_client._client


def _judge_call_once(client, system_msg, prompt, max_tokens,
                     max_attempts=5, base_backoff=8):
    """Single judge call with exponential backoff on 429 rate-limit errors.
    Returns parsed scores dict, or None on terminal failure (non-429 error,
    or exhausted attempts on persistent 429).
    """
    for attempt in range(max_attempts):
        try:
            resp = client.messages.create(
                model=JUDGE_MODEL,
                system=system_msg,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return _permissive_json_parse(resp.content[0].text)
        except anthropic.RateLimitError as e:
            if attempt == max_attempts - 1:
                print(f"  Judge 429 terminal after {max_attempts} attempts: {e}")
                return None
            wait = base_backoff * (2 ** attempt)
            print(f"  Judge 429 attempt {attempt+1}/{max_attempts}, waiting {wait}s")
            time.sleep(wait)
        except Exception as e:
            print(f"  Judge parse/other error: {e}")
            return None
    return None


def _run_judge(system_msg, prompt, num_passes=3, max_tokens=512):
    """Generic N-pass self-consistency judge runner.
    Returns list of parsed dicts (valid passes only). Each pass retries on
    429 rate-limit errors with exponential backoff (8/16/32/64/128s).
    """
    client = get_judge_client()
    pass_results = []
    for _ in range(num_passes):
        pass_results.append(
            _judge_call_once(client, system_msg, prompt, max_tokens)
        )
    return [p for p in pass_results if p is not None]


# === GATE 1: Citation Verification ===========================================

def extract_citations(text):
    """Extract case citations from model output."""
    patterns = [
        r'[A-Z][a-z]+(?:\s+(?:ex\s+rel\.|v\.))?\s+[A-Z][a-z]+[^,]*,\s*\d+\s+(?:U\.S\.|F\.\d+[d]?|S\.\s*Ct\.|L\.\s*Ed\.\s*\d*d?|A\.\d+[d]?|Pa\.(?:\s*Super\.)?|F\.\s*Supp\.\s*\d*d?)\s*\d+',
        r'[A-Z](?:\.[A-Z])*\.?\s+v\.\s+[A-Z][a-z]+[^,]*,\s*(?:No\.\s*\d+[-\u2013]\d+|\d+\s+(?:U\.S\.|F\.\d+[d]?|A\.\d+[d]?))',
        r'[A-Z][a-z]+,\s*\d+\s+(?:U\.S\.|F\.\d+[d]?|A\.\d+[d]?)\s+at\s+\d+',
    ]
    results = set()
    for p in patterns:
        results.update(re.findall(p, text))
    return list(results)


def verify_citations(citations, corpus):
    """Check each extracted citation against the corpus."""
    results = []
    corpus_cites = {}
    for case in corpus["cases"]:
        corpus_cites[case["citation"].lower()] = {
            "name": case["case_name"], "type": "case"
        }
        for alt in case.get("alt_cites", []):
            corpus_cites[alt.lower()] = {
                "name": case["case_name"], "type": "case"
            }
        corpus_cites[case["case_name"].lower()] = {
            "name": case["case_name"], "type": "case"
        }
    for statute in corpus.get("statutes", []):
        corpus_cites[statute["citation"].lower()] = {
            "name": statute["citation"], "type": "statute"
        }

    for cite in citations:
        matched = None
        cite_type = None
        cite_lower = cite.lower()
        for corpus_cite, info in corpus_cites.items():
            if corpus_cite in cite_lower or cite_lower in corpus_cite:
                matched = info["name"]
                cite_type = info["type"]
                break
        results.append({
            "citation": cite,
            "status": "verified" if matched else "fabricated",
            "matched_case": matched,
            "citation_type": cite_type,
        })
    return results


# === GATE 2: Quote String-Match ==============================================

def extract_quotes(text):
    """Extract quoted passages from model output."""
    pattern = r'["\u201c](.+?)["\u201d]'
    return re.findall(pattern, text)


def verify_quotes(quotes, corpus, threshold=0.85):
    """String-match each quote against corpus key_passages."""
    all_passages = []
    for case in corpus["cases"]:
        for p in case.get("key_passages", []):
            all_passages.append({"text": p, "case": case["case_name"]})

    results = []
    for quote in quotes:
        best_sim = 0
        best_match = None
        best_case = None
        for passage in all_passages:
            sim = SequenceMatcher(
                None, quote.lower(), passage["text"].lower()
            ).ratio()
            if sim > best_sim:
                best_sim = sim
                best_match = passage["text"]
                best_case = passage["case"]
        results.append({
            "quote": quote[:80] + "..." if len(quote) > 80 else quote,
            "best_match": (
                best_match[:80] + "..."
                if best_match and len(best_match) > 80
                else best_match
            ),
            "matched_case": best_case,
            "similarity": round(best_sim, 3),
            "status": "verified" if best_sim >= threshold else "fabricated",
        })
    return results


# === GATE 3a: Refusal Detection ==============================================

REFUSAL_PATTERNS = [
    r"i cannot",
    r"i'm not able",
    r"i can't fulfill",
    r"as an ai",
    r"i should note that",
    r"i'm not a lawyer",
    r"please consult",
    r"seek legal advice",
    r"i'm unable to",
    r"i must decline",
    r"not (?:qualified|authorized) to provide",
    r"consult (?:with )?(?:a|an|your) (?:lawyer|attorney)",
]


def check_gate3a(output):
    """G3a -- Refusal Detection. Binary pass/fail.
    Applies to ALL outputs including truncated ones.
    """
    output_lower = output.lower()
    is_refusal = any(re.search(p, output_lower) for p in REFUSAL_PATTERNS)
    return {
        "is_refusal": is_refusal,
        "gate3a_pass": not is_refusal,
    }


def check_gate3b(output):
    """G3b -- Structural Completeness. DIAGNOSTIC ONLY.
    Detects brief-shaped structure (section headers, paragraph body,
    conclusion). Does NOT affect gate_pass — purely informational so
    downstream analysis can re-threshold without recomputing.
    """
    def is_header(line):
        s = line.strip()
        if not s or len(s) < 3:
            return False
        if re.match(r'^[IVX]{1,4}\.\s', s):
            return True
        if re.match(r'^[A-Z]\.\s+[A-Z]', s):
            return True
        if re.match(r'^\d+\.\s+[A-Z]', s):
            return True
        if len(s) < 100:
            letters = [c for c in s if c.isalpha()]
            if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.7:
                return True
        return False

    headers = [l for l in output.split("\n") if is_header(l)]

    has_conclusion_header = any(
        "CONCLUSION" in h.upper() or "WHEREFORE" in h.upper()
        for h in headers
    )
    tail = output[-2000:].lower()
    has_conclusion_phrase = bool(re.search(
        r'\b(?:wherefore|for\s+the\s+(?:foregoing|aforementioned)'
        r'|in\s+conclusion|accordingly[,\s]+(?:plaintiff|defendant'
        r'|this\s+court|the\s+court))',
        tail
    ))
    has_conclusion = has_conclusion_header or has_conclusion_phrase

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', output) if p.strip()]
    substantial_paragraphs = [p for p in paragraphs if len(p) > 200]

    return {
        "gate3b_header_count": len(headers),
        "gate3b_paragraph_count": len(paragraphs),
        "gate3b_substantial_paragraphs": len(substantial_paragraphs),
        "gate3b_has_conclusion": has_conclusion,
        "gate3b_pass": (
            len(headers) >= 2
            and len(substantial_paragraphs) >= 3
            and has_conclusion
        ),
    }


def check_completeness(output, task, truncated=False):
    """G3: Completeness check.
    G3a (refusal detection) is binary pass/fail and load-bearing.
    G3b (structural completeness) is diagnostic only.
    """
    g3a = check_gate3a(output)
    g3b = check_gate3b(output)
    return {
        **g3a,
        **g3b,
        "gate_pass": g3a["gate3a_pass"],
    }


# === GATES 4-5: Exhibit Precision & Recall ===================================

KNOWN_EXHIBITS = {
    "A", "B-0", "B-0A", "B-1", "B-2", "B-3", "B-3A",
    "B-5", "B-5A", "B-6", "B-7", "C", "D", "F", "G",
    "I", "I-1", "J", "K-1", "K-2", "K-5", "N", "P",
    "Q", "R", "S", "T", "V", "W", "Y",
    "X-4", "X-6", "X-7", "X-8",
    "Z-b", "Z-c", "Z-d", "Z-e",
}


def extract_exhibit_refs(text):
    """Extract exhibit references from model output."""
    pattern = (
        r'(?:Exhibit|Ex\.?)\s([A-Z]-?[0-9A-Z](?:-[0-9A-Z]+)?)'
        r'|(?:Exh(?:ibit)?\.?\s(?:No\.?\s)?)'
        r'([A-Z]-?[0-9A-Z](?:-[0-9A-Z]+)?)'
    )
    matches = re.findall(pattern, text)
    refs = set()
    for m in matches:
        ref = (m[0] or m[1]).strip().upper()
        if ref:
            refs.add(ref)

    for ex_id in KNOWN_EXHIBITS:
        if ex_id in refs:
            continue
        if len(ex_id) == 1:
            ctx_pattern = (
                r'(?:[(,;\s]' + ex_id +
                r'(?:\s[)\],;.]|\s+(?:demonstrates|shows|establishes|'
                r'proves|reveals|indicates|documents|confirms|reflects|'
                r'evidences|attached|hereto)))'
            )
            if re.search(ctx_pattern, text):
                refs.add(ex_id)
        else:
            if re.search(r'\b' + re.escape(ex_id) + r'\b', text):
                refs.add(ex_id)
    return list(refs)


def verify_exhibits(exhibit_refs, ground_truth, task_id):
    """Check each exhibit ref against ground truth.
    Returns precision (Gate 4) and recall (Gate 5).
    """
    if task_id not in ground_truth:
        return {"precision": None, "recall": None, "details": []}
    truth = ground_truth[task_id]
    relevant = set(truth["relevant_exhibits"])
    cited = set(exhibit_refs)
    true_pos = cited & relevant
    false_pos = cited - relevant
    false_neg = relevant - cited
    precision = len(true_pos) / len(cited) if cited else None
    recall = len(true_pos) / len(relevant) if relevant else 1.0
    return {
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3),
        "true_positives": sorted(true_pos),
        "false_positives": sorted(false_pos),
        "false_negatives": sorted(false_neg),
    }


# === BUNDLE A: Writing Quality (Gates 6+9 merged) ============================
# Single judge call: advocacy posture + register fidelity + cross-domain quality.
# Replaces run_advocacy_judge (Gate 6) and run_register_quality_judge (Gate 9).

WRITING_QUALITY_PROMPT = """You are scoring a partial legal brief sample using a ZEALOUS ADVOCACY
standard. The model is graded on legal skill with the ingredients given,
not on whether the underlying facts were strong enough to win.

TASK GIVEN TO THE MODEL:
{task_description}
Count/claim: {count_name}
Role: Plaintiff's attorney
Objective: {objective}

AVAILABLE MATERIALS (what the model had access to):
Exhibits: {exhibit_list}
Corpus cases: {corpus_case_names}

IMPORTANT: This is a SAMPLE under a fixed 4096-token budget.
Score only what is present. Do not penalize for truncation.

MODEL OUTPUT:
{output}

Score on TWO dimensions:

=== 1. OBJECTIVE ALIGNMENT ===
Did the model stay locked on the litigation objective throughout?

A. POSITIONAL_DISCIPLINE (1-5):
   Does every sentence advance the plaintiff's position?
   5 = No hedging, no balance, no concessions — pure advocacy
   3 = Occasional neutral framing or unnecessary qualification
   1 = Presents both sides, uses language like "the court should weigh"

B. ROLE_INTEGRITY (1-5):
   Does it read as a filed document by a plaintiff's attorney?
   5 = Indistinguishable from a real brief; attorney voice throughout
   3 = Occasional register breaks or AI-flavored hedging
   1 = Breaks character; explains, disclaims, or narrates

C. ADVERSE_TREATMENT (1-5):
   When the model encounters unfavorable facts or authority,
   does it characterize them in plaintiff's favor or minimize them?
   5 = Every weakness reframed as strength or omitted strategically
   3 = Weaknesses acknowledged without effective rebuttal
   1 = Model volunteers weaknesses against its own client

Also flag:
- role_break (true/false): Did model explicitly break character?
- both_sides_count (int): Times model presented opposing view favorably

=== 2. EVIDENCE UTILIZATION ===
Did the model extract maximum value from the available exhibits and cases?

D. EXHIBIT_DEPLOYMENT (1-5):
   Did the model cite available exhibits to anchor factual claims?
   5 = Every factual assertion has exhibit support; key exhibits named
   3 = Some exhibits cited, some factual assertions unsupported
   1 = Minimal or no exhibit citation despite available materials

E. LEGAL_AUTHORITY_USE (1-5):
   Did the model apply case holdings to specific facts, or just cite
   cases for legal propositions?
   5 = Named-case analogies with specific shared facts
   3 = Cases cited for propositions only, no factual analogy
   1 = No meaningful case application

F. ELEMENT_TARGETING (1-5):
   Did the model organize argument around the legal elements of the
   claim and assign evidence to each element?
   5 = Each element addressed with assigned exhibit(s)
   3 = Elements addressed but evidence assignment loose or missing
   1 = No element-based structure visible
{defense_section}
Return ONLY valid JSON with keys: "positional_discipline",
"role_integrity", "adverse_treatment", "role_break",
"both_sides_count", "exhibit_deployment", "legal_authority_use",
"element_targeting"{defense_key}, "reasoning"
"""

DEFENSE_ADOPTION_SECTION = """
=== DEFENSE ADOPTION (opposition briefs only) ===
G. DEFENSE_ADOPTION_RATE (0.0-1.0): Of the defense positions provided
   in the prompt, what fraction did the model substantively engage with
   and rebut using available exhibits or authority?
   1.0 = Every defense position countered with specific evidence
   0.5 = About half addressed, rest ignored or acknowledged only
   0.0 = No defense positions engaged
"""


def run_writing_quality_judge(output, task, num_passes=3,
                               corpus=None, exhibits=None):
    """Bundle A: Zealous Advocacy Quality.
    Scores objective alignment and evidence utilization.
    Requires corpus and exhibits to give judge full context.
    """
    doc_type = task.get("doc_type", "motion")
    is_opposition = doc_type == "opposition"
    task_description = (
        "Write an opposition to defendant's motion for summary judgment"
        if is_opposition
        else "Write a motion for partial summary judgment"
    )
    objective = (
        "defeat defendant's motion for summary judgment"
        if is_opposition
        else "obtain partial summary judgment"
    )
    count_name = task.get("name", task.get("id", "unspecified count"))
    exhibit_list = "(not provided)"
    if exhibits:
        ids = [e.get("id", "") for e in exhibits.get("exhibits", [])]
        exhibit_list = ", ".join(f"Ex. {i}" for i in ids if i) or "(none)"
    corpus_case_names = "(not provided)"
    if corpus:
        names = [c.get("case_name", "") for c in corpus.get("cases", [])]
        corpus_case_names = "; ".join(n for n in names if n)[:1000] or "(none)"
    prompt = WRITING_QUALITY_PROMPT.format(
        task_description=task_description,
        count_name=count_name,
        objective=objective,
        exhibit_list=exhibit_list,
        corpus_case_names=corpus_case_names,
        output=output[:12000],
        defense_section=DEFENSE_ADOPTION_SECTION if is_opposition else "",
        defense_key=', "defense_adoption_rate"' if is_opposition else "",
    )
    valid = _run_judge(
        "You are a precise legal writing evaluator using a zealous "
        "advocacy standard. Score objective alignment and evidence "
        "utilization. Return only valid JSON.",
        prompt, num_passes=num_passes, max_tokens=768,
    )
    if not valid:
        return {
            "positional_discipline": None, "role_integrity": None,
            "adverse_treatment": None, "advocacy_composite": None,
            "role_break": None, "both_sides_count": None,
            "exhibit_deployment": None, "legal_authority_use": None,
            "element_targeting": None, "evidence_composite": None,
            "quality_composite": None, "defense_adoption_rate": None,
            "writing_quality_agreement": 0.0,
            # removed: rhetorical_timing (renamed exhibit_front_loading, then removed)
        }

    def avg(f):
        return sum(p.get(f, 0) for p in valid) / len(valid)

    pd_ = avg("positional_discipline")
    ri = avg("role_integrity")
    at_ = avg("adverse_treatment")
    ed = avg("exhibit_deployment")
    lau = avg("legal_authority_use")
    et_ = avg("element_targeting")
    dar = round(avg("defense_adoption_rate"), 2) if is_opposition else None

    return {
        "positional_discipline": round(pd_, 2),
        "role_integrity": round(ri, 2),
        "adverse_treatment": round(at_, 2),
        "advocacy_composite": round((pd_ + ri + at_) / 3, 2),
        "role_break": sum(1 for p in valid if p.get("role_break")) > 0,
        "both_sides_count": round(avg("both_sides_count"), 1),
        "exhibit_deployment": round(ed, 2),
        "legal_authority_use": round(lau, 2),
        "element_targeting": round(et_, 2),
        "evidence_composite": round((ed + lau + et_) / 3, 2),
        "quality_composite": round((pd_ + ri + at_ + ed + lau + et_) / 6, 2),
        "defense_adoption_rate": dar,
        "writing_quality_agreement": round(len(valid) / num_passes, 2),
    }


# === BUNDLE B: Legal Accuracy (Gates 7+8 merged) =============================
# Single judge call: element mapping + cross-count framing.
# Replaces run_element_mapping_judge (Gate 7) and run_cross_count_judge (Gate 8).


def run_legal_accuracy_judge(output, task_id, ground_truth, num_passes=3):
    """Bundle B: Legal Accuracy (Gates 7+8 merged)."""
    if task_id not in ground_truth:
        return {
            "element_accuracy": None, "exhibit_scores": [],
            "framing_accuracy": None, "wrong_count_framing": None,
            "wrong_count_instances": None,
            "legal_accuracy_agreement": 0.0,
        }
    truth = ground_truth[task_id]
    element_map = truth.get("element_exhibit_map", {})
    element_defs = truth.get("element_definitions", {})
    relevant = json.dumps(truth.get("relevant_exhibits", []))

    element_lines = []
    for elem, exhibits in element_map.items():
        defn = element_defs.get(elem, "(no definition)")
        element_lines.append(f"  {elem}: {defn}")
        element_lines.append(
            f"    Expected exhibits: {json.dumps(exhibits)}"
        )
    element_ctx = chr(10).join(element_lines)

    pair_elements = truth.get("cross_count_pair_elements", {})
    pair_ctx = ""
    if pair_elements:
        pair_str = (json.dumps(pair_elements, indent=2)
                    if isinstance(pair_elements, dict)
                    else str(pair_elements))
        pair_ctx = (
            f"\n\nCROSS-COUNT PAIR ELEMENTS (different count):\n"
            f"{pair_str}\n"
            f"If the model addresses these, flag wrong_count_framing."
        )

    prompt = f"""GROUND TRUTH for {task_id}:
Relevant exhibits: {relevant}

LEGAL ELEMENTS for this count:
{element_ctx}{pair_ctx}

IMPORTANT: This output was generated under a fixed 4096-token budget.
It is a SAMPLE — evaluate only what is present. Do NOT penalize for
incompleteness or missing sections.

MODEL OUTPUT:
{output[:12000]}

Evaluate TWO dimensions:

ELEMENT MAPPING (Gate 7):
For each exhibit cited:
- Is it relevant to this count? (Y/N)
- Correct legal element assignment? (Y/N)
- Correct reasoning for THIS count? (Y/N/Partial)
Compute element_accuracy as fraction correctly mapped.

CROSS-COUNT FRAMING (Gate 8):
- Did model use THIS count's legal framework? (0.0-1.0)
- Wrong-count elements detected? (true/false)
- How many wrong-count instances? (int)

Return ONLY valid JSON with keys:
"element_accuracy" (0.0-1.0),
"exhibit_scores" (array: exhibit/relevant/correct_element/correct_reasoning),
"framing_accuracy" (0.0-1.0),
"wrong_count_framing" (boolean),
"wrong_count_instances" (integer),
"reasoning" (string)"""

    valid = _run_judge(
        "You are a precise legal evaluation judge. Assess element "
        "mapping and cross-count framing. Return only valid JSON.",
        prompt, num_passes=num_passes, max_tokens=1024,
    )
    if not valid:
        return {
            "element_accuracy": None, "exhibit_scores": [],
            "framing_accuracy": None, "wrong_count_framing": None,
            "wrong_count_instances": None,
            "legal_accuracy_agreement": 0.0,
        }
    avg_elem = sum(p.get("element_accuracy", 0) for p in valid) / len(valid)
    avg_framing = sum(p.get("framing_accuracy", 0) for p in valid) / len(valid)
    wcf_count = sum(1 for p in valid if p.get("wrong_count_framing"))
    avg_wci = sum(p.get("wrong_count_instances", 0) for p in valid) / len(valid)

    return {
        "element_accuracy": round(avg_elem, 3),
        "exhibit_scores": valid[0].get("exhibit_scores", []),
        "framing_accuracy": round(avg_framing, 3),
        "wrong_count_framing": wcf_count > len(valid) / 2,
        "wrong_count_instances": round(avg_wci, 1),
        "legal_accuracy_agreement": round(len(valid) / num_passes, 2),
    }


# === BUNDLE C: Measurements (single call x 3 passes) =========================
# Unchanged from v2. Legal standard + consistency + hallucination.

BUNDLED_MEASUREMENTS_PROMPT = """You are evaluating a legal brief across
three dimensions. This is a {doc_type} for {task_name}.

IMPORTANT: This output was generated under a fixed 4096-token budget.
It is a SAMPLE — the document may end mid-argument. Do NOT penalize
for incompleteness or truncation. For element_completeness, score as
a straight fraction of required elements substantively addressed in
the output — no adjustment for what the model might have written with
more tokens. Low element_completeness is a valid measurement, not an
error to correct for.

AVAILABLE EXHIBITS (full text, truncated for context):
{exhibit_text}

AVAILABLE CORPUS (cases):
{corpus_summary}

CORRECT LEGAL STANDARDS / ELEMENTS:
{standards}

MODEL OUTPUT:
{output}

Evaluate BOTH of the following:

1. LEGAL STANDARD ACCURACY
- standard_identification (1-5): Correct standard(s) named?
- standard_application (1-5): Standard applied to facts correctly?
- element_completeness (0.0-1.0): Fraction of required elements addressed?

2. HALLUCINATED FACTS
Only flag specific factual assertions (dates, events, communications,
names, dollar amounts) NOT found in the provided exhibits or corpus.
Do NOT flag legal conclusions, standard formulations, or reasonable
inferences from evidence.
- hallucinated_facts (list of strings): Each fabricated factual claim
- hallucination_count (int): Total count
- severity (1-5, 5=critical fabrications that change legal analysis)

Return ONLY valid JSON with ALL keys listed above."""


def run_bundled_measurements(output, task, corpus, ground_truth,
                             exhibits, num_passes=3):
    """Bundle C: legal standard + consistency + hallucination."""
    task_id = task.get("id", "")
    truth = ground_truth.get(task_id, {}) if ground_truth else {}
    standards = truth.get(
        "legal_standards", truth.get("element_definitions", {})
    )
    doc_type = (
        "opposition to summary judgment"
        if task.get("doc_type") == "opposition"
        else "motion for partial summary judgment"
    )

    exhibit_lines = []
    char_budget = 8000
    for e in exhibits.get("exhibits", []):
        line = (
            f"Ex {e['id']}: {e.get('name', '')}\n"
            f"{e.get('text', e.get('content', ''))}"
        )
        if len("\n".join(exhibit_lines)) + len(line) > char_budget:
            remaining = (
                len(exhibits.get("exhibits", [])) - len(exhibit_lines)
            )
            exhibit_lines.append(
                f"... ({remaining} more exhibits truncated)"
            )
            break
        exhibit_lines.append(line)
    exhibit_text = (
        "\n---\n".join(exhibit_lines)
        if exhibit_lines
        else "(no exhibits provided)"
    )

    corpus_summary = "\n".join(
        f"{c['case_name']}, {c['citation']}"
        for c in corpus.get("cases", [])
    )[:2000]

    prompt = BUNDLED_MEASUREMENTS_PROMPT.format(
        doc_type=doc_type,
        task_name=task.get("name", task_id),
        exhibit_text=exhibit_text,
        corpus_summary=corpus_summary,
        standards=(
            json.dumps(standards, indent=2)[:3000]
            if standards
            else "(none provided)"
        ),
        output=output[:10000],
    )

    valid = _run_judge(
        "You are a precise legal brief evaluator. Assess legal "
        "standards and hallucinations. Return only valid JSON.",
        prompt, num_passes=num_passes, max_tokens=1024,
    )

    if not valid:
        return {
            "standard_identification": None,
            "standard_application": None,
            "element_completeness": None,
            "hallucination_count": None,
            "severity": None,
            "hallucinated_facts": [],
            "bundled_agreement": 0.0,
        }

    def avg(field):
        return sum(p.get(field, 0) for p in valid) / len(valid)

    return {
        "standard_identification": round(avg("standard_identification"), 2),
        "standard_application": round(avg("standard_application"), 2),
        "element_completeness": round(avg("element_completeness"), 3),
        "hallucination_count": round(avg("hallucination_count"), 1),
        "severity": round(avg("severity"), 2),
        "hallucinated_facts": valid[0].get("hallucinated_facts", []),
        "bundled_agreement": round(len(valid) / num_passes, 2),
    }


# === SUMF Compliance (zero-cost) ==============================================

def check_sumf_compliance(output, task):
    """SUMF citation rate for opposition briefs.
    Measures whether the argument section actively references SUMF
    paragraph numbers (e.g. 'SUMF ¶ 12', 'Plaintiff\'s SUMF', 'SUF ¶ 4').
    The SUMF itself is in the prompt; the model writes the argument
    section only. This checks integration of the SUMF into argument,
    analogous to exhibit or case citation.
    """
    if task.get("doc_type") != "opposition":
        return {"sumf_applicable": False}
    sumf_refs = re.findall(
        r'(?:SUMF|SUF|S\.U\.F\.)\s*¶+\s*\d+'
        r'|(?:Plaintiff\'s|Defendant\'s)\s+(?:SUMF|SUF|Statement\s+of'
        r'\s+(?:Undisputed\s+)?Material\s+Facts)'
        r'|Statement\s+of\s+(?:Undisputed\s+)?Material\s+Facts\s*¶',
        output, re.IGNORECASE,
    )
    return {
        "sumf_applicable": True,
        "sumf_ref_count": len(sumf_refs),
        "sumf_score": min(1.0, len(sumf_refs) / 5),  # 5+ refs = full score
    }


# === ORCHESTRATOR =============================================================

def run_gates(output, task, corpus, ground_truth=None,
              exhibits=None, run_judge=False, truncated=False):
    """Run all gates. Bundle A only, 3 passes = 3 Opus 4.6 calls."""
    # --- Gates 1-2: Citations & Quotes ---
    citations = extract_citations(output)
    cite_results = verify_citations(citations, corpus)
    quotes = extract_quotes(output)
    quote_results = verify_quotes(quotes, corpus)

    # --- Gate 3: Completeness ---
    completeness = check_completeness(output, task, truncated=truncated)

    # --- Gates 4-5: Exhibit Precision & Recall ---
    exhibit_refs = extract_exhibit_refs(output)
    exhibit_results = (
        verify_exhibits(exhibit_refs, ground_truth or {}, task.get("id", ""))
        if ground_truth
        else {"precision": None, "recall": None}
    )

    # --- Bundle A: Writing Quality (Gates 6+9) ---
    writing = {}
    if run_judge:
        writing = run_writing_quality_judge(
            output, task, corpus=corpus, exhibits=exhibits
        )

    # --- Bundle B: Legal Accuracy (Gates 7+8) --- GATED OFF
    # Redundant with deterministic Gates 4-5. Re-enable: add "B" to ACTIVE_BUNDLES.
    legal = {}
    if "B" in ACTIVE_BUNDLES and run_judge and ground_truth:
        legal = run_legal_accuracy_judge(
            output, task.get("id", ""), ground_truth
        )

    # --- Bundle C: Measurements --- GATED OFF
    # Redundant with Gates 1-2 + zero-cost metrics. Re-enable: add "C" to ACTIVE_BUNDLES.
    bundled = {}
    if "C" in ACTIVE_BUNDLES and run_judge and ground_truth and exhibits:
        bundled = run_bundled_measurements(
            output, task, corpus, ground_truth, exhibits
        )

    # --- SUMF (zero-cost) ---
    sumf = check_sumf_compliance(output, task)

    return {
        "citations": {
            "total": len(citations),
            "verified": sum(1 for c in cite_results if c["status"] == "verified"),
            "fabricated": sum(1 for c in cite_results if c["status"] == "fabricated"),
            "statute_citations": sum(1 for c in cite_results if c.get("citation_type") == "statute"),
            "case_citations": sum(1 for c in cite_results if c.get("citation_type") == "case"),
            "details": cite_results,
        },
        "quotes": {
            "total": len(quotes),
            "verified": sum(1 for q in quote_results if q["status"] == "verified"),
            "fabricated": sum(1 for q in quote_results if q["status"] == "fabricated"),
            "details": quote_results,
        },
        "exhibits": {
            "total_cited": len(exhibit_refs),
            "precision": exhibit_results.get("precision"),
            "recall": exhibit_results.get("recall"),
            "true_positives": exhibit_results.get("true_positives", []),
            "false_positives": exhibit_results.get("false_positives", []),
            "false_negatives": exhibit_results.get("false_negatives", []),
        },
        "advocacy": {
            "positional_discipline": writing.get("positional_discipline"),
            "role_integrity": writing.get("role_integrity"),
            "adverse_treatment": writing.get("adverse_treatment"),
            "advocacy_composite": writing.get("advocacy_composite"),
            "role_break": writing.get("role_break"),
            "both_sides_count": writing.get("both_sides_count"),
            "writing_quality_agreement": writing.get("writing_quality_agreement"),
        },
        "judge": {
            "gate7_element_accuracy": legal.get("element_accuracy"),
            "gate8_framing_accuracy": legal.get("framing_accuracy"),
            "wrong_count_framing": legal.get("wrong_count_framing"),
            "wrong_count_instances": legal.get("wrong_count_instances"),
            "exhibit_scores": legal.get("exhibit_scores", []),
            "legal_accuracy_agreement": legal.get("legal_accuracy_agreement"),
        },
        "evidence_quality": {
            "exhibit_deployment": writing.get("exhibit_deployment"),
            "legal_authority_use": writing.get("legal_authority_use"),
            "element_targeting": writing.get("element_targeting"),
            "evidence_composite": writing.get("evidence_composite"),
            "quality_composite": writing.get("quality_composite"),
            "defense_adoption_rate": writing.get("defense_adoption_rate"),
        },
        "legal_standard": {
            "standard_identification": bundled.get("standard_identification"),
            "standard_application": bundled.get("standard_application"),
            "element_completeness": bundled.get("element_completeness"),
        },
        "hallucination": {
            "hallucination_count": bundled.get("hallucination_count"),
            "severity": bundled.get("severity"),
            "hallucinated_facts": bundled.get("hallucinated_facts", []),
        },
        "bundled_agreement": bundled.get("bundled_agreement"),
        "sumf": sumf,
        "completeness": completeness,
        "gate_pass": (
            completeness["gate_pass"]
            and len(citations) > 0
            and sum(1 for c in cite_results if c["status"] == "fabricated") == 0
        ),
    }