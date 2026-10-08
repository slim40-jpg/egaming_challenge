```powershell
# ============================================
# CSTAM eGaming Challenge - Startup Script
# ============================================

Write-Host "============================================"
Write-Host "   CSTAM eGaming Challenge - STARTUP"
Write-Host "============================================"

# --------------------------------------------
# 1. Detect the interface used by the default route
# --------------------------------------------

$DefaultRoute = Get-NetRoute `
    -AddressFamily IPv4 `
    -DestinationPrefix "0.0.0.0/0" |
    Where-Object {
        $_.NextHop -ne "0.0.0.0"
    } |
    Sort-Object RouteMetric |
    Select-Object -First 1

if (-not $DefaultRoute) {
    Write-Error "Could not find the default network interface."
    exit 1
}

$InterfaceIndex = $DefaultRoute.InterfaceIndex

# --------------------------------------------
# 2. Detect the LAN IPv4 address
# --------------------------------------------

$LAN_IP = Get-NetIPAddress `
    -AddressFamily IPv4 `
    -InterfaceIndex $InterfaceIndex |
    Where-Object {
        $_.IPAddress -notlike "169.254.*" -and
        $_.IPAddress -ne "127.0.0.1" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -ExpandProperty IPAddress -First 1

if (-not $LAN_IP) {
    Write-Error "Could not detect LAN IPv4 address."
    exit 1
}

Write-Host ""
Write-Host "Detected LAN IP: $LAN_IP"

# --------------------------------------------
# 3. Export LAN_IP for Docker Compose
# --------------------------------------------

$env:LAN_IP = $LAN_IP

Write-Host "Docker LAN_IP set to: $env:LAN_IP"

# --------------------------------------------
# 4. Start / rebuild the complete stack
# --------------------------------------------

Write-Host ""
Write-Host "Starting Docker services..."
Write-Host ""

docker compose up --build -d

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Compose failed to start."
    exit 1
}

# --------------------------------------------
# 5. Display running containers
# --------------------------------------------

Write-Host ""
Write-Host "Docker services started successfully."
Write-Host ""

docker compose ps

# --------------------------------------------
# 6. Display useful access information
# --------------------------------------------

Write-Host ""
Write-Host "============================================"
Write-Host "   CSTAM eGaming Challenge READY"
Write-Host "============================================"
Write-Host ""
Write-Host "LAN IP       : $LAN_IP"
Write-Host "Frontend     : http://$LAN_IP`:3000"
Write-Host "Local API    : http://$LAN_IP`:8003"
Write-Host "Cloud API    : http://$LAN_IP`:5000"
Write-Host "Discovery    : UDP $LAN_IP`:9000"
Write-Host ""
Write-Host "Gaming agents should connect to:"
Write-Host "http://$LAN_IP`:8003"
Write-Host ""
```