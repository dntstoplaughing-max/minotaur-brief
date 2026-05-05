#!/usr/bin/env python3
"""03_regex_probe.py — run gates.py extraction regexes against the
generations from 02_base_format_probe.sh.

This is the most likely test to fail: the citation/quote/exhibit regexes
were tuned against handwritten samples and may miss the formatting the
base 405B actually emits. We loudly print mismatches so they can be
fixed in gates.py BEFORE the full 800-gen run.
"""

import os
import sys
import importlib.util


def load_gates(minotaur_dir):
    """Import gates.py without triggering its config-side-effects (API
    keys), by injecting a stub config first."""
    gates_path = os.path.join(minotaur_dir, "gates.py")
    if not os.path.isfile(gates_path):
        sys.exit(f"[03] FAIL: gates.py not found at {gates_path}")

    # Provide a minimal config stub so `from config import ...` succeeds
    # without requiring real API keys. Must include every name gates.py
    # imports from config — kept in sync with gates.py's `from config import ...`.
    if "config" not in sys.modules:
        import types
        stub = types.ModuleType("config")
        stub.JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"
        stub.ANTHROPIC_API_KEY = "stub"
        stub.AWS_ACCESS_KEY_ID = "stub"
        stub.AWS_SECRET_ACCESS_KEY = "stub"
        stub.AWS_REGION = "us-east-2"
        sys.modules["config"] = stub

    spec = importlib.util.spec_from_file_location("gates", gates_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gates"] = mod
    spec.loader.exec_module(mod)
    return mod


def show_matches(name, matches, limit=3):
    print(f"    {name:<22} count={len(matches):<3}", end="")
    if matches:
        sample = matches[:limit]
        rendered = []
        for m in sample:
            if isinstance(m, tuple):
                m = " | ".join(x for x in m if x)
            s = str(m).replace("\n", " ")
            rendered.append(s[:80] + ("..." if len(s) > 80 else ""))
        print("  first: " + " || ".join(rendered))
    else:
        print()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    minotaur_dir = os.environ.get(
        "MINOTAUR_DIR",
        os.path.abspath(os.path.join(here, "..", "..")),
    )
    out_dir = os.path.join(here, "outputs", "02")

    if not os.path.isdir(out_dir):
        sys.exit(f"[03] FAIL: missing {out_dir} — run 02_base_format_probe.sh first")

    gens = sorted(
        f for f in os.listdir(out_dir)
        if f.startswith("gen_") and f.endswith(".txt")
    )
    if not gens:
        sys.exit(f"[03] FAIL: no gen_*.txt files in {out_dir}")

    gates = load_gates(minotaur_dir)
    print(f"[03] loaded gates.py from {minotaur_dir}/gates.py")
    print(f"[03] probing {len(gens)} generations from {out_dir}")
    print()

    any_zero = False
    summary = []

    for fn in gens:
        path = os.path.join(out_dir, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        print(f"  === {fn}  ({len(text)} chars) ===")
        if not text.strip():
            print("    (empty file — skipping)")
            print()
            summary.append((fn, 0, 0, 0, 0))
            any_zero = True
            continue

        citations = gates.extract_citations(text)
        quotes = gates.extract_quotes(text)
        exhibit_refs = gates.extract_exhibit_refs(text)
        # gates.py exposes REFUSAL_PATTERNS via check_gate3a; show that too.
        refusal = gates.check_gate3a(text)

        show_matches("extract_citations", citations)
        show_matches("extract_quotes",    quotes)
        show_matches("extract_exhibit_refs", exhibit_refs)
        print(f"    {'check_gate3a':<22} is_refusal={refusal['is_refusal']}")
        print()

        summary.append(
            (fn, len(citations), len(quotes), len(exhibit_refs),
             1 if refusal["is_refusal"] else 0)
        )
        if len(citations) == 0 or len(quotes) == 0 or len(exhibit_refs) == 0:
            any_zero = True

    print("=" * 70)
    print(
        f"  {'file':<14} {'citations':>10} {'quotes':>8} "
        f"{'exhibits':>10} {'refusal':>8}"
    )
    for row in summary:
        fn, c, q, e, r = row
        print(f"  {fn:<14} {c:>10} {q:>8} {e:>10} {r:>8}")
    print("=" * 70)

    if any_zero:
        print("\n[03] ATTENTION: at least one generation produced ZERO matches "
              "for citations, quotes, or exhibits.")
        print("[03] If the generation visibly contains these things, the "
              "regexes in gates.py need tuning before the 800-gen run.")
        sys.exit(2)
    else:
        print("\n[03] PASS: every generation produced at least one match per "
              "regex family.")


if __name__ == "__main__":
    main()
