#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$patch = Join-Path $PSScriptRoot 'dsh-autocad.generated.yml'
if (-not (Test-Path $patch)) { throw 'Run .\install\install.ps1 first to generate the DSH overlay.' }
Write-Host "Starting DeepSeek Harness Web with AutoCAD Engineering MCP overlay: $patch" -ForegroundColor Cyan
& npx @deepseek-ai/dsh --profile web --patch $patch
