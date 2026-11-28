# AI Dev Kit — Implementation Evidence

## Setup

- Coding agent: Codex.
- Integration: Databricks AI Dev Kit and MCP.
- Workspace: Databricks Free Edition.
- Authentication: local Databricks CLI profile `lab12_free`.
- Configuration: `.codex/config.toml` and `.agents/skills/` in the repository root.

The existing AI Dev Kit installation was reused. MCP registration was restored manually after an installer issue.

Local configuration and credentials are excluded from Git.

## MCP Verification

The registered `mcp__databricks__execute_sql` tool successfully executed a read-only SQL query.

| Resource | Result |
|---|---|
| document_pages | 147 rows |
| document_chunks | 550 rows |
| Vector Search index | Online |

Evidence:

- [MCP execution](screenshots/13_mcp_execution.png)
- [MCP results](screenshots/13_mcp_results.png)

## AI-Assisted Development

Codex assisted with:

- Workspace resource inspection through MCP.
- Shared RAG utility refactoring.
- Unit and integration tests.
- Bundle configuration and CI/CD validation.
- Deployment safety checks.

## Validation and Deployment

| Check | Result |
|---|---|
| Unit tests | 23/23 passed |
| Project validation | Passed |
| Bundle validation | Passed |
| Deployment plan | 0 additions, 2 updates, 0 deletions |
| GitHub CI/CD | Successful |
| Smoke Job | Successful |
| QA Job | Executed separately after deployment |

## Human Review and Guardrails

- Review AI-generated code before committing.
- Use read-only MCP operations for workspace inspection.
- Store deployment credentials in GitHub Secrets.
- Reject unexpected resource creation, deletion or Job identity changes.
- Deploy only after successful CI checks and human-approved merge.
- Avoid automatic LLM evaluation during CI/CD to control resource usage.
- Manually review answer quality and citation correctness.

AI assistance accelerated development but did not replace human verification or deployment approval.

## References

- [Databricks AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)
- [Codex MCP Configuration](https://developers.openai.com/codex/mcp)
