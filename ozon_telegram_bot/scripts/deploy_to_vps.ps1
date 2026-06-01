param(
    [string]$VpsHost = "103.153.254.116",
    [string]$User = "root",
    [string]$RemoteDir = "/opt/ozon_telegram_bot",
    [string]$RemotePython = "/opt/ozon_telegram_bot/venv/bin/python",
    [switch]$SkipTests,
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$remote = "$User@$VpsHost"

$pathsToCopy = @(
    "app",
    "core",
    "db",
    "formatters",
    "integrations",
    "scripts",
    "services",
    "systemd",
    "tests",
    "logger_config.py",
    "main.py",
    "requirements.txt",
    "MANUAL_API_CALLS.md",
    "README.md"
)

Write-Host "Copying code to $remote`:$RemoteDir"

$scpArgs = @()
foreach ($relativePath in $pathsToCopy) {
    $scpArgs += (Join-Path $projectRoot $relativePath)
}
$scpArgs += "${remote}:${RemoteDir}/"

& scp -r @scpArgs

if (-not $SkipTests) {
    Write-Host "Running tests on VPS"
    & ssh $remote "cd $RemoteDir && $RemotePython -m unittest tests.test_formatter tests.test_ozon_client"
}

if (-not $SkipRestart) {
    Write-Host "Restarting services on VPS"
    & ssh $remote "systemctl restart ozon-worker ozon-scheduler ozon-command-server && systemctl --no-pager --full status ozon-worker --lines=5"
}

Write-Host "Done"
