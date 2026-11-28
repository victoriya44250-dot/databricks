# Lab 12 continuation checkpoint

Date: 2026-11-28. Branch: `feature/lab12-final`. This is a work-in-progress checkpoint for another chat, not a completed deployment or final submission.

## User intent and permissions

Continue the existing agricultural-risk RAG implementation; do not generate a second RAG implementation. Communicate in Ukrainian, write code and final documentation in English. Explain meaningful changes in terms suitable for a Data Engineering trainee. Workspace access is time-limited, so prioritize technical tasks needing Databricks before final documentation.

The user authorized committing and pushing this checkpoint to GitHub to continue in another chat. This does not authorize a PR, merge, deployment, remote Job execution, LLM inference, or changes to Databricks resources. Obtain approval before those actions. Local Lab 12 edits, tests, read-only MCP/CLI operations, Bundle validation and planning are authorized. Do not change other labs, touch the Lab 8 stash, use destructive Git commands, or delete remote tables/indexes.

## Entry points and assignment

- `notebooks/01_ingest_pdf_pages.py` through `06_evaluation.py` are the user's authoritative implementation; `07_smoke_test.py` verifies existing data and filtered retrieval.
- `src/rag_helpers.py` contains shared page filters, retrieval parsing, prompts and citation diagnostics. It is imported by notebooks 04-07.
- `databricks.yml` declares the existing Jobs; `.github/workflows/lab12.yml` defines PR checks and deployment on pushes to main.
- `EVALUATION.md` distinguishes the user's five-question experiment from the older eight-question experiment in `historical/agent-eight-question-run/`.
- `AI_DEV_KIT_EVIDENCE.md` records current versus historical evidence and a UI screenshot checklist.
- `README.md` still contains older Ukrainian narrative below an explicit warning. It needs a final English rewrite; do not treat that older narrative as current status.

The supplied assignment requires a document RAG workflow with filtered retrieval, grounded QA, comparison against baseline, evaluation, logging/governance, and AI-assisted development using AI Dev Kit/MCP plus reviewed Bundle CI/CD. It does not explicitly require a custom Model Serving endpoint or ResponsesAgent.

## Completed local changes

- Removed unreachable helper code and redundant notebook cells; translated executable comments/messages; removed the READY LLM call.
- Preserved notebook 05's specialized prompt and the `qa_log`/`qa_evaluation` schemas. Notebook 06 keeps its five-question methodology but uses shared prompt logic: old results must not be attributed to this modified code without rerunning.
- Implemented Workspace Files imports using an absolute `project_root` notebook widget; Bundle supplies `${workspace.file_path}`. Manual runs must supply the actual synced project directory. No JVM notebook-context API is used.
- Pinned AI Search SDK to 0.83 across notebooks and Bundle. Inspected the package's creation-method signatures. Notebook 03 create/reuse checks were updated but not executed remotely.
- Kept Bundle resource keys and remote Job identities. `rag_qa` now uses notebooks 05 and 06; `rag_smoke` uses notebook 07. Verified source-module sync inclusion.
- Removed the duplicate generated notebook, runtime, notebook generator and obsolete export script after replacing their dependencies. Preserved the older evaluation artifacts under `historical/`.
- Added offline integration and deployment-plan tests. The plan guard rejects unexpected keys, creates/deletes and changed remote Job identities.
- Updated CI/CD to test, validate, plan, deploy, and run only the smoke Job. QA inference/evaluation is not automatic. PowerShell wrappers now perform checks without automatic deployment.

## Actual verification and limits

At checkpoint preparation, reran `python -B -m unittest discover -s tests -v` from `lab12-rag/`: 23 tests passed. `python -B scripts/check_project.py` passed: 16 Python files parsed and Bundle paths/imports/pins/workflow structure checked. Whitespace checks passed.

Earlier in this refactoring session, actionlint 1.7.12 passed; CLI strict Bundle validation passed; the plan reported 0 creates, 2 updates, 0 deletes. Bundle dry-run included `src/__init__.py` and `src/rag_helpers.py`, excluding Python caches. Recheck validation/plan before actual deployment because remote state can change. File synchronization may remove obsolete files inside the Bundle's deployed file directory; the resource plan does not delete tables or indexes.

The modified notebooks have NOT yet been verified by a newly deployed Serverless Job. Unit tests and validation alone cannot establish that runtime result. The smoke test does not call the answer LLM, but text retrieval can invoke the embedding model and therefore still needs remote-run approval.

Historical GitHub Actions run `45970698837`, commit `e904fe1`, successfully deployed the OLD version and ran smoke Job run `848125194702379`. This is not proof for the refactor. The current branch push alone does not trigger the Lab 12 workflow; its push trigger targets main. No PR/merge/deployment is part of this checkpoint request.

## Workspace and resources

Use CLI profile `lab12_free`. Schema: `workspace.viktoriia_kalenichenko_lab12`.

| Resource | Observed state |
|---|---|
| Volume | `raw_docs` |
| `document_pages` | 147 rows |
| `document_chunks` | 550 chunks from 144 pages; unique IDs, nonempty text, maximum 1200 characters |
| AI Search endpoint | `lab12_agri_search`, STANDARD, ONLINE |
| Index | `workspace.viktoriia_kalenichenko_lab12.document_chunks_index`, Delta Sync, TRIGGERED, 550 indexed rows |
| Embedding endpoint | `databricks-qwen3-embedding-0-6b`, 1024 dimensions |
| Answer LLM | `databricks-gpt-oss-120b` |
| QA Job | `rag_qa`, ID `708337744279402` |
| Smoke Job | `rag_smoke`, ID `333515008590836` |

Chunking uses 1200 characters with 200-character overlap and deterministic SHA-256 IDs. Primary retrieval is ANN, top-5, pages 7-146 excluding 96 and 97. HYBRID is a separate Q3 experiment. Main logs are `qa_log` and `qa_evaluation`; preserve the old `rag_runs` table without using it as the authoritative log.

Historical five-question findings: Q1 correct climatic risks, Q2 correctly answered 19.2%, Q3 ANN abstained but HYBRID found K-means on page 20, Q4/Q5 correctly abstained. ANN answered two of three answerable questions. This small manual evaluation and citation checks do not establish general factual correctness or superiority of HYBRID.

## Local MCP and secrets

Codex is the coding agent; the AI Dev Kit MCP server is a local process connecting it to Databricks. Project registration is `../.codex/config.toml`, skills are `../.agents/skills/`. Both are ignored local configuration, not files to publish.

Reused AI Dev Kit checkout: `C:/Users/vikto/Documents/Codex/2026-11-22/referenced-chatgpt-conversation-this-is-an-5/work/ai-dev-kit`, revision `07f8e1ccf3dfc09a794eaf86fd15a5848f9d63d4`. Its `.venv/Scripts/python.exe` runs `databricks-mcp-server/run_server.py` with `DATABRICKS_CONFIG_PROFILE=lab12_free`. Another machine needs its own supported installation/configuration; do not assume this path is portable.

The real stdio MCP check completed 11 calls and listed 44 tools. Direct registered `mcp__databricks__execute_sql` and `mcp__databricks__manage_vs_index` calls also succeeded. The direct SQL count was repeated during the UI comparison and returned 147 pages and 550 chunks. CLI Bundle checks are separate and must never be described as MCP operations.

Local diagnostics in ignored `evidence/` include `mcp_workspace.json`, `mcp_direct_tools.json`, `predeployment-review.json`, Bundle plan/summary, SDK checks and prior GitHub CD verification. They are not transferred by Git. `.databricks/bundle/` is CLI-generated local state, also ignored. Credentials, environments, raw local diagnostics and private configuration must not be added to Git.

GitHub metadata checks found required `LAB12_DATABRICKS_HOST` and `LAB12_DATABRICKS_TOKEN` secrets at repository scope. The `lab12-dev` environment existed without environment-level secrets or protection rules. Values were not disclosed. Recheck metadata if needed; do not request tokens in chat.

## User's latest concern and next work

The user wants a comprehensible structure and real UI screenshots, similar to the peer repository: https://github.com/olesJS/databricks_academy/tree/master/lab-12-rag-assistant . The peer includes a ResponsesAgent wrapper, serving configuration, MLflow tracing and Playground demonstrations. Our application currently has no custom serving endpoint or ResponsesAgent wrapper. Discuss whether that additional scope is desired; do not invent evidence or build a duplicate RAG application.

`screenshots/` is empty locally and therefore is not tracked by Git. UI browser access returned `browser access host is unavailable`. The last requested manual step was to open Catalog > workspace > viktoriia_kalenichenko_lab12 > document_chunks_index and provide a status screenshot without clicking Sync. No screenshot has been supplied yet.

Next: collect existing-state UI evidence; review any remaining implementation issues; obtain approval for the controlled PR/CI/merge/CD/smoke sequence; verify the new deployed version; only then finish README, evaluation narrative and guardrail documentation. Any new QA/evaluation run requires approval and must be recorded separately from historical results.
