param([switch]$ExportOnly, [string]$KitPath = '')
$ErrorActionPreference = 'Stop'
$kitPath = if ($KitPath) { [IO.Path]::GetFullPath($KitPath) } elseif (Test-Path (Join-Path $PSScriptRoot 'vendor/ai-dev-kit')) { Join-Path $PSScriptRoot 'vendor/ai-dev-kit' } else { [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../work/ai-dev-kit')) }
$kitPython = Join-Path $kitPath '.venv/Scripts/python.exe'
Push-Location $PSScriptRoot
try {
    Write-Host 'Collecting original Lab 12 notebooks...'
    & $kitPython scripts/export_original_notebooks.py
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Export could not finish; continuing with the completed QA evidence.' }
    if ($ExportOnly) { return }
    Write-Host 'Collecting job run status and saved QA answers via MCP...'
    & $kitPython scripts/check_mcp.py --kit $kitPath --profile lab12_free
    if ($LASTEXITCODE -ne 0) { throw 'MCP verification failed.' }
    Write-Host 'Validating and deploying citation formatting fix and pinned SDK (no new model calls)...'
    & databricks bundle validate --strict -t dev -p lab12_free
    if ($LASTEXITCODE -ne 0) { throw 'Validation failed.' }
    & databricks bundle plan -t dev -p lab12_free
    if ($LASTEXITCODE -ne 0) { throw 'Plan failed.' }
    & databricks bundle deploy -t dev -p lab12_free
    if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }
    Write-Host 'Final checks completed. Do not rerun QA unless another sample is needed.'
} finally { Pop-Location }
