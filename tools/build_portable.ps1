[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

$releaseName = 'PaliaHotpotReminder-v2.8-portable'
$releaseRoot = Join-Path $repoRoot "dist\$releaseName"
$zipPath = Join-Path $repoRoot "dist\$releaseName.zip"
$pyiDist = Join-Path $repoRoot 'dist\pyinstaller-build'
$pyiWork = Join-Path $repoRoot 'build\pyinstaller-work'
$pyiSpec = Join-Path $repoRoot 'build\pyinstaller-spec'
$mainScript = Join-Path $repoRoot 'src\main.py'
$requirementsPath = Join-Path $repoRoot 'requirements.txt'
$assetsDir = Join-Path $repoRoot 'assets'
$configDir = Join-Path $repoRoot 'config'
$iconPath = Join-Path $assetsDir 'app_icon.ico'
$tesseractSource = 'C:\Program Files\Tesseract-OCR'
$portableTesseract = Join-Path $releaseRoot 'tesseract'
$portableAssets = Join-Path $releaseRoot 'assets'
$portableConfig = Join-Path $releaseRoot 'config'
$portableExeName = 'Hotpot-Remind.exe'
$portableIconName = 'Hotpot-Remind.ico'

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

function Invoke-Py312 {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & py -3.12 @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: py -3.12 $($Arguments -join ' ')"
    }
}

function Remove-PathIfExists {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

Write-Step 'Verifying Python 3.12'
$pythonVersion = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0 -or -not $pythonVersion.StartsWith('3.12')) {
    throw 'Python 3.12 is required but was not found.'
}
Write-Host "Python 3.12 detected: $pythonVersion"

Write-Step 'Verifying project inputs'
Assert-PathExists -Path $mainScript -Message "Missing entrypoint: $mainScript"
Assert-PathExists -Path $requirementsPath -Message "Missing requirements file: $requirementsPath"
Assert-PathExists -Path $assetsDir -Message "Missing assets folder: $assetsDir"
Assert-PathExists -Path $configDir -Message "Missing config folder: $configDir"
Assert-PathExists -Path $iconPath -Message "Missing app icon: $iconPath"
Assert-PathExists -Path $tesseractSource -Message "Missing local Tesseract folder: $tesseractSource"
Assert-PathExists -Path (Join-Path $tesseractSource 'tesseract.exe') -Message "Missing tesseract.exe in $tesseractSource"
Assert-PathExists -Path (Join-Path $tesseractSource 'tessdata\eng.traineddata') -Message "Missing tessdata\eng.traineddata in $tesseractSource"

Write-Step 'Installing/verifying Python requirements'
Invoke-Py312 @('-m', 'pip', 'install', '-r', $requirementsPath)
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

Write-Step 'Cleaning old build artifacts'
Remove-PathIfExists -Path $releaseRoot
Remove-PathIfExists -Path $zipPath
Remove-PathIfExists -Path $pyiDist
Remove-PathIfExists -Path (Join-Path $repoRoot 'build')
Remove-PathIfExists -Path (Join-Path $repoRoot 'PaliaHotpotReminder.spec')

Write-Step 'Building PyInstaller onedir package'
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
    '--hidden-import', 'PIL',
    '--hidden-import', 'PIL.Image',
    '--hidden-import', 'PIL.ImageDraw',
    '--paths', (Join-Path $repoRoot 'src'),
    '--distpath', $pyiDist,
    '--workpath', $pyiWork,
    '--specpath', $pyiSpec,
    $mainScript
)
Invoke-Py312 $pyinstallerArgs

$buildOutputRoot = Join-Path $pyiDist 'PaliaHotpotReminder'
Assert-PathExists -Path $buildOutputRoot -Message "PyInstaller output missing: $buildOutputRoot"

Write-Step 'Creating portable release layout'
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
Copy-Item -Path (Join-Path $buildOutputRoot '*') -Destination $releaseRoot -Recurse -Force
Copy-Item -Path $assetsDir -Destination $portableAssets -Recurse -Force
Copy-Item -Path $configDir -Destination $portableConfig -Recurse -Force
Remove-PathIfExists -Path (Join-Path $portableConfig 'recall_state.json')
New-Item -ItemType Directory -Force -Path $portableTesseract | Out-Null
Copy-Item -Path (Join-Path $tesseractSource '*') -Destination $portableTesseract -Recurse -Force

$portableSettingsPath = Join-Path $portableConfig 'settings.json'
$portableExamplePath = Join-Path $portableConfig 'settings.example.json'
foreach ($settingsFile in @($portableSettingsPath, $portableExamplePath)) {
    if (Test-Path -LiteralPath $settingsFile) {
        $settings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
        $settings.tesseract_cmd = 'tesseract\tesseract.exe'
        $settings | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $settingsFile -Encoding UTF8
    }
}

if (Test-Path -LiteralPath $portableSettingsPath) {
    $cleanReleaseSettings = Get-Content -LiteralPath $portableExamplePath -Raw | ConvertFrom-Json
    $cleanReleaseSettings.clock_setup_completed = $false
    $cleanReleaseSettings.clock_region = @{}
    $cleanReleaseSettings | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $portableSettingsPath -Encoding UTF8
}

Copy-Item -LiteralPath $iconPath -Destination (Join-Path $releaseRoot $portableIconName) -Force
$builtExe = Join-Path $releaseRoot 'PaliaHotpotReminder.exe'
$renamedExe = Join-Path $releaseRoot $portableExeName
if (Test-Path -LiteralPath $renamedExe) {
    Remove-Item -LiteralPath $renamedExe -Force
}
Rename-Item -LiteralPath $builtExe -NewName $portableExeName

& attrib +r $releaseRoot | Out-Null

@"
PaliaHotpotReminder v2.8 Portable Release

1. Extract the whole ZIP first.
2. Open Palia.
3. Run Hotpot-Remind.exe.
4. Click Setup Clock once.
5. Click Start Reminder. Auto-arm is enabled by default for later sessions.
6. HPR remembers safe local setup facts and automatically rechecks them after tray restore or app refocus.
7. Keep the assets, config, and tesseract folders next to the EXE.
8. This is an external reminder app, not a Palia mod.
9. It does not modify Palia, read game memory, or automate gameplay.
10. It only reads the clock area selected through Setup Clock.
11. Dark Mode, Minimize to tray, Close to tray, logging, Smart Resume, and Smart Recall are enabled by default.
12. Debug / Support tools are available inside the app if support evidence is needed.
"@ | Set-Content -LiteralPath (Join-Path $releaseRoot 'README-START-HERE.txt') -Encoding UTF8

$installerScript = Join-Path $repoRoot 'installer\PaliaHotpotReminder.iss'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $installerScript) | Out-Null
@"
; PaliaHotpotReminder v2.8 installer scaffold
; Build with Inno Setup when available.

[Setup]
AppName=PaliaHotpotReminder
AppVersion=2.8
DefaultDirName={localappdata}\PaliaHotpotReminder
DefaultGroupName=PaliaHotpotReminder
OutputBaseFilename=PaliaHotpotReminder-v2.8-Setup
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=no
DisableDirPage=no
PrivilegesRequired=lowest

[Files]
Source: "..\dist\PaliaHotpotReminder-v2.8-portable\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Hotpot-Remind"; Filename: "{app}\Hotpot-Remind.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\Hotpot-Remind"; Filename: "{app}\Hotpot-Remind.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
"@ | Set-Content -LiteralPath $installerScript -Encoding ASCII

Write-Step 'Creating portable ZIP'
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path $releaseRoot -DestinationPath $zipPath -Force

Write-Step 'Portable build complete'
Write-Host "Release folder: $releaseRoot"
Write-Host "ZIP file: $zipPath"
