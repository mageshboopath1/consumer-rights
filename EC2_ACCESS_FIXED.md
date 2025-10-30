# EC2 Access and Deployment - FIXED

**Date**: October 30, 2025  
**Status**: WORKING

---

## Problem Solved

### Issue
EC2 instance was created but SSH access was failing with error:
```
Failed to connect to your instance
Error establishing SSH connection to your instance
```

### Root Cause
1. **IP Address Changed**: Your IP changed from `106.51.175.132` to `106.51.168.212`
2. **Security Group Restriction**: SSH was only allowed from old IP
3. **GitHub Actions Blocked**: GitHub Actions runners couldn't connect due to security group

### Solution Applied
1. Updated security group to allow SSH from current IP
2. Opened SSH port (22) to `0.0.0.0/0` for GitHub Actions access
3. Configured GitHub Secrets (EC2_HOST, EC2_USER, EC2_SSH_KEY)
4. Fixed workflow timeouts

---

## Current Status

### EC2 Instance
```
Instance ID: i-024ce9cb9afd203e2
Public IP: 15.207.114.126
Region: ap-south-1
Type: t3.small (Spot)
Status: RUNNING
```

### SSH Access
```bash
# From your machine
ssh -i consumer-rights-key.pem ubuntu@15.207.114.126

# Test connection
ssh -i consumer-rights-key.pem ubuntu@15.207.114.126 "uptime"
```

### Services Running
All services are UP and healthy:
- pii-filter
- psql_worker
- rag-core
- llm-connector
- rabbitmq (healthy)
- chroma_service
- postgres_service

### GitHub Actions CI/CD
- **Status**: WORKING
- **Latest Run**: SUCCESS
- **Deployment Time**: 17 seconds
- **URL**: https://github.com/mageshboopath1/consumer-rights/actions

---

## Security Group Configuration

### Current Rules

**Inbound Rules:**
```
Port 22 (SSH): 0.0.0.0/0 (open to all)
Port 80 (HTTP): 0.0.0.0/0 (open to all)
```

### Security Recommendation

For production, restrict SSH access:

```bash
# Get your current IP
MY_IP=$(curl -s https://checkip.amazonaws.com)

# Remove open SSH rule
aws ec2 revoke-security-group-ingress \
  --group-id sg-09efc1e7f775538a3 \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region ap-south-1

# Add restricted SSH rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-09efc1e7f775538a3 \
  --protocol tcp \
  --port 22 \
  --cidr ${MY_IP}/32 \
  --region ap-south-1
```

**Note**: This will break GitHub Actions deployment. For CI/CD to work, you need either:
1. Keep SSH open to `0.0.0.0/0` (less secure)
2. Use GitHub Actions self-hosted runner on EC2
3. Use AWS Systems Manager Session Manager instead of SSH

---

## GitHub Actions Workflow

### How It Works

1. **Trigger**: Push to main branch
2. **Connect**: SSH to EC2 using GitHub Secrets
3. **Pull**: Latest code from GitHub
4. **Detect**: Changes in service files
5. **Rebuild**: Docker containers (if needed)
6. **Restart**: Services with new code
7. **Verify**: All services running

### Workflow File
`.github/workflows/deploy-to-ec2.yml`

### Configuration
- Connection timeout: 60s
- Command timeout: 10m
- Triggers: Push to main, manual dispatch

---

## Testing the System

### 1. SSH to EC2
```bash
ssh -i consumer-rights-key.pem ubuntu@15.207.114.126
```

### 2. Check Services
```bash
cd consumer-rights
docker ps
docker-compose logs -f rag-core
```

### 3. Test RAG System
```bash
cd live_inference_pipeline/CLI
python cli.py
```

### 4. View Deployment Logs
```bash
tail -f /var/log/deployment.log
```

---

## Automatic Deployment

### Every Push to Main

```bash
# Make changes
echo "# Update" >> README.md

# Commit and push
git add .
git commit -m "update: feature"
git push origin main

# GitHub Actions automatically deploys
# Monitor at: https://github.com/mageshboopath1/consumer-rights/actions
```

### Manual Deployment

```bash
# Trigger workflow manually
gh workflow run deploy-to-ec2.yml

# Or via GitHub web interface
# Go to Actions > Deploy to EC2 > Run workflow
```

---

## Troubleshooting

### If SSH Fails Again

```bash
# Check your current IP
curl https://checkip.amazonaws.com

# Update security group
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id sg-09efc1e7f775538a3 \
  --protocol tcp \
  --port 22 \
  --cidr ${MY_IP}/32 \
  --region ap-south-1
```

### If Services Not Running

```bash
# SSH to EC2
ssh -i consumer-rights-key.pem ubuntu@15.207.114.126

# Check logs
cd consumer-rights/live_inference_pipeline
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

### If Deployment Fails

```bash
# Check workflow logs
gh run list
gh run view <run-id> --log

# SSH to EC2 and check manually
ssh -i consumer-rights-key.pem ubuntu@15.207.114.126
cd consumer-rights
git status
git pull origin main
```

---

## Cost Information

### Current Setup
- **EC2 Spot Instance (t3.small)**: ~$4.53/month
- **EBS 20GB**: ~$1.76/month
- **Data Transfer**: ~$1/month
- **Total Infrastructure**: ~$7.29/month

### Plus Usage Costs
- **AWS Bedrock** (if used): ~$0.01 per 1000 tokens
- **GCP Vertex AI** (if used): ~$0.02 per 1000 tokens

---

## Next Steps

1. **Test the system**: SSH to EC2 and run CLI
2. **Upload documents**: Place PDFs in `data_prepartion_pipeline/data/`
3. **Trigger DAG**: Access Airflow at http://15.207.114.126:8080
4. **Query system**: Use CLI or API to ask questions
5. **Monitor**: Check logs and metrics

---

## Files Reference

- **Workflow**: `.github/workflows/deploy-to-ec2.yml`
- **Deployment Script**: `deploy_to_ec2.sh`
- **Setup Guide**: `SETUP_GITHUB_SECRETS.md`
- **README**: `README.md`

---

**Status**: All systems operational and deployment working!
