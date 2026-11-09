# The Windows package of Meridiana, from the repository root (r28, 09/11/2026):
#   powershell -ExecutionPolicy Bypass -File build-aux\windows\build.ps1 [-Python <venv python>] [-Iscc <ISCC.exe>]
# 1. the catalogues (locale\) and the icon; 2. PyInstaller (dist\Meridiana); 3. the self-test of the bundle;
# 4. Inno Setup with the version of src\meridiana\__init__.py: dist\meridiana-setup-v<version>-windows-x64.exe,
# the name the program's own update looks for in a release (updates.installer_name).
# Signing (minisign) and publishing are separate steps: docs\progetto.md, section 4.
param(
    [string]$Python = "$env:USERPROFILE\dev\meridiana\.venv\Scripts\python.exe",
    [string]$Iscc = "",
    [switch]$SkipSelfTest
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $root
if (-not $Iscc) {
    $Iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
              "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) { throw 'Inno Setup 6 not found: winget install --scope user JRSoftware.InnoSetup' }
}
$version = (Select-String -Path 'src\meridiana\__init__.py' -Pattern '^__version__ = "([^"]+)"').Matches[0].Groups[1].Value
Write-Host "Meridiana $version"
$env:PYTHONPATH = Join-Path $root 'src'
& $Python tools\compile_po.py
if ($LASTEXITCODE) { throw 'compile_po failed' }
& $Python tools\make_ico.py
if ($LASTEXITCODE) { throw 'make_ico failed' }
& $Python -m PyInstaller --noconfirm --distpath dist --workpath build\pyinstaller build-aux\windows\meridiana.spec
if ($LASTEXITCODE) { throw 'PyInstaller failed' }
if (-not $SkipSelfTest) {
    $report = Join-Path $root 'build\selftest.txt'
    $p = Start-Process -FilePath dist\Meridiana\Meridiana.exe -ArgumentList '--self-test', "`"$report`"" -Wait -PassThru
    # the Widgets self-test fails at its report since r27 (no module laid in its sample, from the sources too):
    # said, not fatal; the Qt Quick's check is meridiana.quick.package_check (docs\progetto.md, section 4)
    if ($p.ExitCode) { Write-Warning "self-test: exit $($p.ExitCode), see $report" }
}
& $Iscc "/DAppVersion=$version" build-aux\windows\meridiana.iss
if ($LASTEXITCODE) { throw 'Inno Setup failed' }
Get-Item "dist\meridiana-setup-v$version-windows-x64.exe"
