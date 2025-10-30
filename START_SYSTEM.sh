#!/bin/bash

# Consumer Rights RAG System - Startup Script
# This script ensures all services start in the correct order

set -e  # Exit on error

echo "=========================================="
echo "Consumer Rights RAG System Startup"
echo "=========================================="
echo ""

# Step 1: Start Shared Services (CRITICAL FIRST)
echo "[1/3] Starting Shared Services (ChromaDB & PostgreSQL)..."
cd shared_services/chroma
docker-compose up -d
echo " Shared services started"
echo ""

# Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 10
echo ""

# Step 2: Start Data Preparation Pipeline (Optional - only if adding documents)
echo "[2/3] Starting Data Preparation Pipeline..."
cd ../../data_prepartion_pipeline
docker-compose up -d chunker embedder
echo " Data preparation services started"
echo ""

# Step 3: Start Live Inference Pipeline
echo "[3/3] Starting Live Inference Pipeline..."
cd ../live_inference_pipeline
docker-compose up -d
echo " Live inference pipeline started"
echo ""

# Wait for all services to be ready
echo "Waiting for all services to initialize..."
sleep 15
echo ""

# Verify ChromaDB has data
echo "=========================================="
echo "Verifying System Status"
echo "=========================================="
echo ""

echo "Checking ChromaDB..."
docker exec rag-core python -c "
import chromadb
try:
    client = chromadb.HttpClient(host='chroma_service', port=8000)
    collections = client.list_collections()
    if len(collections) > 0:
        for col in collections:
            count = col.count()
            print(f' Collection \"{col.name}\" has {count} documents')
            if count == 0:
                print('  WARNING: Collection is empty! Run populate script.')
    else:
        print('WARNING: No collections found! Run populate script.')
except Exception as e:
    print(f'ERROR: Cannot connect to ChromaDB: {e}')
" 2>/dev/null || echo " ChromaDB check failed"

echo ""
echo "Checking RabbitMQ queues..."
docker exec rabbitmq rabbitmqctl list_queues name durable 2>/dev/null | tail -n +3 | head -6 || echo " RabbitMQ check failed"

echo ""
echo "=========================================="
echo "System Status"
echo "=========================================="
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "chroma|postgres|rabbitmq|rag-core|llm-connector|pii-filter|ollama|psql"

echo ""
echo "=========================================="
echo "Startup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. If ChromaDB is empty, populate it:"
echo "     docker cp simple_populate.py rag-core:/tmp/"
echo "     docker exec rag-core python /tmp/simple_populate.py"
echo ""
echo "  2. Test the system:"
echo "     cd live_inference_pipeline/CLI"
echo "     python cli.py"
echo ""
echo "  3. Access Airflow (optional):"
echo "     http://localhost:8080 (admin/admin)"
echo ""
