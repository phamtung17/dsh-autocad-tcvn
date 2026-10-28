# Real AutoCAD 2025 English validation (operator-run, Windows only)

**Preconditions**: Full AutoCAD 2025 English (not LT), Python 3.11/3.12 64-bit,
`requirements-windows.txt` installed, AutoCAD opened interactively under same
Windows account/privilege as Python; close any modal dialogs. Save other work.

## A. COM and actual DWG smoke test

From a Windows PowerShell at the project root:

```powershell
python tools\autocad_2025_regression.py
```

The test creates a **uniquely named new** DWG in `CAD_OUTPUT_DIR`, then opens that
file in AutoCAD, counts entities, checks `INSUNITS=4`, a closed outline, block
`TEST_MARK`, and reads associative dimension `Measurement` of 100/200 mm.
It leaves the output open for manual review. The original drawing is untouched.

If it fails, attach console output, AutoCAD version (`VERNUM`), and whether it
ran elevated / non-elevated. **Do not mass-retry after a COM timeout.**

## B. Actual PDF plotting and layout validation

Verify the installed `DWG To PDF.pc3` and A3 paper media in AutoCAD's Plot UI.
Optionally install a project-approved DWT in an explicit folder (do not fetch
untrusted templates). Then:

```powershell
$env:CAD_DWT_DIR = 'C:\CAD_DWT_Templates'
python tools\autocad_2025_regression.py --pdf
# or use --dwt MyApproved.dwt
```

The plugin uses `PaperSpace.AddPViewport`, fixes custom scale from model units to
paper millimeters, locks the viewport, selects the device media, plots via
`Document.Plot.PlotToFile`, and checks PDF page dimensions. The plot gate **never**
silently changes scale to fit. It fails if drawing bounds would be clipped.

**Manual checks mandatory**: visually inspect the returned PDF in Acrobat or
another independent viewer, measure known dimensions with calibrated print
scale, confirm text/font, viewport target, correct physical orientation,
CTB/STB, lineweights, clipping, title block and revision. Automatic page-size
check is **not** verification of content or physical print scale.

## C. DeepSeek Harness + Skills actual connection

1. Install with `install.ps1 -InstallHarnessPlugins` (or install packages manually).
2. Run `install\verify-dsh.ps1` to check the composed `--patch` config.
3. Start `install\start-dsh.ps1`.
4. In chat, ask for `cad_capabilities` then list the model skill catalog. Expect
   `cad-automation`, `cad-designer` plus 8 `autocad-*` skills.
5. Call `cad_quality_gate`, `cad_template`, `cad_preview` before `cad_prepare`.
6. In default approval mode, run `python -m autocad_agent.cli approve <ticket>`
   by hand in PowerShell. Then ask `cad_create_dwg` using the ticket.
7. Confirm `CAD_OUTPUT_DIR` DWG file can reopen in AutoCAD.

Neither mock COM, offline `ezdxf` tests, nor MCP stdio handshake alone prove
DeepSeek Harness -> AutoCAD 2025 works on your own installation.

## References (Autodesk official)

- ActiveX Layout: https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-ActiveX-Reference/files/GUID-EFC848F1-26BE-4EFA-BC0E-11F874D73842.htm
- PViewport: https://help.autodesk.com/cloudhelp/2024/KOR/AutoCAD-LT-ActiveX-Reference/files/GUID-63DF4686-8A79-4A39-8247-4A3565F31FAA.htm
- PlotToFile: https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-ActiveX-Reference/files/GUID-85A6B1AF-80AA-4F56-8305-6EFD4A4D8CF8.htm
- Plot object: https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-ActiveX-Reference/files/GUID-0A01876A-13D5-4938-8BEE-7712FD7C12CF.htm
