#requires -Version 5.1
param(
    [string]$Python = 'python',
    [string]$OutputDir = "$env:USERPROFILE\Documents\CAD_AGENT_OUTPUT",
    [switch]$EnableAutomaticNewDWG,
    [switch]$InstallHarnessPlugins,
    [string]$DwtDir = "$env:USERPROFILE\Documents\CAD_DWT_Templates"
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedPython = (Get-Command $Python -ErrorAction Stop).Source
Write-Host "Installing AutoCAD Engineering Agent at $root" -ForegroundColor Cyan
& $resolvedPython -m pip install -r (Join-Path $root 'requirements-windows.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
& $resolvedPython -m pip install -r (Join-Path $root 'requirements-test.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip test requirements install failed' }
Push-Location $root
try {
  & $resolvedPython -m pytest tests -q
  if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
} finally { Pop-Location }
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $DwtDir | Out-Null
function QuoteYaml([string]$v) { return "'" + ($v.Replace("'", "''").Replace('\','/')) + "'" }
$pyQuoted = QuoteYaml $resolvedPython
$rootQuoted = QuoteYaml $root
$outQuoted = QuoteYaml $OutputDir
$dwtQuoted = QuoteYaml (Resolve-Path $DwtDir).Path
$rulesQuoted = QuoteYaml (Join-Path $root 'standards/verified_rules')
$skillsQuoted = QuoteYaml (Join-Path $root 'skills')
$disciplinesQuoted = QuoteYaml (Join-Path $root 'skills/disciplines')
$autoApprovalRow = if ($EnableAutomaticNewDWG.IsPresent) { "      CAD_APPROVAL_MODE: 'auto_new'" } else { "      CAD_APPROVAL_MODE: 'manual'" }
$yml = @"
- id: mcp-autocad-engineering
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: cad_engineering
    transport: stdio
    command: $pyQuoted
    args: ['-m', 'autocad_agent.mcp_server']
    cwd: $rootQuoted
    env:
      CAD_OUTPUT_DIR: $outQuoted
      CAD_DWT_DIR: $dwtQuoted
      CAD_RULES_DIR: $rulesQuoted
$autoApprovalRow
    toolCallTimeoutMs: 180000
    failOnStartupError: true
- id: autocad-skill-filesystem
  name: '@deepseek-ai/dsh-skill-filesystem'
  config:
    providerName: autocad-engineering-local
    customSkillDirs: [$skillsQuoted, $disciplinesQuoted]
"@
$overlay = Join-Path $PSScriptRoot 'dsh-autocad.generated.yml'
[System.IO.File]::WriteAllText($overlay,$yml,(New-Object System.Text.UTF8Encoding($false)))
Write-Host "Generated: $overlay" -ForegroundColor Green
if ($InstallHarnessPlugins.IsPresent) {
  Write-Host 'Installing DeepSeek Harness MCP and skill filesystem plugin packages into Web profile...' -ForegroundColor Yellow
  & npx @deepseek-ai/dsh plugin --profile web add @deepseek-ai/dsh-mcp-client @deepseek-ai/dsh-skill @deepseek-ai/dsh-skill-filesystem @deepseek-ai/dsh-tool-skill
  if ($LASTEXITCODE -ne 0) { throw 'DSH plugin package installation failed; check npm/pnpm and DSH version' }
}
Write-Host 'Check skill discovery structure: python tools/check_skills.py' -ForegroundColor Yellow
Write-Host 'Check DSH composed config: powershell -File .\install\verify-dsh.ps1' -ForegroundColor Yellow
Write-Host "To start DSH: npx @deepseek-ai/dsh --profile web --patch `"$overlay`"" -ForegroundColor Yellow
Write-Host 'Open AutoCAD 2025 before drawing; model must call cad_template/cad_validate/cad_preview/cad_prepare.'

if ($EnableAutomaticNewDWG.IsPresent) { Write-Warning 'Auto-new-DWG mode ENABLED: the AI may create NEW CONCEPT drawings without CLI approval. It cannot overwrite existing DWGs.' }
