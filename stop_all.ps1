# Dừng toàn bộ Stage 5 services (theo cổng).
$ports = 10000, 10100, 10101, 10102, 10103
foreach ($p in $ports) {
    try {
        Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction Stop |
            ForEach-Object {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped PID $($_.OwningProcess) on port $p"
            }
    } catch {
        Write-Host "No listener on port $p"
    }
}
Get-Process uv -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Done."
