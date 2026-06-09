# Khởi động toàn bộ Stage 5 trên Windows (PowerShell).
# Tương đương start_all.sh nhưng chạy qua `uv run` và ghi log ra thư mục logs/.
#
# Dùng:
#   .\start_all.ps1            # chạy bản gốc
#   $env:LAW_OPTIMIZED="1"; .\start_all.ps1   # chạy bản law_agent tối ưu latency
#
# Sau đó (terminal khác):  uv run python test_client_timed.py
# Dừng tất cả:             .\stop_all.ps1

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$root = $PSScriptRoot
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Start-Svc($name) {
    Start-Process -FilePath "uv" -ArgumentList "run", "python", "-m", $name `
        -WorkingDirectory $root `
        -RedirectStandardOutput (Join-Path $logs "$name.out.log") `
        -RedirectStandardError  (Join-Path $logs "$name.err.log") `
        -WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id
}

Write-Host "Starting Registry (port 10000)..."
Start-Svc "registry" | Out-Null
Start-Sleep -Seconds 4

Write-Host "Starting Tax Agent (port 10102)..."
Start-Svc "tax_agent" | Out-Null
Write-Host "Starting Compliance Agent (port 10103)..."
Start-Svc "compliance_agent" | Out-Null
Start-Sleep -Seconds 5

Write-Host "Starting Law Agent (port 10101) [LAW_OPTIMIZED=$($env:LAW_OPTIMIZED)]..."
Start-Svc "law_agent" | Out-Null
Start-Sleep -Seconds 5

Write-Host "Starting Customer Agent (port 10100)..."
Start-Svc "customer_agent" | Out-Null
Start-Sleep -Seconds 6

try {
    $health = (Invoke-WebRequest -UseBasicParsing http://localhost:10000/health).Content
    Write-Host "Registry health: $health"
    Write-Host "All services started. Logs in: $logs"
} catch {
    Write-Host "WARNING: registry not reachable yet. Check logs in $logs"
}
