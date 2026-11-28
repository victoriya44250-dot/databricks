# AI-assisted development and evidence

Review date: 2026-11-28. The local refactor is awaiting approval for publication and deployment. Historical executions do not validate the modified code.

## Where the agent and MCP run

Codex is the coding agent used for Part B. The Databricks AI Dev Kit MCP server runs locally and exposes Databricks tools to Codex using CLI profile `lab12_free`. It is not a Databricks Job, a deployed QA endpoint, or a separate chat application.

Project registration is in `../.codex/config.toml`; the four Databricks skills are under `../.agents/skills/`. These local configuration directories are ignored by Git. The working AI Dev Kit checkout and Python environment were reused from an earlier local installation, at revision `07f8e1ccf3dfc09a794eaf86fd15a5848f9d63d4`. The upstream MCP installer failed during the current recovery attempt; the project registration was restored manually using the supported configuration format. This was not a fresh successful installer run.

The QA application remains the authoritative notebooks and their shared `src/rag_helpers.py` module. No MLflow ResponsesAgent wrapper or custom serving endpoint has been added.

## Observed checks

| Check | Evidence and scope |
|---|---|
| MCP protocol | `scripts/check_mcp.py` performed initialization, listed 44 tools, and completed 11 read-only tool calls. |
| Direct agent MCP use | Registered `mcp__databricks__execute_sql` returned 147 document pages and 550 chunks; repeated successfully during this review. Registered `manage_vs_index` reported the existing Delta Sync index ONLINE. |
| Workspace inspection through MCP | Inspected Unity Catalog objects, row counts, log schemas, AI Search resources, existing Jobs and run history. No new Job or inference was started. |
| Local checks | 23 unit tests passed; 16 Python files parsed; actionlint 1.7.12 passed. These are recorded checks from the current refactor, not tests rerun during the UI comparison. |
| Bundle checks through CLI | Strict validation passed. Plan updates the existing `rag_qa` and `rag_smoke` Jobs: 0 creates, 2 updates, 0 deletes. Source-module synchronization was checked with a dry run. CLI checks are not MCP usage. |
| Historical GitHub CD | Workflow run 45970698837 at commit `e904fe1` succeeded, including deployment and smoke Job run 848125194702379. This is evidence for the previous version only. |
| Current refactor CI/CD | Pending approval and execution: commit, push, PR, CI, merge, CD, and deployed smoke verification. |
| UI screenshots | Not yet captured; `screenshots/` is currently empty. |

Machine-readable diagnostics are in the ignored local `evidence/` directory, including `mcp_workspace.json`, `mcp_direct_tools.json`, `predeployment-review.json`, and `previous_github_cd.json`. These files support inspection; they are not screenshots and are not published automatically. Selected evidence must be reviewed for credentials and private information before publication.

## UI capture checklist

Save genuine captures to `screenshots/`. Capture existing state and saved outputs first. Do not rerun ingestion, evaluation, inference, or Jobs just to obtain a screenshot without approval. Label older results as historical.

| Suggested filename | View and required content |
|---|---|
| `01-catalog.png` | Catalog Explorer: the Lab 12 schema, raw document volume, document tables, and QA log/evaluation tables. |
| `02-search-index.png` | Existing `document_chunks_index` details: status, source table, and indexed rows. |
| `03-rag-baseline.png` | Notebook 05 saved outputs: question, retrieved passages, RAG answer with citations, and baseline answer. Use multiple captures if needed. |
| `04-evaluation.png` | Notebook 06 saved five-question results, including the separate Q3 HYBRID follow-up and limitations. |
| `05-qa-log.png` | Existing `qa_log` records showing RAG/baseline modes and stored responses. |
| `06-mcp.png` | Codex's actual Databricks MCP tool call and returned counts. A screenshot of a CLI command alone does not prove MCP use. |
| `07-ci-review.png` | The new PR and successful CI checks, after the approved Git workflow. |
| `08-cd.png` | Successful GitHub Actions deployment for the new merged commit. |
| `09-smoke-job.png` | Corresponding Databricks smoke Job run and successful task output for the deployed refactor. |

Playground and MLflow tracing screenshots would require additional implemented features. Do not present a chat with the base LLM as evidence that this RAG application is deployed in Playground.

## Human review and guardrails

AI assistance accelerated MCP recovery, helper integration, tests, Bundle configuration, and CI/CD checks. Human review remains necessary to preserve the specialized prompt, distinguish historical evaluation from new results, inspect permissions, and approve remote execution and cost.

The deployment-plan guard rejects unexpected resource keys, new or deleted Jobs, and changes to expected existing Job identities. CI/CD deploys the smoke workflow without automatically running answer generation or evaluation. Citation diagnostics check citation syntax and retrieved-page membership; they do not establish factual correctness. Unit tests and Bundle validation do not establish that refactored notebooks execute successfully on Serverless; the approved deployment and smoke run must supply that evidence.

Official references: [Databricks AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit), [Codex MCP configuration](https://developers.openai.com/codex/mcp).
