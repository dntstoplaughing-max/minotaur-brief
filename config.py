import os

# --- Providers ---
# Base model served locally on Bridges-2 (NSF ACCESS) via vLLM
# No chat template — raw completion mode, BF16 precision
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")

# AWS Bedrock for instruct model
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = "us-east-2"  # US East (Ohio) — where 405B is available

# Anthropic API for Opus judge calls (gates + pairwise)
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# OpenAI API for GPT-4o IAA cross-family judge (pairwise only)
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Models
BASE_MODEL = "meta-llama/Llama-3.1-405B"  # Bridges-2 vLLM — true base checkpoint, no chat template
INSTRUCT_MODEL = "us.meta.llama3-1-405b-instruct-v1:0"  # AWS Bedrock (cross-region inference profile)
JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"  # AWS Bedrock cross-region inference profile — judge for gates

# Experiment parameters
SEED = 54  # §54 of Kant's Critique of Judgment (the unlabeled section)
TEMPERATURE = 0.4  # Low temp for reproducibility
RUNS_PER_CONDITION = 10  # Per condition per level per task (5 × 4 × 4 × 10 = 800 total)

# Paths
CORPUS_PATH = "corpus.json"
TASKS_PATH = "prompts/tasks.json"
LADDER_PATH = "prompts/context_ladder.json"
EXHIBIT_POOL_PATH = "prompts/exhibit_pool.json"
GROUND_TRUTH_PATH = "prompts/ground_truth.json"
RAW_RESULTS_DIR = "results/raw"
SCORED_RESULTS_DIR = "results/scored"
PROMPT_LOG_DIR = "results/prompts"  # Full assembled prompts logged per generation

# Together AI for Gemma 4 31B Instruct
TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]

# DeepSeek API for V4-Flash Instruct
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

# Together AI for Gemma 4 31B Instruct
TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]

# DeepSeek API for V4-Flash Instruct
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
