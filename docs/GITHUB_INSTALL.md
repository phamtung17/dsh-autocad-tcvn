# Install from Git repository in DeepSeek Harness Web

This repository **is a real DSH bundle as of v1.1.2**. Its root `package.json` declares
`dsh.bundle.patch: ./cordis.patch.yml`; the bundle patch inserts a Cordis path service,
the official DSH MCP client, and the DSH skill-filesystem provider.

## Install

1. Install **Python 3.10+** on Windows, enable PATH. Install Autodesk AutoCAD 2025 English (full desktop edition).
2. In DeepSeek Harness Web, open **Install Plugin → Git repository** and enter:
   `https://github.com/phamtung17/dsh-autocad-TCVN`.
3. **The v1.1.2 files must first be committed to that GitHub repo's main branch.**
   The old Git commit without `package.json:dsh.bundle` will still fail.
4. After installing, restart DeepSeek Harness Web. The package contains ready-to-run
   JavaScript, so there is no TypeScript build/`prepare` script and no pnpm build allowlist required.
5. On first start the Node launcher creates an isolated Python venv under
   `%LOCALAPPDATA%\DSH-AutoCAD-TCVN\python-venv` and installs the dependencies in
   `requirements-windows.txt` from PyPI. **An internet connection is needed for this first setup.**
   Python install logs go to stderr, never the MCP protocol stdout.
6. Start AutoCAD 2025. Ask DSH to call `mcp__cad_engineering__cad_capabilities`
   and `mcp__cad_engineering__cad_probe_autocad`.

## Verify in PowerShell

```powershell
npx @deepseek-ai/dsh --profile web --dump-config
```

Look for `autocad-tcvn-bundle-paths`, `autocad-tcvn-mcp`, and
`autocad-tcvn-skill-filesystem` in the composed config.

If Python setup takes too long or MCP tools do not appear, find the installed package
folder under `%USERPROFILE%\.dsh\profiles\web\node_modules\@phamtung17\dsh-autocad-tcvn`
and run:

```powershell
cd "$env:USERPROFILE\.dsh\profiles\web\node_modules\@phamtung17\dsh-autocad-tcvn"
node .\scripts\launch-mcp.cjs --check
```

Then restart DSH. If the user's DSH_HOME is custom, use that profile path instead.
The `--check` command does not open or modify DWG files.

## Safe defaults and limitations

- `CAD_APPROVAL_MODE=manual`: the agent cannot create a new DWG without out-of-band human approval.
- The package does **not** edit existing DWG files or certify TCVN compliance.
- The COM AutoCAD 2025 integration still requires a real Windows smoke test.
- Skills are discovered from two roots: `skills/` and `skills/disciplines/` (10 total).
- The PDF preview is schematic; use AutoCAD plotting and a visual check for production prints.

## Troubleshooting

| Symptom | Cause / next action |
| --- | --- |
| `This package declares no bundle` | GitHub main still contains the old version; push `package.json` and `cordis.patch.yml` to repo root, then reinstall |
| `Python >= 3.10 not found` | Install Python or set `CAD_PYTHON` in the DSH MCP row's env |
| `pip install failed` | Verify Python, network/PyPI access; run `node scripts/launch-mcp.cjs --check` and read stderr |
| No `mcp__cad_engineering__...` tools | Restart DSH, check `--dump-config`, then inspect MCP startup stderr |
| `cad_probe_autocad` cannot connect | Open AutoCAD 2025 in the same logged-in Windows desktop session |
| Skills absent | Confirm `autocad-tcvn-skill-filesystem` loaded and base Web profile provides `ctx.skills` |

## Updating GitHub

This zip does **not** modify the GitHub repository automatically. In a local Git
checkout of `phamtung17/dsh-autocad-TCVN`, copy the v1.1.2 overlay files into
its root, then:

```powershell
git add package.json index.js cordis.patch.yml scripts tests_node docs README.md VERSION.txt RELEASE_NOTES.md .github/workflows/ci.yml
git commit -m "fix: ship DSH installable AutoCAD TCVN bundle v1.1.2"
git push origin main
```

Only do this after reviewing the changes. Do not overwrite uncommitted local work.

Official DSH packaging reference:
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md
