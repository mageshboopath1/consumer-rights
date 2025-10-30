# Setup GitHub Secrets for CI/CD

This guide explains how to configure GitHub Secrets for automatic deployment to EC2.

---

## Prerequisites

1. EC2 instance running (use `deploy_to_ec2.sh` to create one)
2. SSH key file (`consumer-rights-key.pem`)
3. EC2 public IP address

---

## Required Secrets

You need to configure 3 secrets in GitHub:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `EC2_HOST` | EC2 public IP address | `13.232.123.45` |
| `EC2_USER` | SSH username | `ubuntu` |
| `EC2_SSH_KEY` | Private SSH key content | Contents of `consumer-rights-key.pem` |

---

## Setup Instructions

### Step 1: Get EC2 Information

```bash
# Get EC2 public IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=consumer-rights-rag" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text \
  --region ap-south-1
```

### Step 2: Get SSH Key Content

```bash
# Display SSH key content
cat consumer-rights-key.pem
```

Copy the entire output including:
- `-----BEGIN RSA PRIVATE KEY-----`
- All the key content
- `-----END RSA PRIVATE KEY-----`

### Step 3: Add Secrets to GitHub

#### Option A: Using GitHub Web Interface

1. Go to your repository on GitHub
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add each secret:

**Secret 1: EC2_HOST**
- Name: `EC2_HOST`
- Value: Your EC2 public IP (e.g., `13.232.123.45`)
- Click **Add secret**

**Secret 2: EC2_USER**
- Name: `EC2_USER`
- Value: `ubuntu`
- Click **Add secret**

**Secret 3: EC2_SSH_KEY**
- Name: `EC2_SSH_KEY`
- Value: Paste entire content of `consumer-rights-key.pem`
- Click **Add secret**

#### Option B: Using GitHub CLI

```bash
# Set EC2_HOST
gh secret set EC2_HOST --body "13.232.123.45"

# Set EC2_USER
gh secret set EC2_USER --body "ubuntu"

# Set EC2_SSH_KEY (from file)
gh secret set EC2_SSH_KEY < consumer-rights-key.pem
```

---

## Verify Setup

### Check Secrets Are Configured

```bash
gh secret list
```

You should see:
```
EC2_HOST        Updated YYYY-MM-DD
EC2_SSH_KEY     Updated YYYY-MM-DD
EC2_USER        Updated YYYY-MM-DD
```

### Test Deployment

```bash
# Push to main branch
git push origin main

# Or manually trigger workflow
gh workflow run deploy-to-ec2.yml

# Watch workflow
gh run watch
```

---

## How It Works

1. **Push to main** triggers GitHub Actions workflow
2. **Workflow connects** to EC2 via SSH using secrets
3. **Pulls latest code** from GitHub
4. **Rebuilds services** if needed
5. **Restarts containers** with new code
6. **Verifies** services are running

---

## Troubleshooting

### Workflow Fails with "missing server host"

**Problem**: `EC2_HOST` secret is not set or empty

**Solution**:
```bash
gh secret set EC2_HOST --body "YOUR_EC2_IP"
```

### Workflow Fails with "Permission denied (publickey)"

**Problem**: `EC2_SSH_KEY` is incorrect or not set

**Solution**:
```bash
# Make sure you copy the ENTIRE key including headers
gh secret set EC2_SSH_KEY < consumer-rights-key.pem
```

### Workflow Fails with "Connection refused"

**Problem**: EC2 instance is not running or IP changed

**Solution**:
```bash
# Check EC2 status
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=consumer-rights-rag" \
  --query "Reservations[0].Instances[0].[State.Name,PublicIpAddress]" \
  --output table \
  --region ap-south-1

# Update EC2_HOST if IP changed
gh secret set EC2_HOST --body "NEW_IP"
```

### Services Not Starting After Deployment

**Problem**: Docker containers failing to start

**Solution**:
```bash
# SSH to EC2
ssh -i consumer-rights-key.pem ubuntu@YOUR_EC2_IP

# Check logs
cd consumer-rights/live_inference_pipeline
docker-compose logs

# Restart manually
docker-compose down
docker-compose up -d
```

---

## Security Best Practices

1. **Never commit** SSH keys to repository
2. **Rotate keys** periodically
3. **Use minimal permissions** for SSH keys
4. **Monitor** GitHub Actions logs for suspicious activity
5. **Enable** two-factor authentication on GitHub

---

## Updating Secrets

If you need to update a secret (e.g., EC2 IP changed):

```bash
# Update EC2_HOST
gh secret set EC2_HOST --body "NEW_IP"

# Update SSH key
gh secret set EC2_SSH_KEY < new-key.pem
```

---

## Next Steps

After setting up secrets:

1. Push to main branch to trigger deployment
2. Monitor workflow at: https://github.com/YOUR_USERNAME/consumer-rights/actions
3. Verify services on EC2: `ssh -i consumer-rights-key.pem ubuntu@YOUR_EC2_IP`
4. Check services: `docker ps`

---

**Last Updated**: October 30, 2025
