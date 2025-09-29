Param(
  [switch]$Clean = $false,
  [string]$Name = "HSVCalibrator",
  [string]$VersionFile = "windows/version_file.txt"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Detecting Python..."
$pycmd = $null
try { $pycmd = (Get-Command py -ErrorAction SilentlyContinue) } catch { }
if ($pycmd) { $python = "py -3" } else { $python = "python" }
Write-Host "Using Python launcher: $python"

if ($Clean) {
  Write-Host "==> Cleaning build artifacts"
  Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue | Out-Null
  Get-ChildItem -Filter *.spec | Remove-Item -Force -ErrorAction SilentlyContinue | Out-Null
}

if (-not (Test-Path ".venv")) {
  Write-Host "==> Creating virtual environment (.venv)"
  & $python -m venv .venv
}

Write-Host "==> Activating virtual environment"
. .\.venv\Scripts\Activate.ps1

Write-Host "==> Installing dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

Write-Host "==> Building $Name.exe with PyInstaller"
pyinstaller tools/hsv_calibrator.py --onefile --name $Name --noconfirm --clean --version-file $VersionFile

$exePath = Join-Path "dist" ("$Name.exe")
if (-not (Test-Path $exePath)) {
  throw "Build failed: $exePath not found"
}

Write-Host "==> Creating zip archive"
$zipPath = Join-Path "dist" ("$Name-win64.zip")
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $exePath -DestinationPath $zipPath -Force

Write-Host "✅ Done"
Write-Host "Executable: $exePath"
Write-Host "Zip:        $zipPath"
