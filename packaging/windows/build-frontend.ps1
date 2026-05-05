param(
    [string]$FlutterExe = ""
)

$ErrorActionPreference = "Stop"

function Resolve-FlutterExe {
    param([string]$Preferred)

    $candidates = @(
        $Preferred,
        "C:\src\flutter\bin\flutter.bat",
        "flutter"
    ) | Where-Object { $_ -and $_.Trim().Length -gt 0 }

    foreach ($candidate in $candidates) {
        if ($candidate -eq "flutter") {
            $command = Get-Command flutter -ErrorAction SilentlyContinue
            if ($command) {
                return $command.Source
            }
            continue
        }
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Flutter executable not found. Pass -FlutterExe explicitly."
}

function Invoke-External {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Remove-DirectoryRobust {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    try {
        attrib -R "$Path\*" /S /D 2>$null
    } catch {
    }

    try {
        Remove-Item -Recurse -Force $Path -ErrorAction Stop
        return
    } catch {
    }

    cmd /c "rd /s /q `"$Path`""
    if (Test-Path $Path) {
        throw "Failed to remove directory: $Path"
    }
}

$FlutterExe = Resolve-FlutterExe -Preferred $FlutterExe

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$FrontendRoot = Join-Path $ProjectRoot "crawldesk_pro"
$OutputRoot = Join-Path $ScriptDir "output"
$AppOutput = Join-Path $OutputRoot "app"
$RunId = Get-Date -Format "yyyyMMdd_HHmmss"
$StageRoot = Join-Path "C:\CrawlDeskBuild\frontend" $RunId
$StageProject = Join-Path $StageRoot "crawldesk_pro"
$StageReleaseRoot = Join-Path $StageProject "build\windows\x64\runner\Release"

if (Test-Path $AppOutput) {
    Remove-DirectoryRobust -Path $AppOutput
}

New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null

$robocopyArgs = @(
    $FrontendRoot,
    $StageProject,
    "/MIR",
    "/XD", ".dart_tool", "build", ".git"
)

& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed with exit code $LASTEXITCODE while staging frontend source."
}

$generatedPaths = @(
    (Join-Path $StageProject ".dart_tool"),
    (Join-Path $StageProject "build"),
    (Join-Path $StageProject "android\.dart_tool"),
    (Join-Path $StageProject "ios\Flutter\ephemeral"),
    (Join-Path $StageProject "linux\flutter\ephemeral"),
    (Join-Path $StageProject "macos\Flutter\ephemeral"),
    (Join-Path $StageProject "windows\flutter\ephemeral"),
    (Join-Path $StageProject "linux\flutter\generated_plugin_registrant.cc"),
    (Join-Path $StageProject "linux\flutter\generated_plugins.cmake"),
    (Join-Path $StageProject "macos\Flutter\GeneratedPluginRegistrant.swift"),
    (Join-Path $StageProject "windows\flutter\generated_plugins.cmake"),
    (Join-Path $StageProject "windows\flutter\generated_plugin_registrant.cc"),
    (Join-Path $StageProject "windows\flutter\generated_plugin_registrant.h")
)

foreach ($generatedPath in $generatedPaths) {
    if (Test-Path $generatedPath) {
        if ((Get-Item $generatedPath) -is [System.IO.DirectoryInfo]) {
            Remove-DirectoryRobust -Path $generatedPath
        } else {
            Remove-Item -Force $generatedPath
        }
    }
}

Push-Location $StageProject
try {
    Invoke-External -FilePath $FlutterExe -Arguments @("pub", "get")
    Invoke-External -FilePath $FlutterExe -Arguments @("build", "windows", "--release")
} finally {
    Pop-Location
}

if (-not (Test-Path $StageReleaseRoot)) {
    throw "Flutter release output not found at: $StageReleaseRoot"
}

Copy-Item -Recurse -Force $StageReleaseRoot $AppOutput

Write-Host "Frontend build staged at: $AppOutput"
