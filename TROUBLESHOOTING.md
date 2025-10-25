# Troubleshooting Guide

## PostgreSQL Connection Issues

### Issue: "Role postgres does not exist" errors in logs

**Symptom:**
```
FATAL: password authentication failed for user "postgres"
DETAIL: Role "postgres" does not exist.
```

**Cause:**
Something is trying to connect to PostgreSQL using the old default "postgres" username instead of the configured "consumerrights_user".

**Solutions:**

#### 1. Check if it's from this project
```bash
# Check which services are running
docker ps

# Check live inference pipeline
cd live_inference_pipeline
docker-compose ps

# Check data preparation pipeline  
cd ../data_prepartion_pipeline
docker-compose ps
```

#### 2. Verify environment variables are loaded
```bash
# Check shared services .env
cat shared_services/chroma/.env

# Should show:
# POSTGRES_USER=consumerrights_user
# POSTGRES_PASSWORD=<your_password>
# POSTGRES_DB=consumer_rights
```

#### 3. Reset PostgreSQL database (if needed)
```bash
# Stop and remove volumes
cd shared_services/chroma
docker-compose down -v

# Restart with fresh database
docker-compose up -d

# Wait 10 seconds for initialization
sleep 10

# Verify it works
docker exec postgres_service psql -U consumerrights_user -d consumer_rights -c "\dt"
```

#### 4. Check if external services are connecting
```bash
# List all containers
docker ps -a

# Check network connections
docker network inspect shared_network

# Only postgres_service and chroma_service should be listed
```

#### 5. If errors persist but database works
If you can successfully connect with `consumerrights_user` but still see errors:
- The errors might be from external services not part of this project
- The errors might be from old connection attempts that will stop
- As long as your services can connect, the system will work

**Verification:**
```bash
# Test database connection
docker exec postgres_service psql -U consumerrights_user -d consumer_rights -c "SELECT version();"

# Should return PostgreSQL version info

# Test table exists
docker exec postgres_service psql -U consumerrights_user -d consumer_rights -c "\dt"

# Should show chat_history table
```

---

## ChromaDB Connection Issues

### Issue: ChromaDB not accessible

**Symptom:**
```
Connection refused on port 8002
```

**Solutions:**

```bash
# Check if ChromaDB is running
docker ps | grep chroma

# Check ChromaDB logs
docker logs chroma_service

# Test ChromaDB
curl http://localhost:8002/api/v1/heartbeat

# Restart if needed
cd shared_services/chroma
docker-compose restart chroma
```

---

## RabbitMQ Connection Issues

### Issue: Services can't connect to RabbitMQ

**Solutions:**

```bash
# Check RabbitMQ is running
docker ps | grep rabbitmq

# Check RabbitMQ logs
docker logs rabbitmq

# Access management UI
open http://localhost:15672
# Username: guest, Password: guest

# Restart if needed
cd live_inference_pipeline
docker-compose restart rabbitmq
```

---

## Service Won't Start

### Issue: Container exits immediately

**Diagnosis:**
```bash
# Check container logs
docker logs <container-name>

# Check last 50 lines
docker logs <container-name> 2>&1 | tail -50

# Follow logs in real-time
docker logs -f <container-name>
```

**Common causes:**

1. **Missing environment variables**
   ```bash
   # Check .env files exist
   ls -la .env
   ls -la live_inference_pipeline/.env
   ls -la data_prepartion_pipeline/.env
   ls -la shared_services/chroma/.env
   ```

2. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :5432  # PostgreSQL
   lsof -i :8002  # ChromaDB
   lsof -i :5672  # RabbitMQ
   ```

3. **Network doesn't exist**
   ```bash
   # Create shared network
   docker network create shared_network
   ```

---

## Performance Issues

### Issue: Slow query responses

**Check:**

1. **Model loading**
   ```bash
   # Check RAG Core logs for model loading
   docker logs rag-core | grep "Model loaded"
   
   # Should see: "[i] Model loaded successfully." at startup
   ```

2. **Resource usage**
   ```bash
   # Check Docker stats
   docker stats
   
   # Look for high CPU/memory usage
   ```

3. **Database queries**
   ```bash
   # Check slow queries
   docker exec postgres_service psql -U consumerrights_user -d consumer_rights -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
   ```

---

## Data Preparation Pipeline Issues

### Issue: Airflow won't start

**Solutions:**

```bash
# Check Airflow database is initialized
cd data_prepartion_pipeline

# Initialize database
docker-compose run --rm airflow-webserver airflow db init

# Create admin user
docker-compose run --rm airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Start services
docker-compose up -d
```

---

## Complete System Reset

If all else fails, perform a complete reset:

```bash
# Stop all services
cd live_inference_pipeline && docker-compose down -v && cd ..
cd data_prepartion_pipeline && docker-compose down -v && cd ..
cd shared_services/chroma && docker-compose down -v && cd ../..

# Remove network
docker network rm shared_network

# Recreate network
docker network create shared_network

# Start fresh
cd shared_services/chroma && docker-compose up -d && cd ../..
sleep 10
cd data_prepartion_pipeline && docker-compose up -d && cd ..
cd live_inference_pipeline && docker-compose up -d && cd ..
```

---

## Checking System Health

### Quick Health Check Script

```bash
#!/bin/bash

echo "=== Checking PostgreSQL ==="
docker exec postgres_service psql -U consumerrights_user -d consumer_rights -c "SELECT 1;" && echo "OK" || echo "FAILED"

echo "=== Checking ChromaDB ==="
curl -s http://localhost:8002/api/v1/heartbeat && echo "OK" || echo "FAILED"

echo "=== Checking RabbitMQ ==="
curl -s http://localhost:15672 > /dev/null && echo "OK" || echo "FAILED"

echo "=== Checking Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Save this as `health_check.sh`, make it executable (`chmod +x health_check.sh`), and run it.

---

## Getting More Help

1. **Check logs systematically:**
   ```bash
   docker logs postgres_service
   docker logs chroma_service
   docker logs rabbitmq
   docker logs rag-core
   docker logs llm-connector
   docker logs psql_worker
   ```

2. **Check Docker resources:**
   ```bash
   docker system df
   docker system prune  # Clean up if needed
   ```

3. **Verify configuration:**
   ```bash
   # Validate docker-compose files
   cd shared_services/chroma && docker-compose config
   cd ../../live_inference_pipeline && docker-compose config
   cd ../data_prepartion_pipeline && docker-compose config
   ```

4. **Check documentation:**
   - SETUP_GUIDE.md - Setup instructions
   - SECURITY_FIXES.md - Security details
   - DEPLOYMENT_SUMMARY.md - Deployment overview
