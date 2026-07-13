# Next Steps — Verification Product Roadmap

**Prepared:** July 13, 2026
**Scope:** Path from the current verification pipeline (Minotaur gates + the operational
filing-verification pipeline) to a generalizable verification product, with the author's
active federal case as the continuous testbed and a late-fall 2026 target for grant
applications and pilot conversations.

---

## 1. Product thesis

**Two products, strictly separated:**

| | Product 1 — Verification | Product 2 — Drafting |
|---|---|---|
| What | Deterministic gates + contextual-deployment (Relay) layer + audit report over any draft filing | Generation of filings, gated by Product 1 |
| Status | Operational (pre-v1.0); deployed on real federal filings | Not started as a product; deferred |
| Market position | Empty lane; drafting tools are potential customers | Crowded, capital-heavy (Harvey, CoCounsel, Paxton) |
| Priority | **Now** | Later, as a client of the verification layer |

**The independence principle (architectural and commercial).** The verifier must be
adversarial to whatever produced the text — human, Claude, or a competitor's drafting
tool. A verifier that certifies its own drafter's output is grading its own homework.
Separation is therefore not just a repo boundary; it is the credibility of the product.
The verification layer takes a document and a record; it does not know or care who wrote
the document.

**The deliverable is the audit report.** The product's output is a timestamped,
methodology-documented verification report suitable for attaching to a filing
(increasingly relevant as courts adopt AI-use certification requirements). Every gate
contributes findings to one report artifact.

## 2. What generalizes vs. what is case-specific

Inventory of the current pipeline, sorted by what must change to serve a second matter:

| Component | Engine (keep) | Case-specific (parameterize) |
|---|---|---|
| Gate 1 — citation existence | Extraction + lookup logic | Hand-built corpus → auto-built per-matter corpus |
| Gate 2 — quote string-match | Matching logic | Curated full-text archive → fetched opinion text |
| Gate 3 — contextual deployment (Relay) | Role / Deployed Quote / Danger Zone schema; backward verification flow | Relay contents are inherently per-matter (that is the point); the *authoring workflow* must be automated |
| Gate 4 — formatting compliance | Check runner | Judge-specific standing-order rules → per-court rule packs |
| Gate 5 — AI certification | Check runner | Per-court certification requirements |
| Gate 5.5 — compilation/quality | pdflatex round-trip | Input format support (.docx is table stakes for anyone who isn't the author) |
| Exhibit/element mapping (Minotaur Gates 4–5) | Element-coverage logic | Ground-truth element↔exhibit map → assisted authoring per matter |
| Audit report | Report generator | — |

**Key engineering swaps for generalization:**

- **Citation extraction:** replace hand-rolled regexes with `eyecite` (Free Law Project's
  citation parser — battle-tested on millions of documents).
- **Ground truth:** CourtListener API (citation lookup, dockets, opinion text; full API
  open as of May 2026) + Caselaw Access Project bulk data. No Westlaw dependency
  (opinions are public domain; the only WL moat is the citator, which is itself imperfect).
- **Corpus builder:** a per-matter ingest step (docket + cited authorities → fetched full
  text → matter corpus). `docket_sync.py` is the seed for the docket half.
- **Relay authoring:** LLM drafts Role / Deployed Quote / Danger Zone per authority from
  the fetched opinion text; human confirms. The confirmed Relay is the compounding asset.

## 3. Workstreams (July → late fall 2026)

### WS1 — Repository and separation (July)
- [ ] Move the pipeline runner, gate modules, and existing audit reports from local disk
      into a **private** repo, scrubbed of privileged material. The audit reports are the
      evidence base; they must be in version control.
- [ ] Establish the verification/drafting boundary in code: verification takes
      (document, matter-corpus) as inputs; nothing in it depends on how the document was
      produced.

### WS2 — Calibration ("Phase C") (July–August)
The single highest-value task. No product claim, grant application, or paper survives
without characterized error rates.
- [ ] Build a known-good / known-bad test suite: previously verified filings (known-good)
      plus deliberately seeded failures (fabricated citation, altered quote, misattributed
      quote, paraphrase-as-quotation, missing certification, formatting violations).
- [ ] Run all gates; record false-positive and false-negative rates per gate.
- [ ] Tune gate sensitivity; re-run; freeze calibration results with a dated report.

### WS3 — Generalization (August–September)
- [ ] Swap in `eyecite` + CourtListener/CAP as the ground-truth layer (WS2 test suite
      guards against regressions).
- [ ] Build the per-matter corpus builder (docket + authorities → matter corpus).
- [ ] Prototype assisted Relay authoring (LLM draft → human confirm).
- [ ] Accept .docx input, not just .tex.

### WS4 — Second-matter test (September–October)
- [ ] Run the full pipeline on at least one filing from a matter that is **not** the
      author's case (a public docket with a decided motion works: the briefing and the
      record are public, and the outcome provides a sanity check).
- [ ] Document what transferred cleanly vs. what needed hand-fitting. This distinction —
      engine vs. case-specific — is the core generalization evidence.

### WS5 — Evidence and write-up (October)
- [ ] Consolidate the honest metrics: gated filings to date, references verified,
      fabrications reaching a filing (zero to date), errata caught pre-filing, calibrated
      FP/FN rates from WS2, second-matter transfer results from WS4.
- [ ] Framing discipline: the pipeline "structurally prevents ungrounded text from
      reaching the court" — never "eliminates hallucination." Head-to-head comparisons
      against commercial tools are a proposed study until actually run (the Minotaur
      benchmark is the instrument for running it).

### WS6 — Demand tests and funding (parallel, low-cost; decisions late fall)
- [ ] Demand test: conversations with ~10 solo/small-firm practitioners and/or a law
      school clinic; publish the write-up where legal-tech readers will see it.
- [ ] Grant scan and applications: two independent funding narratives —
      **access to justice** (verification keeps pro se filings from being struck) and
      **AI safety** (external verification / deterministic oversight of model output in a
      high-stakes deployed setting). Target: applications submitted by late fall.
- [ ] Defer incorporation until there is pull (someone asking to use or fund it). An LLC
      is an afternoon; premature company-building is not.

## 4. Continuous testbed

The author's active federal case remains the live proving ground: every real filing
continues to run through the pipeline, extending the deployment record while WS1–WS5
proceed. Each gated filing adds to the evidence base at zero marginal research cost.

## 5. Decision gate (late fall 2026)

With calibration numbers (WS2), generalization evidence (WS4), the consolidated write-up
(WS5), and demand-test results (WS6) in hand, choose among:

1. **Commercial** — incorporate and pursue pilots (only with demonstrated pull).
2. **Grant-funded build** — public-interest verification infrastructure; keep IP.
3. **Open-core / career artifact** — open the engine, let the record and the benchmark
   do the talking, and let an employer or partner fund continued development.

All three are served identically by WS1–WS5; the fork requires no commitment today.

## 6. What this document is not

- Not a commitment to specific claims: all public statements about the pipeline's record
  follow the metrics-discipline rules above (concrete verification counts; no retired
  aggregate "event" counts; no "eliminates hallucination").
- Not the drafting-product plan: drafting is out of scope until the verification layer
  is calibrated, generalized, and independently credible.
