#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$ConfigPath = (Join-Path $env:USERPROFILE ".sap-windowsgui-logon\config.json"),

    [Parameter()]
    [ValidateRange(5, 600)]
    [int]$TimeoutSeconds = 60,

    [Parameter()]
    [string]$SapLogonPath,

    [Parameter()]
    [string]$SapShcutPath,

    [Parameter()]
    [switch]$DisableSapshcutFallback,

    [Parameter()]
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pythonCommand = Get-Command "python" -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    Write-Error "Python was not found. Install Python 3.11 or later and scripts\requirements.txt."
    exit 1
}

$pythonScript = Join-Path $PSScriptRoot "logon.py"
if (-not (Test-Path -LiteralPath $pythonScript -PathType Leaf)) {
    Write-Error "SAP logon backend not found: $pythonScript"
    exit 1
}

$pythonArguments = @(
    $pythonScript,
    "--config", $ConfigPath,
    "--timeout", [string]$TimeoutSeconds
)
if (-not [string]::IsNullOrWhiteSpace($SapLogonPath)) {
    $pythonArguments += @("--sap-logon-path", $SapLogonPath)
}
if (-not [string]::IsNullOrWhiteSpace($SapShcutPath)) {
    $pythonArguments += @("--sap-shcut-path", $SapShcutPath)
}
if ($DisableSapshcutFallback) {
    $pythonArguments += "--disable-sapshcut-fallback"
}
if ($ValidateOnly) {
    $pythonArguments += "--validate-only"
}

& $pythonCommand.Source @pythonArguments
exit $LASTEXITCODE
