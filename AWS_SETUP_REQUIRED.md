# AWS Setup Required - URGENT

**Status:** IAM Permissions Missing  
**User:** arn:aws:iam::692461731109:user/Jesus  
**Issue:** No permission to invoke Bedrock models

---

## Quick Fix (5 minutes)

### Option 1: AWS Console (Recommended for Root Account)

1. **Go to IAM Console:**
   - https://console.aws.amazon.com/iam/

2. **Find User "Jesus":**
   - Click "Users" in left sidebar
   - Click on "Jesus"

3. **Add Bedrock Permissions:**
   - Click "Add permissions" → "Attach policies directly"
   - Search for: `AmazonBedrockFullAccess`
   - Check the box
   - Click "Add permissions"

**OR Create Custom Policy (More Secure):**

Click "Add permissions" → "Create inline policy" → JSON tab:

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
      "Resource": "arn:aws:bedrock:ap-south-1::foundation-model/*"
    }
  ]
}
```

Name it: `BedrockInvokeAccess`

---

### Option 2: AWS CLI (Faster)

```bash
# Attach managed policy
aws iam attach-user-policy \
  --user-name Jesus \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Verify
aws iam list-attached-user-policies --user-name Jesus
```

---

## Check Model Access in Region

**Important:** Llama 3 70B may not be available in `ap-south-1` (Mumbai)

### Check Available Regions:

```bash
# List available models in ap-south-1
aws bedrock list-foundation-models --region ap-south-1 \
  --query 'modelSummaries[?contains(modelId, `llama`)].{ModelId:modelId, Name:modelName}' \
  --output table

# If empty, try us-east-1
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `llama`)].{ModelId:modelId, Name:modelName}' \
  --output table
```

### If Llama 3 70B Not Available in ap-south-1:

**Option A:** Use `us-east-1` (N. Virginia) - Most models available
**Option B:** Use smaller model in ap-south-1 (if available)

---

## After Fixing Permissions

### Test Again:

```bash
cd /Users/mageshboopathi/Desktop/final/consumer-rights
python3 test_bedrock.py
```

**Expected Output:**
```
✅ SUCCESS! AWS Bedrock is configured correctly!
```

---

## Alternative: Use Smaller Model (If 70B Not Available)

If Llama 3 70B is not in ap-south-1, you can use:

1. **Llama 3 8B Instruct** (faster, cheaper, still good quality)
   - Model ID: `meta.llama3-8b-instruct-v1:0`
   - Cost: ~70% cheaper than 70B
   - Speed: 2-3x faster

2. **Update .env file:**
   ```bash
   BEDROCK_MODEL_ID=meta.llama3-8b-instruct-v1:0
   ```

---

## Cost Monitoring Setup

### Set Billing Alarm ($5 budget):

```bash
# Create SNS topic for alerts
aws sns create-topic --name bedrock-billing-alerts --region us-east-1

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:692461731109:bedrock-billing-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "Bedrock-Budget-5USD" \
  --alarm-description "Alert when Bedrock costs exceed $5" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 5.0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value=AmazonBedrock \
  --alarm-actions arn:aws:sns:us-east-1:692461731109:bedrock-billing-alerts \
  --region us-east-1
```

---

## Next Steps

1. ✅ Fix IAM permissions (5 min)
2. ✅ Verify model availability in ap-south-1
3. ✅ Run test_bedrock.py successfully
4. ✅ Set up billing alarm
5. ✅ Deploy the application

---

## Questions?

**Q: Which region should I use?**  
A: If Llama 3 70B not in ap-south-1, use us-east-1 (most reliable)

**Q: Will latency be high from India to us-east-1?**  
A: ~200-300ms extra, but still faster than local Ollama (30-60s)

**Q: Can I use 8B instead of 70B?**  
A: Yes! 8B is faster, cheaper, and still very good quality

---

**Run this after fixing permissions:**
```bash
python3 test_bedrock.py
```
