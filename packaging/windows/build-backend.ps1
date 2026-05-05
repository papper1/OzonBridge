param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

function Resolve-PythonExe {
    param([string]$Preferred)

    $candidates = @(
        $Preferred,
        "C:\Users\thang\AppData\Local\Programs\pgAdmin 4\python\python.exe",
        "python"
    ) | Where-Object { $_ -and $_.Trim().Length -gt 0 }

    foreach ($candidate in $candidates) {
        if ($candidate -eq "python") {
            $command = Get-Command python -ErrorAction SilentlyContinue
            if ($command) {
                return $command.Source
            }
            continue
        }
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Python executable not found. Pass -PythonExe explicitly."
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

$PythonExe = Resolve-PythonExe -Preferred $PythonExe

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$BackendRoot = Join-Path $ProjectRoot "1688_to_ozon"
$OutputRoot = Join-Path $ScriptDir "output"
$RuntimeRoot = Join-Path $OutputRoot "runtime"
$BackendOutput = Join-Path $RuntimeRoot "backend"
$PlaywrightRoot = Join-Path $RuntimeRoot "ms-playwright"
$BuildRoot = Join-Path $ScriptDir "build\backend"
$RunId = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = Join-Path $BuildRoot $RunId
$DistRoot = Join-Path $RunRoot "dist"
$WorkRoot = Join-Path $RunRoot "work"
$SpecRoot = Join-Path $RunRoot "spec"
$EntryScript = Join-Path $BackendRoot "backend\desktop_entry.py"

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
New-Item -ItemType Directory -Force -Path $RunRoot | Out-Null

if (Test-Path $BackendOutput) {
    Remove-Item -Recurse -Force $BackendOutput
}

$templatesStage = Join-Path $RuntimeRoot "templates"
$assetsStage = Join-Path $RuntimeRoot "assets\templates"

if (Test-Path $templatesStage) {
    Remove-Item -Recurse -Force $templatesStage
}
if (Test-Path $assetsStage) {
    Remove-Item -Recurse -Force $assetsStage
}

$env:PLAYWRIGHT_BROWSERS_PATH = $PlaywrightRoot

Invoke-External -FilePath $PythonExe -Arguments @(
    "-m", "pip", "install", "-r", (Join-Path $BackendRoot "requirements.txt")
)
Invoke-External -FilePath $PythonExe -Arguments @(
    "-m", "pip", "install", "pyinstaller"
)
Invoke-External -FilePath $PythonExe -Arguments @(
    "-m", "playwright", "install", "chromium"
)

Invoke-External -FilePath $PythonExe -Arguments @(
    "-m", "PyInstaller", $EntryScript,
    "--name", "crawldesk_backend",
    "--onedir",
    "--noconsole",
    "--clean",
    "--paths", $BackendRoot,
    "--distpath", $DistRoot,
    "--workpath", $WorkRoot,
    "--specpath", $SpecRoot,
    "--collect-all", "playwright",
    "--collect-all", "uvicorn",
    "--collect-all", "openai",
    "--collect-all", "bs4",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.protocols.websockets.auto",
    "--hidden-import", "uvicorn.lifespan.on"
)

Copy-Item -Recurse -Force (Join-Path $DistRoot "crawldesk_backend") $BackendOutput
Copy-Item -Recurse -Force (Join-Path $BackendRoot "templates") $templatesStage
Copy-Item -Recurse -Force (Join-Path $BackendRoot "assets\templates") $assetsStage

Write-Host "Backend runtime staged at: $RuntimeRoot"
