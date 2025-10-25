# AWS ECS Simplified Deployment - Consumer Rights RAG System

**Date:** 2025-10-26  
**Architecture:** Single ECS Task with All Containers + EFS Storage  
**No RDS, No Auto-Scaling**

---

## 📊 SIMPLIFIED COMPUTE REQUIREMENTS

### All Services in One ECS Task

| Container | CPU | Memory | Essential |
|-----------|-----|--------|-----------|
| pii-filter | 256 | 256 MB | Yes |
| rag-core | 256 | 512 MB | Yes |
| llm-connector | 256 | 256 MB | Yes |
| psql_worker | 256 | 256 MB | Yes |
| rabbitmq | 512 | 512 MB | Yes |
| postgres | 256 | 512 MB | Yes |
| chroma | 256 | 256 MB | Yes |
| **TOTAL** | **2048 (2 vCPU)** | **2560 MB (2.5 GB)** | |

**Recommended Fargate Size:** 2 vCPU, 3 GB RAM

---

## 💰 SIMPLIFIED COST ANALYSIS

### Monthly Cost Breakdown

```
ECS Fargate (2 vCPU, 3 GB):
  vCPU: 2 × $0.04048/hour × 730 hours = $59.10
  Memory: 3 GB × $0.004445/GB/hour × 730 hours = $9.73
  Subtotal: $68.83/month

EFS Storage (5 GB for PostgreSQL + ChromaDB):
  Storage: 5 GB × $0.30/GB/month = $1.50/month

Data Transfer:
  Bedrock API calls: Included
  Internet egress: ~$1/month

AWS Bedrock (Llama 3 70B):
  250 queries/day × $0.002 = $0.50/day = $15/month
  (Already budgeted with cost limiter)

TOTAL: ~$71/month
```

### With Cost Optimization (Fargate Spot)

```
Fargate Spot (70% discount):
  vCPU: 2 × $0.01214/hour × 730 hours = $17.73
  Memory: 3 GB × $0.001334/GB/hour × 730 hours = $2.92
  Subtotal: $20.65/month

EFS: $1.50/month
Data Transfer: $1/month
Bedrock: $15/month (cost-limited)

TOTAL: ~$38/month
```

**Savings: $33/month (46% cheaper!)**

---

## 🏗️ SIMPLIFIED ARCHITECTURE

```
Internet
   ↓
Application Load Balancer (Optional - can use direct IP)
   ↓
ECS Fargate Task (Single Task, No Auto-Scaling)
   ├── pii-filter ────────┐
   ├── rag-core ──────────┤
   ├── llm-connector ─────┤
   ├── psql_worker ───────┼──→ rabbitmq
   ├── postgres ──────────┤
   └── chroma ────────────┘
        ↓
   EFS Volume (Persistent Storage)
   ├── /postgres-data (PostgreSQL data)
   └── /chroma-data (ChromaDB data)
```

**Key Points:**
- All containers in ONE task (like docker-compose)
- Containers communicate via localhost
- Persistent data on EFS
- Single task, no scaling

---

## 📋 INFRASTRUCTURE REQUIREMENTS

### 1. VPC & Networking (Minimal)

```
VPC: 10.0.0.0/16
├── Public Subnet: 10.0.1.0/24 (for ALB - optional)
└── Private Subnet: 10.0.11.0/24 (for ECS task)

Security Groups:
├── ECS-SG: Allow all traffic within task
└── Optional ALB-SG: Allow 80/443 from internet
```

### 2. EFS File System

```
EFS: consumer-rights-data
├── /postgres-data (PostgreSQL volume)
└── /chroma-data (ChromaDB volume)

Performance: General Purpose
Throughput: Bursting
Encryption: Yes
Size: ~5 GB
```

### 3. ECS Cluster

```
Cluster: consumer-rights-prod
├── Launch Type: Fargate
├── Task Count: 1 (fixed, no auto-scaling)
└── Fargate Platform: LATEST
```

---

## 🔧 ECS TASK DEFINITION

```json
{
  "family": "consumer-rights-all-in-one",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "3072",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskRole",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  
  "containerDefinitions": [
    {
      "name": "postgres",
      "image": "postgres:13",
      "cpu": 256,
      "memory": 512,
      "essential": true,
      "environment": [
        {"name": "POSTGRES_USER", "value": "postgres"},
        {"name": "POSTGRES_DB", "value": "consumer_rights"}
      ],
      "secrets": [
        {
          "name": "POSTGRES_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:ap-south-1:ACCOUNT_ID:secret:consumer-rights/db-password"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "postgres-data",
          "containerPath": "/var/lib/postgresql/data"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "postgres"
        }
      }
    },
    {
      "name": "chroma",
      "image": "ghcr.io/chroma-core/chroma:0.5.23",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "environment": [
        {"name": "IS_PERSISTENT", "value": "TRUE"}
      ],
      "mountPoints": [
        {
          "sourceVolume": "chroma-data",
          "containerPath": "/data"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "chroma"
        }
      }
    },
    {
      "name": "rabbitmq",
      "image": "rabbitmq:3-management",
      "cpu": 512,
      "memory": 512,
      "essential": true,
      "portMappings": [
        {"containerPort": 5672, "protocol": "tcp"},
        {"containerPort": 15672, "protocol": "tcp"}
      ],
      "healthCheck": {
        "command": ["CMD", "rabbitmq-diagnostics", "ping"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "rabbitmq"
        }
      }
    },
    {
      "name": "pii-filter",
      "image": "ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "dependsOn": [
        {"containerName": "rabbitmq", "condition": "HEALTHY"}
      ],
      "environment": [
        {"name": "PYTHONUNBUFFERED", "value": "1"},
        {"name": "RABBITMQ_HOST", "value": "localhost"}
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
      "image": "ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/rag-core:latest",
      "cpu": 256,
      "memory": 512,
      "essential": true,
      "dependsOn": [
        {"containerName": "rabbitmq", "condition": "HEALTHY"},
        {"containerName": "chroma", "condition": "START"}
      ],
      "environment": [
        {"name": "PYTHONUNBUFFERED", "value": "1"},
        {"name": "RABBITMQ_HOST", "value": "localhost"},
        {"name": "CHROMA_HOST", "value": "localhost"},
        {"name": "CHROMA_PORT", "value": "8000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "rag-core"
        }
      }
    },
    {
      "name": "llm-connector",
      "image": "ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/llm-connector:latest",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "dependsOn": [
        {"containerName": "rabbitmq", "condition": "HEALTHY"}
      ],
      "environment": [
        {"name": "PYTHONUNBUFFERED", "value": "1"},
        {"name": "RABBITMQ_HOST", "value": "localhost"},
        {"name": "AWS_REGION", "value": "ap-south-1"},
        {"name": "BEDROCK_MODEL_ID", "value": "meta.llama3-70b-instruct-v1:0"}
      ],
      "secrets": [
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": "arn:aws:secretsmanager:ap-south-1:ACCOUNT_ID:secret:consumer-rights/aws-credentials:access_key::"
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": "arn:aws:secretsmanager:ap-south-1:ACCOUNT_ID:secret:consumer-rights/aws-credentials:secret_key::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "llm-connector"
        }
      }
    },
    {
      "name": "psql-worker",
      "image": "ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/psql-worker:latest",
      "cpu": 256,
      "memory": 256,
      "essential": true,
      "dependsOn": [
        {"containerName": "rabbitmq", "condition": "HEALTHY"},
        {"containerName": "postgres", "condition": "START"}
      ],
      "environment": [
        {"name": "PYTHONUNBUFFERED", "value": "1"},
        {"name": "RABBITMQ_HOST", "value": "localhost"},
        {"name": "DB_HOST", "value": "localhost"},
        {"name": "DB_USER", "value": "postgres"},
        {"name": "DB_NAME", "value": "consumer_rights"}
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:ap-south-1:ACCOUNT_ID:secret:consumer-rights/db-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/consumer-rights",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "psql-worker"
        }
      }
    }
  ],
  
  "volumes": [
    {
      "name": "postgres-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-XXXXX",
        "rootDirectory": "/postgres-data",
        "transitEncryption": "ENABLED"
      }
    },
    {
      "name": "chroma-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-XXXXX",
        "rootDirectory": "/chroma-data",
        "transitEncryption": "ENABLED"
      }
    }
  ]
}
```

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Create EFS File System

```bash
# Create EFS
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=consumer-rights-data \
  --region ap-south-1

# Note the FileSystemId: fs-xxxxx

# Create mount target in your subnet
aws efs create-mount-target \
  --file-system-id fs-xxxxx \
  --subnet-id subnet-xxxxx \
  --security-groups sg-xxxxx \
  --region ap-south-1
```

### Step 2: Store Secrets in Secrets Manager

```bash
# Database password
aws secretsmanager create-secret \
  --name consumer-rights/db-password \
  --secret-string "your-secure-password" \
  --region ap-south-1

# AWS credentials for Bedrock
aws secretsmanager create-secret \
  --name consumer-rights/aws-credentials \
  --secret-string '{"access_key":"YOUR_KEY","secret_key":"YOUR_SECRET"}' \
  --region ap-south-1
```

### Step 3: Create ECR Repositories

```bash
aws ecr create-repository --repository-name consumer-rights/pii-filter --region ap-south-1
aws ecr create-repository --repository-name consumer-rights/rag-core --region ap-south-1
aws ecr create-repository --repository-name consumer-rights/llm-connector --region ap-south-1
aws ecr create-repository --repository-name consumer-rights/psql-worker --region ap-south-1
```

### Step 4: Build and Push Docker Images

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-south-1

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build and push pii-filter
cd live_inference_pipeline/PII
docker build -t consumer-rights/pii-filter .
docker tag consumer-rights/pii-filter:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/pii-filter:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/pii-filter:latest

# Build and push rag-core
cd ../RAG-Core
docker build -t consumer-rights/rag-core .
docker tag consumer-rights/rag-core:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/rag-core:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/rag-core:latest

# Build and push llm-connector
cd ../LLM-Connector
docker build -t consumer-rights/llm-connector .
docker tag consumer-rights/llm-connector:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/llm-connector:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/llm-connector:latest

# Build and push psql-worker
cd ../psql_worker
docker build -t consumer-rights/psql-worker .
docker tag consumer-rights/psql-worker:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/psql-worker:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/psql-worker:latest
```

### Step 5: Create IAM Roles

```bash
# Create task execution role (for pulling images, logs)
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create task role (for Bedrock access)
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### Step 6: Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name consumer-rights-prod \
  --region ap-south-1
```

### Step 7: Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/consumer-rights \
  --region ap-south-1
```

### Step 8: Register Task Definition

```bash
# Update task definition JSON with your:
# - ACCOUNT_ID
# - EFS file system ID (fs-xxxxx)
# - Secret ARNs

aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region ap-south-1
```

### Step 9: Create ECS Service (No Auto-Scaling)

```bash
aws ecs create-service \
  --cluster consumer-rights-prod \
  --service-name consumer-rights-service \
  --task-definition consumer-rights-all-in-one:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxxxx],
    securityGroups=[sg-xxxxx],
    assignPublicIp=ENABLED
  }" \
  --region ap-south-1
```

### Step 10: Get Task Public IP

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster consumer-rights-prod \
  --service-name consumer-rights-service \
  --query 'taskArns[0]' \
  --output text \
  --region ap-south-1)

# Get task details
aws ecs describe-tasks \
  --cluster consumer-rights-prod \
  --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text \
  --region ap-south-1

# Get public IP from ENI
aws ec2 describe-network-interfaces \
  --network-interface-ids eni-xxxxx \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text \
  --region ap-south-1
```

---

## 📊 MONITORING

### CloudWatch Logs

```bash
# View logs for each container
aws logs tail /ecs/consumer-rights --follow --filter-pattern "pii-filter"
aws logs tail /ecs/consumer-rights --follow --filter-pattern "rag-core"
aws logs tail /ecs/consumer-rights --follow --filter-pattern "llm-connector"
```

### Task Status

```bash
# Check service status
aws ecs describe-services \
  --cluster consumer-rights-prod \
  --services consumer-rights-service \
  --region ap-south-1

# Check task status
aws ecs describe-tasks \
  --cluster consumer-rights-prod \
  --tasks $TASK_ARN \
  --region ap-south-1
```

---

## 🔄 UPDATES & MAINTENANCE

### Update Docker Images

```bash
# Build new image
docker build -t consumer-rights/pii-filter .
docker tag consumer-rights/pii-filter:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/pii-filter:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/consumer-rights/pii-filter:latest

# Force new deployment
aws ecs update-service \
  --cluster consumer-rights-prod \
  --service consumer-rights-service \
  --force-new-deployment \
  --region ap-south-1
```

### Restart Service

```bash
# Stop current task (new one will start automatically)
aws ecs stop-task \
  --cluster consumer-rights-prod \
  --task $TASK_ARN \
  --region ap-south-1
```

### Backup Data

```bash
# EFS is automatically backed up
# Manual backup:
aws backup start-backup-job \
  --backup-vault-name Default \
  --resource-arn arn:aws:elasticfilesystem:ap-south-1:ACCOUNT_ID:file-system/fs-xxxxx \
  --iam-role-arn arn:aws:iam::ACCOUNT_ID:role/AWSBackupDefaultServiceRole \
  --region ap-south-1
```

---

## 💰 COST OPTIMIZATION

### Use Fargate Spot (Recommended)

```json
{
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE_SPOT",
      "weight": 1,
      "base": 1
    }
  ]
}
```

**Savings:** $68/month → $20/month (70% discount!)

### Stop Service When Not Needed

```bash
# Scale to 0 (stop service)
aws ecs update-service \
  --cluster consumer-rights-prod \
  --service consumer-rights-service \
  --desired-count 0 \
  --region ap-south-1

# Scale back to 1 (start service)
aws ecs update-service \
  --cluster consumer-rights-prod \
  --service consumer-rights-service \
  --desired-count 1 \
  --region ap-south-1
```

**Savings:** Only pay when running!

---

## 🎯 FINAL COST SUMMARY

### Without Optimization
```
ECS Fargate (2 vCPU, 3 GB): $68/month
EFS (5 GB): $1.50/month
Bedrock (250 queries/day): $15/month
TOTAL: $84.50/month
```

### With Fargate Spot
```
ECS Fargate Spot (2 vCPU, 3 GB): $20/month
EFS (5 GB): $1.50/month
Bedrock (250 queries/day): $15/month
TOTAL: $36.50/month
```

**Savings: $48/month (57% cheaper!)**

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] EFS file system created
- [ ] Secrets stored in Secrets Manager
- [ ] ECR repositories created
- [ ] Docker images built and pushed
- [ ] IAM roles created
- [ ] ECS cluster created
- [ ] CloudWatch log group created
- [ ] Task definition registered
- [ ] ECS service created
- [ ] Task running successfully
- [ ] Public IP obtained
- [ ] All containers healthy
- [ ] Test query successful

---

## 🚨 TROUBLESHOOTING

### Task Won't Start
```bash
# Check task events
aws ecs describe-tasks \
  --cluster consumer-rights-prod \
  --tasks $TASK_ARN \
  --query 'tasks[0].stoppedReason' \
  --region ap-south-1
```

### Container Crashes
```bash
# Check logs
aws logs tail /ecs/consumer-rights --follow
```

### Can't Pull Images
```bash
# Check execution role has ECR permissions
aws iam get-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name ECRAccess
```

### EFS Mount Fails
```bash
# Check security group allows NFS (port 2049)
# Check EFS mount target is in same subnet
```

---

## 📚 NEXT STEPS

**I can create for you:**

1. **Complete Task Definition JSON** - Ready to deploy
2. **Deployment Automation Script** - One command deploy
3. **IAM Policy Documents** - All required permissions
4. **Terraform/CloudFormation** - Infrastructure as Code

**Which would you like me to create?**

---

**SIMPLIFIED ARCHITECTURE BENEFITS:**

✅ No RDS costs (save $17/month)  
✅ No auto-scaling complexity  
✅ Single task = easy to manage  
✅ All containers communicate via localhost  
✅ Persistent data on EFS  
✅ Total cost: ~$37/month with Spot  

**Ready to deploy?**
