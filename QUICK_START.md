# Quick Start Guide

Get the Consumer Rights RAG system running in 5 minutes.

---

## Prerequisites

- Docker & Docker Compose installed
- 8GB RAM available
- 10GB disk space

---

## Fast Track Deployment

```bash
# 1. Create Docker network
docker network create shared_network

# 2. Start all services (from project root)
cd shared_services/chroma && docker-compose up -d && cd ../..
cd data_prepartion_pipeline && docker-compose up -d && cd ..
cd live_inference_pipeline && docker-compose up -d && cd ..

# 3. Wait 30 seconds for services to initialize
sleep 30

# 4. Test the system
cd live_inference_pipeline/CLI
python cli.py
```

---

## Verify Everything Works

```bash
# Check all containers are running
docker ps | grep -E "postgres|chroma|rabbitmq|ollama|rag-core|llm-connector|psql_worker"

# Should see 7+ containers running
```

---

## Test Query

In the CLI, try:
```
> What are my rights if I receive a defective product?
```

Expected: Response in 5-8 seconds (first query) or 2-3 seconds (subsequent queries)

---

## Quick Health Checks

```bash
# Database
docker exec -it postgres_service psql -U consumerrights_user -d consumer_rights -c "\dt"

# ChromaDB
curl http://localhost:8002/api/v1/heartbeat

# RabbitMQ
curl http://localhost:15672
```

---

## Stop Everything

```bash
cd live_inference_pipeline && docker-compose down && cd ..
cd data_prepartion_pipeline && docker-compose down && cd ..
cd shared_services/chroma && docker-compose down && cd ../..
```

---

## Troubleshooting

**Services won't start?**
```bash
docker network create shared_network
docker-compose up -d --force-recreate
```

**Out of memory?**
```bash
# Increase Docker memory to 8GB in Docker Desktop settings
```

**Can't connect to database?**
```bash
# Check .env files exist
ls -la .env */.env
```

---

## Need More Help?

- **Full setup:** See `SETUP_GUIDE.md`
- **Security details:** See `SECURITY_FIXES.md`
- **Deployment info:** See `DEPLOYMENT_SUMMARY.md`

---

## You're Ready

System is running when `docker ps` shows all services as healthy/running.

**Happy querying!**
