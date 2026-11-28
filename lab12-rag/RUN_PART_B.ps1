param([switch]$SkipMcp)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Force evidence | Out-Null
    if (-not $SkipMcp) {
        # Read only the registered executable, never credential values.
        $kitPython = & python -c "import pathlib,tomllib; print(tomllib.loads(pathlib.Path('../.codex/config.toml').read_text(encoding='utf-8-sig'))['mcp_servers']['databricks']['command'])"
        if ($LASTEXITCODE -ne 0) { throw 'Project MCP registration is unavailable.' }
        & $kitPython -B scripts/check_mcp.py --profile lab12_free
        if ($LASTEXITCODE -ne 0) { throw 'MCP checks failed. Inspect sanitized evidence.' }
    }
    & databricks bundle validate --strict -t dev -p lab12_free
    if ($LASTEXITCODE -ne 0) { throw 'Bundle validation failed.' }
    $plan = & databricks bundle plan -t dev -p lab12_free -o json
    if ($LASTEXITCODE -ne 0) { throw 'Bundle plan failed.' }
    $planPath = Join-Path $PSScriptRoot 'evidence/bundle-plan.json'
    [IO.File]::WriteAllText($planPath, ($plan -join [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    & python -B scripts/check_plan.py $planPath
    if ($LASTEXITCODE -ne 0) { throw 'Unexpected resource changes; stop for review.' }
    Write-Host 'Read-only checks complete. Deployment and job execution require separate approval.'
} finally {
    Pop-Location
}
