# EC2 t3.small Spot Instance Deployment Guide

**Cost:** $22/month  
**Deployment Time:** 10 minutes  
**Region:** ap-south-1 (Mumbai)

---

## 🚀 QUICK START - Automated Deployment

### Step 1: Run Deployment Script

```bash
# Make script executable
chmod +x deploy_to_ec2.sh

# Run deployment
./deploy_to_ec2.sh
```

**The script will:**
1. ✅ Create SSH key pair
2. ✅ Create security group
3. ✅ Create IAM role for Bedrock
4. ✅ Launch EC2 Spot instance
5. ✅ Install Docker & Docker Compose
6. ✅ Clone your repository
7. ✅ Start all services
8. ✅ Configure auto-restart

**Time:** 5-10 minutes

---

## 📋 WHAT YOU'LL NEED

Before running the script, have ready:

1. **AWS CLI configured**
   ```bash
   aws configure
   # Enter your AWS credentials
   ```

2. **AWS Bedrock Access Key**
   - Access Key ID
   - Secret Access Key
   - (Script will prompt for these)

3. **PostgreSQL Password**
   - Choose a secure password
   - (Script will prompt for this)

---

## 🎯 AFTER DEPLOYMENT

### Wait 5-10 Minutes

The instance needs time to:
- Install Docker
- Clone repository
- Pull Docker images
- Start all services

### Check Installation Progress

```bash
# SSH to instance (key created by script)
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>

# View installation log
tail -f /var/log/user-data.log

# Wait for "Deployment completed" message
```

### Verify Services Running

```bash
# Check all containers
docker ps

# Should see 9 containers:
# - pii-filter
# - rag-core
# - llm-connector
# - psql_worker
# - rabbitmq
# - postgres_service
# - chroma_service
# - chunker-service (optional)
# - embedder-service (optional)
```

### Test the System

```bash
# Navigate to CLI
cd consumer-rights/live_inference_pipeline/CLI

# Run test query
python cli.py

# Enter a question:
# "What is the Consumer Protection Act?"

# Should get response in 2-5 seconds
```

---

## 📊 INSTANCE DETAILS

### Specifications

```
Instance Type: t3.small
vCPU: 2
RAM: 2 GB
Storage: 20 GB EBS gp3
Network: Enhanced networking
Region: ap-south-1 (Mumbai)
```

### Spot Instance Configuration

```
Market Type: Spot
Max Price: $0.0208/hour (on-demand price)
Actual Price: ~$0.0062/hour (70% discount)
Interruption Behavior: Stop (not terminate)
Persistence: Yes (auto-restarts after interruption)
```

### Security

```
Security Group: consumer-rights-sg
Inbound Rules:
  - SSH (22) from your IP only
  - HTTP (80) from anywhere (optional)

IAM Role: EC2BedrockRole
Permissions:
  - AmazonBedrockFullAccess
```

---

## 💰 COST BREAKDOWN

### Monthly Cost

```
EC2 t3.small Spot:
  $0.0062/hour × 730 hours = $4.53/month

EBS Storage (20 GB gp3):
  $0.088/GB × 20 GB = $1.76/month

Data Transfer:
  Bedrock API: Included
  Internet egress: ~$1/month

AWS Bedrock (Llama 3 70B):
  250 queries/day × $0.002 = $15/month
  (Protected by cost limiter)

────────────────────────────────────
TOTAL: $22.29/month
```

### Cost Optimization Tips

**1. Stop when not needed:**
```bash
# Stop instance (keeps data, no compute charges)
aws ec2 stop-instances --instance-ids i-xxxxx --region ap-south-1

# Only pay for EBS: $1.76/month
```

**2. Use Reserved Instance (if long-term):**
```
1-year commitment: $10.66/month (save $5/month)
3-year commitment: $7.30/month (save $8/month)
```

**3. Monitor Bedrock usage:**
```bash
# Check cost limiter stats
docker exec pii-filter python -c "
from security.cost_limiter import cost_limiter
print(cost_limiter.get_stats())
"
```

---

## 🔧 MANAGEMENT COMMANDS

### SSH Access

```bash
# Connect to instance
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>
```

### Service Management

```bash
# View all containers
docker ps

# View logs
docker logs -f pii-filter
docker logs -f rag-core
docker logs -f llm-connector

# Restart a service
docker restart pii-filter

# Restart all services
cd consumer-rights/live_inference_pipeline
docker-compose restart

# Stop all services
docker-compose down

# Start all services
docker-compose up -d
```

### System Status

```bash
# Check systemd service
sudo systemctl status consumer-rights

# View system logs
journalctl -u consumer-rights -f

# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU usage
top
```

### Updates

```bash
# Pull latest code
cd consumer-rights
git pull origin main

# Rebuild and restart
cd live_inference_pipeline
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 🔄 AUTO-RESTART ON SPOT INTERRUPTION

The deployment script creates a systemd service that automatically restarts all containers when the instance boots.

### How it works:

1. **Spot interruption detected** (2-minute warning)
2. **Instance stops** (not terminated)
3. **AWS restarts instance** (usually within minutes)
4. **Systemd service starts** on boot
5. **All containers restart** automatically
6. **System is back online** (~2 minutes total downtime)

### Test auto-restart:

```bash
# Reboot instance
sudo reboot

# Wait 2 minutes, then SSH back
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>

# Check services restarted
docker ps
```

---

## 📈 MONITORING

### CloudWatch Metrics (Optional)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure monitoring
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s
```

### Custom Monitoring Script

```bash
# Create monitoring script
cat > /home/ubuntu/monitor.sh <<'EOF'
#!/bin/bash
while true; do
  echo "=== $(date) ==="
  echo "CPU Usage:"
  top -bn1 | grep "Cpu(s)"
  echo ""
  echo "Memory Usage:"
  free -h
  echo ""
  echo "Disk Usage:"
  df -h /
  echo ""
  echo "Docker Containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}"
  echo ""
  sleep 300  # Every 5 minutes
done
EOF

chmod +x /home/ubuntu/monitor.sh

# Run in background
nohup /home/ubuntu/monitor.sh > /home/ubuntu/monitor.log 2>&1 &
```

---

## 🔒 SECURITY BEST PRACTICES

### 1. Secure SSH Key

```bash
# Keep key secure
chmod 400 consumer-rights-key.pem

# Don't commit to git
echo "*.pem" >> .gitignore
```

### 2. Update Security Group

```bash
# Restrict SSH to your IP only
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr $(curl -s https://checkip.amazonaws.com)/32 \
  --region ap-south-1
```

### 3. Regular Updates

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Update Docker images
cd consumer-rights/live_inference_pipeline
docker-compose pull
docker-compose up -d
```

### 4. Backup Data

```bash
# Create EBS snapshot
aws ec2 create-snapshot \
  --volume-id vol-xxxxx \
  --description "Consumer Rights backup $(date +%Y-%m-%d)" \
  --region ap-south-1
```

---

## 🆘 TROUBLESHOOTING

### Issue 1: Services Not Starting

```bash
# Check logs
tail -f /var/log/user-data.log

# Common causes:
# - Docker not installed yet (wait 5 min)
# - Network issues (check security group)
# - Out of memory (upgrade to t3.medium)
```

### Issue 2: Can't SSH

```bash
# Check security group allows your IP
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --region ap-south-1

# Update security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr $(curl -s https://checkip.amazonaws.com)/32 \
  --region ap-south-1
```

### Issue 3: Spot Instance Terminated

```bash
# Check instance status
aws ec2 describe-instances \
  --instance-ids i-xxxxx \
  --region ap-south-1

# If terminated, re-run deployment script
# (EBS volume persists, data is safe)
```

### Issue 4: Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a -f

# Remove old logs
sudo journalctl --vacuum-time=7d
```

### Issue 5: High Memory Usage

```bash
# Check memory
free -h

# Restart services to free memory
cd consumer-rights/live_inference_pipeline
docker-compose restart

# If persistent, upgrade to t3.medium
```

---

## 📊 PERFORMANCE TUNING

### Optimize Docker

```bash
# Add to /etc/docker/daemon.json
sudo tee /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

### Optimize PostgreSQL

```bash
# Edit postgres config
docker exec -it postgres_service bash
vi /var/lib/postgresql/data/postgresql.conf

# Add:
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 1GB
```

### Optimize ChromaDB

```bash
# Increase memory if needed
# Edit docker-compose.yml
# Under chroma service:
mem_limit: 512m
```

---

## 🎯 NEXT STEPS AFTER DEPLOYMENT

### 1. Test System (5 minutes)

```bash
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>
cd consumer-rights/live_inference_pipeline/CLI
python cli.py
# Test with sample questions
```

### 2. Populate ChromaDB (Optional)

```bash
# If you need to add documents
cd consumer-rights/data_prepartion_pipeline
docker-compose up -d

# Access Airflow
# http://<PUBLIC_IP>:8080
# Trigger DAG to process documents
```

### 3. Setup Monitoring (10 minutes)

```bash
# Install CloudWatch agent
# Setup custom monitoring script
# Configure alerts
```

### 4. Configure Backups (5 minutes)

```bash
# Create snapshot schedule
aws dlm create-lifecycle-policy \
  --description "Daily EBS snapshots" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::ACCOUNT_ID:role/AWSDataLifecycleManagerDefaultRole \
  --policy-details file://backup-policy.json \
  --region ap-south-1
```

### 5. Document Your Setup

- Save instance ID
- Save public IP (or use Elastic IP)
- Document any customizations
- Share access with team (if needed)

---

## 💡 TIPS & TRICKS

### 1. Use Elastic IP (Optional)

```bash
# Allocate Elastic IP
aws ec2 allocate-address --region ap-south-1

# Associate with instance
aws ec2 associate-address \
  --instance-id i-xxxxx \
  --allocation-id eipalloc-xxxxx \
  --region ap-south-1

# Cost: $3.60/month (but IP doesn't change)
```

### 2. Setup Domain Name (Optional)

```bash
# Point domain to instance IP
# In Route53 or your DNS provider:
# A record: rag.yourdomain.com → <PUBLIC_IP>
```

### 3. Add HTTPS (Optional)

```bash
# Install Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d rag.yourdomain.com

# Configure reverse proxy
# Edit /etc/nginx/sites-available/default
```

### 4. Setup Alerts (Optional)

```bash
# SNS topic for alerts
aws sns create-topic --name consumer-rights-alerts --region ap-south-1

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-south-1:ACCOUNT_ID:consumer-rights-alerts \
  --protocol email \
  --notification-endpoint your@email.com \
  --region ap-south-1
```

---

## 📞 SUPPORT

### Common Commands Reference

```bash
# SSH to instance
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>

# View all logs
docker-compose logs -f

# Restart everything
sudo systemctl restart consumer-rights

# Check system status
docker ps && free -h && df -h

# Update code
cd consumer-rights && git pull && docker-compose restart
```

### Getting Help

1. **Check logs:** `/var/log/user-data.log`
2. **Check Docker:** `docker ps` and `docker logs`
3. **Check system:** `free -h`, `df -h`, `top`
4. **Review documentation:** This guide + other docs

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] AWS CLI configured
- [ ] Run `deploy_to_ec2.sh`
- [ ] Wait 5-10 minutes for installation
- [ ] SSH to instance
- [ ] Verify all containers running (`docker ps`)
- [ ] Test with sample query
- [ ] Check security group settings
- [ ] Setup monitoring (optional)
- [ ] Configure backups (optional)
- [ ] Document instance details
- [ ] Test auto-restart (reboot instance)

---

## 🎉 SUCCESS!

**Your Consumer Rights RAG system is now running on EC2!**

**Cost:** $22/month  
**Performance:** 2-5 second responses  
**Capacity:** 250 queries/day  
**Uptime:** ~95% (with Spot auto-restart)

**Enjoy your cost-effective deployment!** 🚀
