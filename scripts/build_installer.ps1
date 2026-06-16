[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

$version = '3.0'
$buildRoot = Join-Path $repoRoot 'build'
$payloadRoot = Join-Path $buildRoot 'installer-payload'
$pyiDist = Join-Path $buildRoot 'pyinstaller-dist'
$pyiWork = Join-Path $buildRoot 'pyinstaller-work'
$pyiSpec = Join-Path $buildRoot 'pyinstaller-spec'
$mainScript = Join-Path $repoRoot 'src\main.py'
$assetsDir = Join-Path $repoRoot 'assets'
$configDir = Join-Path $repoRoot 'config'
$iconPath = Join-Path $assetsDir 'App Icon\HPR_Icon.ico'
$tesseractSource = 'C:\Program Files\Tesseract-OCR'
$payloadTesseract = Join-Path $payloadRoot 'tesseract'
$payloadAssets = Join-Path $payloadRoot 'assets'
$payloadConfig = Join-Path $payloadRoot 'config'
$installerScript = Join-Path $repoRoot 'installer\PaliaHotpotReminder.iss'
$distDir = Join-Path $repoRoot 'dist'
$installerExe = Join-Path $distDir "PaliaHotpotReminder-Setup-v$version.exe"
$hashPath = "$installerExe.sha256"

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

function Remove-PathIfExists {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Invoke-Py312 {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & py -3.12 @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: py -3.12 $($Arguments -join ' ')"
    }
}

function Find-InnoCompiler {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        'C:\Program Files\Inno Setup 6\ISCC.exe'
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    return $null
}

Write-Step 'Locating Inno Setup compiler'
$iscc = Find-InnoCompiler
if (-not $iscc) {
    Write-Host 'Inno Setup 6 was not found.' -ForegroundColor Yellow
    Write-Host 'Install it with:' -ForegroundColor Yellow
    Write-Host '  winget install JRSoftware.InnoSetup' -ForegroundColor Yellow
    throw 'Missing ISCC.exe; installer build cannot continue.'
}
Write-Host "ISCC.exe: $iscc"

Write-Step 'Verifying Python 3.12'
$pythonVersion = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0 -or -not $pythonVersion.StartsWith('3.12')) {
    throw 'Python 3.12 is required but was not found.'
}
Write-Host "Python 3.12 detected: $pythonVersion"

Write-Step 'Verifying project inputs'
Assert-PathExists -Path $mainScript -Message "Missing entrypoint: $mainScript"
Assert-PathExists -Path $assetsDir -Message "Missing assets folder: $assetsDir"
Assert-PathExists -Path $configDir -Message "Missing config folder: $configDir"
Assert-PathExists -Path $iconPath -Message "Missing app icon: $iconPath"
Assert-PathExists -Path $installerScript -Message "Missing installer script: $installerScript"
Assert-PathExists -Path $tesseractSource -Message "Missing local Tesseract folder: $tesseractSource"
Assert-PathExists -Path (Join-Path $tesseractSource 'tesseract.exe') -Message "Missing tesseract.exe in $tesseractSource"
Assert-PathExists -Path (Join-Path $tesseractSource 'tessdata\eng.traineddata') -Message "Missing tessdata\eng.traineddata in $tesseractSource"

Write-Step 'Installing/verifying Python requirements'
$pythonPackages = @(
    'mss',
    'pillow',
    'pytesseract',
    'winotify',
    'pyinstaller',
    'pystray',
    'psutil',
    'customtkinter'
)
$pipInstallArgs = @('-m', 'pip', 'install') + $pythonPackages
Invoke-Py312 $pipInstallArgs
try {
    Invoke-Py312 @('-m', 'PyInstaller', '--version')
} catch {
    Write-Step 'PyInstaller missing, installing explicitly'
    Invoke-Py312 @('-m', 'pip', 'install', 'pyinstaller')
}

Write-Step 'Verifying icon asset is a real ICO'
Invoke-Py312 @(
    '-c',
    "from pathlib import Path; from PIL import Image; p = Path(r'$iconPath'); img = Image.open(p); assert img.format == 'ICO'; print('ICO OK', img.size)"
)

Write-Step 'Running repository validation'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Test-Repo.ps1')
if ($LASTEXITCODE -ne 0) {
    throw 'Repository validation failed.'
}

Write-Step 'Cleaning build and generated release artifacts'
$resolvedBuildRoot = [System.IO.Path]::GetFullPath($buildRoot)
if (-not $resolvedBuildRoot.StartsWith([System.IO.Path]::GetFullPath($repoRoot), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe build path: $resolvedBuildRoot"
}
Remove-PathIfExists -Path $buildRoot
Remove-PathIfExists -Path $installerExe
Remove-PathIfExists -Path $hashPath
Remove-PathIfExists -Path (Join-Path $repoRoot 'PaliaHotpotReminder.spec')
Remove-PathIfExists -Path (Join-Path $repoRoot 'dist\installer')
Remove-PathIfExists -Path (Join-Path $repoRoot 'dist\pyinstaller-build')
Remove-PathIfExists -Path (Join-Path $repoRoot "dist\PaliaHotpotReminder-v$version-portable")
Remove-PathIfExists -Path (Join-Path $repoRoot "dist\PaliaHotpotReminder-v$version-portable.zip")
New-Item -ItemType Directory -Force -Path $payloadRoot, $distDir | Out-Null

Write-Step 'Building PyInstaller app payload'
$pyinstallerArgs = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onedir',
    '--windowed',
    '--name', 'PaliaHotpotReminder',
    '--icon', $iconPath,
    '--hidden-import', 'winotify',
    '--hidden-import', 'pystray',
    '--hidden-import', 'psutil',
    '--hidden-import', 'psutil._psutil_windows',
    '--hidden-import', 'customtkinter',
    '--hidden-import', 'darkdetect',
    '--hidden-import', 'PIL',
    '--hidden-import', 'PIL.Image',
    '--hidden-import', 'PIL.ImageDraw',
    '--collect-data', 'customtkinter',
    '--paths', (Join-Path $repoRoot 'src'),
    '--distpath', $pyiDist,
    '--workpath', $pyiWork,
    '--specpath', $pyiSpec,
    $mainScript
)
Invoke-Py312 $pyinstallerArgs

$buildOutputRoot = Join-Path $pyiDist 'PaliaHotpotReminder'
Assert-PathExists -Path $buildOutputRoot -Message "PyInstaller output missing: $buildOutputRoot"

Write-Step 'Creating installer payload'
Copy-Item -Path (Join-Path $buildOutputRoot '*') -Destination $payloadRoot -Recurse -Force
Copy-Item -Path $assetsDir -Destination $payloadAssets -Recurse -Force
Copy-Item -Path $configDir -Destination $payloadConfig -Recurse -Force
Remove-PathIfExists -Path (Join-Path $payloadConfig 'recall_state.json')
New-Item -ItemType Directory -Force -Path $payloadTesseract | Out-Null
Copy-Item -Path (Join-Path $tesseractSource '*') -Destination $payloadTesseract -Recurse -Force

$payloadSettingsPath = Join-Path $payloadConfig 'settings.json'
$payloadExamplePath = Join-Path $payloadConfig 'settings.example.json'
foreach ($settingsFile in @($payloadSettingsPath, $payloadExamplePath)) {
    if (Test-Path -LiteralPath $settingsFile) {
        $settings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
        $settings.tesseract_cmd = 'tesseract\tesseract.exe'
        $settings | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $settingsFile -Encoding UTF8
    }
}

if (Test-Path -LiteralPath $payloadSettingsPath) {
    $cleanReleaseSettings = Get-Content -LiteralPath $payloadExamplePath -Raw | ConvertFrom-Json
    $cleanReleaseSettings.clock_setup_completed = $false
    $cleanReleaseSettings.clock_region = @{}
    $cleanReleaseSettings | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $payloadSettingsPath -Encoding UTF8
}

Copy-Item -LiteralPath $iconPath -Destination (Join-Path $payloadRoot 'Hotpot-Remind.ico') -Force
$builtExe = Join-Path $payloadRoot 'PaliaHotpotReminder.exe'
$renamedExe = Join-Path $payloadRoot 'Hotpot-Remind.exe'
if (Test-Path -LiteralPath $renamedExe) {
    Remove-Item -LiteralPath $renamedExe -Force
}
Rename-Item -LiteralPath $builtExe -NewName 'Hotpot-Remind.exe'

Write-Step 'Running staged app self-test'
$payloadExe = Join-Path $payloadRoot 'Hotpot-Remind.exe'
Assert-PathExists -Path $payloadExe -Message "Missing staged EXE: $payloadExe"
$selfTest = Start-Process -FilePath $payloadExe -ArgumentList '--self-test' -Wait -PassThru
if ($selfTest.ExitCode -ne 0) {
    throw "Staged app self-test failed with exit code $($selfTest.ExitCode)"
}
Remove-PathIfExists -Path (Join-Path $payloadRoot 'debug')
Remove-PathIfExists -Path (Join-Path $payloadRoot 'logs')
Remove-PathIfExists -Path (Join-Path $payloadConfig 'recall_state.json')

Write-Step 'Compiling Inno Setup installer'
& $iscc "/DMyAppVersion=$version" "/DMyPayloadDir=$payloadRoot" $installerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

Write-Step 'Verifying installer artifact'
Assert-PathExists -Path $installerExe -Message "Expected installer was not created: $installerExe"
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $installerExe
"$($hash.Hash)  $([System.IO.Path]::GetFileName($installerExe))" | Set-Content -LiteralPath $hashPath -Encoding ASCII

Write-Step 'Installer build complete'
Write-Host "Installer: $installerExe"
Write-Host "SHA-256:   $($hash.Hash)"
Write-Host "Hash file: $hashPath"
