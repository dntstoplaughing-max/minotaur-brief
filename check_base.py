from config import *
from openai import OpenAI
import anthropic
import boto3

# --- Test 1: Bridges-2 vLLM (base model) ---
print("Testing vLLM base model...", end=" ")
try:
    c = OpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)
    r = c.completions.create(
        model=BASE_MODEL,
        prompt="The court held that",
        max_tokens=5,
    )
    print(f"LIVE! Response: {r.choices[0].text.strip()}")
except Exception as e:
    print(f"DOWN — {str(e)[:150]}")

# --- Test 2: AWS Bedrock (instruct model) ---
print("Testing Bedrock instruct...", end=" ")
try:
    bedrock = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    r2 = bedrock.converse(
        modelId=INSTRUCT_MODEL,
        messages=[{"role": "user", "content": [{"text": "Say hello"}]}],
        inferenceConfig={"temperature": 0.4, "maxTokens": 5},
    )
    print(f"LIVE! Response: {r2['output']['message']['content'][0]['text']}")
except Exception as e:
    print(f"DOWN — {str(e)[:150]}")

# --- Test 3: Anthropic API (Opus judge) ---
print("Testing Anthropic judge...", end=" ")
try:
    ac = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    r3 = ac.messages.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=5,
    )
    print(f"LIVE! Response: {r3.content[0].text}")
except Exception as e:
    print(f"DOWN — {str(e)[:150]}")

print("\nDone.")
