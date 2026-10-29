# Local upgrade 1.7.0-local — live AutoCAD drawing

New project/fitout export now creates native Model entities in visible batches from an empty target Model, with Regen, AutoCAD command-line progress and cad_project_progress heartbeat/status. One DWG; no PDF by default. See [Live drawing guide](docs/LIVE_DRAWING_V17_VI.md).

# Local upgrade 1.6.0-local — spatial drawing rules

Hosted wall openings, synchronized wall/hatch cuts, door swing clearance, full object footprints, room usage/access and bounded label placement now gate project preparation. One DWG with layouts; PDF only by explicit request. See [Vietnamese rules](docs/SPATIAL_RULES_V16_VI.md). Legacy drawings require a separate audit; passing file integrity does not establish design correctness.

# Local upgrade 1.2.0-local — native reference drawing sets

See [Native reference profiles and fit-out publication](docs/REFERENCE_PROFILES_VI.md).
Adds five MCP tools for profile discovery, measured native layouts/resources,
completeness preflight, signed approvals and multi-sheet native publication.
The local STU4 profile has 35 sheets and preserves native DWG components.
Private reference assets are local-only and excluded from source releases.

## Previous local upgrade 1.1.3-local — Windows AutoCAD 2025 tested

See [Vietnamese installation, test evidence and usage](docs/LOCAL_UPGRADE_VI.md).
This checkout adds Codex MCP registration, corrected MCP dependencies and skill
discovery, real AutoCAD COM/plot fixes, native dimensions, Unicode vector previews,
project title blocks, and conservative presentation preflight. Original upstream
release information below is historical; current evidence is under `output/`.

# DSH AutoCAD 2025 TCVN — Git-installable DSH bundle v1.1.2

**DeepSeek Harness Web → Install Plugin → Git repository:**
`https://github.com/phamtung17/dsh-autocad-TCVN`

This works **after** the v1.1.2 files have been committed to the GitHub repo.
The root `package.json` declares `dsh.bundle`; the Cordis bundle automatically
registers the MCP server and all 10 skill roots. Install Python 3.10+ and open
AutoCAD 2025 on Windows. First startup may download Python dependencies.

**[Full Git installation, verification and troubleshooting guide](docs/GITHUB_INSTALL.md).**

---

# DSH AutoCAD 2025 Engineering Agent v1.1.0

**DeepSeek Harness MCP stdio plugin + 10 skills + AutoCAD 2025 English COM backend + project QA + configurable, traceable TCVN/QCVN clause checks.** This updates `phamtung17/dsh-autocad-TCVN` v1.0.0 and preserves its conceptual 2D examples.

> **Production status: WINDOWS INTEGRATION REQUIRED.** 92 offline tests passed in the development environment when prepared (exact current result in `TEST_REPORT.json`). The actual AutoCAD 2025 COM, DSH Web MCP startup, and real plotter are **not** verified here. No TCVN standard clauses have been independently authenticated. No built-in "TCVN PASS" certificate exists.

## 1. What changed in v1.1

- Fixed P0 block normalization, including implicit layer `0`, base point and duplicate internal IDs.
- Worker no longer reads unapproved pending tickets: main API consumes approval and issues a signed, one-use worker execution permit. **Same-user arbitrary code execution remains outside this boundary**; do not expose shell execution to untrusted prompts.
- Fail-closed Quality Gate blocks ambiguous geometry, unreadable referenced rule packs, failed project rules, missing engineering inputs (review drawings), unknown/mismatched standard IDs (review drawings); manufacture/construction release is explicitly not supported.
- DSH filesystem provider overlay mounts `skills/` and `skills/disciplines/` to make all **10 skills** discoverable (the skill loader must be enabled in the Web profile).
- COM integration regression script creates a unique DWG, reopens and measures entities, associative dimensions and block references. Windows+AutoCAD required to execute.
- Optional paper-space layout, locked viewport with unit-correct `CustomScale`, device media selection, plot style, real `PlotToFile` to PDF, PDF physical page-size test. **Configured and mocked here, actual print quality/scale must be measured on a real AutoCAD machine.**
- Local TCVN/QCVN clause-linked rule packs carry catalog ID, edition, source SHA256, reviewer, clause, method and machine-measurable rules. Incomplete provenance = `NOT_CHECKED`. `PASS` is for the measured constraint only, never national compliance certification.
- CI runs Python offline tests on Windows/Linux; build reports include commit SHA when run under GitHub Actions.

## 2. Install on the ONE Windows machine with DSH + AutoCAD 2025

Extract the ZIP so `C:\CAD_DSH_Agent\autocad_agent\mcp_server.py` exists. Install Python 3.11/3.12 64-bit, open AutoCAD 2025 English; in PowerShell:

```powershell
cd C:\CAD_DSH_Agent
Set-ExecutionPolicy -Scope Process Bypass
.\install\install.ps1 -InstallHarnessPlugins
```

The installer installs Python dependencies, runs offline tests and writes **only** `install\dsh-autocad.generated.yml` (does not overwrite existing DSH model settings). It can optionally install DSH skill/MCP package dependencies into `web` profile with the switch shown above; Internet connectivity and npm/pnpm may be required. If packages already exist and plugin installation fails, install manually or rerun without `-InstallHarnessPlugins`.

Confirm DSH patch composition and discovered local skill metadata:

```powershell
.\install\verify-dsh.ps1
python tools\check_skills.py
```

If the DSH profile is missing the skill registry/model tool, ensure `@deepseek-ai/dsh-skill`, `@deepseek-ai/dsh-skill-filesystem`, and `@deepseek-ai/dsh-tool-skill` are mounted in that profile. The generated patch mounts the dedicated filesystem provider; default profiles may already mount the registry/tool. Avoid duplicate instances.

Start Harness with the *generated overlay*:

```powershell
.\install\start-dsh.ps1
```

DSH launcher equivalent:

```powershell
npx @deepseek-ai/dsh --profile web --patch "C:\CAD_DSH_Agent\install\dsh-autocad.generated.yml"
```

The model running on another machine through your existing local AI endpoint **does not need** its own AutoCAD connection; DSH and AutoCAD both live on Windows.

## 3. Safe first use

Ask the Harness agent to:

> “Hãy liệt kê các skill AutoCAD, gọi `cad_capabilities` và `cad_probe_autocad`. Tạo `cad_template` cơ khí 200 x 100 mm, chạy `cad_quality_gate`, `cad_validate`, `cad_preview`, chưa lưu DWG.”

Default mode uses local human approval. Then:

1. Ask DSH to call `cad_prepare` for the reviewed JSON job. DSH returns a ticket.
2. In a **human-operated PowerShell**, with the same output directory configured by the installer, run:

```powershell
cd C:\CAD_DSH_Agent
python -m autocad_agent.cli approve YOUR_64_HEX_TICKET
```

3. Type `VE` in the local terminal. Ask DSH to call `cad_create_dwg(ticket)`. The new DWG is stored in `%USERPROFILE%\Documents\CAD_AGENT_OUTPUT` by default; no overwrite is permitted.

`-EnableAutomaticNewDWG` on the installer is opt-in and **only bypasses the local approval step for `concept_only` new drawings**. It never enables modification/overwrite of existing DWG.

## 4. A3 PDF with a real AutoCAD plotter

`cad_preview` creates an auto-fit **schematic PDF** and **is never scale-verified**. The optional real plot is different. Add to job JSON:

```json
"sheet": {"format": "A3", "orientation": "landscape", "scale_denominator": 1},
"plot": {"enabled": true, "pdf": true, "dwt": null, "ctb": null}
```

For approved DWT, copy the file into the installer's `CAD_DWT_DIR` (default `%USERPROFILE%\Documents\CAD_DWT_Templates`) and set `"dwt":"YourApprovedTemplate.dwt"`. Only the basename is allowed; no arbitrary file path. If you set `"ctb":"monochrome.ctb"`, that plot style must exist in the installed AutoCAD environment. Print device is `DWG To PDF.pc3`; a matching canonical A3 media name is required, otherwise export stops with an error. Real plotting is tested only with a local full AutoCAD session.

Before approving an actual paper-space plot, call `cad_plot_plan` to calculate drawing extents at 1:N. Oversized drawings fail rather than silently scaling-to-fit. Page-size reading via `pypdf` does **not** prove font, lineweight, viewport contents or physical print scale are correct; inspect the AutoCAD PDF independently.

## 5. Actual AutoCAD 2025 integration test (MUST do before production)

```powershell
python tools\autocad_2025_regression.py
python tools\autocad_2025_regression.py --pdf
```

These tests create uniquely named files and reopen DWG under AutoCAD via COM, checking WCS geometry, circle radius, dimensions `Measurement`, layers, closed polyline, static block insertion, and PDF existence/page count. They never overwrite or close the user's other documents. The output should remain open for review. More detail: [docs/AUTOCAD_2025_VALIDATION.md](docs/AUTOCAD_2025_VALIDATION.md).

For `pytest` opt-in on Windows:

```powershell
$env:CAD_REAL_AUTOCAD_TEST='1'
python -m pytest tests/test_integration_autocad.py -q
```

## 6. TCVN/QCVN rulepacks

- `cad_catalog`: catalog leads only, source currentness must be checked.
- `cad_screen_standards`: declared refs and likely scope only.
- `cad_check_clause_rules(job,rule_pack_name)`: run conservative local measure rules from `standards/verified_rules` or `CAD_RULES_DIR`; **no arbitrary code**.
- `cad_quality_gate`: blocks explicitly requested rule pack if rule result `FAIL` or `NOT_CHECKED`.

**No verified national standard values are shipped.** A licensed engineer must verify exact applicable editions, amendments, clause wording, units, methods, all limits, hashes and approval. See [docs/TCVN_RULEPACK_GUIDE.md](docs/TCVN_RULEPACK_GUIDE.md). No rule PASS implies engineering/legal approval.

## 7. Tests / release provenance

```powershell
python -m pytest -q tests
python tools\make_test_report.py --output TEST_REPORT.json
```

CI `.github/workflows/ci.yml` runs offline pytest on Windows/Linux Python 3.11/3.12, structure discovery and MCP SDK handshake and uploads a commit-linked report; does not have Autodesk AutoCAD installed. **Until workflow is pushed and runs on GitHub, CI is code only and not evidenced as successful on GitHub.**

## 8. Remaining production work

No editing old DWG, dynamic blocks/XREF, automatic dimension collision avoidance, 3D assemblies, structural/hydraulic/electrical design calculations, stamped government compliance, verified clause-level national standards, or certified plotting. Physical AutoCAD 2025 and real DSH startup must be tested on the user's Windows machine. Engineering sign-off is always separate.

Official interfaces: [DSH MCP client](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md), [DSH Skill Filesystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md), [Autodesk PlotToFile](https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-ActiveX-Reference/files/GUID-85A6B1AF-80AA-4F56-8305-6EFD4A4D8CF8.htm).


## Local v1.3: new studio generation

11 newly generated detailed sheets, native DWG/PDF and configurable title block.
See [Vietnamese workflow](docs/NEW_DESIGN_V13_VI.md). Temporary brand: boyxpxt.io.vn.


## Local v1.4: fourteen-stage building dossier

Shared model, detailed drawings per floor and discipline, revision/dependency checks, modeled route clashes, scoped estimate and hashed native handover. The two-storey demo has 58 A3 sheets. This is a bounded low-rise template, not autonomous engineering approval. See [workflow and limits](docs/PROJECT_WORKFLOW_V14_VI.md).
# Bản local 1.5.1 — một DWG cho toàn bộ hồ sơ, không tự xuất PDF

Xuất native mặc định tạo một `PROJECT.dwg`, mọi bộ môn nằm chung Model và các layout,
tự kết nối/khởi động AutoCAD và mở Model. **PDF mặc định tắt, kể cả preview**;
chỉ bật sau yêu cầu PDF rõ ràng của người dùng. DXF trung gian nằm trong cache riêng.
Có kiểm chữ ký định dạng DWG, kích thước, hình học và viewport.
Đầu vào mở rộng cho nhà 18×17 m, thiết bị theo tầng, mái hip và bố trí hồ/thang máy:
xem [hướng dẫn và trạng thái từng nhóm lỗi](docs/SINGLE_DWG_V15_VI.md).
Hồ/thang máy hiện chỉ là footprint/ô chờ; tính toán kỹ thuật vẫn cần chuyên gia.
