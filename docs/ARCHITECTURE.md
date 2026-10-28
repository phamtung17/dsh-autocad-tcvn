# DSH AutoCAD Engineering Agent — technical architecture

`DeepSeek Harness` → `@deepseek-ai/dsh-mcp-client (stdio)` → `autocad_agent.mcp_server` → Python API. The MCP plugin is spawned as a **local process**. It opens **no TCP port** and accepts no shell commands from the LLM. One MCP client config row can be added using DSH's `--patch` option without replacing the user's existing model configuration.

Two main paths:

- Offline: `cad_template`/`cad_validate`/`cad_screen_standards` → `ezdxf` DXF + `reportlab` preview PDF + `pypdf` page-size check; output in per-user `CAD_OUTPUT_DIR`.
- AutoCAD: `cad_prepare` validates and fingerprints a job → optional **manual human approval** → `cad_create_dwg` subprocess → COM on AutoCAD 2025 (`win32com.client.GetActiveObject`) → staging DWG → exclusive copy to destination → execution report.

`CAD_APPROVAL_MODE=manual` (default) requires human CLI approval, expires after 15 minutes. `CAD_APPROVAL_MODE=auto_new` is an explicit user-managed configuration opt-in for automated creation of *new* DWGs; jobs still cannot overwrite an existing file, and geometry failures still block.

## Defense in depth

- Strict JSON structure, unit and coordinate limits; whitelist entity types.
- Only basename `.dwg` filenames, output directory controlled by environment; no file-path parameters from model.
- No `SendCommand`, no arbitrary AutoLISP or shell tools, no `Quit`, `taskkill`, purge, or direct modification to existing user documents.
- Separate COM worker with timeout; on timeout it emits `HALTED_AFTER_TIMEOUT`, requiring manual inspection before re-execution. **COM timeout does not guarantee AutoCAD doc rollback.**
- No sharing COM proxies across threads. Only a single CAD worker can run per output directory; lockfile needs manual verification after a crash.
- COM 25.x version check, save under a working path, final output exclusive copy with `'xb'`; not a substitute for opening the actual DWG.
- DXF+PDF + geometry+discipline completeness+project rules are evidence, NOT signed engineer approval.

## Honest limits

The plugin is not AutoCAD Civil 3D, Revit, Revit MEP, Inventor, advanced 3D CAD or a BIM checker. It has starter 2D schemas per discipline, cannot generate complete shop/construction documentation from an unspecified prompt, and does not contain licensed TCVN clauses. The 8 templates are non-authoritative illustrations.

The current PDF uses viewport auto-fitting purely for review; it **does not honor sheet scale_denominator** as a professional CAD plot. Future production implementation should build layouts/DWT, configure `AcPlot` via AutoCAD 2025 API and inspect plotted PDF page geometry.

The offline tests mock COM rather than running an installed Autodesk process. To validate real AutoCAD integration, use `python tools/smoke_autocad_2025.py` on Windows with AutoCAD 2025 open and inspect the resulting DWG.
