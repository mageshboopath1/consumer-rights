# EC2 vs Fargate Cost Analysis - Consumer Rights RAG System

**Date:** 2025-10-26  
**Comparison:** EC2 Instance vs ECS Fargate for Docker Compose Deployment

---

## 💰 COST COMPARISON SUMMARY

| Option | Monthly Cost | Setup Complexity | Management | Best For |
|--------|--------------|------------------|------------|----------|
| **EC2 On-Demand** | $30-35 | Medium | Manual | Always-on, predictable |
| **EC2 Spot** | $8-12 | Medium | Manual + interruptions | Cost-sensitive |
| **EC2 Reserved (1yr)** | $18-22 | Medium | Manual | Long-term commitment |
| **Fargate On-Demand** | $68 | Low | Automatic | Simplicity |
| **Fargate Spot** | $20 | Low | Automatic | Best balance |

**Winner for your use case: EC2 Spot Instance ($8-12/month)**

---

## 📊 DETAILED EC2 COST ANALYSIS

### Option 1: EC2 t3.small (Recommended)

**Specs:**
- 2 vCPU
- 2 GB RAM
- 20 GB EBS storage
- Perfect for your workload (currently using ~1.5 GB)

**Cost Breakdown:**

```
EC2 t3.small (ap-south-1):
  On-Demand: $0.0208/hour × 730 hours = $15.18/month
  Spot (70% discount): $0.0062/hour × 730 hours = $4.53/month
  Reserved 1yr (30% discount): $0.0146/hour × 730 hours = $10.66/month

EBS Storage (20 GB gp3):
  $0.088/GB/month × 20 GB = $1.76/month

Data Transfer:
  Bedrock API calls: Included
  Internet egress: ~$1/month

AWS Bedrock (Llama 3 70B):
  250 queries/day × $0.002 = $15/month (cost-limited)

TOTAL:
  On-Demand: $15.18 + $1.76 + $1 + $15 = $32.94/month
  Spot: $4.53 + $1.76 + $1 + $15 = $22.29/month
  Reserved: $10.66 + $1.76 + $1 + $15 = $28.42/month
```

### Option 2: EC2 t3.medium (If you need more headroom)

**Specs:**
- 2 vCPU
- 4 GB RAM
- 20 GB EBS storage

**Cost Breakdown:**

```
EC2 t3.medium (ap-south-1):
  On-Demand: $0.0416/hour × 730 hours = $30.37/month
  Spot (70% discount): $0.0125/hour × 730 hours = $9.13/month
  Reserved 1yr (30% discount): $0.0291/hour × 730 hours = $21.24/month

EBS Storage: $1.76/month
Data Transfer: $1/month
Bedrock: $15/month

TOTAL:
  On-Demand: $48.13/month
  Spot: $26.89/month
  Reserved: $39/month
```

### Option 3: EC2 t4g.small (ARM-based, cheapest)

**Specs:**
- 2 vCPU (ARM Graviton2)
- 2 GB RAM
- 20 GB EBS storage
- ⚠️ Requires ARM-compatible Docker images

**Cost Breakdown:**

```
EC2 t4g.small (ap-south-1):
  On-Demand: $0.0168/hour × 730 hours = $12.26/month
  Spot (70% discount): $0.0050/hour × 730 hours = $3.65/month
  Reserved 1yr (30% discount): $0.0118/hour × 730 hours = $8.61/month

EBS Storage: $1.76/month
Data Transfer: $1/month
Bedrock: $15/month

TOTAL:
  On-Demand: $30.02/month
  Spot: $20.41/month
  Reserved: $26.37/month
```

---

## 🆚 EC2 vs FARGATE COMPARISON

### Cost Comparison (Your Workload: 2 vCPU, 3 GB RAM)

| Option | Compute | Storage | Total/Month | Savings vs Fargate |
|--------|---------|---------|-------------|-------------------|
| **Fargate On-Demand** | $68.83 | $1.50 (EFS) | $70.33 | Baseline |
| **Fargate Spot** | $20.65 | $1.50 (EFS) | $22.15 | 69% |
| **EC2 t3.small On-Demand** | $15.18 | $1.76 (EBS) | $16.94 | 76% |
| **EC2 t3.small Spot** | $4.53 | $1.76 (EBS) | $6.29 | **91%** |
| **EC2 t3.small Reserved** | $10.66 | $1.76 (EBS) | $12.42 | 82% |
| **EC2 t4g.small Spot** | $3.65 | $1.76 (EBS) | $5.41 | **92%** |

**+ Bedrock costs ($15/month) apply to all options**

**Winner: EC2 t4g.small Spot = $20.41/month total (71% cheaper than Fargate)**

---

## ✅ EC2 ADVANTAGES

### 1. **Much Lower Cost**
- **EC2 Spot:** $6-9/month (vs $22/month Fargate Spot)
- **Savings:** $13-16/month (60-70% cheaper)
- **Annual Savings:** $156-192/year

### 2. **Full Control**
- SSH access to server
- Install any tools you need
- Debug directly on server
- Run docker-compose exactly as local

### 3. **Persistent Storage Included**
- EBS volume (no extra EFS cost)
- Faster than EFS
- Snapshots for backups

### 4. **Simpler Deployment**
- Just run `docker-compose up -d`
- No task definitions
- No ECR (can use Docker Hub or local images)
- Easier to update/restart

### 5. **Better for Development**
- Can test directly on server
- Easy to make changes
- No image rebuilds for small tweaks

---

## ⚠️ EC2 DISADVANTAGES

### 1. **Manual Management**
- You manage OS updates
- You handle server restarts
- You monitor disk space
- You configure security

### 2. **Single Point of Failure**
- If instance fails, service is down
- No automatic failover
- Need to manually restart

### 3. **No Auto-Scaling**
- Fixed capacity
- Can't handle sudden traffic spikes
- Need to manually resize

### 4. **Spot Interruptions** (if using Spot)
- Can be terminated with 2-minute notice
- ~5% chance per month
- Need to handle gracefully

### 5. **Security Responsibility**
- You patch OS
- You configure firewall
- You manage SSH keys

---

## 🎯 RECOMMENDED: EC2 t3.small Spot Instance

**Why this is the best choice for you:**

### Cost Analysis
```
EC2 t3.small Spot: $4.53/month
EBS 20 GB: $1.76/month
Data Transfer: $1/month
Bedrock: $15/month (cost-limited)
TOTAL: $22.29/month

vs Fargate Spot: $37/month
SAVINGS: $14.71/month (40% cheaper)
ANNUAL SAVINGS: $176.52/year
```

### Why Spot is Safe for You
1. **Low interruption rate:** ~5% per month in ap-south-1
2. **Quick recovery:** Docker Compose restarts automatically
3. **Data persists:** EBS volume survives interruptions
4. **Cost savings:** 70% cheaper than On-Demand

### Interruption Handling
```bash
# Add to user data script
#!/bin/bash
# Auto-restart docker-compose on boot
cat > /etc/systemd/system/docker-compose.service <<EOF
[Unit]
Description=Docker Compose Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/consumer-rights
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

systemctl enable docker-compose
systemctl start docker-compose
```

---

## 🚀 EC2 DEPLOYMENT STEPS

### Step 1: Launch EC2 Instance

```bash
# Launch t3.small Spot instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.small \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx \
  --instance-market-options '{
    "MarketType": "spot",
    "SpotOptions": {
      "MaxPrice": "0.0208",
      "SpotInstanceType": "persistent",
      "InstanceInterruptionBehavior": "stop"
    }
  }' \
  --block-device-mappings '[
    {
      "DeviceName": "/dev/sda1",
      "Ebs": {
        "VolumeSize": 20,
        "VolumeType": "gp3",
        "DeleteOnTermination": false
      }
    }
  ]' \
  --user-data file://user-data.sh \
  --region ap-south-1
```

### Step 2: User Data Script (Auto-setup)

```bash
#!/bin/bash
# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone your repository
cd /home/ubuntu
git clone https://github.com/mageshboopath1/consumer-rights.git
cd consumer-rights

# Create .env file
cat > live_inference_pipeline/.env <<EOF
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
DB_USER=postgres
DB_PASSWORD=your_password
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
EOF

# Start services
cd shared_services/chroma
docker-compose up -d

cd ../../live_inference_pipeline
docker-compose up -d

# Setup auto-restart on boot
cat > /etc/systemd/system/consumer-rights.service <<EOF
[Unit]
Description=Consumer Rights RAG System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/consumer-rights/live_inference_pipeline
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

systemctl enable consumer-rights
systemctl start consumer-rights
```

### Step 3: Connect and Verify

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<instance-public-ip>

# Check services
docker ps

# View logs
docker logs pii-filter
docker logs rag-core
docker logs llm-connector

# Test query
cd consumer-rights/live_inference_pipeline/CLI
python cli.py
```

---

## 🔒 EC2 SECURITY SETUP

### Security Group Configuration

```bash
# Create security group
aws ec2 create-security-group \
  --group-name consumer-rights-sg \
  --description "Consumer Rights RAG System" \
  --vpc-id vpc-xxxxx

# Allow SSH (your IP only)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32

# Allow HTTP (optional - for web interface)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Allow HTTPS (optional)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### IAM Role for Bedrock Access

```bash
# Create IAM role for EC2
aws iam create-role \
  --role-name EC2BedrockRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach Bedrock policy
aws iam attach-role-policy \
  --role-name EC2BedrockRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name EC2BedrockProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2BedrockProfile \
  --role-name EC2BedrockRole

# Attach to instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-xxxxx \
  --iam-instance-profile Name=EC2BedrockProfile
```

---

## 📊 COST OPTIMIZATION STRATEGIES

### 1. Use Spot Instances (70% savings)
```
On-Demand: $15.18/month
Spot: $4.53/month
Savings: $10.65/month
```

### 2. Use Reserved Instances (30% savings)
```
1-year commitment: $10.66/month (vs $15.18)
3-year commitment: $7.30/month (vs $15.18)
Best for: Long-term production
```

### 3. Use ARM-based t4g instances (20% cheaper)
```
t3.small: $15.18/month
t4g.small: $12.26/month
Savings: $2.92/month
Note: Requires ARM Docker images
```

### 4. Stop instance when not needed
```bash
# Stop instance (keeps EBS, no compute charges)
aws ec2 stop-instances --instance-ids i-xxxxx

# Start when needed
aws ec2 start-instances --instance-ids i-xxxxx

# Cost: Only pay for EBS ($1.76/month)
```

### 5. Use smaller EBS volume
```
20 GB: $1.76/month
10 GB: $0.88/month
Savings: $0.88/month
```

---

## 🎯 FINAL RECOMMENDATION

### For Your Use Case (Demo Platform, 250 queries/day):

**Best Option: EC2 t3.small Spot Instance**

**Monthly Cost Breakdown:**
```
EC2 t3.small Spot: $4.53
EBS 20 GB: $1.76
Data Transfer: $1.00
Bedrock (cost-limited): $15.00
TOTAL: $22.29/month
```

**vs Fargate Spot: $37/month**
**SAVINGS: $14.71/month (40% cheaper)**
**ANNUAL SAVINGS: $176.52/year**

---

## ✅ EC2 vs FARGATE DECISION MATRIX

| Factor | EC2 Spot | Fargate Spot | Winner |
|--------|----------|--------------|--------|
| **Cost** | $22/month | $37/month | 🏆 EC2 |
| **Setup Time** | 30 min | 2-3 hours | 🏆 EC2 |
| **Management** | Manual | Automatic | 🏆 Fargate |
| **Flexibility** | High | Low | 🏆 EC2 |
| **Reliability** | 95% | 99.9% | 🏆 Fargate |
| **Scalability** | Manual | Automatic | 🏆 Fargate |
| **Updates** | Manual | Easy | 🏆 Fargate |
| **Debugging** | Easy (SSH) | Harder | 🏆 EC2 |

**For Demo/MVP: EC2 wins (cheaper, simpler, more control)**
**For Production: Fargate wins (managed, scalable, reliable)**

---

## 🚀 QUICK START: EC2 DEPLOYMENT

### Option 1: Automated (Recommended)

I can create a script that:
1. Launches EC2 Spot instance
2. Installs Docker & Docker Compose
3. Clones your repo
4. Starts all services
5. Configures auto-restart

**Time: 5 minutes**

### Option 2: Manual

1. Launch EC2 instance (AWS Console)
2. SSH and install Docker
3. Clone repo and run docker-compose
4. Configure security

**Time: 30 minutes**

---

## 📋 EC2 DEPLOYMENT CHECKLIST

- [ ] Launch EC2 t3.small Spot instance
- [ ] Configure security group (SSH, HTTP)
- [ ] Attach IAM role for Bedrock
- [ ] SSH to instance
- [ ] Install Docker & Docker Compose
- [ ] Clone repository
- [ ] Create .env file with credentials
- [ ] Start shared services (chroma, postgres)
- [ ] Start live inference pipeline
- [ ] Test with sample query
- [ ] Configure auto-restart on boot
- [ ] Setup CloudWatch monitoring (optional)
- [ ] Configure backups (EBS snapshots)

---

## 💡 MY RECOMMENDATION

**Start with EC2 t3.small Spot for $22/month**

**Reasons:**
1. ✅ **40% cheaper** than Fargate ($22 vs $37)
2. ✅ **Simpler deployment** (just docker-compose)
3. ✅ **More control** (SSH access, easy debugging)
4. ✅ **Perfect for demo/MVP** phase
5. ✅ **Easy to migrate** to Fargate later if needed

**When to switch to Fargate:**
- When you need high availability (99.9% uptime)
- When you need auto-scaling
- When you go to production with real users
- When you want zero server management

---

**Would you like me to create:**
1. **EC2 Deployment Script** (automated setup)
2. **User Data Script** (auto-install everything)
3. **Both** (complete automation)

**Let me know and I'll create it!**
