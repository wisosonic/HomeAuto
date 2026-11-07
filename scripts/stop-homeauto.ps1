# Stops a HomeAuto backend that is still running on the given port (default 8000), e.g. one
# left behind by an earlier run. It only touches the port if the HomeAuto API answers there,
# so it never kills an unrelated program. Exit code 1 = port is used by something else.
param([int]$Port = 8000)

function Get-Listeners { Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue }

$owners = @(Get-Listeners | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique)
if ($owners.Count -eq 0) { exit 0 }

# 127.0.0.1, not localhost: PowerShell tries IPv6 first and uvicorn listens on IPv4 only
try { $info = Invoke-RestMethod "http://127.0.0.1:$Port/api/info" -TimeoutSec 3 } catch { $info = $null }
if ($null -eq $info -or $null -eq $info.mock) {
    Write-Host "[error] port $Port is in use by another program"
    exit 1
}

# uvicorn --reload = supervisor + worker (+ the venv launcher). The worker inherits the listening
# socket, so it keeps the port busy even after the supervisor dies: stop every python process that
# mentions homeauto.api, plus the listeners and their children.
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'"
$victims = $procs | Where-Object {
    $_.CommandLine -match 'homeauto\.api' -or $owners -contains $_.ProcessId -or $owners -contains $_.ParentProcessId
}
foreach ($v in $victims) { Stop-Process -Id $v.ProcessId -Force -ErrorAction SilentlyContinue }
foreach ($o in $owners) { Stop-Process -Id $o -Force -ErrorAction SilentlyContinue }

# wait for the port to actually be released
foreach ($i in 1..20) {
    if (-not (Get-Listeners)) { exit 0 }
    Start-Sleep -Milliseconds 250
}
Write-Host "[error] could not free port $Port"
exit 1
