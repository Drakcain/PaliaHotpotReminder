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

function Get-IcoSizes {
    param([Parameter(Mandatory = $true)][string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 6) {
        throw "ICO file too small: $Path"
    }
    $count = [BitConverter]::ToUInt16($bytes, 4)
    $sizes = New-Object System.Collections.Generic.List[string]
    $offset = 6
    for ($i = 0; $i -lt $count; $i++) {
        if ($offset + 15 -ge $bytes.Length) {
            throw "ICO directory entry truncated in $Path"
        }
        $width = if ($bytes[$offset] -eq 0) { 256 } else { [int]$bytes[$offset] }
        $height = if ($bytes[$offset + 1] -eq 0) { 256 } else { [int]$bytes[$offset + 1] }
        $sizes.Add(("{0}x{1}" -f $width, $height)) | Out-Null
        $offset += 16
    }
    return $sizes
}

Write-Host '==> Checking required repository files' -ForegroundColor Cyan
foreach ($path in @(
    'BUILD.md',
    'INSTALL-NOTICE.txt',
    'SECURITY.md',
    'SIGNING.md',
    'THIRD-PARTY-NOTICES.md',
    'VERSION',
    'README.md',
    '.github\ISSUE_TEMPLATE\bug_report.md',
    '.github\ISSUE_TEMPLATE\config.yml',
    'src',
    'assets',
    'assets\App Icon\HPR_Icon.ico',
    'assets\App Icon\HPR_Icon.png',
    'assets\App Icon\HPR_Icon_Source_OG.png',
    'assets\Branding\Palia-HPR-brand-banner.png',
    'assets\Message Board\popup_scroll.png',
    'assets\Message Board\popup_scroll_clean.png',
    'scripts\build_installer.ps1',
    'scripts\Test-Repo.ps1',
    'installer\PaliaHotpotReminder.iss',
    'installer\README.md',
    'installer\assets',
    'docs\CHANGELOG.md',
    'docs\INSTALLER.md',
    'docs\PROJECT_IDENTITY.md',
    'docs\PROJECT_TRACKER.md',
    'docs\RELEASE_PROCESS.md',
    'docs\UI_ROADMAP.md',
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

Write-Host '==> Checking removed root clutter stays removed' -ForegroundColor Cyan
foreach ($path in @(
    'README-START-HERE.txt',
    'requirements.txt',
    'docs\GITHUB_RELEASE_CHECKLIST.md',
    'docs\GPT_Handoff_Report.md',
    'docs\RELEASE_NOTES-v2.8.md',
    'docs\RELEASE-NOTES-v2.8.md',
    'docs\RELEASE-NOTES-v2.9.md',
    'docs\CUSTOMTKINTER_MODERNIZATION_PLAN.md',
    'docs\UI-THEME-GUIDE.md'
)) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $path)) {
        Add-Failure "Removed stale file has been reintroduced: $path"
    }
}

Write-Host '==> Checking version references' -ForegroundColor Cyan
$versionFiles = @(
    'src\app_version.py',
    'scripts\build_installer.ps1',
    'installer\PaliaHotpotReminder.iss',
    'README.md',
    'BUILD.md',
    'INSTALL-NOTICE.txt',
    'SECURITY.md',
    'SIGNING.md',
    'THIRD-PARTY-NOTICES.md',
    'VERSION',
    'docs\INSTALLER.md',
    'docs\CHANGELOG.md',
    'docs\RELEASE_PROCESS.md'
)
foreach ($path in $versionFiles) {
    $full = Join-Path $repoRoot $path
    if (Test-Path -LiteralPath $full) {
        $text = Get-Content -LiteralPath $full -Raw
        if ($text -notmatch 'v3\.1\.2|3\.1\.2') {
            Add-Failure "No v3.1.2/3.1.2 reference found in $path"
        }
    }
}

Write-Host '==> Checking installer target and preservation rules' -ForegroundColor Cyan
$iss = Get-Content -LiteralPath (Join-Path $repoRoot 'installer\PaliaHotpotReminder.iss') -Raw
foreach ($pattern in @(
    'DefaultDirName=C:\\Tools\\PaliaHotpotReminder',
    'PrivilegesRequired=admin',
    'MyPayloadDir',
    'CloseApplications=no',
    'PrepareToInstall',
    'Hotpot-Remind\.exe',
    'taskkill /IM',
    'onlyifdoesntexist',
    'uninsneveruninstall',
    'InfoBeforeFile=\.\.\\INSTALL-NOTICE\.txt',
    'THIRD-PARTY-NOTICES\.md',
    'SIGNING\.md',
    '\.\.\\VERSION',
    'PaliaHotpotReminder-Setup-v3\.1\.2'
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
    'PaliaHotpotReminder-Setup-v3\.1\.2\.exe',
    'C:\\Tools\\PaliaHotpotReminder'
)) {
    if ($readme -notmatch $pattern) {
        Add-Failure "README missing installed-first wording: $pattern"
    }
}

Write-Host '==> Checking professional documentation truth' -ForegroundColor Cyan
$docsText = @(
    (Get-Content -LiteralPath (Join-Path $repoRoot 'README.md') -Raw),
    (Get-Content -LiteralPath (Join-Path $repoRoot 'INSTALL-NOTICE.txt') -Raw),
    (Get-Content -LiteralPath (Join-Path $repoRoot 'SECURITY.md') -Raw),
    (Get-Content -LiteralPath (Join-Path $repoRoot 'SIGNING.md') -Raw),
    (Get-Content -LiteralPath (Join-Path $repoRoot 'THIRD-PARTY-NOTICES.md') -Raw),
    (Get-Content -LiteralPath (Join-Path $repoRoot 'docs\PROJECT_IDENTITY.md') -Raw),
    (Get-Content -LiteralPath (Join-Path $repoRoot 'docs\RELEASE_PROCESS.md') -Raw)
) -join "`n"
foreach ($pattern in @(
    'installer-first|installed Windows reminder utility',
    'C:\\Tools\\PaliaHotpotReminder',
    'PaliaHotpotReminder-Setup-v3\.1\.2\.exe',
    'does not modify Palia',
    'read game memory',
    'inject|hook',
    'network traffic',
    'automate gameplay',
    'unsigned',
    'SHA-256',
    'not affiliated'
)) {
    if ($docsText -notmatch $pattern) {
        Add-Failure "Professional docs missing expected truth: $pattern"
    }
}

Write-Host '==> Checking documentation consolidation' -ForegroundColor Cyan
$rootAndDocsText = Get-ChildItem -LiteralPath $repoRoot -File |
    Where-Object { $_.Extension -in @('.md', '.txt') } |
    ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }
$rootAndDocsText += Get-ChildItem -LiteralPath (Join-Path $repoRoot 'docs') -File |
    Where-Object { $_.Extension -in @('.md', '.txt') } |
    ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }
$combinedText = ($rootAndDocsText -join "`n")
foreach ($pattern in @(
    'GITHUB_RELEASE_CHECKLIST',
    'GitHub release checklist',
    'GPT_Handoff_Report',
    'RELEASE-NOTES-v2\.8',
    'RELEASE_NOTES-v2\.8',
    'RELEASE-NOTES-v2\.9',
    'CUSTOMTKINTER_MODERNIZATION_PLAN',
    'UI-THEME-GUIDE',
    'README-START-HERE',
    'requirements\.txt',
    'tools\\Test-Repo',
    'tools\\build_installer',
    'tools\\build_portable',
    'build_portable'
)) {
    if ($combinedText -match $pattern) {
        Add-Failure "Documentation contains stale reference pattern: $pattern"
    }
}

Write-Host '==> Checking release process and changelog truth' -ForegroundColor Cyan
$releaseProcess = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\RELEASE_PROCESS.md') -Raw
foreach ($pattern in @(
    'Release Process',
    'PaliaHotpotReminder-Setup-v3\.1\.2\.exe',
    'PaliaHotpotReminder-Setup-v3\.1\.2\.exe\.sha256',
    'C:\\Tools\\PaliaHotpotReminder',
    'Portable ZIP files are not the normal release path',
    'No Palia memory reading',
    'No injection or hooking',
    'No network inspection',
    'No gameplay automation',
    'No game file edits',
    'Only OCRs the user-selected visible clock region',
    'CloseApplications=no|Hotpot-Remind\.exe|taskkill'
)) {
    if ($releaseProcess -notmatch $pattern) {
        Add-Failure "Release process doc missing expected pattern: $pattern"
    }
}

$changelog = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\CHANGELOG.md') -Raw
foreach ($pattern in @(
    '## v3\.1\.2',
    '## v3\.1\.1',
    '## v3\.1',
    '## v3\.0',
    '## v2\.9',
    '## v2\.8',
    'Installer-first|installer-first',
    'PaliaHotpotReminder-Setup-v3\.1\.2\.exe',
    'PaliaHotpotReminder-v2\.8-portable\.zip',
    'No gameplay automation'
)) {
    if ($changelog -notmatch $pattern) {
        Add-Failure "Changelog missing expected pattern: $pattern"
    }
}

$uiRoadmap = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\UI_ROADMAP.md') -Raw
foreach ($pattern in @(
    'Current UI State',
    'Theme Direction',
    'CustomTkinter Modernization Notes',
    'Asset And Branding Rules',
    'Deferred Ideas',
    'Do Not Change Without Testing'
)) {
    if ($uiRoadmap -notmatch $pattern) {
        Add-Failure "UI roadmap missing expected section: $pattern"
    }
}

Write-Host '==> Checking CustomTkinter v3.1.2 fixed-window UI wiring' -ForegroundColor Cyan
$uiSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\ui.py') -Raw
$mainSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\main.py') -Raw
$themeSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\theme.py') -Raw
$buildScript = Get-Content -LiteralPath (Join-Path $repoRoot 'scripts\build_installer.ps1') -Raw
$shellSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\ui_shell.py') -Raw
$stateSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\ui_state.py') -Raw
$actionsSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\ui_actions.py') -Raw
$pageIndexSource = Get-Content -LiteralPath (Join-Path $repoRoot 'src\ui_pages\__init__.py') -Raw
foreach ($pattern in @(
    'import customtkinter as ctk',
    'ctk\.CTkFrame',
    'StatusChip',
    'UIShell',
    'UIState',
    'UIActions',
    'PAGE_BUILDERS',
    'build_dashboard_page',
    'build_clock_setup_page',
    'build_reminders_page',
    'build_automation_page',
    'build_diagnostics_page',
    'build_settings_page',
    'resizable\(False, False\)',
    '_compact_palia_chip_text',
    '_compact_reminder_chip_text',
    '_compact_clock_chip_text',
    'High-Contrast Black Purple|HPR High-Contrast Black Purple',
    'customtkinter',
    '--collect-data'
)) {
    $haystack = ($uiSource, $mainSource, $themeSource, $buildScript, $shellSource, $stateSource, $actionsSource, $pageIndexSource) -join "`n"
    if ($haystack -notmatch $pattern) {
        Add-Failure "CustomTkinter v3.1.2 wiring missing expected pattern: $pattern"
    }
}
if ($shellSource -match 'CTkScrollableFrame') {
    Add-Failure 'UI shell still uses CTkScrollableFrame pages; fixed-window pages should not show a right-side page scrollbar.'
}

Write-Host '==> Checking .gitignore release/runtime exclusions' -ForegroundColor Cyan
$gitignore = Get-Content -LiteralPath (Join-Path $repoRoot '.gitignore') -Raw
foreach ($pattern in @(
    '(?m)^dist/$',
    '(?m)^build/$',
    '(?m)^logs/$',
    '(?m)^debug/$',
    '(?m)^config/settings\.json$',
    '(?m)^config/recall_state\.json$',
    '(?m)^\*\.exe$',
    '(?m)^\*\.zip$',
    '(?m)^\*\.log$'
)) {
    if ($gitignore -notmatch $pattern) {
        Add-Failure ".gitignore missing expected exclusion: $pattern"
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

Write-Host '==> Checking app icon source and ICO frame sizes' -ForegroundColor Cyan
$iconPng = Join-Path $repoRoot 'assets\App Icon\HPR_Icon.png'
$iconOg = Join-Path $repoRoot 'assets\App Icon\HPR_Icon_Source_OG.png'
$iconIco = Join-Path $repoRoot 'assets\App Icon\HPR_Icon.ico'
$pngHash = (Get-FileHash -LiteralPath $iconPng -Algorithm SHA256).Hash
$ogHash = (Get-FileHash -LiteralPath $iconOg -Algorithm SHA256).Hash
if ($pngHash -ne $ogHash) {
    Add-Failure 'HPR_Icon.png does not match HPR_Icon_Source_OG.png; icon source drift detected.'
}
$icoSizes = Get-IcoSizes -Path $iconIco
foreach ($size in @('16x16', '24x24', '32x32', '48x48', '64x64', '128x128', '256x256')) {
    if ($icoSizes -notcontains $size) {
        Add-Failure "HPR_Icon.ico missing required embedded size: $size"
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
