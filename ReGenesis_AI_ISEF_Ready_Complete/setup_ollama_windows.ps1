$ErrorActionPreference = 'Stop'
Write-Host '=== REGENESIS Local AI Setup ===' -ForegroundColor Cyan

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Ollama is not installed and winget is unavailable. Install Ollama from https://ollama.com/download/windows, then rerun this script.'
    }
    Write-Host 'Installing Ollama...' -ForegroundColor Yellow
    winget install --id Ollama.Ollama --exact --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw 'Ollama was installed but is not available in this terminal yet. Close PowerShell, open it again, and run this script once more.'
}

# Ensure the local Ollama service is available.
try {
    ollama list | Out-Null
} catch {
    Write-Host 'Starting the local Ollama service...' -ForegroundColor Yellow
    Start-Process -FilePath (Get-Command ollama).Source -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

Write-Host 'Downloading Qwen3 4B (recommended default for 16GB RAM)...' -ForegroundColor Yellow
ollama pull qwen3:4b
ollama pull qwen2.5vl:3b

Write-Host ''
Write-Host 'Local AI model is ready.' -ForegroundColor Green
Write-Host 'The project is configured to use: qwen3:4b'
Write-Host 'Optional stronger model (more memory/compute): ollama pull qwen3:8b'
Write-Host 'To test: ollama run qwen3:4b'
