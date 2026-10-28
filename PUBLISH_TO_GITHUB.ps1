#requires -Version 5.1
param(
  [string]$RepoPath = "$env:USERPROFILE\Documents\dsh-autocad-TCVN-git",
  [switch]$Push
)
$ErrorActionPreference = 'Stop'
$repoUrl = 'https://github.com/phamtung17/dsh-autocad-TCVN.git'
$files = @(
  'package.json', 'index.js', 'cordis.patch.yml',
  'scripts/launch-core.cjs', 'scripts/launch-mcp.cjs', 'scripts/verify-bundle.cjs',
  'tests_node/bundle.test.cjs', 'docs/GITHUB_INSTALL.md',
  'README.md', 'VERSION.txt', 'RELEASE_NOTES.md', '.github/workflows/ci.yml'
)
if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git not found; install Git for Windows first.' }
if (!(Test-Path $RepoPath)) {
  Write-Host "Cloning $repoUrl to $RepoPath"
  & git clone $repoUrl $RepoPath
  if ($LASTEXITCODE -ne 0) { throw 'git clone failed' }
}
if (!(Test-Path (Join-Path $RepoPath '.git'))) { throw "Not a Git checkout: $RepoPath" }
Push-Location $RepoPath
try {
  $remote = (& git remote get-url origin).Trim()
  if ($LASTEXITCODE -ne 0 -or $remote -notmatch 'phamtung17/dsh-autocad-TCVN(\.git)?$') { throw "Unexpected origin remote: $remote" }
  $dirty = & git status --porcelain
  if ($dirty) { throw 'Repository has uncommitted changes. Commit/stash them before applying the overlay.' }
  foreach ($relative in $files) {
    $src = Join-Path $PSScriptRoot $relative
    if (!(Test-Path $src)) { throw "Missing overlay file: $relative" }
    $dest = Join-Path $RepoPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
    Copy-Item -LiteralPath $src -Destination $dest -Force
  }
  & git add -- $files
  if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
  $changes = & git diff --cached --name-only
  if (!$changes) { Write-Host 'No changes; the GitHub checkout may already contain this fix.'; return }
  Write-Host 'Staged files:' -ForegroundColor Cyan
  $changes | ForEach-Object { Write-Host " - $_" }
  & git commit -m 'fix: make AutoCAD TCVN installable as a DSH Git bundle (v1.1.2)'
  if ($LASTEXITCODE -ne 0) { throw 'git commit failed; configure Git user.name/user.email and retry.' }
  if ($Push) {
    & git push origin HEAD:main
    if ($LASTEXITCODE -ne 0) { throw 'git push failed; verify GitHub authentication and branch permissions.' }
    Write-Host 'Published to GitHub main. Restart DSH and retry Install Plugin.' -ForegroundColor Green
  } else {
    Write-Host "Local commit created at $RepoPath. Review and run: git push origin HEAD:main" -ForegroundColor Yellow
  }
} finally { Pop-Location }
