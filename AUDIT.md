# Minotaur Pipeline — Comprehensive Audit

**Date:** April 5, 2026
**Audited against:** Notion README + File Index + Build Spec
**Pipeline version:** $300 Sprint (Opus 4.6 / Bundle A only)

---

## Executive Summary

The pipeline is **structurally complete** — all 5 Python scripts and 5 JSON data files are present, and the core experimental logic (2x2 factorial, 4-level context ladder, 800 generations, 9 gates) is implemented. However, the audit identifies **3 critical issues**, **6 moderate issues**, and **8 minor issues** that should be resolved before running on Bridges-2.

| Component | Status | Compliance |
|-----------|--------|------------|
| config.py | CRITICAL | Hardcoded API keys |
| runner.py | PASS (with notes) | 95% — functional, oversized |
| gates.py | MODERATE | 75% — missing metrics, 1-pass not 3-pass |
| scorer.py | PASS | 98% — all major features present |
| pairwise.py | MODERATE | 75% — Cohen's kappa missing |
| corpus.json | PASS | 31 cases + 6 statutes, compliant |
| tasks.json | MODERATE | Missing 5 schema fields |
| context_ladder.json | PASS | 4 levels, compliant |
| exhibit_pool.json | PASS | 38 exhibits, compliant |
| ground_truth.json | PASS | 5 counts, Z-series mapped, compliant |

---

## CRITICAL Issues (must fix before run)

### C1. Hardcoded API Keys in config.py
**File:** `config.py` (lines 9-10, 14, 17)
**Problem:** AWS credentials, Anthropic API key, and OpenAI API key are hardcoded in plaintext. This is a credential leak risk — if the repo is ever shared, pushed to git, or backed up, all keys are exposed.
**Spec says:** Use `os.environ[]` for all secrets.
**Fix:** Replace all hardcoded keys with `os.environ["KEY_NAME"]`. The VLLM_BASE_URL already uses `os.environ.get()` correctly — follow that pattern for all secrets.

### C2. Self-Consistency Passes: 1-Pass Instead of 3-Pass
**File:** `gates.py` (lines 383, 471, 613)
**Problem:** All three bundle runners default to `num_passes=1`. The README and Build Spec both state "3-pass self-consistency" and the cost model ($71 judging) is calculated based on 3 Opus calls per generation (800 x 3 = 2,400 calls). Running 1-pass cuts judge reliability by ~67% and invalidates the cost model.
**Spec says:** "Opus 4.6 via OpenRouter, 3-pass self-consistency"
**Fix:** Change default `num_passes=3` in `run_writing_quality_judge()`, or set it in the orchestrator `run_gates()` call.

### C3. Cohen's Kappa Not Implemented in pairwise.py
**File:** `pairwise.py` (lines 492-496)
**Problem:** Inter-rater agreement between Opus 4.6 (primary) and GPT-4o (IAA) uses binary agreement only (`winner_a == winner_b`). Cohen's kappa — which corrects for chance agreement — is never computed. The README explicitly claims "Cohen's kappa" as a bias control.
**Fix:** Implement `cohen_kappa()` over the 15% IAA sample. Compute per-axis and overall. Report in summary output.

---

## MODERATE Issues (should fix before run)

### M1. API Endpoint Mismatch: Anthropic Direct vs. OpenRouter
**File:** `gates.py` (line 59)
**Problem:** Spec says "Opus 4.6 via OpenRouter" but code uses `anthropic.Anthropic()` (direct Anthropic API). These use different auth tokens, different pricing, and different rate limits. The cost model may be wrong if pricing differs.
**Impact:** Functional (both reach Opus 4.6) but pricing/rate-limiting assumptions differ.
**Fix:** Either update the spec to say "Anthropic API" or switch to OpenRouter client.

### M2. Gate 3b (Structural Completeness) Not Implemented
**File:** `gates.py`
**Problem:** Spec splits Gate 3 into G3a (refusal detection, scored) and G3b (structural completeness, diagnostic only). G3a is implemented. G3b is completely missing.
**Impact:** Diagnostic data loss — you won't know if outputs have proper brief structure (headings, argument sections, conclusion) even though this was designed as a logged-but-not-scored metric.
**Fix:** Add G3b as a diagnostic function that checks for section headers, argument structure, and conclusion. Log results but don't include in `gate_pass`.

### M3. Alignment Overhead Metrics Missing from gates.py
**File:** `gates.py`
**Problem:** The README lists zero-cost alignment overhead metrics: "hedge count, meta-commentary, balanced-analysis patterns, disclaimers, tokens-to-first-claim." These are NOT implemented in gates.py.
**Note:** scorer.py DOES implement these (lines 60-158, `compute_output_metrics()`). So the metrics exist in the pipeline — they're just in scorer.py rather than gates.py.
**Impact:** Low — metrics are computed, just in a different file than spec suggests.
**Fix:** Either move metrics to gates.py or update spec to note scorer.py computes them.

### M4. Token Efficiency Metrics Missing from gates.py
**File:** `gates.py`
**Problem:** Same as M3 — "substantive density, type-token ratio, sentence length variance" not in gates.py but ARE in scorer.py.
**Impact:** Same as M3.

### M5. tasks.json Missing Schema Fields
**File:** `prompts/tasks.json`
**Problem:** All 5 tasks are missing: `count`, `task_type`, `title`, `placeholders`, and `nudge_text` fields. The required_elements are present and correct (212, 188, 184, 281, 258 elements respectively).
**Impact:** runner.py works around this by inferring task type from ID naming convention, but the schema doesn't match the Build Spec's documented format.
**Fix:** Add missing fields to each task object.

### M6. gate_pass References Undefined Field
**File:** `gates.py` (lines 833-837)
**Problem:** `gate_pass` logic checks `completeness.get("has_citation", False)` but `has_citation` is never computed or returned by `check_completeness()`. This means the gate_pass check will always evaluate `has_citation` as False.
**Impact:** gate_pass is more restrictive than intended — outputs without citations will fail even if they shouldn't (or the check is a dead branch).
**Fix:** Either remove the `has_citation` check or add the computation to `check_completeness()`.

---

## MINOR Issues

### m1. config.py Exceeds Spec Size
38 lines vs. spec's ~15-20 lines. Extra variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, JUDGE_MODEL) are functional additions beyond original spec. Not a problem per se, but spec should be updated.

### m2. runner.py Exceeds Spec Size
301 lines vs. spec's ~180 lines. Extra code includes retry logic, detailed logging, and validation helpers. All valuable, but 67% over spec.

### m3. gates.py Exceeds Spec Size
837 lines vs. spec's ~550 lines. 52% over. Includes detailed prompts and comprehensive Bundle B/C implementations (even though gated off).

### m4. pairwise.py Exceeds Spec Size
729 lines vs. spec's ~300 lines. 143% over. Includes holistic zealous advocacy judge, detailed CSV export, and extensive summary output.

### m5. Unused Variable in runner.py
Line 238: `total_expected` is calculated but only used in a print statement, not for validation.

### m6. context_ladder.json Token Budgets
All 4 levels show `max_tokens: 4096`. The README says L3 should be 10240 and L4 should be 6144. The context_ladder.json has all levels at 4096.
**Impact:** L3 and L4 generations will be token-limited at 4096 instead of 10240/6144, potentially truncating long outputs.
**Fix:** Update L3 to 10240 and L4 to 6144 in context_ladder.json.

### m7. pairwise.py Self-Agreement Always 1.0
Line 369: `agreement = round(len(pass_results) / NUM_PASSES, 2)` with NUM_PASSES=1 always yields 1.0. Misleading metric name.

### m8. pairwise.py Pair Count
Spec says "200 pairs" but code generates all available pairs from data (variable count). The `--sample` flag can limit, but default is uncapped.

---

## Data Files Summary

### corpus.json — PASS
- **31 cases** (IDs 1-13, 15-32; ID 14 intentionally skipped)
- **6 statutes** (Title IX, ADA, 34 CFR sections)
- All cases have: id, case_name, citation, short_cite, alt_cites, holding, key_passages, used_in
- Phase 2 additions (cases 19-32: retaliation canon) present

### tasks.json — MODERATE (schema gaps)
- **5 tasks** correctly mapped to 5 counts
- required_elements populated for all tasks
- Missing fields: count, task_type, title, placeholders, nudge_text

### context_ladder.json — PASS (with m6 token note)
- **4 levels** (L1-L4) with correct filter configurations
- L1: relevant corpus + relevant exhibits
- L2: relevant corpus + all 38 exhibits
- L3: all 31 cases + all 38 exhibits + all defendants
- L4: same as L3 + cross-count elements

### exhibit_pool.json — PASS
- **38 exhibits** (A through Z-e, B-4 excluded)
- Z-series topic chunks present: Z-b (DI Standard), Z-c (Supportive Measures), Z-d (Conflict of Interest), Z-e (Actual Knowledge)
- All exhibits have: id, name, date, from, to, type, text

### ground_truth.json — PASS
- **5 count mappings** with element-exhibit maps
- Per-count: relevant + irrelevant = 38 (universe check passes)
- Z-series correctly distributed (Z-b/c/e -> Count I, Z-d/e -> Count IV)
- Cross-count pairings complete and bidirectional
- Signal ratios match File Index (39%, 34%, 29%, 55%, 47%)

---

## Pre-Run Checklist

Before submitting to Bridges-2:

- [ ] **C1:** Remove hardcoded API keys from config.py; use os.environ[] for all secrets
- [ ] **C2:** Set num_passes=3 in gates.py Bundle A judge call
- [ ] **C3:** Implement Cohen's kappa in pairwise.py IAA computation
- [ ] **m6:** Update context_ladder.json: L3 max_tokens=10240, L4 max_tokens=6144
- [ ] **M6:** Fix gate_pass has_citation reference in gates.py
- [ ] **M5:** Add missing schema fields to tasks.json (count, task_type, etc.)
- [ ] Verify Bridges-2 vLLM endpoint URL in config.py
- [ ] Verify AWS Bedrock access in us-east-2 for 405B instruct
- [ ] Test with 1 generation per cell (python runner.py --test) before full 800-gen run
- [ ] Confirm OpenRouter vs. Anthropic API decision for judge calls

---

*Audit performed by Claude Opus 4.6 against Notion README, File Index, and Build Spec pages.*
