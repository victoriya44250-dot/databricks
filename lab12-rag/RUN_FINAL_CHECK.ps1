param([switch]$Workspace)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python -B -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed.' }
    & python -B scripts/check_project.py
    if ($LASTEXITCODE -ne 0) { throw 'Static project checks failed.' }
    if ($Workspace) {
        & ./RUN_PART_B.ps1
    }
    Write-Host 'Checks finished. No deployment, job execution or model inference was performed.'
} finally {
    Pop-Location
}
