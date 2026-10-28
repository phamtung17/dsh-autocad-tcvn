# v1.1.0 release notes — 2026-10-28

Source basis: `phamtung17/dsh-autocad-TCVN` v1.0.0 plus locally preserved source package. The GitHub repository has **read-only** permission in this session; nothing was pushed or altered remotely.

## P0
- Block normalization: base point, entity implicit layer 0, duplicate internal IDs.
- Approval-consuming API issues a short-lived, signed one-use COM worker permit. Worker no longer reads pending tickets directly.
- Quality Gate blocks incomplete geometry checks, unsafe review states, unknown/mismatched standard references for review drawings and failing declared local rules.
- Approval opt-in `auto_new` narrowed to concept-only.

## DSH skill integration
- MCP plugin now exposes 14 tools.
- Installer overlay includes a filesystem provider with two search roots to discover 10 skills, with a helper that verifies frontmatter and expected layout.
- `install/verify-dsh.ps1` checks composed profile; real Web startup must occur on Windows.

## Real AutoCAD regression
- New `tools/autocad_2025_regression.py` and opt-in pytest test create fresh DWG via AutoCAD 2025 COM, reopen, verify actual geometry/dimensions/block and optionally PDF.
- Not executed in this Linux authoring environment.

## Plot / DWT
- `plot.enabled`, `plot.pdf`, `plot.dwt`, `plot.ctb`; project-owned DWT basename under allowlisted directory.
- Paper-space layout, locked viewport, physical unit-aware custom scale, hardware media detection and real AutoCAD PDF with physical page-size checks.
- Only mocked offline. Real AutoCAD validation/independent visual QA required; no STB support claim.

## TCVN/QCVN
- `clause_rules.py`: rulepack ID, edition, clause, source SHA256, reviewer, comparison, measured value and PASS/FAIL/NOT_CHECKED.
- Example rulepack is intentionally not attested and returns NOT_CHECKED; **no authenticated national code rules bundled**.
- A local reviewer assertion is not independent verification of a legal source or valid engineering practice.

## Test/CI
- Offline pytest, COM plot mock, Windows/Linux matrix CI, MCP SDK stdio handshake test, test-report generator with `GITHUB_SHA` during CI.
- Repository workflow has not executed until files are pushed to GitHub.

## Limitations
No existing-DWG editing, complete MEP/structural/architectural calculations, dynamic blocks, 3D, automated dimension collision avoidance, real-world AutoCAD acceptance yet or certified TCVN compliance. Review engineering outputs with qualified professionals.

## v1.1.2 — Git Install Bundle Fix

- Added npm `package.json` with `dsh.bundle.patch` for **Install Plugin → Git repository**.
- Added `cordis.patch.yml` in official DSH bundle patch-list format (`- insert:`).
- Added a Cordis service to resolve package-local Python, rules and skill paths in pnpm Git installs.
- Mounted MCP client and the 10-skill filesystem provider automatically.
- Added a Node stdio launcher that provisions isolated Python dependencies on first run (stderr-only diagnostics).
- Added static Node bundle tests, npm package verification and Git install documentation.
- Retained manual DWG approval and all existing Python CAD/TCVN limitations.
- No claim of Windows AutoCAD COM or live DSH end-to-end verification from Linux CI.
