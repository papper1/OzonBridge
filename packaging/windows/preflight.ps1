$ErrorActionPreference = "Stop"

function Write-Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )

    $prefix = if ($Ok) { "[OK]" } else { "[MISSING]" }
    Write-Host "$prefix $Name - $Detail"
}

$flutterDefault = "C:\src\flutter\bin\flutter.bat"
$pythonDefault = "C:\Users\thang\AppData\Local\Programs\pgAdmin 4\python\python.exe"
$isccDefault = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

$flutterOk = (Test-Path $flutterDefault) -or [bool](Get-Command flutter -ErrorAction SilentlyContinue)
$pythonOk = (Test-Path $pythonDefault) -or [bool](Get-Command python -ErrorAction SilentlyContinue)
$isccOk = (Test-Path $isccDefault) -or [bool](Get-Command ISCC.exe -ErrorAction SilentlyContinue)

Write-Check -Name "Flutter" -Ok $flutterOk -Detail "Required to build Windows frontend"
Write-Check -Name "Python" -Ok $pythonOk -Detail "Required to build backend runtime"
Write-Check -Name "Inno Setup" -Ok $isccOk -Detail "Required to build CrawlDeskProSetup.exe"

if (-not $isccOk) {
    Write-Host ""
    Write-Host "Install Inno Setup 6 from: https://jrsoftware.org/isinfo.php"
}
