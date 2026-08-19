<#
.SYNOPSIS
    web-mcp installer (Windows).
.DESCRIPTION
    Installs the web-mcp server and prints the next step for wiring it into
    Claude Code. Safe to re-run; it upgrades an existing install in place.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$RepoUrl  = 'https://github.com/ManiaSacha/web-mcp'
$MinMinor = 10

# ---- locate a suitable interpreter -------------------------------------------
$py = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, $MinMinor) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $py = $candidate; break }
}

if (-not $py) {
    Write-Error "Python 3.$MinMinor+ is required but was not found on PATH.`nInstall it from https://www.python.org/downloads/ and re-run this script."
    exit 1
}

$version = (& $py --version)
$location = (Get-Command $py).Source
Write-Host "Using $version at $location"

# ---- install ------------------------------------------------------------------
# Run from a checkout if one is present, otherwise pull straight from GitHub.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path (Join-Path $scriptDir 'pyproject.toml')) {
    Write-Host "Installing from local checkout: $scriptDir"
    & $py -m pip install --upgrade $scriptDir
} else {
    Write-Host "Installing from $RepoUrl"
    & $py -m pip install --upgrade "git+$RepoUrl.git"
}

if ($LASTEXITCODE -ne 0) {
    Write-Error 'pip install failed. See the output above.'
    exit 1
}

# ---- verify -------------------------------------------------------------------
$installed = Get-Command web-mcp -ErrorAction SilentlyContinue
if (-not $installed) {
    Write-Host ''
    Write-Host 'web-mcp installed, but the "web-mcp" command is not on your PATH.'
    Write-Host 'pip usually places it in:'
    Write-Host '  %APPDATA%\Python\Python3xx\Scripts'
    Write-Host 'Add that directory to PATH, then re-run this script to verify.'
    exit 1
}

Write-Host ''
Write-Host "Installed: $($installed.Source)"
Write-Host ''
Write-Host 'Next - pick one:'
Write-Host ''
Write-Host '  A) Claude Code plugin (also installs the skills and agents):'
Write-Host '       /plugin marketplace add ManiaSacha/web-mcp'
Write-Host '       /plugin install web-mcp@maniasacha-web-mcp'
Write-Host ''
Write-Host '  B) MCP server only:'
Write-Host '       claude mcp add web -- web-mcp --feeds https://hnrss.org/frontpage'
Write-Host ''
Write-Host '  C) Claude Desktop - add this to claude_desktop_config.json:'
Write-Host '       "web": { "command": "web-mcp", "args": ["--feeds", "https://hnrss.org/frontpage"] }'
