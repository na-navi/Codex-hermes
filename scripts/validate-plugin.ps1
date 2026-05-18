<#
.SYNOPSIS
  Validate the codex-hermes plugin structure and check for common issues.
.DESCRIPTION
  Checks:
    - plugin.json is valid JSON with required fields
    - plugin.json.skills points to ./skills/
    - skills/hermes/SKILL.md exists with valid frontmatter
    - invoke-hermes.ps1 exists
    - no hardcoded local usernames or private paths
.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-plugin.ps1
#>

$ErrorActionPreference = "Stop"

$rootDir = Resolve-Path (Split-Path $PSScriptRoot -Parent)
$exitCode = 0

function Write-Pass {
    Write-Host "  [PASS] $($args[0])" -ForegroundColor Green
}

function Write-Fail {
    Write-Host "  [FAIL] $($args[0])" -ForegroundColor Red
    $script:exitCode = 1
}

function Write-Skip {
    Write-Host "  [SKIP] $($args[0])" -ForegroundColor Yellow
}

Write-Host "Validating codex-hermes plugin..." -ForegroundColor Cyan
Write-Host "Root: $rootDir`n" -ForegroundColor Gray

# ---------- plugin.json ----------
Write-Host "--- .codex-plugin/plugin.json ---" -ForegroundColor Cyan

$pluginPath = Join-Path $rootDir ".codex-plugin\plugin.json"
if (-not (Test-Path $pluginPath)) {
    Write-Fail "plugin.json not found at $pluginPath"
} else {
    Write-Pass "plugin.json exists"

    try {
        $plugin = Get-Content $pluginPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
        Write-Pass "plugin.json is valid JSON"

        if ($plugin.name) { Write-Pass "name: $($plugin.name)" } else { Write-Fail "name is missing" }
        if ($plugin.version) { Write-Pass "version: $($plugin.version)" } else { Write-Fail "version is missing" }
        if ($plugin.description) { Write-Pass "description present" } else { Write-Fail "description is missing" }

        if ($plugin.skills -eq "./skills/") {
            Write-Pass "skills: ./skills/"
        } elseif ($plugin.skills) {
            Write-Fail "skills is '$($plugin.skills)', expected './skills/'"
        } else {
            Write-Fail "skills field is missing"
        }

        if ($plugin.interface -and $plugin.interface.displayName) {
            Write-Pass "interface.displayName: $($plugin.interface.displayName)"
        } else {
            Write-Fail "interface.displayName is missing"
        }

        if ($plugin.interface -and $plugin.interface.capabilities) {
            Write-Pass "interface.capabilities: $($plugin.interface.capabilities -join ', ')"
        } else {
            Write-Fail "interface.capabilities is missing"
        }
    } catch {
        Write-Fail "plugin.json parse error: $_"
    }
}

# ---------- skills/hermes/SKILL.md ----------
Write-Host "`n--- skills/hermes/SKILL.md ---" -ForegroundColor Cyan

$skillPath = Join-Path $rootDir "skills\hermes\SKILL.md"
if (-not (Test-Path $skillPath)) {
    Write-Fail "SKILL.md not found at $skillPath"
} else {
    Write-Pass "SKILL.md exists"

    $content = Get-Content $skillPath -Raw -Encoding UTF8
    if ($content -match '(?s)^---\s*\n(.*?)\n---') {
        Write-Pass "YAML frontmatter found"
        $frontmatter = $Matches[1]

        if ($frontmatter -match '^name:\s*(\S+)') {
            $name = $Matches[1]
            if ($name -eq "hermes") {
                Write-Pass "name: hermes"
            } else {
                Write-Fail "name is '$name', expected 'hermes'"
            }
        } else {
            Write-Fail "name field missing in frontmatter"
        }

        if ($frontmatter -match '(?m)^description:\s*') {
            Write-Pass "description field present"
        } else {
            Write-Fail "description field missing in frontmatter"
        }
    } else {
        Write-Fail "No YAML frontmatter (--- ... ---) found"
    }
}

# ---------- scripts/invoke-hermes.ps1 ----------
Write-Host "`n--- scripts/invoke-hermes.ps1 ---" -ForegroundColor Cyan

$wrapperPath = Join-Path $rootDir "scripts\invoke-hermes.ps1"
if (Test-Path $wrapperPath) {
    Write-Pass "invoke-hermes.ps1 exists"
} else {
    Write-Fail "invoke-hermes.ps1 not found at $wrapperPath"
}

# ---------- secret / privacy scan ----------
Write-Host "`n--- privacy & secret scan ---" -ForegroundColor Cyan

$scanPaths = @(
    ".codex-plugin\plugin.json",
    "skills\hermes\SKILL.md",
    "commands\hermes.md",
    ".codex\commands\hermes.md",
    "scripts\invoke-hermes.ps1",
    "README.md",
    "PLANS.md"
)

$foundIssue = $false
$tokenPattern = '(?i)(api[_-]?key|api[_-]?secret|access[_-]?token|bearer)\s*[:=]\s*[""'']?\w{20,}'
$ghTokenPattern = 'gh[op]_[A-Za-z0-9]{20,}'
$userPathPattern = 'C:\\Users\\([^\\]+)\\.*?(?:\s|$)'

foreach ($relPath in $scanPaths) {
    $fullPath = Join-Path $rootDir $relPath
    if (-not (Test-Path $fullPath)) { continue }

    $text = Get-Content $fullPath -Raw -Encoding UTF8

    # Check for hardcoded Windows username patterns like C:\Users\SomeUser\
    $userMatches = [regex]::Matches($text, $userPathPattern)
    foreach ($m in $userMatches) {
        $username = $m.Groups[1].Value
        Write-Fail "$relPath contains hardcoded username '$username'"
        $foundIssue = $true
    }

    # Check for common API key / token patterns
    if ($text -match $tokenPattern) {
        Write-Fail "$relPath may contain a secret/token"
        $foundIssue = $true
    }

    # Check for gho_ / ghp_ tokens
    if ($text -match $ghTokenPattern) {
        Write-Fail "$relPath may contain a GitHub token"
        $foundIssue = $true
    }
}

if (-not $foundIssue) {
    Write-Pass "No hardcoded usernames, secrets, or tokens found in tracked files"
}

# ---------- summary ----------
Write-Host "`n================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "RESULT: PASS" -ForegroundColor Green
} else {
    Write-Host "RESULT: FAIL (exit code $exitCode)" -ForegroundColor Red
}
Write-Host "================================" -ForegroundColor Cyan

exit $exitCode
