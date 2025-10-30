# Consumer Rights RAG System

**Author:** Magesh Boopathi

A production-grade Retrieval-Augmented Generation (RAG) system for answering consumer rights legal questions using microservices architecture, semantic chunking, and advanced embeddings.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Development](#development)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Documentation](#documentation)
- [Technology Stack](#technology-stack)
- [Contributing](#contributing)

---

## Overview

This system provides intelligent legal assistance for consumer rights questions through:

1. **Semantic Document Processing** - Advanced chunking with MPNet embeddings
2. **PII Protection** - Automatic redaction of sensitive information
3. **Multi-Provider LLM Support** - AWS Bedrock, GCP Vertex AI, and Ollama
4. **Vector Search** - Semantic search using ChromaDB
5. **Production-Ready** - CI/CD, monitoring, security, and scalability

### Architecture Patterns

- **Microservices** - Independently deployable services
- **Event-Driven** - RabbitMQ message queue
- **Containerized** - Full Docker Compose deployment
- **Cloud-Native** - AWS EC2 deployment with auto-scaling

---

## Key Features

### Core Capabilities

- **Semantic Chunking** - Groups sentences by semantic similarity
- **MPNet Embeddings** - 768-dimensional vectors (all-mpnet-base-v2)
- **Multi-LLM Support** - AWS Bedrock, GCP Vertex AI, Ollama
- **PII Redaction** - Names, emails, phone numbers
- **Vector Search** - ChromaDB with persistent storage
- **Conversation History** - PostgreSQL audit trails
- **Real-time Processing** - Event-driven architecture

### Production Features

- **CI/CD Pipeline** - GitHub Actions automatic deployment to EC2
- **Security** - Rate limiting, cost control, DDoS protection
- **Monitoring** - Health checks, metrics, logging
- **Experiments** - MLflow tracking for chunking strategies
- **API Gateway** - FastAPI with authentication
- **Scalability** - Horizontal scaling support

---

## Architecture

### System Overview

```
DATA PREPARATION PIPELINE
PDF -> Semantic Chunker -> MPNet Embedder -> ChromaDB
       (500 chars)         (768-dim)         (279 chunks)
       
Orchestrated by: Apache Airflow

LIVE INFERENCE PIPELINE
User Query -> API Gateway -> PII Filter -> RAG Core -> LLM
                |              |            |          |
           Authentication   Redaction   Retrieval  Generation
                                                       |
                                              PostgreSQL Worker
```

### Message Flow

```
API Gateway -> terminal_messages -> PII Filter -> redacted_queue
                                                      |
                                                  RAG Core
                                                      |
                                             query_and_context
                                                      |
                                              LLM Connector
                                                      |
                                    +-----------------+-----------------+
                                    |                                   |
                            llm_output_queue                       CUD_queue
                                    |                                   |
                                Response                        PostgreSQL Worker
```

---

## Quick Start

### Prerequisites

- Docker (v20.10+)
- Docker Compose (v2.0+)
- Python 3.9+
- 8GB RAM minimum

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/mageshboopathi/consumer-rights.git
cd consumer-rights

# 2. Create shared network
docker network create shared_network

# 3. Start shared services (ChromaDB, PostgreSQL)
cd shared_services/chroma
docker-compose up -d
cd ../..

# 4. Start data preparation pipeline
cd data_prepartion_pipeline
docker-compose up -d
cd ..

# 5. Start live inference pipeline
cd live_inference_pipeline
docker-compose up -d
cd ..

# 6. Access services
# Airflow: http://localhost:8080
# RabbitMQ: http://localhost:15672 (guest/guest)
# API Gateway: http://localhost:3001
```

### Process Documents

```bash
# Place PDFs in data_prepartion_pipeline/data/
# Trigger Airflow DAG at http://localhost:8080
# DAG ID: document_processing_pipeline
```

### Query System

```bash
# Option 1: CLI
cd live_inference_pipeline/CLI
python cli.py

# Option 2: API
curl -X POST http://localhost:3001/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my consumer rights?"}'
```

---

## Deployment

### AWS EC2 Deployment

#### Step 1: Deploy EC2 Instance (One-Time)

```bash
# Run deployment script
./deploy_to_ec2.sh

# Follow prompts to enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - PostgreSQL password

# Wait 5-10 minutes for setup to complete
```

This creates:
- EC2 Spot Instance (t3.small)
- Security groups
- IAM roles
- Installs Docker and services
- Clones repository
- Starts all services

#### Step 2: Setup GitHub Secrets (One-Time)

Configure 3 secrets in GitHub for automatic deployment:

**Using GitHub CLI:**
```bash
# Get your EC2 IP
EC2_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=consumer-rights-rag" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text \
  --region ap-south-1)

# Set secrets
gh secret set EC2_HOST --body "$EC2_IP"
gh secret set EC2_USER --body "ubuntu"
gh secret set EC2_SSH_KEY < consumer-rights-key.pem
```

**Using GitHub Web Interface:**
1. Go to repository **Settings** > **Secrets and variables** > **Actions**
2. Add 3 secrets:
   - `EC2_HOST`: Your EC2 public IP
   - `EC2_USER`: `ubuntu`
   - `EC2_SSH_KEY`: Contents of `consumer-rights-key.pem`

See [SETUP_GITHUB_SECRETS.md](SETUP_GITHUB_SECRETS.md) for detailed instructions.

#### Step 3: Deploy Automatically

```bash
# Push to main branch
git push origin main

# GitHub Actions automatically:
# 1. Connects to EC2 via SSH
# 2. Pulls latest code
# 3. Rebuilds changed services
# 4. Restarts containers
# 5. Verifies services are running
```

### CI/CD Pipeline

- **Trigger**: Push to main branch or manual workflow dispatch
- **Process**: SSH to EC2, pull code, rebuild, restart services
- **Time**: 2-3 minutes
- **Monitoring**: https://github.com/YOUR_USERNAME/consumer-rights/actions

### Manual Deployment

If you prefer manual deployment:

```bash
# SSH to EC2
ssh -i consumer-rights-key.pem ubuntu@YOUR_EC2_IP

# Pull latest code
cd consumer-rights
git pull origin main

# Restart services
cd live_inference_pipeline
docker-compose down
docker-compose up -d --build
```

---

## Development

### Project Structure

```
consumer-rights/
├── data_prepartion_pipeline/       # ETL pipeline
│   ├── Chunking/
│   │   ├── semantic_chunker.py    # Semantic chunking
│   │   ├── naive_chunker.py       # Naive chunking
│   │   └── chunker_factory.py     # Factory pattern
│   ├── Embedding/
│   │   └── embeder.py             # MPNet embeddings
│   └── dags/
│       └── process_document_dag.py # Airflow DAG
│
├── live_inference_pipeline/        # Real-time inference
│   ├── api_gateway/               # FastAPI gateway
│   ├── PII/                       # PII redaction
│   ├── RAG-Core/                  # Vector retrieval
│   ├── LLM-Connector/             # Multi-LLM support
│   ├── llm_providers/             # Provider implementations
│   ├── security/                  # Security features
│   └── monitoring/                # Metrics & logging
│
├── experiments/                    # Chunking experiments
├── shared_services/                # Shared infrastructure
├── tests/                         # Test suite
├── .github/workflows/             # CI/CD pipelines
└── docs/                          # Documentation
```

### Configuration

System configuration is centralized in `config.py`:

```python
# RAG Configuration
RAG_CHUNKING_STRATEGY=semantic
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50
RAG_SEMANTIC_SIMILARITY_THRESHOLD=0.5
RAG_EMBEDDING_MODEL=all-mpnet-base-v2
RAG_EMBEDDING_DIMENSION=768

# ChromaDB
CHROMA_HOST=chroma_service
CHROMA_PORT=8000
CHROMA_COLLECTION_NAME=semantic_mpnetbasev_500_20251030

# LLM Provider (bedrock, vertex_ai, ollama)
LLM_PROVIDER=vertex_ai
```

---

## Code Quality

### Tools Available

```bash
# Format all code (Black + isort + flake8)
./format_code.sh

# Individual checks
black . --exclude '(chroma_data|mlruns|\.venv|venv)'
isort . --skip chroma_data --skip mlruns
flake8 . --exclude=chroma_data,mlruns,.venv,venv
mypy . --exclude chroma_data --exclude mlruns
pytest
```

### Code Standards

- **Line Length** - 100 characters
- **String Quotes** - Double quotes preferred
- **Import Order** - stdlib -> third-party -> first-party
- **Type Hints** - Encouraged but optional
- **Docstrings** - Google style

### Configuration Files

- `pyproject.toml` - Black, isort, mypy configuration
- `pytest.ini` - Test configuration
- `.pre-commit-config.yaml` - Pre-commit hooks

---

## Testing

### Test Suite

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_rag_core.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v
```

### Test Categories

- `test_api_gateway.py` - API Gateway tests
- `test_rag_core.py` - RAG Core tests
- `test_pii_filter.py` - PII redaction tests
- `test_llm_connector.py` - LLM integration tests
- `test_llm_providers.py` - Multi-provider tests
- `test_integration_e2e.py` - End-to-end tests
- `test_security_phase1.py` - Security tests

---

## Documentation

### Essential Documentation

- **README.md** - This file (overview)
- **CONTRIBUTING.md** - Contribution guidelines
- **docs/CODE_QUALITY.md** - Code quality tools guide

### API Documentation

- **API Gateway** - http://localhost:3001/docs (Swagger UI)
- **Chunker Service** - http://localhost:5001/api/docs
- **Embedder Service** - http://localhost:5002/api/docs

### Monitoring

- **Airflow** - http://localhost:8080
- **RabbitMQ** - http://localhost:15672
- **MLflow** - http://localhost:5000 (experiments)

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Orchestration** | Apache Airflow | 2.9.2 |
| **Message Queue** | RabbitMQ | 3-management |
| **Vector Database** | ChromaDB | 0.5.23 |
| **Relational DB** | PostgreSQL | 13 |
| **LLM Providers** | AWS Bedrock, GCP Vertex AI, Ollama | Latest |
| **Embeddings** | Sentence Transformers | all-mpnet-base-v2 |
| **API Framework** | FastAPI | Latest |
| **PDF Processing** | PyMuPDF (fitz) | Latest |
| **Code Quality** | Black, isort, flake8, mypy | Latest |
| **Testing** | pytest | Latest |
| **CI/CD** | GitHub Actions | Latest |
| **Containerization** | Docker & Docker Compose | Latest |

---

## Security Features

### Built-in Security

- **PII Redaction** - Automatic removal of sensitive data
- **Rate Limiting** - Per-user request limits
- **Cost Control** - Budget limits per user
- **DDoS Protection** - Request throttling
- **Input Validation** - Prompt injection detection
- **Output Validation** - Response sanitization
- **Authentication** - JWT-based API auth
- **Network Isolation** - Docker network segmentation

### Security Configuration

```python
# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600  # 1 hour

# Cost Control
COST_LIMIT_PER_USER=10.0  # USD
COST_LIMIT_WINDOW=86400   # 24 hours

# DDoS Protection
DDOS_MAX_REQUESTS=1000
DDOS_WINDOW=60  # 1 minute
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Run code quality checks (`./format_code.sh`)
5. Run tests (`pytest`)
6. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

See CONTRIBUTING.md for detailed guidelines.

---

## License

This project is licensed under the MIT License.

---

## Author

**Magesh Boopathi**

- GitHub: [@mageshboopathi](https://github.com/mageshboopathi)

---

## Quick Commands Reference

```bash
# Development
./format_code.sh                    # Format code
pytest                              # Run tests
docker-compose up -d                # Start services

# Deployment
./deploy_to_ec2.sh                  # Deploy to EC2
./setup_github_secrets.sh           # Setup CI/CD
git push origin main                # Auto-deploy

# Code Quality
flake8 .                            # Lint code
mypy .                              # Type check
black .                             # Format code

# Monitoring
docker-compose logs -f <service>    # View logs
docker ps                           # Check services
curl http://localhost:3001/health   # Health check
```

---

**Last Updated**: October 30, 2025
