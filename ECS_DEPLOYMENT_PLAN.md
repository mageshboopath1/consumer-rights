# AWS ECS Deployment Plan - Consumer Rights RAG System

**Date:** 2025-10-26  
**Status:** Planning Phase  

---

## 📊 COMPUTE REQUIREMENTS ANALYSIS

### Current Resource Usage (Local Docker)

| Service | CPU % | Memory | Image Size | Priority |
|---------|-------|--------|------------|----------|
| **Production Services** ||||
| pii-filter | 0.00% | 11.5 MB | ~50 MB | Critical |
| rag-core | 0.10% | 356 MB | ~500 MB | Critical |
| llm-connector | 0.00% | 13.2 MB | ~50 MB | Critical |
| psql_worker | 0.00% | 31.5 MB | ~50 MB | Critical |
| rabbitmq | 0.53% | 141.8 MB | ~200 MB | Critical |
| chroma_service | 0.05% | 32.9 MB | ~300 MB | Critical |
| postgres_service | 0.10% | 356 MB | ~400 MB | Critical |
| **Data Pipeline** ||||
| chunker-service | 0.00% | 24.7 MB | ~500 MB | Optional |
| embedder-service | 0.53% | 109 MB | ~1.5 GB | Optional |
| airflow-webserver | 0.54% | 587.5 MB | ~1 GB | Optional |
| airflow-scheduler | 2.58% | 369.6 MB | ~1 GB | Optional |
| postgres (airflow) | 0.93% | 28.6 MB | ~400 MB | Optional |

### Resource Summary

**Production Services (Always Running):**
- **Total CPU:** ~1% idle, ~5-10% under load
- **Total Memory:** ~950 MB idle, ~1.5 GB under load
- **Storage:** ~1.5 GB for images + data volumes

**Data Pipeline (Run Periodically):**
- **Total CPU:** ~4% idle, ~50% during processing
- **Total Memory:** ~1.1 GB idle, ~2.5 GB during processing
- **Storage:** ~3.5 GB for images

---

## 🎯 RECOMMENDED ECS ARCHITECTURE

### Option 1: MINIMAL (Recommended for Demo - $15-25/month)

**Single ECS Cluster with Fargate**

```
ECS Cluster: consumer-rights-prod
├── Task Definition: live-inference (Fargate)
│   ├── pii-filter (256 CPU, 256 MB)
│   ├── rag-core (256 CPU, 512 MB)
│   ├── llm-connector (256 CPU, 256 MB)
│   ├── psql_worker (256 CPU, 256 MB)
│   └── rabbitmq (512 CPU, 512 MB)
│
├── RDS PostgreSQL (db.t3.micro - $15/month)
│   └── Single database for both prod + airflow
│
└── EFS (Elastic File System - $3/month)
    └── ChromaDB data persistence
```

**Compute:**
- **Fargate Task:** 1.5 vCPU, 2 GB RAM
- **Cost:** ~$22/month (730 hours)
- **RDS:** db.t3.micro (1 vCPU, 1 GB) - $15/month
- **EFS:** 1 GB storage - $0.30/month
- **Total:** ~$37/month + Bedrock costs

**Data Pipeline:**
- Run as separate Fargate task (on-demand)
- Triggered manually or via EventBridge
- Cost: ~$0.10 per run

---

### Option 2: OPTIMIZED (Better Performance - $40-60/month)

**ECS Cluster with EC2 Spot Instances**

```
ECS Cluster: consumer-rights-prod
├── EC2 Spot Instance: t3.small (2 vCPU, 2 GB)
│   ├── Task: live-inference
│   │   ├── pii-filter
│   │   ├── rag-core
│   │   ├── llm-connector
│   │   ├── psql_worker
│   │   └── rabbitmq
│   │
│   └── Task: data-pipeline (on-demand)
│       ├── chunker
│       ├── embedder
│       └── airflow-scheduler
│
├── RDS PostgreSQL (db.t3.micro - $15/month)
│
└── EBS Volume (20 GB - $2/month)
    └── ChromaDB + logs
```

**Compute:**
- **EC2 Spot:** t3.small - $5-8/month (70% discount)
- **RDS:** db.t3.micro - $15/month
- **EBS:** 20 GB - $2/month
- **ALB:** Application Load Balancer - $16/month
- **Total:** ~$38-41/month + Bedrock costs

---

### Option 3: PRODUCTION (High Availability - $100-150/month)

**Multi-AZ ECS with Auto-Scaling**

```
ECS Cluster: consumer-rights-prod
├── Auto Scaling Group (2 AZs)
│   ├── EC2: t3.medium (2 vCPU, 4 GB) x 2
│   └── Tasks: 2 replicas of live-inference
│
├── RDS PostgreSQL Multi-AZ (db.t3.small)
│   └── Automated backups, failover
│
├── ElastiCache Redis (cache.t3.micro)
│   └── Query caching, rate limiting
│
├── EFS (Multi-AZ)
│   └── ChromaDB persistence
│
└── CloudWatch + X-Ray
    └── Monitoring & tracing
```

**Compute:**
- **EC2:** 2x t3.medium - $60/month
- **RDS Multi-AZ:** db.t3.small - $30/month
- **ElastiCache:** cache.t3.micro - $12/month
- **EFS:** 5 GB - $1.50/month
- **ALB:** $16/month
- **CloudWatch:** $10/month
- **Total:** ~$130/month + Bedrock costs

---

## 💡 RECOMMENDED: Option 1 (Minimal Fargate)

**Why?**
- ✅ Lowest cost for demo platform
- ✅ No server management
- ✅ Auto-scaling built-in
- ✅ Pay only for what you use
- ✅ Perfect for 250 queries/day

**Cost Breakdown:**
```
ECS Fargate (1.5 vCPU, 2 GB):
  - vCPU: 1.5 × $0.04048/hour × 730 hours = $44.33
  - Memory: 2 GB × $0.004445/GB/hour × 730 hours = $6.49
  - Total: $50.82/month

RDS db.t3.micro:
  - Instance: $15/month
  - Storage (20 GB): $2.30/month
  - Total: $17.30/month

EFS (1 GB):
  - Storage: $0.30/month

Data Transfer:
  - Bedrock API calls: Included
  - Internet egress: ~$1/month (minimal)

TOTAL: ~$70/month
```

**With Reserved Capacity (1-year):**
- Fargate Savings: 20% = $40.66/month
- RDS Reserved: 30% = $12.11/month
- **Total: ~$54/month**

---

## 🏗️ ECS DEPLOYMENT ARCHITECTURE

### Network Architecture

```
VPC: consumer-rights-vpc (10.0.0.0/16)
│
├── Public Subnets (2 AZs)
│   ├── 10.0.1.0/24 (us-east-1a)
│   ├── 10.0.2.0/24 (us-east-1b)
│   └── Resources:
│       ├── Application Load Balancer
│       └── NAT Gateway (optional)
│
├── Private Subnets (2 AZs)
│   ├── 10.0.11.0/24 (us-east-1a)
│   ├── 10.0.12.0/24 (us-east-1b)
│   └── Resources:
│       ├── ECS Tasks (Fargate)
│       ├── RDS PostgreSQL
│       └── EFS Mount Targets
│
└── Security Groups
    ├── ALB-SG (80, 443 from 0.0.0.0/0)
    ├── ECS-SG (All from ALB-SG)
    ├── RDS-SG (5432 from ECS-SG)
    └── EFS-SG (2049 from ECS-SG)
```

### Service Communication

```
Internet → ALB → ECS Tasks
                 ├── pii-filter → RabbitMQ
                 ├── rag-core → ChromaDB (EFS) → RabbitMQ
                 ├── llm-connector → AWS Bedrock → RabbitMQ
                 └── psql_worker → RDS PostgreSQL
```

---

## 📋 DETAILED RESOURCE SPECIFICATIONS

### ECS Task Definition: live-inference

```json
{
  "family": "consumer-rights-live-inference",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1536",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "pii-filter",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "environment": [
        {"name": "PYTHONUNBUFFERED", "value": "1"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "pii-filter"
        }
      }
    },
    {
      "name": "rag-core",
      "cpu": 256,
      "memory": 512,
      "essential": true,
      "mountPoints": [{
        "sourceVolume": "chroma-data",
        "containerPath": "/data"
      }],
      "environment": [
        {"name": "CHROMA_HOST", "value": "localhost"},
        {"name": "CHROMA_PORT", "value": "8000"}
      ]
    },
    {
      "name": "llm-connector",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "secrets": [
        {"name": "AWS_ACCESS_KEY_ID", "valueFrom": "arn:aws:secretsmanager:..."},
        {"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ]
    },
    {
      "name": "psql-worker",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "secrets": [
        {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "environment": [
        {"name": "DB_HOST", "value": "consumer-rights.xxxxx.ap-south-1.rds.amazonaws.com"}
      ]
    },
    {
      "name": "rabbitmq",
      "image": "rabbitmq:3-management",
      "cpu": 512,
      "memory": 512,
      "essential": true,
      "portMappings": [
        {"containerPort": 5672},
        {"containerPort": 15672}
      ]
    }
  ],
  "volumes": [
    {
      "name": "chroma-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-xxxxx",
        "transitEncryption": "ENABLED"
      }
    }
  ]
}
```

### RDS Configuration

```yaml
Engine: postgres
Version: 13.12
Instance: db.t3.micro
  vCPU: 2 (burstable)
  RAM: 1 GB
  Storage: 20 GB GP3
  IOPS: 3000 (baseline)
  
Multi-AZ: No (for cost savings)
Backup: 7 days retention
Encryption: Yes (at rest)
Auto Minor Version Upgrade: Yes

Parameter Group:
  max_connections: 100
  shared_buffers: 256MB
  work_mem: 4MB
```

### EFS Configuration

```yaml
Performance Mode: General Purpose
Throughput Mode: Bursting
  - Baseline: 50 MB/s per TB
  - Burst: 100 MB/s
  
Lifecycle Policy: 
  - Transition to IA: 30 days
  
Encryption: Yes (at rest + in transit)
Backup: AWS Backup (daily)
```

---

## 🔧 DEPLOYMENT STEPS

### Phase 1: Infrastructure Setup (Day 1)

**1. Create VPC & Networking**
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region ap-south-1

# Create subnets (2 public, 2 private)
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone ap-south-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone ap-south-1b
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.11.0/24 --availability-zone ap-south-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.12.0/24 --availability-zone ap-south-1b

# Create Internet Gateway
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway --vpc-id vpc-xxx --internet-gateway-id igw-xxx

# Create route tables
# ... (detailed in deployment script)
```

**2. Create Security Groups**
```bash
# ALB Security Group
aws ec2 create-security-group \
  --group-name consumer-rights-alb-sg \
  --description "ALB security group" \
  --vpc-id vpc-xxx

# ECS Security Group
aws ec2 create-security-group \
  --group-name consumer-rights-ecs-sg \
  --description "ECS tasks security group" \
  --vpc-id vpc-xxx

# RDS Security Group
aws ec2 create-security-group \
  --group-name consumer-rights-rds-sg \
  --description "RDS security group" \
  --vpc-id vpc-xxx

# EFS Security Group
aws ec2 create-security-group \
  --group-name consumer-rights-efs-sg \
  --description "EFS security group" \
  --vpc-id vpc-xxx
```

**3. Create RDS Instance**
```bash
aws rds create-db-instance \
  --db-instance-identifier consumer-rights-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 13.12 \
  --master-username postgres \
  --master-user-password <secure-password> \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name consumer-rights-subnet-group \
  --backup-retention-period 7 \
  --storage-encrypted \
  --region ap-south-1
```

**4. Create EFS**
```bash
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --region ap-south-1

aws efs create-mount-target \
  --file-system-id fs-xxx \
  --subnet-id subnet-xxx \
  --security-groups sg-xxx
```

**5. Store Secrets in Secrets Manager**
```bash
aws secretsmanager create-secret \
  --name consumer-rights/db-password \
  --secret-string '{"password":"<secure-password>"}' \
  --region ap-south-1

aws secretsmanager create-secret \
  --name consumer-rights/aws-credentials \
  --secret-string '{"access_key":"xxx","secret_key":"xxx"}' \
  --region ap-south-1
```

---

### Phase 2: Container Setup (Day 2)

**1. Create ECR Repositories**
```bash
aws ecr create-repository --repository-name consumer-rights/pii-filter --region ap-south-1
aws ecr create-repository --repository-name consumer-rights/rag-core --region ap-south-1
aws ecr create-repository --repository-name consumer-rights/llm-connector --region ap-south-1
aws ecr create-repository --repository-name consumer-rights/psql-worker --region ap-south-1
```

**2. Build & Push Images**
```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com

# Build and push each service
cd live_inference_pipeline/PII
docker build -t consumer-rights/pii-filter .
docker tag consumer-rights/pii-filter:latest <account-id>.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest
docker push <account-id>.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest

# Repeat for rag-core, llm-connector, psql-worker
```

**3. Initialize Database**
```bash
# Connect to RDS
psql -h consumer-rights-db.xxxxx.ap-south-1.rds.amazonaws.com -U postgres -d consumer_rights

# Run init script
\i shared_services/chroma/postgres_init/init.sql
```

---

### Phase 3: ECS Deployment (Day 3)

**1. Create ECS Cluster**
```bash
aws ecs create-cluster \
  --cluster-name consumer-rights-prod \
  --region ap-south-1
```

**2. Register Task Definition**
```bash
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region ap-south-1
```

**3. Create Application Load Balancer**
```bash
aws elbv2 create-load-balancer \
  --name consumer-rights-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --region ap-south-1

aws elbv2 create-target-group \
  --name consumer-rights-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-path /health \
  --region ap-south-1
```

**4. Create ECS Service**
```bash
aws ecs create-service \
  --cluster consumer-rights-prod \
  --service-name live-inference \
  --task-definition consumer-rights-live-inference:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=pii-filter,containerPort=80" \
  --region ap-south-1
```

---

### Phase 4: Monitoring & Optimization (Day 4-7)

**1. Setup CloudWatch Alarms**
```bash
# CPU Utilization
aws cloudwatch put-metric-alarm \
  --alarm-name consumer-rights-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# Memory Utilization
aws cloudwatch put-metric-alarm \
  --alarm-name consumer-rights-high-memory \
  --alarm-description "Alert when Memory > 80%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

**2. Enable Container Insights**
```bash
aws ecs update-cluster-settings \
  --cluster consumer-rights-prod \
  --settings name=containerInsights,value=enabled \
  --region ap-south-1
```

**3. Setup Auto-Scaling**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/consumer-rights-prod/live-inference \
  --min-capacity 1 \
  --max-capacity 3

aws application-autoscaling put-scaling-policy \
  --policy-name consumer-rights-cpu-scaling \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/consumer-rights-prod/live-inference \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

---

## 💰 COST OPTIMIZATION STRATEGIES

### 1. Use Fargate Spot (50-70% savings)
```json
{
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE_SPOT",
      "weight": 2,
      "base": 0
    },
    {
      "capacityProvider": "FARGATE",
      "weight": 1,
      "base": 1
    }
  ]
}
```

**Savings:** $25-35/month on compute

### 2. Use RDS Reserved Instances (30% savings)
- 1-year commitment: $12/month (vs $17/month)
- **Savings:** $5/month

### 3. Use Savings Plans (20% savings)
- Fargate Savings Plan: $40/month (vs $50/month)
- **Savings:** $10/month

### 4. Optimize Data Transfer
- Use VPC Endpoints for AWS services (free)
- Enable CloudFront for static content
- **Savings:** $5-10/month

### 5. Schedule Data Pipeline
- Run only when needed (vs 24/7)
- Use EventBridge for scheduling
- **Savings:** $20-30/month

**Total Potential Savings:** $65-90/month

**Optimized Monthly Cost:** $35-45/month (vs $70/month)

---

## 📊 COST COMPARISON

| Component | Minimal | Optimized | Production |
|-----------|---------|-----------|------------|
| **Compute** ||||
| ECS Fargate | $50 | - | - |
| EC2 Spot | - | $8 | $60 |
| **Database** ||||
| RDS | $17 | $17 | $30 |
| **Storage** ||||
| EFS/EBS | $0.30 | $2 | $2 |
| **Networking** ||||
| ALB | - | $16 | $16 |
| Data Transfer | $1 | $2 | $5 |
| **Monitoring** ||||
| CloudWatch | Included | $5 | $10 |
| **Caching** ||||
| ElastiCache | - | - | $12 |
| **SUBTOTAL** | **$68** | **$50** | **$135** |
| **With Optimization** | **$40** | **$35** | **$100** |
| **+ Bedrock** | **+$5** | **+$5** | **+$5** |
| **TOTAL/MONTH** | **$45** | **$40** | **$105** |

---

## 🎯 RECOMMENDED DEPLOYMENT TIMELINE

### Week 1: Infrastructure
- **Day 1-2:** VPC, subnets, security groups
- **Day 3-4:** RDS, EFS setup
- **Day 5:** Secrets Manager, IAM roles

### Week 2: Containerization
- **Day 1-2:** Create ECR repos, build images
- **Day 3-4:** Push images, test locally
- **Day 5:** Database initialization

### Week 3: ECS Deployment
- **Day 1-2:** ECS cluster, task definitions
- **Day 3-4:** ALB, target groups
- **Day 5:** Deploy service, test

### Week 4: Testing & Optimization
- **Day 1-3:** Load testing, monitoring
- **Day 4-5:** Cost optimization, auto-scaling
- **Day 6-7:** Documentation, runbooks

**Total Time:** 4 weeks (part-time) or 2 weeks (full-time)

---

## ✅ DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] AWS account with billing alerts
- [ ] IAM user with ECS, RDS, VPC permissions
- [ ] Domain name (optional)
- [ ] SSL certificate (optional)
- [ ] Budget approved

### Infrastructure
- [ ] VPC created (2 AZs)
- [ ] Subnets configured (public + private)
- [ ] Security groups defined
- [ ] RDS instance running
- [ ] EFS file system created
- [ ] Secrets stored in Secrets Manager

### Containers
- [ ] ECR repositories created
- [ ] All images built and pushed
- [ ] Task definitions registered
- [ ] IAM roles created

### Deployment
- [ ] ECS cluster created
- [ ] ALB configured
- [ ] Target groups created
- [ ] ECS service deployed
- [ ] Health checks passing

### Post-Deployment
- [ ] CloudWatch alarms configured
- [ ] Auto-scaling enabled
- [ ] Backups configured
- [ ] Monitoring dashboard
- [ ] Cost alerts active

---

## 🚨 RISKS & MITIGATION

### Risk 1: Cost Overrun
**Mitigation:**
- Set AWS Budget alerts at $50, $75, $100
- Use Fargate Spot for 70% savings
- Schedule data pipeline (not 24/7)
- Monitor daily with Cost Explorer

### Risk 2: Service Downtime
**Mitigation:**
- Multi-AZ deployment (production)
- Health checks on all containers
- Auto-scaling for traffic spikes
- RDS automated backups

### Risk 3: Data Loss
**Mitigation:**
- RDS automated backups (7 days)
- EFS backup with AWS Backup
- Point-in-time recovery enabled
- Test restore procedures

### Risk 4: Security Breach
**Mitigation:**
- All services in private subnets
- Secrets in Secrets Manager
- Security groups with least privilege
- VPC Flow Logs enabled
- WAF on ALB (optional)

---

## 📚 NEXT STEPS

1. **Review & Approve Plan**
   - Confirm budget ($40-45/month)
   - Choose architecture (Minimal recommended)
   - Set deployment timeline

2. **Prepare AWS Account**
   - Enable billing alerts
   - Create IAM user/role
   - Request service limits increase (if needed)

3. **Start Infrastructure Setup**
   - Run Terraform/CloudFormation scripts
   - Or use deployment automation script

4. **Deploy & Test**
   - Deploy to staging first
   - Load test with 250 queries/day
   - Monitor for 1 week

5. **Go Live**
   - Switch DNS to production
   - Monitor closely for 48 hours
   - Document lessons learned

---

## 🔧 AUTOMATION SCRIPTS

I can create:
1. **Terraform IaC** - Full infrastructure as code
2. **CloudFormation** - AWS native templates
3. **Deployment Script** - Bash automation
4. **CI/CD Pipeline** - GitHub Actions for auto-deploy

**Which would you like me to create first?**

---

**RECOMMENDATION: Start with Minimal Fargate deployment ($40-45/month)**

This gives you:
- ✅ Production-ready infrastructure
- ✅ Auto-scaling and high availability
- ✅ Managed services (no server maintenance)
- ✅ Room to grow (can upgrade to Production tier)
- ✅ Cost-effective for demo platform

**Ready to proceed with deployment?**
