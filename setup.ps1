[CmdletBinding()]
param(
    [switch]$SkipModelWeights,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendVenvDir = Join-Path $BackendDir ".venv"
$BackendPython = Join-Path $BackendVenvDir "Scripts\python.exe"
$CondaEnvironment = "SoccerNet-FeatureExtraction"
$CondaYaml = Join-Path $BackendDir "environment.soccernet.yml"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Require-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$Name'. $InstallHint"
    }
}

function Assert-LastExitCode([string]$Action) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

function Test-CompatibleVersion([string]$Version) {
    $parts = $Version.Split('.')
    if ($parts.Count -lt 2) {
        return $false
    }
    return (
        [int]$parts[0] -eq 3 -and
        [int]$parts[1] -ge 10 -and
        [int]$parts[1] -le 12
    )
}

function Get-PythonInfoFromExecutable(
    [string]$ExecutablePath,
    [string]$Invocation
) {
    if (-not (Test-Path -LiteralPath $ExecutablePath)) {
        return $null
    }

    $probe = "import json,sys; print(json.dumps({'path':sys.executable,'version':f'{sys.version_info.major}.{sys.version_info.minor}'}))"

    # A failed native command can become a terminating PowerShell error when
    # $ErrorActionPreference is Stop. Probe candidates without aborting setup.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $ExecutablePath -c $probe 2>$null
        $exitCode = $LASTEXITCODE
    } catch {
        return $null
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0 -or -not $output) {
        return $null
    }

    $jsonLine = @($output) |
        Where-Object { $_ -and $_.Trim().StartsWith('{') } |
        Select-Object -Last 1

    if (-not $jsonLine) {
        return $null
    }

    try {
        $info = $jsonLine | ConvertFrom-Json
    } catch {
        return $null
    }

    if (-not (Test-CompatibleVersion ([string]$info.version))) {
        return $null
    }

    if (-not (Test-Path -LiteralPath ([string]$info.path))) {
        return $null
    }

    return [pscustomobject]@{
        Path       = (Resolve-Path -LiteralPath ([string]$info.path)).Path
        Version    = [string]$info.version
        Invocation = $Invocation
    }
}

function Resolve-CompatibleBackendPython {
    $preferredVersions = @("3.11", "3.12", "3.10")
    $candidatePaths = New-Object System.Collections.Generic.List[object]

    # Read installed runtimes from the Windows Python Launcher once. This
    # avoids calling `py -3.12` when 3.12 is absent, which previously stopped
    # the entire setup before the script could try an installed Python 3.11.
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $launcherOutput = & py -0p 2>&1
            $launcherExitCode = $LASTEXITCODE
        } catch {
            $launcherOutput = @()
            $launcherExitCode = 1
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }

        if ($launcherExitCode -eq 0) {
            foreach ($preferredVersion in $preferredVersions) {
                foreach ($line in @($launcherOutput)) {
                    $lineText = [string]$line
                    $pattern = "-V:$([regex]::Escape($preferredVersion))(?:-\d+)?\s+\*?\s*(.+)$"
                    if ($lineText -match $pattern) {
                        $path = $Matches[1].Trim()
                        if ($path -and (Test-Path -LiteralPath $path)) {
                            $candidatePaths.Add([pscustomobject]@{
                                Path       = $path
                                Invocation = "Windows Python Launcher entry $preferredVersion"
                            })
                        }
                    }
                }
            }
        }
    }

    # Common standalone Python installation locations.
    foreach ($preferredVersion in $preferredVersions) {
        $compact = $preferredVersion.Replace(".", "")
        $commonPaths = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Python\Python$compact\python.exe"),
            (Join-Path $env:LOCALAPPDATA "Python\pythoncore-$preferredVersion-64\python.exe"),
            (Join-Path $env:ProgramFiles "Python$compact\python.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Python$compact\python.exe"),
            "C:\Python$compact\python.exe"
        )

        foreach ($path in $commonPaths) {
            if ($path -and (Test-Path -LiteralPath $path)) {
                $candidatePaths.Add([pscustomobject]@{
                    Path       = $path
                    Invocation = "Detected installation path"
                })
            }
        }
    }

    # Finally inspect python/python3 from PATH. They may point to an unsupported
    # newer version, but the compatibility check below will reject those.
    foreach ($commandName in @("python", "python3")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command -and $command.CommandType -eq "Application") {
            $candidatePaths.Add([pscustomobject]@{
                Path       = $command.Source
                Invocation = "$commandName from PATH"
            })
        }
    }

    $seen = @{}
    foreach ($candidate in $candidatePaths) {
        $normalizedPath = [System.IO.Path]::GetFullPath([string]$candidate.Path).ToLowerInvariant()
        if ($seen.ContainsKey($normalizedPath)) {
            continue
        }
        $seen[$normalizedPath] = $true

        $info = Get-PythonInfoFromExecutable `
            -ExecutablePath ([string]$candidate.Path) `
            -Invocation ([string]$candidate.Invocation)

        if ($info) {
            return $info
        }
    }

    $detected = "No Python installations were reported by the Windows Python Launcher."
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $detectedOutput = (& py -0p 2>&1 | Out-String).Trim()
            if ($detectedOutput) {
                $detected = $detectedOutput
            }
        } catch {
            # Keep the fallback message.
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
    }

    throw @"
No compatible backend Python was found.

Required: Python 3.10, 3.11 or 3.12.
A newer default Python is allowed, but at least one compatible version must
also be installed.

Detected installations:
$detected

Install Python 3.11 or 3.12, reopen PowerShell, then run setup.ps1 again.
"@
}

function Resolve-CondaExecutable {
    if ($env:CONDA_EXE -and (Test-Path -LiteralPath $env:CONDA_EXE)) {
        return (Resolve-Path -LiteralPath $env:CONDA_EXE).Path
    }

    Require-Command "conda" "Install Miniconda/Anaconda, run 'conda init powershell', then reopen PowerShell."
    $base = (& conda info --base).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $base) {
        throw "Conda is installed but its base directory could not be resolved."
    }

    $candidates = @(
        (Join-Path $base "Scripts\conda.exe"),
        (Join-Path $base "condabin\conda.bat")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $command = Get-Command conda -ErrorAction Stop
    if ($command.CommandType -eq "Application") {
        return $command.Source
    }
    throw "Could not locate conda.exe. Run 'conda init powershell' and reopen the terminal."
}

Write-Step "Checking required system tools"
Require-Command "ffmpeg" "Install FFmpeg and add its bin directory to PATH."
Require-Command "ffprobe" "Install FFmpeg and add its bin directory to PATH."
if (-not $SkipFrontend) {
    Require-Command "node" "Install Node.js 20.19+ or 22.12+."
    Require-Command "npm" "Install Node.js 20.19+ or 22.12+."
}
$CondaExe = Resolve-CondaExecutable

Write-Host "Conda: $CondaExe"
& ffmpeg -version | Select-Object -First 1
if (-not $SkipFrontend) {
    $NodeVersion = (& node -p "process.versions.node").Trim()
    $NodeParts = $NodeVersion.Split('.')
    $NodeMajor = [int]$NodeParts[0]
    $NodeMinor = [int]$NodeParts[1]
    $NodeCompatible = (
        ($NodeMajor -eq 20 -and $NodeMinor -ge 19) -or
        ($NodeMajor -eq 22 -and $NodeMinor -ge 12) -or
        ($NodeMajor -gt 22)
    )
    if (-not $NodeCompatible) {
        throw "Node.js 20.19+ or 22.12+ is required by the frontend. Detected: $NodeVersion"
    }
    Write-Host "Node.js: $NodeVersion"
}

Write-Step "Creating or updating the backend virtual environment"
if (Test-Path -LiteralPath $BackendPython) {
    $ExistingVenvVersion = (& $BackendPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($LASTEXITCODE -ne 0 -or -not (Test-CompatibleVersion $ExistingVenvVersion)) {
        Write-Host "Existing backend .venv is incompatible or damaged; recreating it." -ForegroundColor Yellow
        Remove-Item -LiteralPath $BackendVenvDir -Recurse -Force
    } else {
        Write-Host "Using existing backend .venv with Python $ExistingVenvVersion"
    }
}

if (-not (Test-Path -LiteralPath $BackendPython)) {
    $BasePython = Resolve-CompatibleBackendPython
    Write-Host "Selected backend Python $($BasePython.Version): $($BasePython.Path)"
    Write-Host "Resolved through: $($BasePython.Invocation)"
    & $BasePython.Path -m venv $BackendVenvDir
    Assert-LastExitCode "Creating backend .venv"
}

$BackendVenvVersion = (& $BackendPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
Assert-LastExitCode "Checking backend .venv"
Write-Host "Backend .venv Python: $BackendVenvVersion"

& $BackendPython -m pip install --upgrade pip
Assert-LastExitCode "Upgrading backend pip"
& $BackendPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
Assert-LastExitCode "Installing backend requirements"

Write-Step "Creating or updating the SoccerNet Conda environment"

# Use the plain-text environment list instead of parsing `conda env list --json`.
# Some Windows Conda installations return JSON containing paths that differ
# only by letter casing, which PowerShell rejects as duplicate dictionary keys.
$CondaEnvironmentList = & $CondaExe env list
Assert-LastExitCode "Listing Conda environments"

$EnvironmentExists = $false
$EscapedEnvironmentName = [regex]::Escape($CondaEnvironment)

foreach ($line in @($CondaEnvironmentList)) {
    $lineText = [string]$line

    if ([string]::IsNullOrWhiteSpace($lineText) -or $lineText.TrimStart().StartsWith("#")) {
        continue
    }

    if ($lineText -match "^\s*$EscapedEnvironmentName(?:\s+\*?)?\s+") {
        $EnvironmentExists = $true
        break
    }

    $parts = $lineText.Trim() -split "\s+"
    if ($parts.Count -gt 0) {
        $environmentPath = $parts[-1]
        try {
            $leaf = Split-Path -Path $environmentPath -Leaf
            if ($leaf -ieq $CondaEnvironment) {
                $EnvironmentExists = $true
                break
            }
        } catch {
            # Ignore non-path lines.
        }
    }
}

if ($EnvironmentExists) {
    & $CondaExe env update -n $CondaEnvironment -f $CondaYaml --prune
    Assert-LastExitCode "Updating the SoccerNet Conda environment"
} else {
    & $CondaExe env create -f $CondaYaml
    Assert-LastExitCode "Creating the SoccerNet Conda environment"
}

Write-Step "Verifying TensorFlow, SoccerNet and extractor dependencies"
$ImportCheck = "import ssl; import tensorflow as tf; import SoccerNet; import cv2; import skvideo; import imutils; import sklearn; print('Extractor imports OK'); print('TensorFlow:', tf.__version__); print('OpenSSL:', ssl.OPENSSL_VERSION)"
& $CondaExe run --no-capture-output -n $CondaEnvironment python -c $ImportCheck
Assert-LastExitCode "Extractor dependency check"

Write-Step "Preparing the pinned SoccerNet extractor assets"
Push-Location $BackendDir
try {
    & $BackendPython .\scripts\setup_soccernet_extractor.py
    Assert-LastExitCode "Preparing SoccerNet extractor assets"
} finally {
    Pop-Location
}

if (-not $SkipModelWeights) {
    Write-Step "Downloading or validating the ResNet-152 ImageNet weights"
    $WeightCheck = "from tensorflow.keras.applications import ResNet152; ResNet152(include_top=True, weights='imagenet', classes=1000); print('ResNet152 weights ready')"
    & $CondaExe run --no-capture-output -n $CondaEnvironment python -c $WeightCheck
    Assert-LastExitCode "Preparing ResNet-152 weights"
}

if (-not $SkipFrontend) {
    Write-Step "Installing and validating frontend packages"
    Push-Location $FrontendDir
    try {
        $PackageLock = Join-Path $FrontendDir "package-lock.json"
        if (Test-Path -LiteralPath $PackageLock) {
            & npm ci
            Assert-LastExitCode "Installing frontend packages with npm ci"
        } else {
            & npm install
            Assert-LastExitCode "Installing frontend packages with npm install"
        }

        & npm run build
        Assert-LastExitCode "Building the frontend"
    } finally {
        Pop-Location
    }
}

Write-Step "Running the backend preflight"
$env:SOCCERNET_EXECUTION_MODE = "conda"
$env:SOCCERNET_CONDA_EXE = $CondaExe
$env:SOCCERNET_CONDA_ENV = $CondaEnvironment
$env:SOCCERNET_GPU = "-1"
Remove-Item Env:SOCCERNET_EXTRACTOR_PYTHON -ErrorAction SilentlyContinue
Push-Location $BackendDir
try {
    & $BackendPython -c "from app.pipeline.feature_extractor import preflight_soccernet_extractor; import pprint; pprint.pp(preflight_soccernet_extractor())"
    Assert-LastExitCode "Backend preflight"
} finally {
    Pop-Location
}

Write-Host "`nSetup completed successfully." -ForegroundColor Green
Write-Host "Run the project with: .\run.ps1"
