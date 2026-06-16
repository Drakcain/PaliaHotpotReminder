[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

$failures = New-Object System.Collections.Generic.List[string]

function Add-Failure {
    param([Parameter(Mandatory = $true)][string]$Message)
    $failures.Add($Message) | Out-Null
}

function Test-RequiredPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $Path))) {
        Add-Failure "Missing required path: $Path"
    }
}

function Test-UntrackedRuntimePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $tracked = & git ls-files -- $Path 2>$null
    if ($tracked) {
        Add-Failure "Runtime/local path is tracked but should not be: $Path"
    }
}

Write-Host '==> Checking required repository files' -ForegroundColor Cyan
foreach ($path in @(
    'README.md',
    'requirements.txt',
    'src',
    'assets',
    'assets\App Icon\HPR_Icon.ico',
    'assets\App Icon\HPR_Icon.png',
    'assets\Branding\Palia-HPR-brand-banner.png',
    'assets\Message Board\popup_scroll.png',
    'assets\Message Board\popup_scroll_clean.png',
    'scripts\build_installer.ps1',
    'scripts\Test-Repo.ps1',
    'installer\PaliaHotpotReminder.iss',
    'installer\README.md',
    'installer\assets',
    'docs\INSTALLER.md',
    'docs\RELEASE-NOTES-v2.9.md',
    'config\settings.example.json'
)) {
    Test-RequiredPath $path
}

Write-Host '==> Checking local runtime paths are not tracked' -ForegroundColor Cyan
foreach ($path in @(
    'config/settings.json',
    'config/recall_state.json',
    'logs',
    'debug',
    'exports',
    'dist'
)) {
    Test-UntrackedRuntimePath $path
}

Write-Host '==> Checking version references' -ForegroundColor Cyan
$versionFiles = @(
    'src\app_version.py',
    'scripts\build_installer.ps1',
    'installer\PaliaHotpotReminder.iss',
    'README.md',
    'README-START-HERE.txt',
    'docs\INSTALLER.md',
    'docs\RELEASE-NOTES-v2.9.md',
    'docs\GITHUB_RELEASE_CHECKLIST.md'
)
foreach ($path in $versionFiles) {
    $full = Join-Path $repoRoot $path
    if (Test-Path -LiteralPath $full) {
        $text = Get-Content -LiteralPath $full -Raw
        if ($text -notmatch 'v2\.9|2\.9') {
            Add-Failure "No v2.9/2.9 reference found in $path"
        }
    }
}

Write-Host '==> Checking installer target and preservation rules' -ForegroundColor Cyan
$iss = Get-Content -LiteralPath (Join-Path $repoRoot 'installer\PaliaHotpotReminder.iss') -Raw
foreach ($pattern in @(
    'DefaultDirName=C:\\Tools\\PaliaHotpotReminder',
    'PrivilegesRequired=admin',
    'MyPayloadDir',
    'onlyifdoesntexist',
    'uninsneveruninstall',
    'PaliaHotpotReminder-Setup-v2\.9'
)) {
    if ($iss -notmatch $pattern) {
        Add-Failure "Installer script missing expected pattern: $pattern"
    }
}

Write-Host '==> Checking installed-first README wording' -ForegroundColor Cyan
$readme = Get-Content -LiteralPath (Join-Path $repoRoot 'README.md') -Raw
foreach ($pattern in @(
    'installed Windows reminder utility',
    'assets/Branding/Palia-HPR-brand-banner\.png',
    'Users download one file',
    'PaliaHotpotReminder-Setup-v2\.9\.exe',
    'C:\\Tools\\PaliaHotpotReminder'
)) {
    if ($readme -notmatch $pattern) {
        Add-Failure "README missing installed-first wording: $pattern"
    }
}

Write-Host '==> Checking asset path compatibility' -ForegroundColor Cyan
$pathsPy = Get-Content -LiteralPath (Join-Path $repoRoot 'src\paths.py') -Raw
foreach ($pattern in @(
    'LEGACY_RESOURCE_PATHS',
    'assets/popup_scroll_clean\.png',
    'Message Board',
    'popup_scroll_clean\.png',
    'App Icon',
    'HPR_Icon\.ico'
)) {
    if ($pathsPy -notmatch $pattern) {
        Add-Failure "Path resolver missing legacy asset compatibility pattern: $pattern"
    }
}

if ($failures.Count -gt 0) {
    Write-Host 'Repository validation failed:' -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host 'Repository validation passed.' -ForegroundColor Green
