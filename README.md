# Consumer Rights RAG System

**Author:** Magesh Boopathi

A production-grade Retrieval-Augmented Generation (RAG) system designed to answer consumer rights legal questions using a microservices architecture with Apache Airflow, RabbitMQ, ChromaDB, and Ollama.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [System Components](#system-components)
- [Technology Stack](#technology-stack)
- [Evaluation & Monitoring](#evaluation--monitoring)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This system provides intelligent legal assistance for consumer rights questions by:

1. **Processing legal documents** (PDFs) into searchable vector embeddings
2. **Filtering sensitive information** (PII) from user queries
3. **Retrieving relevant legal context** from a vector database
4. **Generating accurate answers** using a local LLM (Gemma 2B)
5. **Storing conversation history** for audit and analysis

The architecture follows a **microservices pattern** with two main pipelines:
- **Data Preparation Pipeline**: ETL process for document ingestion
- **Live Inference Pipeline**: Real-time query processing

---

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   DATA PREPARATION PIPELINE                      │
│                                                                   │
│  PDF Document → Chunker → Embedder → ChromaDB                   │
│                    ↓          ↓          ↓                       │
│                 Airflow DAG Orchestration                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   LIVE INFERENCE PIPELINE                        │
│                                                                   │
│  User Query                                                      │
│      ↓                                                           │
│  PII Filter (redacts sensitive data)                            │
│      ↓                                                           │
│  RAG Core (retrieves context from ChromaDB)                     │
│      ↓                                                           │
│  LLM Connector (generates answer via Ollama)                    │
│      ↓                    ↓                                      │
│  User Response    PostgreSQL Worker (stores history)            │
└─────────────────────────────────────────────────────────────────┘
```

### Message Queue Flow

```
terminal_messages → PII Filter → redacted_queue → RAG Core 
                                                      ↓
                                              query_and_context
                                                      ↓
                                              LLM Connector
                                                      ↓
                                        ┌─────────────┴─────────────┐
                                        ↓                           ↓
                                llm_output_queue              CUD_queue
                                        ↓                           ↓
                                    CLI Client              PostgreSQL Worker
```

---

## Features

### Core Features
- **Document Processing**: Automated ETL pipeline for PDF ingestion
- **Vector Search**: Semantic search using ChromaDB
- **PII Protection**: Automatic redaction of names, emails, and phone numbers
- **Local LLM**: Privacy-focused inference using Ollama (no external APIs)
- **Conversation History**: PostgreSQL storage for audit trails
- **Real-time Processing**: Event-driven architecture with RabbitMQ

### Advanced Features
- **RAG Evaluation**: Automated metrics using DeepEval and Ragas
- **Orchestration**: Apache Airflow for workflow management
- **Containerized**: Full Docker Compose deployment
- **Monitoring**: MLflow integration for experiment tracking
- **Health Checks**: Built-in service health monitoring
- **Retry Logic**: Robust error handling and recovery

---

## Prerequisites

- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **Python** (3.8+) - for local CLI usage
- **Node.js** (optional) - for ChatbotUI
- **8GB RAM minimum** (for running Ollama models)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/mageshboopathi/consumer-rights.git
cd consumer-rights
```

### 2. Create Shared Network

```bash
docker network create shared_network
```

### 3. Start Shared Services

```bash
cd shared_services/chroma
docker-compose up -d
cd ../..
```

This starts:
- ChromaDB (port 8002)
- PostgreSQL (port 5432)

### 4. Start Data Preparation Pipeline

```bash
cd data_prepartion_pipeline
docker-compose up -d
cd ..
```

This starts:
- Chunker service (port 5001)
- Embedder service (port 5002)
- Airflow webserver (port 8080)
- Airflow scheduler

### 5. Start Live Inference Pipeline

```bash
cd live_inference_pipeline
docker-compose up -d
cd ..
```

This starts:
- RabbitMQ (ports 5672, 15672)
- Ollama (port 11434)
- PII Filter
- RAG Core
- LLM Connector
- PostgreSQL Worker

### 6. Initialize Airflow

```bash
# Access Airflow webserver
# Navigate to http://localhost:8080
# Default credentials: admin/admin (set during first run)
```

---

## Usage

### Processing Documents

1. **Place PDF documents** in `data_prepartion_pipeline/data/`
2. **Access Airflow UI**: http://localhost:8080
3. **Trigger DAG**: `document_processing_pipeline`
4. **Monitor progress** through Airflow UI

The DAG will:
- Extract text from PDFs
- Chunk text into 500-character segments
- Generate embeddings using all-MiniLM-L6-v2
- Store in ChromaDB collection `document_embeddings`

### Querying the System

#### Option 1: CLI Interface

```bash
cd live_inference_pipeline/CLI
python cli.py
```

Then enter your questions:
```
> What are my rights as a consumer when purchasing defective products?
```

#### Option 2: With Evaluation

```bash
cd live_inference_pipeline/CLI
python evaluation.py
```

This runs queries with real-time evaluation metrics.

### Monitoring Services

- **Airflow UI**: http://localhost:8080
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **ChromaDB**: http://localhost:8002

---

## System Components

### Data Preparation Pipeline

#### Chunker Service
- **Port**: 5001
- **Endpoint**: `POST /api/chunk`
- **Function**: Extracts and chunks PDF text
- **Chunk Size**: 500 characters with 50-character overlap

#### Embedder Service
- **Port**: 5002
- **Endpoint**: `POST /api/embed`
- **Function**: Generates vector embeddings
- **Model**: `all-MiniLM-L6-v2`
- **Batch Size**: 50 chunks

#### Airflow DAG
- **DAG ID**: `document_processing_pipeline`
- **Schedule**: Manual trigger
- **Tasks**:
  1. `call_chunker_service`: Process PDF
  2. `call_embedder_service`: Generate embeddings
  3. `ingest_into_chroma`: Store in vector DB

### Live Inference Pipeline

#### PII Filter
- **Queue In**: `terminal_messages`
- **Queue Out**: `redacted_queue`
- **Function**: Redacts names, emails, phone numbers
- **Patterns**:
  - Names: `[NAME]`
  - Emails: `[EMAIL]`
  - Phones: `[PHONE]`

#### RAG Core
- **Queue In**: `redacted_queue`
- **Queue Out**: `query_and_context`
- **Function**: Retrieves relevant context
- **Retrieval**: Top 3 documents from ChromaDB
- **Embedding Model**: `all-MiniLM-L6-v2`

#### LLM Connector
- **Queue In**: `query_and_context`
- **Queue Out**: `llm_output_queue`, `CUD_queue`
- **Function**: Generates answers using LLM
- **Model**: Gemma 2B Instruct (via Ollama)
- **Features**: Chat history persistence

#### PostgreSQL Worker
- **Queue In**: `CUD_queue`
- **Function**: Handles database operations
- **Operations**: CREATE, UPDATE, DELETE
- **Table**: `chat_history`

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Orchestration** | Apache Airflow | 2.9.2 |
| **Message Queue** | RabbitMQ | 3-management |
| **Vector Database** | ChromaDB | Latest |
| **Relational DB** | PostgreSQL | 13 |
| **LLM** | Ollama (Gemma) | 2B Instruct |
| **Embeddings** | Sentence Transformers | all-MiniLM-L6-v2 |
| **PDF Processing** | PyMuPDF (fitz) | Latest |
| **Web Framework** | Flask + Gunicorn | Latest |
| **Evaluation** | DeepEval, Ragas | Latest |
| **Experiment Tracking** | MLflow | Latest |
| **Containerization** | Docker & Docker Compose | Latest |

---

## Evaluation & Monitoring

### RAG Evaluation

The system includes comprehensive evaluation capabilities:

#### Offline Evaluation
```bash
cd data_prepartion_pipeline/evaluation
python evaluate_rag.py
```

**Metrics**:
- Context Precision
- Retrieval Quality

**Output**: Results logged to MLflow (port 5001)

#### Online Evaluation

Built into the CLI (`evaluation.py`):
- **Answer Relevancy Metric**: Measures response relevance
- **Contextual Precision Metric**: Evaluates context quality
- **Threshold**: 0.8 for both metrics

### Monitoring

#### RabbitMQ Queues
- `terminal_messages`: User input queue
- `redacted_queue`: PII-filtered queries
- `query_and_context`: RAG prompts
- `llm_output_queue`: Final responses
- `CUD_queue`: Database operations
- `process_updates`: Status updates

#### Database Tables
```sql
-- Chat History
SELECT * FROM chat_history 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## Project Structure

```
consumer-rights/
├── data_prepartion_pipeline/
│   ├── Chunking/
│   │   ├── chunker.py          # PDF chunking service
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── Embedding/
│   │   ├── embeder.py          # Embedding generation service
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── dags/
│   │   └── process_document_dag.py  # Airflow DAG
│   ├── data/
│   │   └── sample.pdf          # Sample documents
│   ├── evaluation/
│   │   ├── evaluate_rag.py     # RAG evaluation script
│   │   └── sample_golden_dataset.csv
│   └── docker-compose.yml
│
├── live_inference_pipeline/
│   ├── CLI/
│   │   ├── cli.py              # Command-line interface
│   │   └── evaluation.py       # CLI with evaluation
│   ├── PII/
│   │   ├── piiFilter.py        # PII redaction service
│   │   └── Dockerfile
│   ├── RAG-Core/
│   │   ├── core.py             # RAG retrieval service
│   │   └── dockerfile
│   ├── LLM-Connector/
│   │   ├── connector.py        # LLM inference service
│   │   └── dockerfile
│   ├── psql_worker/
│   │   ├── worker.py           # Database worker
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── ollama/
│   │   ├── Dockerfile
│   │   └── entrypoint.sh
│   └── docker-compose.yml
│
├── shared_services/
│   └── chroma/
│       ├── docker-compose.yml
│       └── postgres_init/
│           └── init.sql        # Database schema
│
├── chroma_data/                # ChromaDB persistent storage
└── README.md
```

---

## Configuration

### Environment Variables

#### Data Pipeline
```bash
# Airflow Configuration
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
```

#### Inference Pipeline
```bash
# RabbitMQ
RABBITMQ_HOST=rabbitmq

# ChromaDB
CHROMA_HOST=chroma_service
CHROMA_PORT=8000

# PostgreSQL
DB_HOST=postgres
DB_USER=myuser
DB_PASSWORD=mypass
DB_NAME=consumer_rights

# Ollama
OLLAMA_HOST=ollama
OLLAMA_MODEL=gemma:2b-instruct
```

### Customization

#### Change Chunk Size
Edit `data_prepartion_pipeline/Chunking/chunker.py`:
```python
def chunk_document(file_stream, chunk_size: int = 500, overlap: int = 50):
```

#### Change Embedding Model
Edit embedding services to use different models:
```python
model = SentenceTransformer('all-MiniLM-L6-v2')  # Change this
```

#### Change LLM Model
Edit `live_inference_pipeline/LLM-Connector/connector.py`:
```python
OLLAMA_MODEL = 'gemma:2b-instruct'  # Change to llama2, mistral, etc.
```

#### Adjust Retrieval Results
Edit `live_inference_pipeline/RAG-Core/core.py`:
```python
search_results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3,  # Change number of retrieved documents
)
```

---

## Security Features

1. **PII Redaction**: Automatic removal of sensitive information
2. **Local Processing**: No external API calls (privacy-focused)
3. **Network Isolation**: Docker network segmentation
4. **Database Authentication**: PostgreSQL with credentials
5. **Message Persistence**: Durable queues for reliability

---

## Troubleshooting

### Services Not Starting

```bash
# Check Docker logs
docker-compose logs <service-name>

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up -d --build
```

### ChromaDB Connection Issues

```bash
# Verify ChromaDB is running
curl http://localhost:8002/api/v1/heartbeat

# Check network connectivity
docker network inspect shared_network
```

### RabbitMQ Queue Issues

```bash
# Access RabbitMQ Management UI
# http://localhost:15672
# Username: guest, Password: guest

# Purge queues if needed
docker exec rabbitmq rabbitmqctl purge_queue terminal_messages
```

### Ollama Model Issues

```bash
# Pull model manually
docker exec ollama ollama pull gemma:2b-instruct

# List available models
docker exec ollama ollama list
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Author

**Magesh Boopathi**

- GitHub: [@mageshboopathi](https://github.com/mageshboopathi)

---

## Acknowledgments

- Apache Airflow for workflow orchestration
- ChromaDB for vector storage
- Ollama for local LLM inference
- RabbitMQ for message queuing
- The open-source community

---

## Support

For questions or issues, please:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review existing GitHub issues
3. Create a new issue with detailed information

---

## Roadmap

- [ ] Add support for multiple document formats (DOCX, TXT)
- [ ] Implement user authentication and authorization
- [ ] Add web-based UI for document management
- [ ] Support for multiple languages
- [ ] Advanced RAG techniques (HyDE, Query Expansion)
- [ ] Streaming responses for better UX
- [ ] Integration with external legal databases
- [ ] Advanced analytics dashboard

---

**Built with care by Magesh Boopathi**
