param()
$FrontendPort = 3000
$BackendPort = 8000
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try { $client.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}

if ((Test-LocalPort $FrontendPort) -or (Test-LocalPort $BackendPort)) {
    throw 'An app port is already in use. Use the existing app or stop its processes before restarting.'
}
$agent2Python = Join-Path $projectRoot '.venv-agent2/Scripts/python.exe'
if (!(Test-Path -LiteralPath $agent2Python)) { throw 'Create the Agent 2 environment first; see docs/Agent2-Application-Integration.md.' }
$env:MERIDIAN_AGENT2_PYTHON = $agent2Python
if (!$env:MERIDIAN_AGENT7_PYTHON) {
    $env:MERIDIAN_AGENT7_PYTHON = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python313/python.exe'
}
if (!(Test-Path -LiteralPath $env:MERIDIAN_AGENT7_PYTHON)) { throw 'Set MERIDIAN_AGENT7_PYTHON to the verified Agent 7 interpreter.' }
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$appPython = (Get-Command python).Source
$node = (Get-Command node).Source
Push-Location $projectRoot
try {
    & $appPython -B scripts/compile_meridian.py
    if ($LASTEXITCODE -ne 0) { throw 'Frontend compilation failed.' }
    $backend = Start-Process -FilePath $appPython -ArgumentList @('-B','-m','reflex','run','--backend-only','--backend-port',"$BackendPort",'--backend-host','127.0.0.1') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'backend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'backend.stderr.log')
    $frontend = Start-Process -FilePath $node -ArgumentList @('node_modules/@react-router/dev/bin.cjs','dev','--host','127.0.0.1','--port',"$FrontendPort") -WorkingDirectory (Join-Path $projectRoot '.web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.stderr.log')
    @{ backend_pid = $backend.Id; frontend_pid = $frontend.Id; url = "http://localhost:$FrontendPort" } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'meridian-processes.json')
    Write-Output "Meridian is starting at http://localhost:$FrontendPort (logs in .runtime)."
}
finally { Pop-Location }
