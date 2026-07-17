#!/usr/bin/env python3
"""06_bundleB_probe.py — single-call test of Bundle B (legal accuracy judge).

Bundle B (run_legal_accuracy_judge) was gated off until tonight; this
verifies that the prompt schema + parse logic produce non-None results
for the expected fields BEFORE the 800-gen run begins relying on it.

Reads the first available gen_*.txt from outputs/02/ if present, else
falls back to a small hardcoded brief. Calls run_legal_accuracy_judge
with num_passes=1 (cheap probe; full run uses num_passes=3).

Exit 0 iff all expected keys present and the two critical numeric
fields (element_accuracy, framing_accuracy) are non-None.
"""
import json
import os
import sys

MINOTAUR_DIR = os.environ.get(
    "MINOTAUR_DIR", "/ocean/projects/cis260106p/dmullins/minotaur"
)
os.chdir(MINOTAUR_DIR)
sys.path.insert(0, MINOTAUR_DIR)

import gates  # noqa: E402

here = os.path.dirname(os.path.abspath(__file__))
gen_dir = os.path.join(here, "outputs", "02")

sample_text = None
sample_source = None
if os.path.isdir(gen_dir):
    for fn in sorted(os.listdir(gen_dir)):
        if fn.startswith("gen_") and fn.endswith(".txt"):
            with open(os.path.join(gen_dir, fn), encoding="utf-8") as f:
                t = f.read()
            if t.strip():
                sample_text = t
                sample_source = fn
                break

if not sample_text:
    sample_source = "(hardcoded fallback)"
    sample_text = (
        "I. INTRODUCTION\n\n"
        "Plaintiff respectfully opposes defendant's motion for summary "
        "judgment on Count I (deliberate indifference under Title IX).\n\n"
        "II. STATEMENT OF FACTS\n\n"
        "The record establishes that the school had actual knowledge of "
        "ongoing harassment. See Exhibit A (initial complaint); Exhibit "
        "B-3 (follow-up email to Title IX Coordinator).\n\n"
        "III. ARGUMENT\n\n"
        "A. Actual Knowledge\n\n"
        "Defendants received written notice via Exhibit A and Exhibit B-3, "
        "establishing actual knowledge under Davis v. Monroe County, 526 "
        "U.S. 629 (1999). The Title IX Coordinator's failure to respond "
        "demonstrates the school's deliberate indifference.\n\n"
        "B. Deliberate Indifference\n\n"
        "Despite multiple reports, defendants took no investigatory action "
        "for ninety days, satisfying the deliberate indifference standard. "
        "See Exhibit C.\n\n"
        "IV. CONCLUSION\n\n"
        "For the foregoing reasons, plaintiff respectfully requests that "
        "the Court deny defendants' motion for summary judgment on Count I."
    )

print(f"[06] sample source: {sample_source}")
print(f"[06] sample length: {len(sample_text)} chars")
print(f"[06] judge model:   {gates.JUDGE_MODEL}")

with open(os.path.join(MINOTAUR_DIR, "prompts", "ground_truth.json")) as f:
    ground_truth = json.load(f)

task_id = "deliberate_indifference"
if task_id not in ground_truth:
    print(f"[06] FAIL: task_id={task_id!r} not in ground_truth.json")
    sys.exit(1)

print(f"[06] running run_legal_accuracy_judge with task={task_id}, "
      f"num_passes=1 (probe; full run uses 3)")
print()

result = gates.run_legal_accuracy_judge(
    sample_text, task_id, ground_truth, num_passes=1
)

print("[06] === RESULT ===")
print(json.dumps(result, indent=2, default=str))
print()

expected_keys = {
    "element_accuracy", "exhibit_scores", "framing_accuracy",
    "wrong_count_framing", "wrong_count_instances",
    "legal_accuracy_agreement",
}
missing = expected_keys - set(result.keys())
critical_none = [
    k for k in ("element_accuracy", "framing_accuracy")
    if result.get(k) is None
]

print("=" * 67)
if missing:
    print(f"[06] FAIL: missing keys: {sorted(missing)}")
    sys.exit(1)
if critical_none:
    print(f"[06] FAIL: critical fields None ({critical_none}). The "
          f"judge call probably failed (network, schema mismatch, or "
          f"_permissive_json_parse couldn't extract from the response).")
    sys.exit(1)
print(f"[06] PASS: all expected fields present, "
      f"element_accuracy={result['element_accuracy']}, "
      f"framing_accuracy={result['framing_accuracy']}")
sys.exit(0)
