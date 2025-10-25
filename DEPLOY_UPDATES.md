# How to Deploy Updates to EC2

## 🚀 QUICK REFERENCE

### Method 1: Build on EC2 (Fastest for testing)
```bash
# SSH to EC2
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>

# Pull latest code
cd consumer-rights
git pull origin main

# Rebuild and restart
cd live_inference_pipeline
docker-compose build
docker-compose up -d
```

### Method 2: Push to ECR (Production)
```bash
# Local: Build and push
cd live_inference_pipeline/PII
docker build -t 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest .
docker push 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest

# EC2: Pull and restart
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>
cd consumer-rights/live_inference_pipeline
docker-compose pull
docker-compose up -d
```

### Method 3: GitHub Actions (Automated)
```bash
# Just push to GitHub
git add .
git commit -m "Update service"
git push origin main

# GitHub Actions automatically:
# 1. Builds images
# 2. Pushes to ECR
# 3. Deploys to EC2
```

---

## 📋 DETAILED GUIDES

### Option 1: Build Directly on EC2

**When to use:**
- Quick testing
- Small changes
- Development

**Steps:**

1. **SSH to instance**
   ```bash
   ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>
   ```

2. **Pull latest code**
   ```bash
   cd consumer-rights
   git pull origin main
   ```

3. **Rebuild specific service**
   ```bash
   cd live_inference_pipeline
   
   # Rebuild one service
   docker-compose build pii-filter
   
   # Or rebuild all
   docker-compose build
   ```

4. **Restart services**
   ```bash
   # Restart one service
   docker-compose up -d pii-filter
   
   # Or restart all
   docker-compose up -d
   ```

5. **Verify**
   ```bash
   docker ps
   docker logs -f pii-filter
   ```

**Time:** 5-10 minutes

---

### Option 2: Use ECR (Amazon Container Registry)

**When to use:**
- Production deployments
- Multiple environments
- Team collaboration

**Setup (One-time):**

1. **Create ECR repositories**
   ```bash
   ACCOUNT_ID=692461731109
   REGION=ap-south-1
   
   aws ecr create-repository --repository-name consumer-rights/pii-filter --region $REGION
   aws ecr create-repository --repository-name consumer-rights/rag-core --region $REGION
   aws ecr create-repository --repository-name consumer-rights/llm-connector --region $REGION
   aws ecr create-repository --repository-name consumer-rights/psql-worker --region $REGION
   ```

2. **Update docker-compose.yml**
   ```yaml
   # Change from:
   services:
     pii-filter:
       build: ./PII
   
   # To:
   services:
     pii-filter:
       image: 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest
   ```

**Deploy workflow:**

1. **Build locally**
   ```bash
   cd live_inference_pipeline/PII
   docker build -t consumer-rights/pii-filter .
   ```

2. **Tag for ECR**
   ```bash
   docker tag consumer-rights/pii-filter:latest \
     692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest
   ```

3. **Login to ECR**
   ```bash
   aws ecr get-login-password --region ap-south-1 | \
     docker login --username AWS --password-stdin \
     692461731109.dkr.ecr.ap-south-1.amazonaws.com
   ```

4. **Push to ECR**
   ```bash
   docker push 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest
   ```

5. **Deploy to EC2**
   ```bash
   ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>
   
   # Login to ECR on EC2
   aws ecr get-login-password --region ap-south-1 | \
     docker login --username AWS --password-stdin \
     692461731109.dkr.ecr.ap-south-1.amazonaws.com
   
   # Pull and restart
   cd consumer-rights/live_inference_pipeline
   docker-compose pull
   docker-compose up -d
   ```

**Time:** 10-15 minutes

---

### Option 3: GitHub Actions (Automated CI/CD)

**When to use:**
- Production
- Team collaboration
- Automated deployments

**Setup (One-time):**

1. **Add GitHub Secrets**
   - Go to: GitHub repo → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
     - `EC2_HOST`: Your EC2 public IP
     - `EC2_SSH_KEY`: Content of `consumer-rights-key.pem`

2. **Create ECR repositories** (if not done)
   ```bash
   aws ecr create-repository --repository-name consumer-rights/pii-filter --region ap-south-1
   aws ecr create-repository --repository-name consumer-rights/rag-core --region ap-south-1
   aws ecr create-repository --repository-name consumer-rights/llm-connector --region ap-south-1
   aws ecr create-repository --repository-name consumer-rights/psql-worker --region ap-south-1
   ```

3. **Update docker-compose.yml on EC2**
   ```yaml
   services:
     pii-filter:
       image: 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/pii-filter:latest
     rag-core:
       image: 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/rag-core:latest
     llm-connector:
       image: 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/llm-connector:latest
     psql-worker:
       image: 692461731109.dkr.ecr.ap-south-1.amazonaws.com/consumer-rights/psql-worker:latest
   ```

**Deploy workflow:**

1. **Make changes locally**
   ```bash
   # Edit your code
   vim live_inference_pipeline/PII/piiFilter.py
   ```

2. **Commit and push**
   ```bash
   git add .
   git commit -m "Update PII filter"
   git push origin main
   ```

3. **GitHub Actions automatically:**
   - ✅ Builds all Docker images
   - ✅ Pushes to ECR
   - ✅ SSHs to EC2
   - ✅ Pulls latest images
   - ✅ Restarts services

4. **Monitor progress**
   - Go to: GitHub repo → Actions tab
   - Watch the deployment

**Time:** 5-8 minutes (automated)

---

## 🔧 HELPER SCRIPTS

### Quick Update Script (for EC2)

```bash
# Save as: update.sh on EC2
#!/bin/bash
cd /home/ubuntu/consumer-rights
git pull origin main
cd live_inference_pipeline
docker-compose build
docker-compose up -d
docker ps
echo "Update complete!"
```

### Quick Deploy Script (for Local)

```bash
# Save as: deploy.sh locally
#!/bin/bash
ACCOUNT_ID=692461731109
REGION=ap-south-1
ECR_REGISTRY=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push all services
for service in pii-filter rag-core llm-connector psql-worker; do
  echo "Building $service..."
  cd live_inference_pipeline/$(echo $service | tr '-' '_' | sed 's/_filter/\/PII/' | sed 's/rag_core/RAG-Core/' | sed 's/llm_connector/LLM-Connector/' | sed 's/psql_worker/psql_worker/')
  docker build -t consumer-rights/$service .
  docker tag consumer-rights/$service:latest $ECR_REGISTRY/consumer-rights/$service:latest
  docker push $ECR_REGISTRY/consumer-rights/$service:latest
  cd -
done

echo "All images pushed to ECR!"
```

---

## 💡 BEST PRACTICES

### Development
- ✅ Build on EC2 for quick testing
- ✅ Use `docker-compose build` for speed
- ✅ Test changes before pushing to main

### Staging
- ✅ Use ECR for consistency
- ✅ Tag images with version numbers
- ✅ Test thoroughly before production

### Production
- ✅ Use GitHub Actions for automation
- ✅ Tag with semantic versions (v1.0.0)
- ✅ Keep rollback images available
- ✅ Monitor deployments

---

## 🆘 TROUBLESHOOTING

### Build fails on EC2
```bash
# Check disk space
df -h

# Clean up Docker
docker system prune -a -f

# Try again
docker-compose build
```

### Can't push to ECR
```bash
# Re-login
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  692461731109.dkr.ecr.ap-south-1.amazonaws.com

# Check permissions
aws ecr describe-repositories --region ap-south-1
```

### Service won't start after update
```bash
# Check logs
docker logs pii-filter

# Rollback
docker-compose down
git checkout HEAD~1
docker-compose build
docker-compose up -d
```

---

## 📊 COMPARISON

| Method | Speed | Complexity | Cost | Best For |
|--------|-------|------------|------|----------|
| Build on EC2 | Fast | Low | Free | Development |
| ECR | Medium | Medium | ~$1/month | Production |
| GitHub Actions | Fast | High | ~$1/month | Teams |

---

## ✅ RECOMMENDED WORKFLOW

**For You (Demo/MVP):**
1. Start with **Build on EC2** (simplest)
2. When stable, move to **ECR** (better for production)
3. Eventually add **GitHub Actions** (full automation)

**Quick command for now:**
```bash
ssh -i consumer-rights-key.pem ubuntu@<PUBLIC_IP>
cd consumer-rights && git pull && cd live_inference_pipeline && docker-compose build && docker-compose up -d
```

That's it! 🚀
