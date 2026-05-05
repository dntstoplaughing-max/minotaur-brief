import boto3, time
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
c = boto3.client('bedrock-runtime', region_name=AWS_REGION,
                 aws_access_key_id=AWS_ACCESS_KEY_ID,
                 aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
t0 = time.time()
r = c.converse(
    modelId='us.meta.llama3-1-70b-instruct-v1:0',
    messages=[{'role':'user','content':[{'text':'Say hello in one word.'}]}],
    inferenceConfig={'maxTokens': 50, 'temperature': 0.4},
)
elapsed = time.time() - t0
text = r['output']['message']['content'][0]['text']
print(f"Bedrock OK in {elapsed:.2f}s: {text!r}")
