# update_tunnel.ps1
# Run this ONCE every time you start a new cloudflared tunnel session.
# Usage: .\update_tunnel.ps1 -TunnelUrl "https://your-new-url.trycloudflare.com"
# Or just run it with no args to use the current session URL from clipboard.

param(
    [string]$TunnelUrl = "",
    [string]$BackendUrl = "https://agrisaathi-6dg1.onrender.com"
)

if (-not $TunnelUrl) {
    $TunnelUrl = Read-Host "Paste the cloudflared tunnel URL (e.g. https://xyz.trycloudflare.com)"
}

$TunnelUrl = $TunnelUrl.Trim().TrimEnd('/')

Write-Host ""
Write-Host "Updating Ollama tunnel URL on Render backend..." -ForegroundColor Cyan
Write-Host "  Backend : $BackendUrl" -ForegroundColor Gray
Write-Host "  Tunnel  : $TunnelUrl" -ForegroundColor Gray
Write-Host ""

$body = @{ tunnel_url = $TunnelUrl } | ConvertTo-Json
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/ollama/config" `
        -Method PUT `
        -ContentType "application/json" `
        -Body $body
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "  Status     : $($response.status)"
    Write-Host "  Tunnel URL : $($response.tunnel_url)"
    Write-Host "  Model      : $($response.model)"
    Write-Host "  Updated at : $($response.updated_at)"
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Verifying — fetching config from backend..." -ForegroundColor Cyan
try {
    $cfg = Invoke-RestMethod -Uri "$BackendUrl/api/ollama/config" -Method GET
    Write-Host "  Active tunnel: $($cfg.tunnel_url)" -ForegroundColor Yellow
} catch {
    Write-Host "Could not verify: $_" -ForegroundColor Red
}
