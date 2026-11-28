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

## 4. Part A - RAG Implementation

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

Chunks contain deterministic identifiers, source metadata and page numbers. Metadata filtering excludes selected non-content pages. Embeddings are managed by the Delta Sync index.

### Evaluation

Five questions were evaluated using the same LLM with and without retrieval.

| Question | Baseline | RAG (ANN) |
|---|---|---|
| Q1 — Catastrophic agricultural risks | Partially correct | Correct |
| Q2 — Insured production value | Insufficient information | Correct: 19.2% |
| Q3 — Clustering methodology | Insufficient information | Missing context |
| Q4 — Private insurance policy number | Correct abstention | Correct abstention |
| Q5 — Exact future wheat yield | Correct abstention | Correct abstention |

The original manual evaluation produced 4/5 correct outcomes for RAG and 2/5 for the baseline, including correct abstentions.

For Q3, ANN retrieval missed the relevant passage. HYBRID retrieval successfully identified K-means clustering on page 20.

The refactored QA workflow was subsequently executed successfully. The numerical results above refer to the original manually reviewed experiment, not a general accuracy benchmark.

### Governance and Logging

- Unity Catalog manages the source volume, Delta tables and search index.
- `qa_log` stores questions, prompts, responses and retrieved chunk identifiers.
- `qa_evaluation` stores evaluation results and execution time.
- Permissions and table ownership were inspected using SQL.
- Citation diagnostics validate citation formatting and retrieved-page membership, but not factual correctness.
- Credentials are excluded from Git.

Access isolation between different users was not independently tested.

## 5. Part B - AI-Assisted Development

Databricks AI Dev Kit was integrated with Codex using a registered MCP server and the `lab12_free` CLI profile.

The agent assisted with workspace inspection, RAG utilities, automated tests, Bundle configuration and CI/CD.

Direct MCP SQL execution confirmed 147 document pages and 550 chunks.

Additional details: [AI_DEV_KIT_EVIDENCE.md](AI_DEV_KIT_EVIDENCE.md).

### Testing and Deployment

- 23 automated tests passed.
- Static project validation passed.
- Strict Bundle validation passed.
- Deployment plan: 0 additions, 2 updates, 0 deletions.

The Bundle manages two Serverless Jobs:

| Job | Purpose |
|---|---|
| `rag_smoke` | Validate corpus and filtered retrieval |
| `rag_qa` | Generate answers and evaluate RAG |

GitHub Actions runs tests and Bundle checks on pull requests. A merge into `main` triggers automated deployment and the smoke test.

The QA Job was executed separately after deployment to verify the updated notebooks.

## 6. Discussion

- **RAG vs prompting alone:** Retrieval provides document-specific evidence, enables source citations and reduces unsupported claims. However, RAG can still fail when relevant context is missing.
- **Chunk size vs retrieval quality:** Smaller chunks may improve retrieval precision but lose surrounding context. Larger chunks preserve context but increase noise and token consumption. The selected configuration is 1200 characters with 200-character overlap; its optimality was not established experimentally.
- **Governance:** Unity Catalog provides centralized access management. Prompts, responses and document references are logged for traceability. Logs should be protected because they may contain sensitive information.
- **Cost:** Triggered synchronization, Top-5 retrieval, controlled Job execution and Free Edition help limit resource consumption.
- **AI-assisted development:** Codex accelerated implementation, testing and deployment configuration. Human review was essential for document selection, factual accuracy, permissions, cost and deployment approval.
- **Guardrails:** Pull requests, automated tests, citation diagnostics, GitHub Secrets and deployment-plan validation reduce development and operational risks.

## 7. Execution

The current deployment uses existing Unity Catalog resources and the Vector Search index.

For initial setup:

1. Create the schema `workspace.viktoriia_kalenichenko_lab12` and the managed volume `raw_docs`.
2. Download the source PDF and upload it to the volume.
3. Execute notebooks 01–03 to prepare the corpus and index.
4. Wait until the index is online.
5. Configure Databricks authentication and deploy the Bundle after reviewing the deployment plan.

Local validation:

```bash
pip install -r requirements-dev.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_project.py
databricks bundle validate --strict -t dev -p lab12_free
```

The deployment guardrail is specific to the existing workspace and Job IDs. Deployment to another workspace requires configuration changes and review.

## 8. Implementation Evidence

| Component | Evidence |
|---|---|
| Unity Catalog | [Catalog](screenshots/01_unity_catalog.png) |
| Delta tables | [Validation](screenshots/02_delta_tables_validation.png) |
| Document chunks | [Chunks](screenshots/03_document_chunks.png) |
| Vector Search | [Index](screenshots/04_search_index.png), [Configuration](screenshots/05_index_configuration.png) |
| Retrieval | [Top-K results](screenshots/06_retrieval_results.png) |
| Evaluation | [Questions](screenshots/07_evaluation_questions.png), [RAG vs baseline](screenshots/08_rag_vs_baseline.png) |
| HYBRID search | [Retrieval](screenshots/09_hybrid_retrieval.png), [Answer](screenshots/10_hybrid_answer.png) |
| Governance | [Permissions](screenshots/11_governance.png) |
| Testing | [Unit tests](screenshots/12_unit_tests.png) |
| MCP | [Execution](screenshots/13_mcp_execution.png), [Results](screenshots/13_mcp_results.png) |
| CI/CD | [GitHub Actions](screenshots/14_github_ci_cd.png) |
| Databricks Jobs | [Smoke Job](screenshots/15_databricks_smoke_job.png), [QA Job](screenshots/16_databricks_qa_job.png) |

## 9. References

- [World Bank — Source document](https://documents1.worldbank.org/curated/en/099032326044016306/pdf/P510294-1b00a8b1-c76e-419d-953a-46bd5805c044.pdf)
- [Databricks Documentation](https://docs.databricks.com/)
- [Databricks AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)
- [Codex MCP Documentation](https://developers.openai.com/codex/mcp)
