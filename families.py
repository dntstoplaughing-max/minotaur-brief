"""Family registry for the multi-family base-vs-instruct experiment.

Each entry pins (a) the base checkpoint served locally on Bridges-2 via vLLM
and (b) the matched instruct endpoint hosted by an external provider. The
pairing is what gives us a clean "alignment delta" measurement for each lab's
post-training recipe.

runner.py reads `--family <name>`, looks up the entry here, and overrides the
BASE_MODEL/INSTRUCT_MODEL constants imported from config.py. Provider dispatch
in run_instruct() switches on `instruct_provider`.

API keys live in config.py (protected), referenced by runner.py per provider.
"""

FAMILIES = {
    "llama70b": {
        "display_name": "Llama 3.1 70B",
        # --- Base (vLLM on Bridges-2) ---
        "base_model_name": "meta-llama/Llama-3.1-70B",
        "base_local_path": "/ocean/projects/cis260106p/dmullins/models/Llama-3.1-70B",
        "base_tp_size": 8,            # Bridges-2 allocates whole 8-GPU nodes; 70B BF16 has ~18 GB/GPU at TP=8
        "base_dtype": "bfloat16",
        "base_quantization": None,    # 70B does not need fp8
        "base_max_model_len": 131072,
        # --- Instruct (AWS Bedrock) ---
        "instruct_provider": "bedrock",
        "instruct_model_id": "us.meta.llama3-1-70b-instruct-v1:0",
        "instruct_endpoint": None,    # boto3 client is region-based
        "instruct_supports_seed": False,
        "instruct_reasoning_mode": None,  # Llama 3.1 70B Instruct has no reasoning toggle
    },
    "gemma31b": {
        # NOTE: family key retained as `gemma31b` for code stability across
        # historical results paths and slurm artifacts; actual model is the
        # Gemma 3 27B base/instruct pair. The `Gemma3ForCausalLM` architecture
        # is registered in vLLM 0.11.2 and well-supported on this stack
        # (transformers >= 4.56, < 5; tokenizers >= 0.21.1).
        "display_name": "Gemma 3 27B",
        # --- Base (vLLM on Bridges-2) ---
        "base_model_name": "google/gemma-3-27b-pt",
        "base_local_path": "/ocean/projects/cis260106p/dmullins/models/gemma-3-27b-pt",
        "base_tp_size": 8,            # Bridges-2 allocates whole 8-GPU nodes; 27B BF16 fits easily at TP=8
        "base_dtype": "bfloat16",
        "base_quantization": None,
        "base_max_model_len": 131072, # Gemma 3 native 128K context window
        # --- Instruct (Together AI, OpenAI-compatible) ---
        "instruct_provider": "together",
        "instruct_model_id": "google/gemma-3-27b-it",
        "instruct_endpoint": "https://api.together.xyz/v1",
        "instruct_supports_seed": True,
        "instruct_reasoning_mode": "on",  # keep as shipped — modern alignment includes reasoning
    },
    "deepseek_v4_flash": {
        # NOTE: family key retained as `deepseek_v4_flash` for code stability;
        # actual model swapped to V3.1 after V4-Flash failed vLLM compatibility
        # check (vLLM 0.11.2 does not support `deepseek_v4` architecture, and
        # source-build of latest vLLM on login node was infeasible within
        # deadline). V3.1 is documented Plan B per PREREGISTRATION.md and the
        # cross-family alignment-recipe story holds with V3.1.
        "display_name": "DeepSeek V3.1",
        # --- Base (vLLM on Bridges-2) ---
        "base_model_name": "deepseek-ai/DeepSeek-V3.1-Base",
        "base_local_path": "/ocean/projects/cis260106p/dmullins/models/DeepSeek-V3.1-Base",
        "base_tp_size": 8,            # 671B MoE FP8 needs all 8 GPUs
        "base_dtype": "auto",         # FP8 native in checkpoint; let vLLM pick
        "base_quantization": None,    # already FP8 weights — do NOT pass --quantization
        "base_max_model_len": 131072, # ships 128K; matches cross-family condition
        # --- Instruct (DeepSeek API, OpenAI-compatible) ---
        "instruct_provider": "deepseek",
        "instruct_model_id": "deepseek-chat",  # DeepSeek API's V3.1 chat endpoint
        "instruct_endpoint": "https://api.deepseek.com/v1",
        "instruct_supports_seed": True,
        "instruct_reasoning_mode": "on",  # preserves alignment-as-shipped methodology
    },
}


def get_family(name):
    if name not in FAMILIES:
        raise ValueError(
            f"Unknown family: {name!r}. Available: {sorted(FAMILIES.keys())}"
        )
    return FAMILIES[name]
