$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

Write-Host ''
Write-Host '============================================================' -ForegroundColor DarkCyan
Write-Host ' REGENESIS AI | LOCAL ISEF DEMO + QWEN' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor DarkCyan

# Locate Ollama using the common Windows install path or PATH.
$Ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
if (-not (Test-Path $Ollama)) {
    $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCommand) { $Ollama = $ollamaCommand.Source }
}
if (-not (Test-Path $Ollama)) {
    throw 'Ollama is not installed. Install Ollama for Windows, then run START_REGENESIS_AI.ps1 again.'
}

# Start the local Ollama API only when it is not already listening.
$ollamaReady = $false
try {
    $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
    $ollamaReady = $true
} catch {
    Write-Host '[1/6] Starting local Ollama service...' -ForegroundColor Yellow
    Start-Process -FilePath $Ollama -ArgumentList 'serve' -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2
            $ollamaReady = $true
            break
        } catch { }
    }
}
if (-not $ollamaReady) { throw 'Ollama did not start at http://127.0.0.1:11434. Check whether another app is using port 11434.' }

function Get-OllamaModels {
    $result = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
    return @($result.models | ForEach-Object { $_.name })
}
function Ensure-OllamaModel([string]$ModelName) {
    $models = Get-OllamaModels
    $baseName = $ModelName.Split(':')[0]
    $loaded = $false
    foreach ($model in $models) {
        if ($model -eq $ModelName) { $loaded = $true; break }
    }
    if (-not $loaded) {
        Write-Host "Downloading $ModelName (first setup only; this may take time)..." -ForegroundColor Yellow
        & $Ollama pull $ModelName
        if ($LASTEXITCODE -ne 0) { throw "Ollama could not download $ModelName. Check internet access and available disk space." }
    } else {
        Write-Host "$ModelName is already downloaded." -ForegroundColor Green
    }
}

Write-Host '[2/6] Checking local AI models...' -ForegroundColor Yellow
Ensure-OllamaModel 'qwen3:4b'
Ensure-OllamaModel 'qwen2.5vl:3b'

# Select a supported installed Python runtime, preferring 3.12; 3.14 is a fallback.
Write-Host '[3/6] Preparing the project Python environment...' -ForegroundColor Yellow
$pythonMinor = $null
foreach ($version in @('3.12','3.13','3.14','3.11','3.10')) {
    try {
        & py ("-" + $version) '--version' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $pythonMinor = $version; break }
    } catch { }
}
if (-not $pythonMinor) { throw 'Python launcher (py) not found. Install Python 3.12+ and enable the Python Launcher.' }
$venvPath = Join-Path $PSScriptRoot '.venv_iseF'
$newVenv = $false
if (-not (Test-Path (Join-Path $venvPath 'Scripts\python.exe'))) {
    & py ("-" + $pythonMinor) -m venv $venvPath
    $newVenv = $true
    if ($LASTEXITCODE -ne 0) { throw "Could not create a virtual environment using Python $pythonMinor." }
}
$activate = Join-Path $venvPath 'Scripts\Activate.ps1'
. $activate
Write-Host "Using $(python --version)" -ForegroundColor Green

# Keep local showcase settings on for this ISEF package. Do not deploy with DEMO_MODE enabled.
Write-Host '[4/6] Applying local showcase settings...' -ForegroundColor Yellow
$envFile = Join-Path $PSScriptRoot '.env'
if (-not (Test-Path $envFile)) { Copy-Item (Join-Path $PSScriptRoot '.env.example') $envFile }
$envLines = @()
if (Test-Path $envFile) { $envLines = @(Get-Content $envFile) }
function Set-EnvLine([string]$Key, [string]$Value) {
    $script:envLines = @($script:envLines | Where-Object { $_ -notmatch ('^\s*' + [regex]::Escape($Key) + '=') })
    $script:envLines += ($Key + '=' + $Value)
}
Set-EnvLine 'ENVIRONMENT' 'development'
Set-EnvLine 'USE_SQLITE' 'true'
Set-EnvLine 'SQLITE_DB_PATH' 'regenesis_isef_demo.db'
Set-EnvLine 'SEED_DEMO_DATA' 'true'
Set-EnvLine 'DEMO_MODE' 'true'
Set-EnvLine 'OLLAMA_ENABLED' 'true'
Set-EnvLine 'OLLAMA_BASE_URL' 'http://127.0.0.1:11434'
Set-EnvLine 'OLLAMA_MODEL' 'qwen3:4b'
Set-EnvLine 'OLLAMA_VISION_MODEL' 'qwen2.5vl:3b'
$secretLine = @($envLines | Where-Object { $_ -match '^SECRET_KEY=' } | Select-Object -First 1)
if (-not $secretLine -or $secretLine[0] -match 'REPLACE_WITH|CHANGE_ME') {
    $newSecret = python -c "import secrets; print(secrets.token_urlsafe(48))"
    Set-EnvLine 'SECRET_KEY' $newSecret.Trim()
}
Set-Content -Path $envFile -Value $envLines -Encoding UTF8

Write-Host '[5/6] Installing project requirements...' -ForegroundColor Yellow
if ($newVenv) {
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
}
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Review the pip error above.' }
python -c "import sqlalchemy, fastapi, uvicorn, PIL; print('Core packages: OK')"
if ($LASTEXITCODE -ne 0) { throw 'A required Python package is still missing.' }

Write-Host '[6/6] Starting REGENESIS AI...' -ForegroundColor Yellow
Write-Host 'Chat model: qwen3:4b' -ForegroundColor Green
Write-Host 'Vision model: qwen2.5vl:3b' -ForegroundColor Green
Write-Host 'Showcase records will be loaded once into the local SQLite database.' -ForegroundColor Green
Write-Host 'Local app: http://127.0.0.1:8000' -ForegroundColor Cyan
Write-Host 'API docs : http://127.0.0.1:8000/docs' -ForegroundColor Cyan
Write-Host 'Do not publish this local demo with DEMO_MODE=true.' -ForegroundColor Yellow
python app.py
