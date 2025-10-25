#!/bin/bash
# EC2 Spot Instance Deployment Script for Consumer Rights RAG System
# Automated deployment - just run this script!

set -e  # Exit on error

echo "=========================================="
echo "Consumer Rights RAG - EC2 Deployment"
echo "=========================================="
echo ""

# Configuration
REGION="ap-south-1"
INSTANCE_TYPE="t3.small"
AMI_ID="ami-087d1c9a513324697"  # Ubuntu 22.04 LTS in ap-south-1 (latest)
KEY_NAME="consumer-rights-key"
SECURITY_GROUP_NAME="consumer-rights-sg"
VOLUME_SIZE=20
MAX_SPOT_PRICE="0.0208"  # On-demand price (will get 70% discount)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check AWS CLI
print_step "Checking AWS CLI..."
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $ACCOUNT_ID"

# Get default VPC
print_step "Getting default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)
if [ "$VPC_ID" == "None" ]; then
    print_error "No default VPC found. Please create one first."
    exit 1
fi
print_info "VPC ID: $VPC_ID"

# Get subnet
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text --region $REGION)
print_info "Subnet ID: $SUBNET_ID"

# Create Key Pair if not exists
print_step "Creating SSH key pair..."
if aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &> /dev/null; then
    print_info "Key pair already exists"
else
    aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text --region $REGION > ${KEY_NAME}.pem
    chmod 400 ${KEY_NAME}.pem
    print_info "Key pair created: ${KEY_NAME}.pem"
fi

# Create Security Group
print_step "Creating security group..."
if aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --region $REGION &> /dev/null 2>&1; then
    SG_ID=$(aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --query "SecurityGroups[0].GroupId" --output text --region $REGION)
    print_info "Security group already exists: $SG_ID"
else
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Consumer Rights RAG System" \
        --vpc-id $VPC_ID \
        --query 'GroupId' \
        --output text \
        --region $REGION)
    print_info "Security group created: $SG_ID"
    
    # Get your public IP
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    print_info "Your IP: $MY_IP"
    
    # Allow SSH from your IP
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr ${MY_IP}/32 \
        --region $REGION
    print_info "SSH access allowed from your IP"
    
    # Allow HTTP (optional - for web interface)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    print_info "HTTP access allowed"
fi

# Create IAM Role for Bedrock access
print_step "Creating IAM role for Bedrock access..."
ROLE_NAME="EC2BedrockRole"
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    print_info "IAM role already exists"
else
    # Create trust policy
    cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
    
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json
    
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
    
    # Create instance profile
    aws iam create-instance-profile --instance-profile-name ${ROLE_NAME}Profile
    aws iam add-role-to-instance-profile --instance-profile-name ${ROLE_NAME}Profile --role-name $ROLE_NAME
    
    print_info "IAM role created and attached"
    print_info "Waiting 10 seconds for IAM propagation..."
    sleep 10
    
    rm trust-policy.json
fi

# Prompt for AWS credentials
print_step "AWS Bedrock Credentials Setup"
echo ""
read -p "Enter AWS Access Key ID for Bedrock: " AWS_ACCESS_KEY
read -sp "Enter AWS Secret Access Key for Bedrock: " AWS_SECRET_KEY
echo ""
read -p "Enter PostgreSQL password: " DB_PASSWORD
echo ""

# Create user data script
print_step "Creating user data script..."
cat > user-data.sh <<EOF
#!/bin/bash
set -e

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting deployment at \$(date)"

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install git
apt-get install -y git

# Clone repository
cd /home/ubuntu
git clone https://github.com/mageshboopath1/consumer-rights.git
chown -R ubuntu:ubuntu consumer-rights

# Create .env files
cd consumer-rights

# Shared services .env
cat > shared_services/chroma/.env <<ENVEOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=consumer_rights
ENVEOF

# Live inference .env
cat > live_inference_pipeline/.env <<ENVEOF
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_KEY}
BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
BEDROCK_MAX_TOKENS=512
BEDROCK_TEMPERATURE=0.7
DB_HOST=postgres
DB_USER=postgres
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=consumer_rights
ENVEOF

# Create shared network
docker network create shared_network || true

# Start shared services
cd shared_services/chroma
docker-compose up -d

# Wait for services to be ready
echo "Waiting for PostgreSQL and ChromaDB to start..."
sleep 30

# Start live inference pipeline
cd ../../live_inference_pipeline
docker-compose up -d

# Wait for all services
echo "Waiting for all services to start..."
sleep 30

# Create systemd service for auto-restart
cat > /etc/systemd/system/consumer-rights.service <<SERVICEEOF
[Unit]
Description=Consumer Rights RAG System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
WorkingDirectory=/home/ubuntu/consumer-rights

ExecStartPre=/bin/sleep 10
ExecStart=/bin/bash -c 'cd shared_services/chroma && /usr/local/bin/docker-compose up -d && sleep 20 && cd ../../live_inference_pipeline && /usr/local/bin/docker-compose up -d'
ExecStop=/bin/bash -c 'cd /home/ubuntu/consumer-rights/live_inference_pipeline && /usr/local/bin/docker-compose down && cd ../shared_services/chroma && /usr/local/bin/docker-compose down'

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable consumer-rights
systemctl start consumer-rights

echo "Deployment completed at \$(date)"
echo "All services are running!"
EOF

# Launch EC2 Spot Instance
print_step "Launching EC2 Spot instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --subnet-id $SUBNET_ID \
    --iam-instance-profile Name=${ROLE_NAME}Profile \
    --instance-market-options "{
        \"MarketType\": \"spot\",
        \"SpotOptions\": {
            \"MaxPrice\": \"$MAX_SPOT_PRICE\",
            \"SpotInstanceType\": \"one-time\",
            \"InstanceInterruptionBehavior\": \"terminate\"
        }
    }" \
    --block-device-mappings "[
        {
            \"DeviceName\": \"/dev/sda1\",
            \"Ebs\": {
                \"VolumeSize\": $VOLUME_SIZE,
                \"VolumeType\": \"gp3\",
                \"DeleteOnTermination\": false
            }
        }
    ]" \
    --user-data file://user-data.sh \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=consumer-rights-rag}]" \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region $REGION)

print_info "Instance ID: $INSTANCE_ID"

# Wait for instance to be running
print_step "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $REGION)

print_info "Instance is running!"
print_info "Public IP: $PUBLIC_IP"

# Clean up
rm user-data.sh

echo ""
echo "=========================================="
echo -e "${GREEN}DEPLOYMENT IN PROGRESS${NC}"
echo "=========================================="
echo ""
echo "Instance Details:"
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP: $PUBLIC_IP"
echo "  Type: $INSTANCE_TYPE (Spot)"
echo "  Region: $REGION"
echo ""
echo "SSH Access:"
echo "  ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo ""
echo "The system is installing Docker and starting services."
echo "This will take about 5-10 minutes."
echo ""
echo "To monitor progress:"
echo "  ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo "  tail -f /var/log/user-data.log"
echo ""
echo "To check services:"
echo "  docker ps"
echo "  docker logs pii-filter"
echo "  docker logs rag-core"
echo ""
echo "=========================================="
echo -e "${GREEN}NEXT STEPS${NC}"
echo "=========================================="
echo ""
echo "1. Wait 5-10 minutes for installation to complete"
echo ""
echo "2. SSH to instance:"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo ""
echo "3. Check services are running:"
echo "   docker ps"
echo ""
echo "4. Test the system:"
echo "   cd consumer-rights/live_inference_pipeline/CLI"
echo "   python cli.py"
echo ""
echo "5. View logs:"
echo "   docker logs -f pii-filter"
echo ""
echo "=========================================="
echo -e "${GREEN}COST INFORMATION${NC}"
echo "=========================================="
echo ""
echo "Estimated Monthly Cost:"
echo "  EC2 Spot: ~\$4.53/month"
echo "  EBS 20GB: ~\$1.76/month"
echo "  Data Transfer: ~\$1/month"
echo "  Bedrock (250 queries/day): ~\$15/month"
echo "  ────────────────────────────────"
echo "  TOTAL: ~\$22.29/month"
echo ""
echo "=========================================="
echo ""
echo "Deployment script completed!"
echo "Instance is being configured..."
echo ""
