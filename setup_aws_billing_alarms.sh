#!/bin/bash
# Setup AWS Billing Alarms for Cost Protection
# Run this script after IAM permissions propagate (wait 5-10 minutes)

echo " Setting up AWS Billing Alarms..."
echo ""

# Wait for IAM propagation
echo "Waiting for IAM permissions to propagate (30 seconds)..."
sleep 30

# Create Daily Cost Alarm ($0.50)
echo "1⃣  Creating daily cost alarm ($0.50 threshold)..."
aws cloudwatch put-metric-alarm \
  --alarm-name "Bedrock-Daily-Cost-Alert" \
  --alarm-description "Alert when daily Bedrock costs exceed $0.50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 0.50 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value=AmazonBedrock \
  --region us-east-1

if [ $? -eq 0 ]; then
    echo " Daily alarm created successfully"
else
    echo " Failed to create daily alarm"
    exit 1
fi

# Create Monthly Cost Alarm ($5.00)
echo ""
echo "2⃣  Creating monthly cost alarm ($5.00 threshold)..."
aws cloudwatch put-metric-alarm \
  --alarm-name "Bedrock-Monthly-Cost-Alert" \
  --alarm-description "Alert when monthly Bedrock costs exceed $5" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 5.00 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value=AmazonBedrock \
  --region us-east-1

if [ $? -eq 0 ]; then
    echo " Monthly alarm created successfully"
else
    echo " Failed to create monthly alarm"
    exit 1
fi

# Verify alarms
echo ""
echo "3⃣  Verifying alarms..."
aws cloudwatch describe-alarms \
  --alarm-names "Bedrock-Daily-Cost-Alert" "Bedrock-Monthly-Cost-Alert" \
  --region us-east-1 \
  --query 'MetricAlarms[*].[AlarmName,Threshold,StateValue]' \
  --output table

echo ""
echo " AWS Billing Alarms Setup Complete!"
echo ""
echo " Alarm Summary:"
echo "   - Daily Alert: $0.50 (250 queries)"
echo "   - Monthly Alert: $5.00 (2500 queries)"
echo ""
echo "  IMPORTANT: Add SNS email notifications"
echo "   1. Go to: https://console.aws.amazon.com/cloudwatch/"
echo "   2. Click on 'Alarms' → Select alarm"
echo "   3. Add 'Actions' → 'Send notification to...'"
echo "   4. Create SNS topic and add your email"
echo ""
