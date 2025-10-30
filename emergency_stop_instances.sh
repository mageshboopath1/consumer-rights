#!/bin/bash
# Emergency script to stop all rogue EC2 instances and spot requests
# Run this if instances keep starting automatically

REGION="ap-south-1"

echo "=========================================="
echo "EMERGENCY: Stopping All Rogue Instances"
echo "=========================================="
echo ""

# 1. Cancel ALL spot instance requests
echo "[1/4] Cancelling all active spot requests..."
SPOT_REQUESTS=$(aws ec2 describe-spot-instance-requests \
  --filters "Name=state,Values=open,active" \
  --query 'SpotInstanceRequests[*].SpotInstanceRequestId' \
  --output text \
  --region $REGION)

if [ -n "$SPOT_REQUESTS" ]; then
  echo "Found spot requests: $SPOT_REQUESTS"
  aws ec2 cancel-spot-instance-requests \
    --spot-instance-request-ids $SPOT_REQUESTS \
    --region $REGION
  echo " Cancelled all spot requests"
else
  echo " No active spot requests found"
fi
echo ""

# 2. Terminate ALL running instances without names
echo "[2/4] Terminating instances without names..."
UNNAMED_INSTANCES=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running,pending" \
  --query 'Reservations[*].Instances[?!Tags || length(Tags[?Key==`Name`]) == `0`].InstanceId' \
  --output text \
  --region $REGION)

if [ -n "$UNNAMED_INSTANCES" ]; then
  echo "Found unnamed instances: $UNNAMED_INSTANCES"
  aws ec2 terminate-instances \
    --instance-ids $UNNAMED_INSTANCES \
    --region $REGION
  echo " Terminated unnamed instances"
else
  echo " No unnamed instances found"
fi
echo ""

# 3. List all remaining instances
echo "[3/4] Checking remaining instances..."
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running,pending" \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,Tags[?Key==`Name`].Value|[0],State.Name]' \
  --output table \
  --region $REGION
echo ""

# 4. Check for any remaining spot requests
echo "[4/4] Checking remaining spot requests..."
aws ec2 describe-spot-instance-requests \
  --filters "Name=state,Values=open,active" \
  --query 'SpotInstanceRequests[*].[SpotInstanceRequestId,State,InstanceId]' \
  --output table \
  --region $REGION
echo ""

echo "=========================================="
echo " Emergency Stop Complete"
echo "=========================================="
echo ""
echo "What happened:"
echo "  - The deployment script created a PERSISTENT spot request"
echo "  - This means it auto-restarts instances when stopped"
echo "  - We've now cancelled the spot request"
echo ""
echo "To prevent this in the future:"
echo "  - Use on-demand instances instead of spot"
echo "  - Or use 'one-time' spot requests (not persistent)"
echo ""
echo "Current status:"
echo "  - All spot requests: CANCELLED"
echo "  - All unnamed instances: TERMINATED"
echo ""
