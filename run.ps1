[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$CondaEnvironment = "SoccerNet-FeatureExtraction"

function Resolve-CondaExecutable {
    if ($env:CONDA_EXE -and (Test-Path -LiteralPath $env:CONDA_EXE)) {
        return (Resolve-Path -LiteralPath $env:CONDA_EXE).Path
    }
    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        throw "Conda was not found. Install Miniconda/Anaconda and run setup.ps1."
    }
    $base = (& conda info --base).Trim()
    $candidates = @(
        (Join-Path $base "Scripts\conda.exe"),
        (Join-Path $base "condabin\conda.bat")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Could not locate conda.exe. Run 'conda init powershell' and reopen PowerShell."
}

function Quote-PowerShellLiteral([string]$Value) {
    return "'" + $Value.Replace("'", "''") + "'"
}

function Encode-PowerShellCommand([string]$Command) {
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($Command)
    return [Convert]::ToBase64String($bytes)
}

if (-not (Test-Path -LiteralPath $BackendPython)) {
    throw "Backend .venv does not exist. Run .\setup.ps1 first."
}
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    throw "Frontend dependencies are missing. Run .\setup.ps1 first."
}

$CondaExe = Resolve-CondaExecutable

# Verify the environment by running its Python directly. This avoids parsing
# `conda env list --json`, which can fail on Windows when paths differ only
# by letter casing.
$previousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    & $CondaExe run -n $CondaEnvironment python -c "import sys; print(sys.executable)" *> $null
    $CondaEnvironmentExitCode = $LASTEXITCODE
} catch {
    $CondaEnvironmentExitCode = 1
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

if ($CondaEnvironmentExitCode -ne 0) {
    throw "Conda environment '$CondaEnvironment' is unavailable. Run .\setup.ps1 first."
}

$BackendDirQ = Quote-PowerShellLiteral $BackendDir
$FrontendDirQ = Quote-PowerShellLiteral $FrontendDir
$BackendPythonQ = Quote-PowerShellLiteral $BackendPython
$CondaExeQ = Quote-PowerShellLiteral $CondaExe

$BackendCommand = @"
`$env:SOCCERNET_EXECUTION_MODE='conda'
`$env:SOCCERNET_CONDA_EXE=$CondaExeQ
`$env:SOCCERNET_CONDA_ENV='$CondaEnvironment'
`$env:SOCCERNET_GPU='-1'
Remove-Item Env:SOCCERNET_EXTRACTOR_PYTHON -ErrorAction SilentlyContinue
Set-Location $BackendDirQ
& $BackendPythonQ -m uvicorn app.main:app --reload
"@

$FrontendCommand = @"
Set-Location $FrontendDirQ
npm run dev
"@

$BackendEncoded = Encode-PowerShellCommand $BackendCommand
$FrontendEncoded = Encode-PowerShellCommand $FrontendCommand

Write-Host "Starting backend..." -ForegroundColor Cyan
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-EncodedCommand", $BackendEncoded
) | Out-Null

Write-Host "Starting frontend..." -ForegroundColor Cyan
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-EncodedCommand", $FrontendEncoded
) | Out-Null

if (-not $NoBrowser) {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
}

Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "The two PowerShell windows contain the live logs."
