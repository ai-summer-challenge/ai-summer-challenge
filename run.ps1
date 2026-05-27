$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Lars\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path $python)) {
    throw "Python runtime not found at $python"
}

$backendArgs = @(
    "-m",
    "uvicorn",
    "pcf_pdf_extractor.api.app:app",
    "--app-dir",
    "src",
    "--host",
    "127.0.0.1",
    "--port",
    "8000"
)

$frontendArgs = @(
    "-m",
    "streamlit",
    "run",
    "frontend\streamlit_app.py",
    "--server.headless=true",
    "--server.port=8501",
    "--server.address=127.0.0.1"
)

$backend = Start-Process -FilePath $python -ArgumentList $backendArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

$env:BACKEND_API_URL = "http://127.0.0.1:8000"
$frontend = Start-Process -FilePath $python -ArgumentList $frontendArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

Write-Host "Backend started with PID $($backend.Id) on http://127.0.0.1:8000"
Write-Host "Frontend started with PID $($frontend.Id) on http://127.0.0.1:8501"
Write-Host "Open http://127.0.0.1:8501 in your browser."
