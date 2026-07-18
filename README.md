# Minotaur-Brief

**A pre-registered benchmark for long-form federal-court advocacy — measuring
whether alignment post-training degrades legal reasoning.**

Frontier labs ship two checkpoints of the same model: the raw base model and
the aligned instruct model. Minotaur-Brief asks a narrow, measurable version
of an important question: on the hardest kind of legal writing — a multi-count
federal brief that must select evidence, deploy authority, and argue under
noise — does the instruct checkpoint outperform its own base, or has
post-training traded capability for compliance?

Source material is a real public docket: *Mullins v. Duquesne Univ.*,
No. 2:25-cv-01366 (W.D. Pa.). The maintainer is the pro se plaintiff in that
case and the benchmark's first author; that dual role is disclosed here and
in the paper.

## Design

- **2×2 factorial:** {base, instruct} × {alone, verification-nudge}, on
  5 drafting tasks (Title IX deliberate indifference, retaliation, ADA
  accommodation, common-law fraud, civil conspiracy).
- **4-level context ladder:** clean signal → exhibit noise → full noise →
  cross-count saturation (`prompts/context_ladder.json`).
- **10 runs per cell → 800 generations per model family.**
- **3 model families**, each a base/instruct pair: Llama 3.1 70B,
  Gemma 3 27B (pt/it), DeepSeek V3.1 (Base/chat). Base checkpoints served
  with vLLM on 8×H100 (PSC Bridges-2, NSF ACCESS allocation); instruct
  checkpoints via commercial APIs.
- **9 evaluation gates** (`gates.py`): five zero-cost automated checks
  (citation verification against the corpus, quote string-match at 0.85,
  refusal detection, structural completeness, exhibit precision/recall)
  ahead of LLM-as-judge scoring with pre-registered rubrics, position
  randomization, 3-pass self-consistency, and cross-family inter-annotator
  agreement.
- **Grounded corpus:** 31 cases + 6 statutes (`corpus.json`), 38 exhibits,
  and per-count element-to-exhibit ground-truth maps with construct-validity
  provenance (`rubrics/GROUND_TRUTH_PROVENANCE.md`).

## Status

- Pre-registration frozen 2026-05-03, amended v2 2026-05-07
  (`rubrics/PREREGISTRATION.md`). Design and rubrics are locked.
- Phase-3 pre-flight probes are complete (`scripts/phase3/outputs/`);
  the full 800-generation runs are pending scheduled HPC time.
- **No headline results yet.** Results and the accompanying manuscript are
  in preparation; nothing in this repository should be read as a finding.

Two naming notes, so the code reads correctly: for code-stability reasons the
family keys kept their original names — `gemma31b` serves **Gemma 3 27B**, and
`deepseek_v4_flash` serves **DeepSeek V3.1** (V4-Flash was dropped for vLLM
incompatibility). See `families.py`.

`AUDIT.md` is the project's spec-vs-reality audit log — every discrepancy
between the pre-registration and the implementation is tracked there with a
severity rating, including resolved historical issues. It is deliberately
public: a benchmark that audits models should audit itself.

## Related

The production counterpart of this benchmark is a gated verification pipeline
used for real filings in the source case — independently tested when a motion
to strike alleged AI fabrication and the court's own review found no
inaccurate, false, or non-existent citations (ECF 55). That story, in the
court's words: https://claude.ai/code/artifact/8225336e-50ac-4641-b390-cf4c82d891d1

## Privacy and pseudonymization

Non-party individuals appearing in the public docket are pseudonymized to
role labels in this dataset (and in the included model outputs), though
unredacted in the public record. Named defendants and the plaintiff (the
first author) are not pseudonymized; their identification is disclosed in
the paper. All personal email addresses and telephone numbers are redacted
for every individual, parties included; institutional role addresses
(e.g., offices of general counsel) are retained.
Pseudonymization pass v3, 2026-07-17 (v3 extends v2 to a non-party
administrator previously missed and redacts all personal contact details).

License: CC BY 4.0.
