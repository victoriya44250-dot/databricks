# Lab 12: AI Capstone: RAG & AI-Assisted Development

## 1. Overview

This project implements a Retrieval-Augmented Generation (RAG) pipeline for question answering on agricultural risk management using Databricks (continue topic of agricultural databases).

**Workspace:** Personal Databricks Free Edition, catalog `workspace`. This environment was selected to avoid the ongoing costs associated with running Vector Search in the course PROD workspace.

**Data source:** [World Bank report](https://documents1.worldbank.org/curated/en/099032326044016306/pdf/P510294-1b00a8b1-c76f-419d-953a-46bd5805c044.pdf).

**Technology stack:** Python, PySpark, Delta Lake, Unity Catalog, Databricks AI Search, Foundation Model APIs, AI Dev Kit, MCP, Declarative Automation Bundles and GitHub Actions.

## 2. Architecture

```text
PDF document
    ↓
Unity Catalog Volume
    ↓
Document pages (Delta)
    ↓
Document chunks (Delta)
    ↓
Embeddings & Vector Search
    ↓
Filtered Top-5 retrieval
    ↓
LLM + retrieved context
    ↓
Answer with page citations
    ↓
Logging & evaluation
```

## 3. Project Structure

```text
lab12-rag/
├── notebooks/
│   ├── 01_ingest_pdf_pages.py
│   ├── 02_prepare_chunks.py
│   ├── 03_create_search_index.py
│   ├── 04_retrieval_test.py
│   ├── 05_rag_answer.py
│   ├── 06_evaluation.py
│   └── 07_smoke_test.py
├── src/
│   ├── __init__.py
│   └── rag_helpers.py
├── scripts/
│   ├── check_mcp.py
│   ├── check_plan.py
│   └── check_project.py
├── tests/
├── screenshots/
├── databricks.yml
├── requirements-dev.txt
├── AI_DEV_KIT_EVIDENCE.md
├── .gitignore
└── README.md
```

- `notebooks/`- document ingestion, chunking, indexing, retrieval, question answering and evaluation.
- `src/` - shared retrieval, prompt construction and citation validation utilities.
- `scripts/` - MCP connectivity, deployment safety and project validation checks.
- `tests/` - unit and mocked integration tests.
- `screenshots/` - implementation and execution evidence.
- `databricks.yml` - Bundle configuration for QA and smoke Jobs.
- `.github/workflows/lab12.yml` - automated CI/CD workflow located in the repository root.

## 4. Part A — RAG Implementation

### Data Preparation and Retrieval

| Parameter | Value |
|---|---|
| Document pages | 147 |
| Document chunks | 550 |
| Chunk size | 1200 characters |
| Chunk overlap | 200 characters |
| Embedding model | databricks-qwen3-embedding-0-6b |
| Embedding dimension | 1024 |
| Index type | Delta Sync |
| Sync mode | Triggered |
| Retrieval | ANN / HYBRID |
| Top-K | 5 |
| LLM | databricks-gpt-oss-120b |

Chunks contain deterministic identifiers, document text and page metadata. Metadata filtering restricts retrieval to selected