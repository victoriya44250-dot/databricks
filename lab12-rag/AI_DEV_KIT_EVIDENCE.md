# AI Dev Kit: installation and verification record

Date: 2026-11-27.

| Component | Observed result |
|---|---|
| CLI | Databricks CLI 1.22.1 |
| AI Dev Kit checkout | `07f8e1ccf3dfc09a794eaf86fd15a5848f9d63d4` |
| Windows installer | `install.ps1` executed for the project; current upstream delegates skills to `databricks aitools` |
| Skills | Release 0.2.32; dabs, unity-catalog, vector-search, core downloaded to project `.agents/skills` |
| Installer adjustment | CLI rejected project-scoped Codex auto-install; used its documented `--path .agents/skills` option |
| MCP packages | `databricks-mcp-server==0.1.0`, `databricks-tools-core==0.1.0`, SDK 0.171.0, FastMCP 3.4.11 |
| MCP registration | Official `mcp_install.ps1` created project `.codex/config.toml`, profile `lab12_free` |
| MCP protocol check | Real stdio client completed initialize/list_tools: **44 tools** in this revision |
| Agent use of skills | Reviewed DAB configuration, deployment guidance, Unity Catalog access and Vector Search guidance |
| MCP workspace calls | Confirmed via user-run launcher: SQL counted 147 pages and 550 chunks; warehouse listing succeeded; SHOW GRANTS on chunks returned no explicit rows |
| Bundle validation and plan | Confirmed through CLI: strict validation succeeded; final plan adds 2 jobs, changes/deletes 0 existing resources |
| Bundle deployment | Two jobs created. MCP job history confirms QA run 572169945663116 and smoke run 1023341086600454 both SUCCESS |
| QA execution | 18 successful logged model calls; see EVALUATION.md |
| GitHub CI | PR 17, first workflow run 45966117325 succeeded; deployment job skipped on PR as designed |
| GitHub CI/CD deployment | Not yet verified |

The lab brief describes 75+ tools. This checkout lists 44 consolidated tools (for example `manage_jobs` and `manage_uc_objects` expose multiple actions); the actual observed count is recorded instead of repeating the brief's number.

Windows build issue: the automatically selected temporary path contained braces, causing setuptools variable expansion to fail. Installation succeeded after using a workspace-local temporary directory. No dependency source code was modified.

The CLI login profile was created by the user, but the agent's process cannot read the Windows keyring. The user-run launcher is therefore used for authenticated checks. No token was requested in chat or written into project files.

Successful remote tool calls are recorded in local `evidence/mcp_workspace.json`. The first attempt to read `rag_runs` correctly reported that the table did not yet exist. Local deployment is not proof of CI/CD; those results remain separate.

## Reproduction on Windows

Run in the project directory, using the CLI profile for the intended Free workspace. Keep the kit checkout on disk because MCP registration refers to its Python environment by absolute path.

```powershell
git clone https://github.com/databricks-solutions/ai-dev-kit.git vendor/ai-dev-kit
git -C vendor/ai-dev-kit checkout 07f8e1ccf3dfc09a794eaf86fd15a5848f9d63d4
$env:DEVKIT_SCOPE = 'project'
$env:DEVKIT_PROFILE = 'lab12_free'
& ./vendor/ai-dev-kit/install.ps1 --tools codex --skills databricks-dabs,databricks-unity-catalog
# Explicit destination works around this CLI revision's project-scoped Codex limitation.
databricks aitools install --path .agents/skills --skills databricks-core,databricks-dabs,databricks-unity-catalog,databricks-vector-search
& ./vendor/ai-dev-kit/databricks-mcp-server/setup.ps1
& ./vendor/ai-dev-kit/databricks-mcp-server/mcp_install.ps1 -Profile_ lab12_free -Tools codex -SkipVenv
```

If setuptools rejects a temporary directory containing braces, set `TEMP` and `TMP` to an existing project-local `build-temp` folder for that installation process and repeat setup. Do not put credentials into any of these files. To use the registered MCP server directly in an agent UI, open this project and reload its MCP configuration; the supplied check script also exercises the actual stdio protocol without requiring an agent reload.
