param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [string]$Model,
    [string]$Provider,
    [string]$Resume,
    [switch]$Raw
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stateDir = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HERMES_STATE_DIR)) {
    $env:CODEX_HERMES_STATE_DIR
} else {
    Join-Path ([System.IO.Path]::GetTempPath()) "codex-hermes"
}
$modelCache = Join-Path $stateDir "default-model.txt"
$defaultModel = "grok-4.3"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Keep Hermes/Python and PowerShell native-command text on UTF-8. This matters
# on Windows where the active console code page may otherwise corrupt Japanese
# text and Hermes box-drawing output before the parser sees it.
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
}

function Read-CachedModel {
    if (-not (Test-Path $modelCache)) {
        return $null
    }

    $raw = ([System.IO.File]::ReadAllText($modelCache, [System.Text.Encoding]::UTF8)).Trim()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }

    $parts = $raw -split "\|", 2
    return @{
        Model = $parts[0]
        Provider = if ($parts.Count -gt 1) { $parts[1] } else { "" }
    }
}

function Write-CachedModel {
    param(
        [string]$ResolvedModel,
        [string]$ResolvedProvider
    )

    if ([string]::IsNullOrWhiteSpace($ResolvedProvider)) {
        [System.IO.File]::WriteAllText($modelCache, $ResolvedModel, $utf8NoBom)
    } else {
        [System.IO.File]::WriteAllText($modelCache, "$ResolvedModel|$ResolvedProvider", $utf8NoBom)
    }
}

function Get-ResponseBlock {
    param([string]$Output)

    $boxTopLeft = [regex]::Escape([string][char]0x256D)
    $boxBottomLeft = [regex]::Escape([string][char]0x2570)
    $boxHorizontal = [regex]::Escape([string][char]0x2500)
    $boxTopRight = [regex]::Escape([string][char]0x256E)

    $blockPattern = "(?m)^\s*${boxTopLeft}${boxHorizontal}[^\r\n]*${boxTopRight}\r*\n([\s\S]*?)^\s*${boxBottomLeft}${boxHorizontal}"
    $block = [regex]::Match($Output, $blockPattern)
    if ($block.Success) {
        $lines = $block.Groups[1].Value -split "\r?\n"
        return (($lines | ForEach-Object { $_ -replace "^\s{4}", "" }) -join [Environment]::NewLine).Trim()
    }

    $skipPatterns = @(
        "^Query:",
        "^Initializing",
        "^──+$",
        "^Resume this",
        "^\s+hermes --resume",
        "^Session:\s",
        "^Duration:\s",
        "^Messages:\s",
        "^\s*${boxTopLeft}${boxHorizontal}",
        "^\s*${boxBottomLeft}${boxHorizontal}"
    )
    $filtered = $Output -split "\r?\n" | Where-Object {
        $line = $_
        -not ($skipPatterns | Where-Object { $line -match $_ } | Select-Object -First 1)
    }
    $text = ($filtered -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $Output.Trim()
    }
    return $text
}

function Split-MessageFlags {
    param([string]$Text)

    $tokens = [regex]::Matches($Text, '("[^"]*"|''[^'']*''|\S+)') | ForEach-Object {
        $value = $_.Value
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value.Substring(1, $value.Length - 2)
        } else {
            $value
        }
    }

    $remaining = New-Object System.Collections.Generic.List[string]
    $parsedModel = $null
    $parsedProvider = $null
    $parsedRaw = $false
    $i = 0

    while ($i -lt $tokens.Count) {
        if ($tokens[$i] -eq "-m" -and ($i + 1) -lt $tokens.Count) {
            $parsedModel = $tokens[$i + 1]
            $i += 2
            continue
        }
        if ($tokens[$i] -eq "-p" -and ($i + 1) -lt $tokens.Count) {
            $parsedProvider = $tokens[$i + 1]
            $i += 2
            continue
        }
        if ($tokens[$i] -eq "--raw") {
            $parsedRaw = $true
            $i += 1
            continue
        }

        $remaining.Add($tokens[$i])
        $i += 1
    }

    return @{
        Message = ($remaining -join " ").Trim()
        Model = $parsedModel
        Provider = $parsedProvider
        Raw = $parsedRaw
    }
}

if ([string]::IsNullOrWhiteSpace($Resume)) {
    $parsed = Split-MessageFlags -Text $Message
    $Message = $parsed.Message
    if ([string]::IsNullOrWhiteSpace($Model) -and -not [string]::IsNullOrWhiteSpace($parsed.Model)) {
        $Model = $parsed.Model
    }
    if ([string]::IsNullOrWhiteSpace($Provider) -and -not [string]::IsNullOrWhiteSpace($parsed.Provider)) {
        $Provider = $parsed.Provider
    }
    if ($parsed.Raw) {
        $Raw = $true
    }
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    throw "No Hermes message was provided."
}

$cached = Read-CachedModel
if ([string]::IsNullOrWhiteSpace($Model)) {
    if ($cached) {
        $Model = $cached.Model
    } else {
        $Model = $defaultModel
    }
}

if ([string]::IsNullOrWhiteSpace($Provider) -and $cached) {
    $Provider = $cached.Provider
}

Write-CachedModel -ResolvedModel $Model -ResolvedProvider $Provider

$hermes = Get-Command hermes -ErrorAction SilentlyContinue
if (-not $hermes) {
    throw "Hermes CLI was not found on PATH. Install and configure the `hermes` command first."
}

if ([string]::IsNullOrWhiteSpace($Resume)) {
    $args = @("chat", "-q", $Message, "-Q", "-m", $Model)
} else {
    $args = @("-z", $Message, "-m", $Model, "--resume", $Resume)
}

if (-not [string]::IsNullOrWhiteSpace($Provider)) {
    $args += @("--provider", $Provider)
}

$output = & $hermes.Source @args 2>&1
$exitCode = $LASTEXITCODE
$textOutput = ($output | Out-String).TrimEnd()

if ($null -eq $exitCode -and $?) {
    $exitCode = 0
}

if ($exitCode -ne 0) {
    throw "Hermes CLI failed with exit code ${exitCode}:`n$textOutput"
}

$sessionId = $null
$sessionLineMatch = [regex]::Match($textOutput, "(?m)^Session:\s*(\S+)")
if ($sessionLineMatch.Success) {
    $sessionId = $sessionLineMatch.Groups[1].Value
} else {
    $sessionMatch = [regex]::Match($textOutput, "hermes --resume (\S+)")
    if ($sessionMatch.Success) {
        $sessionId = $sessionMatch.Groups[1].Value
    }
}

if ([string]::IsNullOrWhiteSpace($sessionId) -and -not [string]::IsNullOrWhiteSpace($Resume)) {
    $sessionId = $Resume
}

$response = if ($Raw) { $textOutput } else { Get-ResponseBlock -Output $textOutput }

Write-Output "MODEL=$Model"
if (-not [string]::IsNullOrWhiteSpace($Provider)) {
    Write-Output "PROVIDER=$Provider"
}
if (-not [string]::IsNullOrWhiteSpace($sessionId)) {
    Write-Output "SESSION_ID=$sessionId"
}
Write-Output "RESPONSE_BEGIN"
Write-Output $response
