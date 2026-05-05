param(
    [string]$PythonExe = "",
    [string]$FlutterExe = "",
    [string]$IsccExe = ""
)

$ErrorActionPreference = "Stop"

function Resolve-IsccExe {
    param([string]$Preferred)

    $candidates = @(
        $Preferred,
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and $_.Trim().Length -gt 0 }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Inno Setup compiler not found. Install Inno Setup 6 or pass -IsccExe explicitly."
}

$IsccExe = Resolve-IsccExe -Preferred $IsccExe

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputRoot = Join-Path $ScriptDir "output"
$AppOutput = Join-Path $OutputRoot "app"
$RuntimeRoot = Join-Path $OutputRoot "runtime"
$InstallerScript = Join-Path $ScriptDir "CrawlDeskPro.iss"
$AppRuntimeTarget = Join-Path $AppOutput "runtime"

& (Join-Path $ScriptDir "build-backend.ps1") -PythonExe $PythonExe
& (Join-Path $ScriptDir "build-frontend.ps1") -FlutterExe $FlutterExe

if (Test-Path $AppRuntimeTarget) {
    Remove-Item -Recurse -Force $AppRuntimeTarget
}

New-Item -ItemType Directory -Force -Path $AppRuntimeTarget | Out-Null
Copy-Item -Recurse -Force (Join-Path $RuntimeRoot "*") $AppRuntimeTarget

& $IsccExe $InstallerScript

Write-Host "Installer build completed."
