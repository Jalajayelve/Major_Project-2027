param([ValidateSet('frontend','backend')][string]$Service = 'frontend')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if ($Service -eq 'backend') {
        & '.\.venv-backend\Scripts\python.exe' -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8001
    } else {
        if (!$env:MERIDIAN_API_URL) { $env:MERIDIAN_API_URL = 'http://127.0.0.1:8001' }
        if (!$env:REFLEX_API_URL) { $env:REFLEX_API_URL = 'http://127.0.0.1:8000' }
        & '.\.venv\Scripts\python.exe' -m reflex run --frontend-port 3000 --backend-port 8000 --backend-host 127.0.0.1
    }
} finally { Pop-Location }
