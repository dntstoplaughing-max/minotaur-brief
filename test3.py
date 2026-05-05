from config import *
from openai import OpenAI
import boto3

print("Testing vLLM (base model)...")
client = OpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)
resp = client.completions.create(
    model=BASE_MODEL,
    prompt="The court held that",
    max_tokens=5,
)
print("  OK:", resp.choices[0].text.strip())

print("Testing Bedrock (instruct model)...")
bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
resp2 = bedrock.converse(
    modelId=INSTRUCT_MODEL,
    messages=[{"role": "user", "content": [{"text": "Say hello"}]}],
    inferenceConfig={"temperature": 0.4, "maxTokens": 5},
)
print("  OK:", resp2["output"]["message"]["content"][0]["text"])

print("\nBoth APIs connected. Ready to launch.")
