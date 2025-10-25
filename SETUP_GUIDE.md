# Consumer Rights RAG System - Setup Guide

This guide walks you through setting up the Consumer Rights RAG system with all security fixes applied.

## Security Improvements Applied

- **SQL Injection Protection** - Parameterized queries with table whitelisting  
- **Secure Credentials** - Environment variables instead of hardcoded passwords  
- **Git Security** - Comprehensive .gitignore to prevent sensitive data commits  
- **Pinned Dependencies** - All package versions locked for reproducibility  
- **Performance Fix** - Model loads once at startup (3-5s improvement per query)  

---

## Prerequisites

- Docker and Docker Compose installed
- Git (for version control)
- At least 8GB RAM available
- 10GB free disk space

---

## Quick Start

### 1. Verify Environment Files

All `.env` files have been created with secure, randomly generated credentials:

```bash
# Check that .env files exist
ls -la .env
ls -la live_inference_pipeline/.env
ls -la data_prepartion_pipeline/.env
ls -la shared_services/chroma/.env
```

**Note:** All .env files are already configured with secure passwords.

### 2. Create Shared Network

The services communicate via a shared Docker network:

```bash
docker network create shared_network
```

### 3. Start Shared Services (PostgreSQL & ChromaDB)

```bash
cd shared_services/chroma
docker-compose up -d
cd ../..
```

Verify services are running:
```bash
docker ps | grep -E "postgres_service|chroma_service"
```

### 4. Start Data Preparation Pipeline (Airflow)

```bash
cd data_prepartion_pipeline
docker-compose up -d
cd ..
```

Wait for Airflow to initialize (~30 seconds), then access:
- Airflow UI: http://localhost:8080
- Default credentials: `admin` / `admin` (set on first login)

### 5. Start Live Inference Pipeline

```bash
cd live_inference_pipeline
docker-compose up -d
cd ..
```

Verify all services are running:
```bash
docker-compose ps
```

### 6. Test the System

```bash
cd live_inference_pipeline/CLI
python cli.py
```

Try a test query:
```
> What are consumer rights regarding defective products?
```

---

## Verification Steps

### Check Service Health

```bash
# Check all containers
docker ps

# Check logs for any errors
docker logs postgres_service
docker logs chroma_service
docker logs psql_worker
docker logs rag-core
```

### Verify Database Connection

```bash
# Connect to PostgreSQL
docker exec -it postgres_service psql -U consumerrights_user -d consumer_rights

# Inside psql, check the table
\dt
SELECT * FROM chat_history LIMIT 5;
\q
```

### Test ChromaDB

```bash
curl http://localhost:8002/api/v1/heartbeat
```

Should return: `{"nanosecond heartbeat": ...}`

### Test RabbitMQ

- Access RabbitMQ Management UI: http://localhost:15672
- Default credentials: `guest` / `guest`
- Check that queues are declared

---

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| ChromaDB | 8002 | Vector database |
| Airflow | 8080 | Data pipeline UI |
| RabbitMQ | 5672 | Message queue |
| RabbitMQ Management | 15672 | Queue monitoring |
| Ollama | 11434 | LLM inference |
| Chunker | 5001 | Document chunking |
| Embedder | 5002 | Text embedding |

---

## Security Configuration

### Generated Credentials

All passwords have been generated using `openssl rand -base64 32`:

- **PostgreSQL Password**: Unique 44-character secure string
- **Airflow DB Password**: Unique 44-character secure string  
- **Airflow Secret Key**: Unique 64-character secure string

### Allowed Database Tables

The PostgreSQL worker only accepts operations on whitelisted tables:

```python
ALLOWED_TABLES = ['chat_history']
```

To add more tables:
1. Create the table in `shared_services/chroma/postgres_init/init.sql`
2. Add table name to `ALLOWED_TABLES` in `live_inference_pipeline/psql_worker/worker.py`
3. Rebuild the worker: `docker-compose up -d --build psql-worker`

---

## Troubleshooting

### Issue: Services can't connect to PostgreSQL

**Solution:**
```bash
# Ensure shared network exists
docker network create shared_network

# Restart services
cd shared_services/chroma
docker-compose restart
```

### Issue: Permission denied errors

**Solution:**
```bash
# Fix permissions on data directories
chmod -R 755 shared_services/chroma/chroma_data
chmod -R 755 ollama_data
```

### Issue: Airflow webserver won't start

**Solution:**
```bash
# Initialize Airflow database
cd data_prepartion_pipeline
docker-compose run --rm airflow-webserver airflow db init
docker-compose up -d
```

### Issue: Model loading errors in RAG Core

**Solution:**
```bash
# The model downloads on first run, may take 2-3 minutes
docker logs -f rag-core

# Wait for: "[i] Model loaded successfully."
```

### Issue: Out of memory errors

**Solution:**
```bash
# Increase Docker memory limit to 8GB
# Docker Desktop → Settings → Resources → Memory

# Or reduce concurrent services
docker-compose up -d rabbitmq ollama rag-core llm-connector
```

---

## Environment Variables Reference

### Live Inference Pipeline

```bash
DB_HOST=postgres                    # PostgreSQL hostname
DB_USER=consumerrights_user        # Database username
DB_PASSWORD=<secure_password>      # Database password
DB_NAME=consumer_rights            # Database name
RABBITMQ_HOST=rabbitmq             # RabbitMQ hostname
RABBITMQ_QUEUE=CUD_queue           # Queue name for DB operations
```

### Data Preparation Pipeline

```bash
AIRFLOW_DB_USER=airflow                    # Airflow database user
AIRFLOW_DB_PASSWORD=<secure_password>      # Airflow database password
AIRFLOW_DB_NAME=airflow                    # Airflow database name
AIRFLOW_SECRET_KEY=<secure_key>            # Airflow webserver secret
```

### Shared Services

```bash
POSTGRES_USER=consumerrights_user          # PostgreSQL username
POSTGRES_PASSWORD=<secure_password>        # PostgreSQL password
POSTGRES_DB=consumer_rights                # PostgreSQL database name
```

---

## Updating the System

### Pull Latest Changes

```bash
git pull origin main
```

### Rebuild Services

```bash
# Rebuild specific service
cd live_inference_pipeline
docker-compose up -d --build rag-core

# Rebuild all services
docker-compose up -d --build
```

### Update Dependencies

After changing `requirements.txt`:
```bash
docker-compose build --no-cache <service-name>
docker-compose up -d <service-name>
```

---

## Cleanup

### Stop All Services

```bash
# Stop live inference
cd live_inference_pipeline
docker-compose down

# Stop data preparation
cd ../data_prepartion_pipeline
docker-compose down

# Stop shared services
cd ../shared_services/chroma
docker-compose down
```

### Remove All Data (WARNING: Destructive)

```bash
# Remove volumes
docker volume prune -f

# Remove network
docker network rm shared_network

# Remove local data
rm -rf shared_services/chroma/chroma_data/*
rm -rf ollama_data/*
```

---

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)

---

## Getting Help

If you encounter issues:

1. Check the logs: `docker logs <container-name>`
2. Verify environment variables: `docker-compose config`
3. Check service health: `docker ps`
4. Review `SECURITY_FIXES.md` for security details
5. Consult `CODE_REVIEW.md` for code-level documentation

---

## System Health Checklist

Before running queries, verify:

- [ ] Shared network created
- [ ] PostgreSQL is running and accessible
- [ ] ChromaDB is running (port 8002)
- [ ] RabbitMQ is running (ports 5672, 15672)
- [ ] Ollama is running (port 11434)
- [ ] All worker services are running
- [ ] No error messages in logs
- [ ] Database tables created successfully
- [ ] Model loaded in RAG Core

---

**System is ready when all services show as "healthy" or "running" in `docker ps`.**
