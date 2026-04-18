$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$OutDir    = Join-Path $RootDir "docs_external"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Write-Host "Place document download logic here or extend with vendor URLs as needed."
