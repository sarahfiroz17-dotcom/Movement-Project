# Sets up the Movement Project backend (Python venv) and frontend (Node/npm).
# Run from PowerShell: .\setup.ps1
# If you get an execution policy error, run this first:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend     = Join-Path $ProjectRoot "backend"
$Frontend    = Join-Path $ProjectRoot "frontend"

# ── Backend ───────────────────────────────────────────────────────────────────
Write-Host "== Backend: Python venv ==" -ForegroundColor Cyan

# scikit-learn/numpy/pandas have no prebuilt wheels for Python 3.13.
# Try py launcher first (Windows standard), then explicit version names.
$PY = $null
$candidates = @("py -3.12", "py -3.11", "python3.12", "python3.11", "python")

foreach ($cand in $candidates) {
    $exe, $arg = $cand -split " ", 2
    try {
        $ver = & $exe $arg --version 2>&1 | Select-String "3\.(11|12)\."
        if ($ver) {
            $PY = if ($arg) { "$exe $arg" } else { $exe }
            break
        }
    } catch { }
}

if (-not $PY) {
    Write-Host ""
    Write-Host "ERROR: Python 3.11 or 3.12 not found." -ForegroundColor Red
    Write-Host "Install from https://www.python.org/downloads/"
    Write-Host "Tick 'Add Python to PATH' during installation."
    exit 1
}

$verStr = Invoke-Expression "$PY --version"
Write-Host "Using $PY ($verStr)"

$VenvPath = Join-Path $Backend "venv"
if (Test-Path $VenvPath) {
    Remove-Item -Recurse -Force $VenvPath
}

Invoke-Expression "$PY -m venv `"$VenvPath`""

$Activate = Join-Path $VenvPath "Scripts\Activate.ps1"
& $Activate

python -m pip install --upgrade pip
pip install -r (Join-Path $Backend "requirements.txt")

deactivate
Write-Host "Backend venv ready at $VenvPath" -ForegroundColor Green

# ── Frontend ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "== Frontend: Node & npm ==" -ForegroundColor Cyan

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "ERROR: Node.js not found." -ForegroundColor Red
    Write-Host "Install from https://nodejs.org/ (LTS version recommended)."
    Write-Host "After installing, re-run this script."
    exit 1
}

Write-Host "Node $(node -v),  npm $(npm -v)"

Push-Location $Frontend
npm install
Pop-Location

Write-Host ""
Write-Host "All set. Open two separate PowerShell windows to run the project:" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:" -ForegroundColor Yellow
Write-Host "    cd `"$Backend`""
Write-Host "    .\venv\Scripts\Activate.ps1"
Write-Host "    uvicorn main:app --reload"
Write-Host ""
Write-Host "  Frontend:" -ForegroundColor Yellow
Write-Host "    cd `"$Frontend`""
Write-Host "    npm run dev"
