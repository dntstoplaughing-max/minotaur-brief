# Phase 3 — Pre-Run Interactive Probes

These scripts run **before** the full SLURM job (`minotaur_run.job`).
They are designed for an interactive 8xH100 session so failures are
immediate and you can see the vLLM logs scroll.

## Get an interactive session

```
interact -p GPU --gres=gpu:h100-80:8 -t 2:00:00 -A cis260106p
```

Once on the compute node, `cd` into the minotaur project and run the
scripts in order. All scripts assume `MINOTAUR_DIR` defaults to
`/ocean/projects/cis260106p/dmullins/minotaur` — override with an env
var if you put the code somewhere else.

## Order to run

| # | Script | Purpose | Needs vLLM running? | Needs Bedrock? |
|---|---|---|---|---|
| 0 | `../verify_model.sh` | Model files intact (run on **login** node before booking GPUs) | no | no |
| 1 | `00b_vllm_deploy.sh` | Boot vLLM on :8000, watch the log | (it starts vLLM) | no |
| 2 | `00c_kvcache_stress.sh` | 24K-token prompt at 4096 / 6144 / 10240 max_tokens | yes | no |
| 3 | `02_base_format_probe.sh` | 3 base-model generations on Count I, L1, no nudge | yes | no |
| 4 | `03_regex_probe.py` | Run gates.py extraction regexes against the generations from step 3 | no | no |
| 5 | `04_bedrock_check.sh` | Confirm AWS Bedrock reachable from compute node | no | yes |
| 6 | `05_runner_smoke.py` | End-to-end runner.py smoke test: 1 task x 1 level x 4 conds x 1 run = 4 gens | yes | yes |
| 7 | `06_bundleB_probe.py` | Single-call validation that Bundle B (legal accuracy judge) parses cleanly before the 800-gen run uses it | no | yes |

### Step 1: launch vLLM in shell A

```
bash scripts/phase3/00b_vllm_deploy.sh
```

That script prints its PID and tails the log. Leave it running. From
**shell B** on the same node, confirm it's serving:

```
curl -s http://127.0.0.1:8000/v1/models | head
```

### Step 2-3: stress + format probe (shell B)

```
bash scripts/phase3/00c_kvcache_stress.sh
bash scripts/phase3/02_base_format_probe.sh
```

### Step 4: regex probe (no GPU needed; can run anywhere with the env)

```
python3 scripts/phase3/03_regex_probe.py
```

This is the **most likely test to fail** — the citation/quote/exhibit
regexes in `gates.py` were tuned against handwritten samples and may
not match the formatting the base 405B emits. Read the output
carefully. Any regex family with zero matches across all three
generations means `gates.py` needs tuning before the 800-gen run.

### Step 5: Bedrock egress

```
bash scripts/phase3/04_bedrock_check.sh
```

Confirms credentials and outbound HTTPS to `bedrock-runtime.us-east-2.amazonaws.com`.
If the compute node has no egress, every `instruct_*` condition in
`runner.py` will fail — better to know now.

### Step 6: end-to-end smoke test

```
python3 scripts/phase3/05_runner_smoke.py
```

Imports `runner.py`'s helpers and runs 1 task x 1 level x 4 conditions
x 1 run = 4 generations. Exercises the full pipeline glue (config import,
both clients, prompt assembly, both `run_base` + `run_instruct`,
truncation detection, output JSON schema). Run this **last** — it
needs both vLLM and Bedrock to be working. If any of conditions
0B/0C/02/03/04 fail, fix those first; this test will fail downstream
otherwise.

Outputs land in `outputs/05/runner_smoke.json` (shape-compatible with
`runner.py`'s real output JSON) plus per-condition assembled prompts.

## Cleanup

When done with the interactive session:

```
# in shell A: Ctrl-C, or from shell B:
kill <vllm_pid>           # the pid printed by 00b_vllm_deploy.sh
```

Do **not** `taskkill //IM` or `pkill -f vllm`. Use the specific PID.

## Outputs

Each script writes under `scripts/phase3/outputs/<test-name>/`. Nothing
is overwritten across tests, so you can re-run individually.
