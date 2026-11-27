param([switch]$Deploy, [switch]$RunQA, [string]$KitPath = '')
$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$kitPath = if ($KitPath) { [IO.Path]::GetFullPath($KitPath) } elseif (Test-Path (Join-Path $projectPath 'vendor/ai-dev-kit')) { Join-Path $projectPath 'vendor/ai-dev-kit' } else { [IO.Path]::GetFullPath((Join-Path $projectPath '../../work/ai-dev-kit')) }
$kitPython = Join-Path $kitPath '.venv/Scripts/python.exe'
$evidencePath = Join-Path $projectPath 'evidence'
New-Item -ItemType Directory -Force $evidencePath | Out-Null
Push-Location $projectPath
try {
    Write-Host '1/5: Checking Databricks login (no token will be printed)...'
    & databricks current-user me -p lab12_free -o json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Login failed. Run databricks auth login with profile lab12_free.' }

    Write-Host '2/5: Running the AI Dev Kit MCP checks...'
    & $kitPython scripts/check_mcp.py --kit $kitPath --profile lab12_free
    if ($LASTEXITCODE -ne 0) { throw 'MCP failed; see the message above.' }

    Write-Host '3/5: Validating the Bundle...'
    & databricks bundle validate --strict -t dev -p lab12_free -o json | Tee-Object -FilePath (Join-Path $evidencePath 'bundle-validate.json')
    if ($LASTEXITCODE -ne 0) { throw 'Bundle validation failed; deployment was not started.' }

    Write-Host '4/5: Preparing the deployment plan...'
    & databricks bundle plan -t dev -p lab12_free | Tee-Object -FilePath (Join-Path $evidencePath 'bundle-plan.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Deployment plan failed; deployment was not started.' }

    if ($Deploy) {
        Write-Host '5/5: Deploying the new Lab 12 jobs and running the smoke test...'
        & databricks bundle deploy -t dev -p lab12_free | Tee-Object -FilePath (Join-Path $evidencePath 'bundle-deploy.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }
        & databricks bundle run -t dev -p lab12_free rag_smoke | Tee-Object -FilePath (Join-Path $evidencePath 'bundle-run.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Smoke job failed.' }
        if ($RunQA) {
            Write-Host 'Running 8 paired RAG/baseline cases plus the demo. This may take several minutes...'
            & databricks bundle run -t dev -p lab12_free rag_qa | Tee-Object -FilePath (Join-Path $evidencePath 'qa-run.txt')
            $qaExit = $LASTEXITCODE
            Write-Host 'Collecting saved answers for review...'
            & $kitPython scripts/check_mcp.py --kit $kitPath --profile lab12_free
            if ($qaExit -ne 0) { throw 'QA job failed; inspect qa-run.txt and rag_runs errors.' }
        }
    } else {
        Write-Host '5/5: Checks finished. No deployment requested. Use -Deploy to deploy the new smoke-test job.'
    }
    Write-Host "Evidence saved in $evidencePath"
} finally {
    Pop-Location
}
