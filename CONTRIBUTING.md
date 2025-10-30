# Contributing to Consumer Rights RAG System

Thank you for your interest in contributing to this project.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

---

## Getting Started

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Git

### Setup Development Environment

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/consumer-rights.git
cd consumer-rights

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install black isort flake8 mypy pytest

# 4. Create shared network
docker network create shared_network

# 5. Start services
cd shared_services/chroma && docker-compose up -d && cd ../..
cd data_prepartion_pipeline && docker-compose up -d && cd ..
cd live_inference_pipeline && docker-compose up -d && cd ..
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write clear, concise code
- Follow code standards
- Add tests for new features
- Update documentation

### 3. Test Your Changes

```bash
# Run code formatting
./format_code.sh

# Run tests
pytest

# Run type checking
mypy .

# Run linting
flake8 .
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add semantic chunking support"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Code Standards

### Python Style Guide

We follow PEP 8 with some modifications:

#### Line Length
```python
# Maximum 100 characters per line
MAX_LINE_LENGTH = 100
```

#### String Quotes
```python
# Prefer double quotes
message = "Hello, world!"
```

#### Import Order
```python
# 1. Standard library
import os
import sys

# 2. Third-party
import numpy as np
from flask import Flask

# 3. First-party
from data_prepartion_pipeline import chunker
from live_inference_pipeline import rag_core
```

#### Type Hints
```python
# Encouraged but not required
def process_query(query: str, max_results: int = 3) -> list[dict]:
    """Process user query and return results."""
    pass
```

### Code Formatting Tools

#### Black (Code Formatter)
```bash
black . --exclude '(chroma_data|mlruns|\.venv|venv)'
```

#### isort (Import Sorter)
```bash
isort . --skip chroma_data --skip mlruns
```

#### flake8 (Linter)
```bash
flake8 . --exclude=chroma_data,mlruns,.venv,venv
```

#### mypy (Type Checker)
```bash
mypy . --exclude chroma_data --exclude mlruns
```

---

## Testing

### Writing Tests

```python
import pytest
from your_module import your_function

def test_your_function():
    """Test your_function with valid input."""
    result = your_function("input")
    assert result == "expected_output"

def test_your_function_error():
    """Test your_function with invalid input."""
    with pytest.raises(ValueError):
        your_function(None)
```

### Running Tests

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

---

## Pull Request Process

### Before Submitting

- Code follows style guidelines
- All tests pass
- New tests added for new features
- Documentation updated
- Commit messages are clear
- Branch is up to date with main

### Review Process

1. **Automated Checks** - CI/CD runs tests
2. **Code Review** - Maintainer reviews code
3. **Feedback** - Address review comments
4. **Approval** - Maintainer approves PR
5. **Merge** - PR merged to main

### After Merge

- PR automatically deploys to EC2 via CI/CD
- Monitor GitHub Actions for deployment status

---

## Resources

- [README.md](README.md) - Project overview
- [docs/CODE_QUALITY.md](docs/CODE_QUALITY.md) - Code quality guide

---

**Questions?** Create an issue or reach out to @mageshboopathi
