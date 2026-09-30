# Detect the IPv4 interface used for the default Internet route
$DefaultRoute = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" |
    Sort-Object RouteMetric |
    Select-Object -First 1

if (-not $DefaultRoute) {
    Write-Error "Could not find the default network interface."
    exit 1
}

$InterfaceIndex = $DefaultRoute.InterfaceIndex

$LAN_IP = Get-NetIPAddress `
    -AddressFamily IPv4 `
    -InterfaceIndex $InterfaceIndex |
    Where-Object {
        $_.IPAddress -notlike "169.254.*" -and
        $_.IPAddress -ne "127.0.0.1"
    } |
    Select-Object -ExpandProperty IPAddress -First 1

if (-not $LAN_IP) {
    Write-Error "Could not detect LAN IPv4 address."
    exit 1
}

Write-Host "Detected LAN IP: $LAN_IP"

$env:LAN_IP = $LAN_IP

docker compose up 