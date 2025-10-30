# Deployment Status

**Last Updated**: October 30, 2025

---

## Current Status

### GitHub Actions Workflow

- **Status**: Configured and running
- **Workflow File**: `.github/workflows/deploy-to-ec2.yml`
- **Latest Run**: https://github.com/mageshboopath1/consumer-rights/actions

### What the Workflow Does

The GitHub Actions workflow will automatically deploy to EC2 when you push to the main branch:

1. **Connects to EC2** via SSH using GitHub Secrets
2. **Pulls latest code** from GitHub
3. **Detects changes** in service files
4. **Rebuilds services** only if needed
5. **Restarts containers** with new code
6. **Verifies** all services are running

---

## Required Setup

### GitHub Secrets (REQUIRED)

The workflow needs 3 secrets to be configured in GitHub:

| Secret | Description | Status |
|--------|-------------|--------|
| `EC2_HOST` | EC2 public IP address | NOT SET |
| `EC2_USER` | SSH username (ubuntu) | NOT SET |
| `EC2_SSH_KEY` | Private SSH key | NOT SET |

**The workflow will FAIL until these secrets are configured.**

---

## How to Setup

### Option 1: Quick Setup (Recommended)

```bash
# 1. Get EC2 IP
EC2_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=consumer-rights-rag" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text \
  --region ap-south-1)

# 2. Set GitHub secrets
gh secret set EC2_HOST --body "$EC2_IP"
gh secret set EC2_USER --body "ubuntu"
gh secret set EC2_SSH_KEY < consumer-rights-key.pem

# 3. Verify
gh secret list
```

### Option 2: Manual Setup via GitHub Web

1. Go to: https://github.com/mageshboopath1/consumer-rights/settings/secrets/actions
2. Click "New repository secret"
3. Add each secret:
   - `EC2_HOST`: Your EC2 public IP
   - `EC2_USER`: `ubuntu`
   - `EC2_SSH_KEY`: Paste entire contents of `consumer-rights-key.pem`

See [SETUP_GITHUB_SECRETS.md](SETUP_GITHUB_SECRETS.md) for detailed instructions.

---

## Testing Deployment

### After Setting Up Secrets

```bash
# Make a small change
echo "# Test" >> README.md

# Commit and push
git add .
git commit -m "test: trigger deployment"
git push origin main

# Watch deployment
gh run watch
```

### Expected Output

```
Deploy to EC2
  [1/7] Navigating to project directory...
  [2/7] Creating backup...
  [3/7] Pulling latest code from GitHub...
  [4/7] Checking for changes...
  [5/7] Stopping services...
  [6/7] Starting services...
  [7/7] Verifying services...
  
  rag-core is running
  pii-filter is running
  llm-connector is running
  
  Deployment completed successfully!
```

---

## Current Workflow Status

### Latest Run

Check: https://github.com/mageshboopath1/consumer-rights/actions

**Expected Status**: 
- If secrets NOT configured: FAILED (missing server host)
- If secrets configured: SUCCESS (deployed to EC2)

---

## Deployment Flow

```
Developer Push
     |
     v
GitHub Actions Triggered
     |
     v
Connect to EC2 via SSH
     |
     v
Pull Latest Code
     |
     v
Detect Changes
     |
     v
Rebuild Services (if needed)
     |
     v
Restart Containers
     |
     v
Verify Services Running
     |
     v
Deployment Complete
```

---

## Troubleshooting

### Workflow Fails: "missing server host"

**Problem**: GitHub Secrets not configured

**Solution**: Follow setup instructions above

### Workflow Fails: "Permission denied"

**Problem**: SSH key is incorrect

**Solution**: 
```bash
gh secret set EC2_SSH_KEY < consumer-rights-key.pem
```

### Services Not Starting

**Problem**: Docker containers failing

**Solution**: SSH to EC2 and check logs
```bash
ssh -i consumer-rights-key.pem ubuntu@YOUR_EC2_IP
cd consumer-rights/live_inference_pipeline
docker-compose logs
```

---

## Next Steps

1. **Setup GitHub Secrets** (required for automatic deployment)
2. **Deploy EC2 Instance** (if not already done)
   ```bash
   ./deploy_to_ec2.sh
   ```
3. **Test Deployment** by pushing to main branch
4. **Monitor** GitHub Actions dashboard

---

## Files Reference

- **Workflow**: `.github/workflows/deploy-to-ec2.yml`
- **Setup Guide**: `SETUP_GITHUB_SECRETS.md`
- **Deployment Script**: `deploy_to_ec2.sh`
- **README**: `README.md` (Deployment section)

---

**Questions?** Check [SETUP_GITHUB_SECRETS.md](SETUP_GITHUB_SECRETS.md) for detailed troubleshooting.
# EC2 Access Fixed
