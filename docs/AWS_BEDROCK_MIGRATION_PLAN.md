# AWS Bedrock Llama 3 70B Migration Plan

**Date:** 2025-10-25  
**Current:** Ollama (Local Gemma 1.1 2B, CPU)  
**Target:** AWS Bedrock (Llama 3 70B, Cloud)

---

## Executive Summary

### Why Migrate?

**Current Issues with Ollama:**
- ❌ Slow inference (30-60 seconds per query on CPU)
- ❌ Large model files (~2GB) stored locally
- ❌ Limited model quality (2B parameters)
- ❌ Resource intensive on local machine
- ❌ No GPU acceleration available

**Benefits of AWS Bedrock:**
- ✅ Fast inference (2-5 seconds per query)
- ✅ No local model storage needed
- ✅ Superior model quality (70B parameters)
- ✅ Scalable cloud infrastructure
- ✅ Pay-per-use pricing model
- ✅ Managed service (no maintenance)

---

## Architecture Changes

### Current Architecture
```
LLM-Connector → Ollama Container (localhost:11434) → Gemma 2B Model
```

### New Architecture
```
LLM-Connector → AWS Bedrock API (HTTPS) → Llama 3 70B Model
```

---

## Detailed Migration Plan

### Phase 1: Prerequisites & Setup (30 minutes)

#### 1.1 AWS Account Setup
- [ ] Ensure AWS account is active
- [ ] Enable AWS Bedrock service in your region
- [ ] Request access to Llama 3 70B model (if not already granted)
- [ ] Note: Some regions may require approval for model access

#### 1.2 AWS Credentials
- [ ] Create IAM user for Bedrock access
- [ ] Attach policy: `AmazonBedrockFullAccess` or custom policy
- [ ] Generate Access Key ID and Secret Access Key
- [ ] Store credentials securely

**IAM Policy (Minimal Permissions):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/meta.llama3-70b-instruct-v1:0"
    }
  ]
}
```

#### 1.3 Verify Bedrock Access
- [ ] Check available models in your region
- [ ] Confirm Llama 3 70B is available
- [ ] Test API access with AWS CLI

**Regions with Bedrock (as of 2025):**
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- ap-southeast-1 (Singapore)
- eu-central-1 (Frankfurt)

---

### Phase 2: Code Changes (1-2 hours)

#### 2.1 Update LLM-Connector Dependencies

**File:** `live_inference_pipeline/LLM-Connector/dockerfile`

**Current:**
```dockerfile
RUN pip install pika==1.3.2 ollama==0.1.7
```

**New:**
```dockerfile
RUN pip install pika==1.3.2 boto3==1.34.44
```

**Changes:**
- Remove: `ollama==0.1.7`
- Add: `boto3==1.34.44` (AWS SDK for Python)

---

#### 2.2 Rewrite LLM-Connector Logic

**File:** `live_inference_pipeline/LLM-Connector/connector.py`

**Current Implementation:**
```python
import ollama

def query_ollama(prompt):
    response = ollama.chat(
        model='gemma:2b-instruct',
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response['message']['content']
```

**New Implementation:**
```python
import boto3
import json
import os

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

def query_bedrock(prompt):
    """Query AWS Bedrock Llama 3 70B model"""
    
    # Llama 3 request format
    request_body = {
        "prompt": prompt,
        "max_gen_len": 512,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId='meta.llama3-70b-instruct-v1:0',
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        output = response_body.get('generation', '')
        
        return output
        
    except Exception as e:
        print(f"Bedrock API Error: {e}")
        return "I apologize, but I'm having trouble processing your request right now."
```

**Key Changes:**
1. Replace `ollama` import with `boto3`
2. Initialize Bedrock client with AWS credentials
3. Use `invoke_model()` instead of `ollama.chat()`
4. Handle Llama 3 specific request/response format
5. Add error handling for API failures

---

#### 2.3 Update Environment Variables

**File:** `live_inference_pipeline/.env.example`

**Add:**
```bash
# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Optional: Bedrock Model Configuration
BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
BEDROCK_MAX_TOKENS=512
BEDROCK_TEMPERATURE=0.7
```

**File:** `live_inference_pipeline/.env` (actual credentials)
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtn...
BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
BEDROCK_MAX_TOKENS=512
BEDROCK_TEMPERATURE=0.7
```

---

#### 2.4 Update Docker Compose

**File:** `live_inference_pipeline/docker-compose.yml`

**Current:**
```yaml
ollama:
  build: ./ollama
  container_name: ollama
  ports:
    - "11434:11434"
  volumes:
    - ./ollama_data:/root/.ollama

llm-connector:
  build: ./LLM-Connector
  depends_on:
    ollama:
      condition: service_healthy
```

**New:**
```yaml
# Remove ollama service entirely

llm-connector:
  build: ./LLM-Connector
  container_name: llm-connector
  depends_on:
    rabbitmq:
      condition: service_healthy
  environment:
    - PYTHONUNBUFFERED=1
    - AWS_REGION=${AWS_REGION}
    - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
    - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-meta.llama3-70b-instruct-v1:0}
    - BEDROCK_MAX_TOKENS=${BEDROCK_MAX_TOKENS:-512}
    - BEDROCK_TEMPERATURE=${BEDROCK_TEMPERATURE:-0.7}
```

**Changes:**
1. Remove entire `ollama` service definition
2. Remove `ollama` dependency from `llm-connector`
3. Add AWS environment variables to `llm-connector`
4. Remove health check for ollama

---

### Phase 3: Complete Code Rewrite (Detailed)

#### 3.1 Full connector.py Rewrite

**File:** `live_inference_pipeline/LLM-Connector/connector.py`

```python
import pika
import time
import sys
import os
import json
import boto3
from datetime import datetime, timezone

# --- Configuration ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
CONSUME_QUEUE = 'query_and_context'
PUBLISH_QUEUE = 'llm_output_queue'
PROCESS_QUEUE = 'process_updates'
CUD_QUEUE = 'CUD_queue'

# AWS Bedrock Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'meta.llama3-70b-instruct-v1:0')
BEDROCK_MAX_TOKENS = int(os.getenv('BEDROCK_MAX_TOKENS', '512'))
BEDROCK_TEMPERATURE = float(os.getenv('BEDROCK_TEMPERATURE', '0.7'))

# Initialize Bedrock client
print(f"[i] Initializing AWS Bedrock client (Region: {AWS_REGION}, Model: {BEDROCK_MODEL_ID})")
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
print("[+] Bedrock client initialized successfully")

def query_bedrock(prompt: str) -> str:
    """
    Query AWS Bedrock Llama 3 70B model
    
    Args:
        prompt: The formatted prompt with context and question
        
    Returns:
        Generated response from Llama 3 70B
    """
    try:
        # Llama 3 request format
        request_body = {
            "prompt": prompt,
            "max_gen_len": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
            "top_p": 0.9
        }
        
        print(f"[i] Sending request to Bedrock (Model: {BEDROCK_MODEL_ID})")
        
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        output = response_body.get('generation', '')
        
        print(f"[+] Received response from Bedrock ({len(output)} characters)")
        return output
        
    except bedrock_runtime.exceptions.ValidationException as e:
        print(f"[!] Bedrock Validation Error: {e}", file=sys.stderr)
        return "I apologize, but the request format was invalid. Please try again."
        
    except bedrock_runtime.exceptions.ThrottlingException as e:
        print(f"[!] Bedrock Throttling Error: {e}", file=sys.stderr)
        return "I apologize, but the service is currently busy. Please try again in a moment."
        
    except bedrock_runtime.exceptions.ModelNotReadyException as e:
        print(f"[!] Bedrock Model Not Ready: {e}", file=sys.stderr)
        return "I apologize, but the AI model is currently unavailable. Please try again later."
        
    except Exception as e:
        print(f"[!] Bedrock API Error: {e}", file=sys.stderr)
        return "I apologize, but I'm having trouble processing your request right now."

def publish_cud_message(history_data: dict) -> bool:
    """Publish message to CUD_queue for database persistence"""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=CUD_QUEUE, durable=True)
        
        cud_message = {
            "operation": "CREATE",
            "table": "chat_history",
            "data": {
                "user_prompt": history_data.get("user_prompt"),
                "llm_output": history_data.get("llm_output"),
                "context": history_data.get("context"),
                "timestamp": history_data.get("timestamp")
            }
        }
        
        message_body = json.dumps(cud_message)
        channel.basic_publish(
            exchange='',
            routing_key=CUD_QUEUE,
            body=message_body.encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        print(f"[>] Published CREATE message to '{CUD_QUEUE}' for chat_history.")
        connection.close()
        return True
    except Exception as e:
        print(f"[-] ERROR: Failed to publish CUD message: {e}", file=sys.stderr)
        return False

def main():
    connection = None
    for i in range(10):
        try:
            print(f"[*] Attempting to connect to RabbitMQ (attempt {i+1}/10)...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST, heartbeat=600))
            print("[+] Successfully connected to RabbitMQ.")
            break
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)
    if not connection:
        print("[-] Could not connect to RabbitMQ. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    channel = connection.channel()
    channel.queue_declare(queue=CONSUME_QUEUE, durable=False)
    channel.queue_declare(queue=PUBLISH_QUEUE, durable=False)
    channel.queue_declare(queue=PROCESS_QUEUE, durable=False)
    channel.queue_declare(queue=CUD_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        context = None
        user_prompt = None
        output = None
        
        try:
            prompt = body.decode()
            print(f"\n[x] Received prompt from '{CONSUME_QUEUE}'")
            
            # Extract context and user query
            if "Context:" in prompt and "Question:" in prompt:
                parts = prompt.split("Question:")
                context_part = parts[0].split("Context:")[1].strip()
                user_prompt = parts[1].strip()
                context = context_part
            else:
                user_prompt = prompt
                context = "No context provided"
            
            # Send status update
            status_payload = {
                "type": "stage_complete",
                "stage": "llm_processing_started",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            ch.basic_publish(exchange='', routing_key=PROCESS_QUEUE, body=json.dumps(status_payload))
            
            # Query Bedrock
            output = query_bedrock(prompt)
            
            # Send status update
            status_payload = {
                "type": "stage_complete",
                "stage": "llm_processing_complete",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            ch.basic_publish(exchange='', routing_key=PROCESS_QUEUE, body=json.dumps(status_payload))
            
            # Publish response
            ch.basic_publish(
                exchange='',
                routing_key=PUBLISH_QUEUE,
                body=output.encode('utf-8'),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(f"[>] Sent final answer to '{PUBLISH_QUEUE}'")
            
            # Persist to database
            history_data = {
                "user_prompt": user_prompt,
                "llm_output": output,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            publish_cud_message(history_data)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"[-] An error occurred: {e}", file=sys.stderr)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback, auto_ack=False)
    
    print(f"\n[*] LLM Connector is waiting for messages. To exit press CTRL+C\n")
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
```

---

### Phase 4: Testing & Validation (1 hour)

#### 4.1 Unit Testing
```python
# test_bedrock_connection.py
import boto3
import json
import os

def test_bedrock_connection():
    """Test AWS Bedrock connectivity"""
    client = boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv('AWS_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    request_body = {
        "prompt": "Hello, please respond with 'Connection successful'",
        "max_gen_len": 50,
        "temperature": 0.1
    }
    
    response = client.invoke_model(
        modelId='meta.llama3-70b-instruct-v1:0',
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    print(f"Response: {response_body.get('generation')}")
    print("✅ Bedrock connection successful!")

if __name__ == '__main__':
    test_bedrock_connection()
```

#### 4.2 Integration Testing
- [ ] Test with sample query through CLI
- [ ] Verify response quality
- [ ] Check response time (should be 2-5 seconds)
- [ ] Verify database persistence
- [ ] Test error handling (invalid credentials, rate limits)

#### 4.3 Performance Testing
- [ ] Measure average response time
- [ ] Test concurrent requests
- [ ] Monitor AWS costs
- [ ] Compare quality vs Gemma 2B

---

### Phase 5: Deployment (30 minutes)

#### 5.1 Build and Deploy
```bash
# 1. Stop current services
cd live_inference_pipeline
docker-compose down

# 2. Remove ollama data (optional - frees up space)
rm -rf ollama_data/

# 3. Update .env with AWS credentials
nano .env
# Add AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# 4. Rebuild llm-connector
docker-compose build llm-connector

# 5. Start services (ollama won't start - it's removed)
docker-compose up -d

# 6. Verify llm-connector logs
docker logs llm-connector
# Should see: "Bedrock client initialized successfully"

# 7. Test the system
cd CLI
python cli.py
```

#### 5.2 Verification Checklist
- [ ] llm-connector starts without errors
- [ ] Bedrock client initializes successfully
- [ ] Test query returns response in 2-5 seconds
- [ ] Response quality is high
- [ ] Database persistence works
- [ ] No ollama errors in logs

---

### Phase 6: Cleanup (15 minutes)

#### 6.1 Remove Ollama Files
```bash
# Remove ollama service directory
rm -rf live_inference_pipeline/ollama/

# Remove ollama data
rm -rf live_inference_pipeline/ollama_data/

# Update .gitignore (remove ollama_data line if desired)
```

#### 6.2 Update Documentation
- [ ] Update README.md with Bedrock information
- [ ] Update SETUP_GUIDE.md with AWS prerequisites
- [ ] Add AWS_BEDROCK_SETUP.md guide
- [ ] Update architecture diagrams

---

## Cost Analysis

### Current Cost (Ollama)
- **Infrastructure:** $0 (local)
- **Compute:** Free (using existing hardware)
- **Storage:** ~2GB disk space
- **Performance:** Slow (30-60s per query)

### New Cost (AWS Bedrock)
- **Model:** Llama 3 70B Instruct
- **Pricing:** ~$0.00265 per 1000 input tokens, ~$0.0035 per 1000 output tokens
- **Average Query:** ~500 input tokens + 200 output tokens
- **Cost per Query:** ~$0.002 (0.2 cents)
- **100 queries/day:** ~$0.20/day = $6/month
- **1000 queries/day:** ~$2/day = $60/month

**Recommendation:** Start with low volume, monitor costs

---

## Risk Assessment

### High Risk
- ❗ **AWS Credentials Exposure:** Store securely, never commit to git
- ❗ **Cost Overrun:** Set AWS billing alarms
- ❗ **API Rate Limits:** Implement retry logic with exponential backoff

### Medium Risk
- ⚠️ **Regional Availability:** Llama 3 70B not in all regions
- ⚠️ **Model Access:** May need to request access
- ⚠️ **Network Latency:** Depends on AWS region proximity

### Low Risk
- ℹ️ **Code Complexity:** Boto3 is well-documented
- ℹ️ **Backward Compatibility:** Can keep ollama as fallback

---

## Rollback Plan

If migration fails:

```bash
# 1. Revert code changes
git checkout HEAD~1 live_inference_pipeline/LLM-Connector/

# 2. Rebuild with old code
cd live_inference_pipeline
docker-compose build llm-connector

# 3. Restart services
docker-compose up -d

# 4. Verify ollama is working
docker logs ollama
docker logs llm-connector
```

---

## Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1: Prerequisites | 30 min | AWS setup, credentials, access |
| Phase 2: Code Changes | 1-2 hours | Update connector.py, dockerfile, env |
| Phase 3: Complete Rewrite | Included | Full implementation |
| Phase 4: Testing | 1 hour | Unit, integration, performance tests |
| Phase 5: Deployment | 30 min | Build, deploy, verify |
| Phase 6: Cleanup | 15 min | Remove ollama, update docs |
| **Total** | **3-4 hours** | End-to-end migration |

---

## Success Criteria

✅ **Functional:**
- [ ] LLM-connector starts without errors
- [ ] Queries return responses in 2-5 seconds
- [ ] Response quality is superior to Gemma 2B
- [ ] Database persistence works
- [ ] Error handling works correctly

✅ **Performance:**
- [ ] Response time < 5 seconds (vs 30-60s before)
- [ ] 10x faster than Ollama
- [ ] No timeout errors

✅ **Quality:**
- [ ] Responses are coherent and accurate
- [ ] Better legal reasoning than Gemma 2B
- [ ] Follows instructions correctly

✅ **Operational:**
- [ ] AWS costs are within budget
- [ ] No credential exposure
- [ ] Monitoring and alerts configured

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up AWS account** and request Bedrock access
3. **Create IAM user** with minimal permissions
4. **Test Bedrock access** with test script
5. **Implement code changes** following Phase 2-3
6. **Test thoroughly** before production deployment
7. **Monitor costs** closely in first week
8. **Update documentation** after successful migration

---

## Additional Resources

### AWS Documentation
- [AWS Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)
- [Llama 3 Model Card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-meta.html)
- [Boto3 Bedrock Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)

### Code Examples
- [AWS Bedrock Python Examples](https://github.com/aws-samples/amazon-bedrock-samples)
- [Boto3 Bedrock Runtime](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)

---

## Questions to Address Before Migration

1. **Do you have an AWS account with Bedrock access?**
2. **Which AWS region will you use?**
3. **What's your expected query volume?** (for cost estimation)
4. **Do you have AWS credentials ready?**
5. **Is there a budget limit for AWS costs?**
6. **Do you need to request Llama 3 70B access?**
7. **Should we keep Ollama as a fallback option?**

---

**Ready to proceed with migration? Let me know and I'll start implementing!**
