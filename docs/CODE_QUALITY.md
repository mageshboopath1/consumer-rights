# Code Quality Guide

This document describes all code quality tools and standards used in the Consumer Rights RAG System.

---

## Overview

We use multiple tools to ensure code quality:

| Tool | Purpose | Config File |
|------|---------|-------------|
| **Black** | Code formatting | `pyproject.toml` |
| **isort** | Import sorting | `pyproject.toml` |
| **flake8** | Linting | `pyproject.toml` |
| **mypy** | Type checking | `pyproject.toml` |
| **pytest** | Testing | `pytest.ini` |

---

## Quick Commands

### All-in-One Script

```bash
./format_code.sh
```

This runs:
1. isort (import sorting)
2. Black (code formatting)
3. flake8 (linting)

### Individual Commands

```bash
# Format code
black . --exclude '(chroma_data|mlruns|\.venv|venv)'

# Sort imports
isort . --skip chroma_data --skip mlruns --skip .venv

# Lint code
flake8 . --exclude=chroma_data,mlruns,.venv,venv

# Type check
mypy . --exclude chroma_data --exclude mlruns

# Run tests
pytest

# All checks
black . && isort . && flake8 . && mypy . && pytest
```

---

## Tools

### 1. Black - Code Formatter

**Purpose**: Automatically formats Python code to a consistent style.

**Usage**:
```bash
# Format all files
black .

# Check without modifying
black . --check

# Show diff
black . --diff
```

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311']
```

---

### 2. isort - Import Sorter

**Purpose**: Sorts and organizes Python imports.

**Usage**:
```bash
# Sort all imports
isort .

# Check without modifying
isort . --check-only

# Show diff
isort . --diff
```

**Configuration** (`pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 100
skip_gitignore = true
known_first_party = ["experiments", "live_inference_pipeline", "data_prepartion_pipeline"]
```

---

### 3. flake8 - Linter

**Purpose**: Checks code for style violations and potential errors.

**Usage**:
```bash
# Check all files
flake8 .

# Check specific file
flake8 my_file.py

# Show statistics
flake8 . --statistics
```

**Common Error Codes**:
- `E501` - Line too long
- `F401` - Module imported but unused
- `F841` - Local variable assigned but never used
- `E402` - Module level import not at top of file
- `W503` - Line break before binary operator

---

### 4. mypy - Type Checker

**Purpose**: Static type checking for Python.

**Usage**:
```bash
# Check all files
mypy .

# Check specific file
mypy my_file.py

# Strict mode
mypy . --strict
```

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
```

---

### 5. pytest - Testing Framework

**Purpose**: Unit and integration testing.

**Usage**:
```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_rag_core.py::test_retrieval

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v
```

**Configuration** (`pytest.ini`):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

---

## Code Standards

### Line Length
- Maximum 100 characters per line

### String Quotes
- Prefer double quotes (")

### Import Order
1. Standard library
2. Third-party packages
3. First-party packages

### Type Hints
- Encouraged but optional
- Use for public APIs

### Docstrings
- Google style
- Required for public functions

---

## Best Practices

### Before Committing

```bash
# 1. Format code
./format_code.sh

# 2. Run tests
pytest

# 3. Commit
git add .
git commit -m "feat: add new feature"
```

### Code Review Checklist

- Code formatted with Black
- Imports sorted with isort
- No flake8 errors
- Tests pass
- Documentation updated

---

**Last Updated**: October 30, 2025
