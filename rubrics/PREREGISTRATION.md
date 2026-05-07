# Pre-registration: Scoring Rubrics

**Project:** Minotaur — Multi-family alignment-induced capability degradation in long-form legal reasoning
**NeurIPS 2026 submission**
**Frozen:** 2026-05-03 (Sun) prior to inspection of any main-run output
**Amended:** 2026-05-07 (Wed) prior to inspection of any main-run output (see Version history)
**Author:** D. Mullins (first author)

## Version history

This pre-registration has been amended once since the original 2026-05-03 freeze. Both versions were committed prior to inspection of any main-run output (`results/scored/` empty as of each freeze date). All changes are documented below; original text is preserved in place, with inline `[Amended v2, 2026-05-07; see Version history]` markers where the v2 amendment overrides earlier commitments.

### v1.0 — 2026-05-03

Original freeze. Files: `doctrinal_rubric.json`, `writing_rubric.json`, `PREREGISTRATION.md`. Three-layer scoring architecture with human anchoring as the Layer 3 human-validation strategy (30-output blinded subsample, sub-stratified 10 per family).

### v2.0 — 2026-05-07

Amendment. Two methodologically motivated changes, both pre-data-inspection:

1. **Human anchor removed.** The Layer 3 human-anchoring strategy is dropped in its entirety. Rationale: convergent validity (Sonnet vs. Opus) plus self-consistency (Sonnet 3-pass) are retained as the Layer 3 validation strategy. Single-rater human anchoring on 30 outputs would not have produced a publishable inter-rater statistic against the LLM judges at that sample size, and the rubric-driven LLM judges have stronger reproducibility properties than a single human rater anyway. Affected:
   - `writing_rubric.json` and `doctrinal_rubric.json`: `meta.human_anchor_n` and `meta.human_anchor_blinding` fields removed.
   - `rubrics/human_anchor_template.csv`: deleted.
   - This document, "Three-layer scoring architecture" → Layer 3 sub-bullet on human anchoring and the κ_human-Sonnet / κ_human-Haiku reporting commitments: marked amended (see inline marker below).
   - This document, "Stratification scheme" → human-anchor 30-output sub-stratification: marked amended (see inline marker below).

2. **Writing rubric v2 (citation-grounded).** The five-axis writing rubric is sharpened with anchor language and per-axis "Sources" blocks tying each axis to standard legal-writing pedagogy and supporting authority (Garner *Winning Brief*; Aldisert *Winning on Appeal*; Edwards; Edwards & Moppett; Neumann/Simon/Painter-Thorne; the Bluebook for signal form; MRPC 3.3; *Smith v. Murray*; *Anderson v. Liberty Lobby*; *Celotex v. Catrett*). The five axes, the 1-5 scale, the 1/3/5 anchor structure, and the composite definition (mean of five axes) are unchanged. v2 ships as `rubrics/writing_rubric_v2.md`; the v1 JSON (`rubrics/writing_rubric.json`) remains in place as the machine-readable spec because the v2 schema (with per-axis Sources blocks) diverges from the v1 schema. Diff documented in `rubrics/CHANGES.md`. Bibliographic entries added to `paper/references.bib`.

Both changes are literature-grounded and pre-data-inspection. Pre-registration freezes scoring methodology at the moment of running scoring, not earlier; main-run scoring has not occurred against either v1 or v2.

## Methodological commitment

The two rubric files in this directory (`doctrinal_rubric.json`, `writing_rubric.json`) define the scoring criteria for all judge-based measurements in the experiment. They are committed prior to:

1. Inspection of any main-run output (`results/raw/*/run_*.json`)
2. Computation of any judge-based scores
3. Final selection of which metrics carry the headline claims

## Disclosure: a priori vs probe-informed elements

Phase 1 probe outputs (instruct-only, in `scripts/phase3/outputs/07/`) were inspected during methodology iteration. Two categories of rubric content are distinguished and disclosed:

### A priori (independent of probe data)
- The five-axis writing-quality rubric (argumentative force, citation integration, element discipline, adverse-fact treatment, standard articulation) — derived from standard legal-writing pedagogy, not from observed outputs.
- The required_elements list per task — derived directly from `prompts/ground_truth.json`, which was committed before probe data existed.
- The 0/1/2 doctrinal scoring scale and pitfall_to_score_rule — derived from psychometric standard practice, not from observed outputs.
- The doctrinal pitfalls list at the task level draws primarily from canonical 1L doctrinal-exam errors known a priori from legal pedagogy: e.g., Burlington Northern adverse-action threshold, *Univ. of Texas v. Nassar* but-for causation in retaliation, *A.J.T. v. Osseo Area Schools* standard articulation in ADA Title II, the underlying-tort requirement for civil conspiracy in Pennsylvania.

### Probe-informed
- A small subset of pitfall framings reflect specific error patterns observed in Phase 1 instruct-only Llama 70B outputs (e.g., the *Doe v. Mercy Catholic Medical Center* citation framing for retaliation, where Mercy Catholic was misapplied to the retaliation framework rather than to its actual holding on Title IX implied causes of action).

These probe-informed pitfalls are methodologically equivalent to selecting from the canonical doctrinal-error space: they are not invented categories, but specific framings within already-known error categories. The rubric does not penalize behaviors that are not within standard 1L doctrinal-error taxonomy.

## Cross-family heterogeneity hypothesis

The hypothesis that alignment recipes produce systematically different output styles across families is grounded in **Phase 1 instruct-only probe data (180 calls across all three families)**: Gemma 4 31B-it produced ~4-5x token count of Llama 3.1 70B-Instruct on identical prompts (Gemma mean ~2,800 output tokens vs Llama mean ~840 over the first 60+18 calls, respectively). DeepSeek V4-Flash data was incomplete at probe-design time. This observation is disclosed; analyses involving cross-family verbosity are framed as confirmatory rather than exploratory only when DeepSeek probe data are also in hand.

## Cost-aware judge selection

Sonnet 4.6 was selected over Opus 4.6 as primary writing-quality judge based on cost-fidelity tradeoff, not on probe-output observations:
- Cost ratio: Sonnet 4.6 is ~5x cheaper per call than Opus 4.6 (input/output token pricing on Bedrock).
- Performance parity: published benchmarks through 2025-2026 show Sonnet within 2-3% of Opus on rubric-style scoring tasks.
- Validation safeguard: Opus 4.6 independently re-scores a stratified 10% subsample (Layer 3 convergent validity); if Sonnet-Opus agreement is below an acceptable threshold (κ < 0.6), Opus scores will be promoted to primary.

This decision was made before Phase 1 outputs were inspected. Probe outputs played no role.

## Three-layer scoring architecture

**Layer 1 — Deterministic checks:** rule-based extraction. Element presence via keyword match against `ground_truth.json` element lists. Citation existence against case corpus. Exhibit precision/recall against ground-truth relevant-exhibit lists. Implemented in `scorer.py` and `gates.py`.

**Layer 2 — Rubric scoring:** LLM judges score outputs against pre-registered rubrics.
- Doctrinal-element accuracy: Claude Haiku 4.5, 1-pass, full corpus, against `doctrinal_rubric.json`
- Writing quality: Claude Sonnet 4.6, 1-pass, full corpus, against `writing_rubric.json`

**Layer 3 — Validation:** convergent validity + self-consistency. *[Amended v2, 2026-05-07; original text below described "convergent validity + human anchoring" and included a human-anchoring sub-bullet and κ_human-* reporting commitments. See Version history.]*
- Convergent validity: Claude Opus 4.6 independently scores stratified 10% subsample (stratified by family × condition × level)
- ~~Human anchoring: first author scores 30-output blinded subsample on identical rubrics, prior to inspecting any LLM-judge scores~~ *[Removed v2, 2026-05-07; see Version history.]*
- Self-consistency: Sonnet 4.6 3-pass scoring of the same 10% subsample
- Reported: κ_doctrinal (Haiku vs Opus), κ_writing (Sonnet vs Opus), ~~κ_human-Sonnet, κ_human-Haiku,~~ κ_self (Sonnet 3-pass) *[κ_human-* removed v2, 2026-05-07; see Version history.]*

## Stratification scheme

The 10% subsample is stratified by:
- Family: 3 levels (llama70b, gemma31b, deepseek_v4_flash)
- Condition: 4 levels (base_alone, base_nudge, instruct_alone, instruct_nudge)
- Level: 4 levels (L1_focused, L2_exhibit_noise, L3_full_noise, L4_cross_count)

Total stratification cells: 48 per family, 144 across all 3 families. 10% sample = ~240 outputs (~5 per cell, 1-2 per cell per family).

~~Human-anchor 30-output sample is sub-stratified: 10 per family, balanced across conditions and levels within each family.~~ *[Removed v2, 2026-05-07; see Version history.]*

## Rubric freeze hash

After this preregistration is committed, future modifications to the rubric JSON files will be tracked via git. Any post-freeze modification must be disclosed in the paper with rationale.

```
v1.0 — frozen 2026-05-03:
  File: doctrinal_rubric.json
  File: writing_rubric.json
  File: PREREGISTRATION.md (this file)

v2.0 — amended 2026-05-07:
  File: doctrinal_rubric.json   (meta.human_anchor_* fields removed)
  File: writing_rubric.json     (meta.human_anchor_* fields removed)
  File: writing_rubric_v2.md    (added; citation-grounded markdown spec)
  File: CHANGES.md              (added; v1 → v2 rubric-level diff)
  File: PREREGISTRATION.md      (this file; Version history added, Layer 3
                                 and Stratification scheme amended in place)
  File: human_anchor_template.csv  (deleted)
  File: paper/references.bib    (10 bibliographic entries added)
```
