#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$patch = Join-Path $PSScriptRoot 'dsh-autocad.generated.yml'
if (-not (Test-Path $patch)) { throw 'Run install.ps1 first' }
Push-Location $root
try {
  & python tools/check_skills.py
  if ($LASTEXITCODE -ne 0) { throw 'Skill layout check FAILED' }
  Write-Host 'Checking DSH composed Web profile without starting the UI...' -ForegroundColor Cyan
  $config = & npx @deepseek-ai/dsh --profile web --patch $patch --dump-config | Out-String
  if ($LASTEXITCODE -ne 0) { throw 'DSH failed to compose profile; run package install and check CLI versions' }
  foreach ($needle in @('mcp-autocad-engineering', 'autocad-skill-filesystem')) {
    if (-not $config.Contains($needle)) { throw "Plugin entry missing in DSH merged configuration: $needle" }
    Write-Host "Found $needle" -ForegroundColor Green
  }
  foreach ($needle in @('@deepseek-ai/dsh-skill', '@deepseek-ai/dsh-tool-skill')) {
    if (-not $config.Contains($needle)) { Write-Warning "Verify model skill loader is installed: $needle" }
  }
  Write-Host 'Composed config OK. Next verify MCP tool listing INSIDE a running DSH session.' -ForegroundColor Green
} finally { Pop-Location }
