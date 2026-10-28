"""DeepSeek Harness MCP stdio plugin; no listening sockets.
Ensure stdout remains reserved for MCP protocol, not print logging.
"""
from __future__ import annotations
# Load native extensions before entering the Windows asyncio loop. Importing
# NumPy/ezdxf for the first time inside a stdio request can stall DLL startup.
import ezdxf
import pymupdf
from mcp.server.fastmcp import FastMCP
from . import api
from .runtime import prepare

mcp=FastMCP('autocad_engineering',instructions=(
    'For a complete building dossier use cad_project_catalog/example/plan/check/preview/change_impact/prepare/export/verify_delivery. '
    'All 14 stages and every modeled floor must be present. Never equate sheet completeness or clash checks with engineering approval. '
    'For NEW detailed studio drawings use cad_fitout_example, cad_fitout_plan, cad_fitout_preview, cad_fitout_prepare, cad_fitout_export. '
    'Use user-supplied project dimensions. Default boyxpxt.io.vn is temporary; ask title block and logo before real project export. '
    'For conceptual geometry jobs ALWAYS call cad_validate and cad_preview first. '
    'For native reference packages call cad_reference_profile and cad_reference_plan, then cad_reference_prepare and cad_reference_export. '
    'Reference reissue preserves source design; never describe it as a newly engineered project. '
    'Never claim TCVN approval. The human must approve a prepared ticket by running the CLI. '
    'cad_create_dwg requires this out-of-band approval unless CAD_APPROVAL_MODE=auto_new was explicitly configured by the user. '
    'DWG uses local Windows AutoCAD 2025; DXF/PDF previews are offline. '
    'NEVER describe PDF preview as scale-accurate official layout. '
    'For real AutoCAD plotting set plot.enabled=true, plot.pdf=true in the approved geometry job; this requires AutoCAD 2025 and installed DWG To PDF.pc3. '
    'Reference export also requires a CLI-approved ticket unless CAD_APPROVAL_MODE=auto_new is explicitly configured. '
    'Full native reference publication can take several minutes. Missing resources and incomplete sheet sets must not be silently ignored.'
))

@mcp.tool()
def cad_capabilities() -> dict:
    """List actually implemented capabilities and limits."""
    return api.capabilities()

@mcp.tool()
def cad_template(discipline:str,width:float=120,height:float=80,output_name:str|None=None,units:str='mm') -> dict:
    """Generate editable conceptual drawing JSON for mechanical, architectural, structural, electrical, HVAC, plumbing, civil or fire safety."""
    return api.template(discipline,width,height,output_name,units)

@mcp.tool()
def cad_validate(job:dict, project_rules:dict|None=None) -> dict:
    """Strictly validate geometry, units and project rules. No CAD write and NO TCVN certification."""
    return api.validate(job,project_rules)

@mcp.tool()
def cad_preview(job:dict) -> dict:
    """Generate a real DXF and a schematic, NOT-TO-SCALE PDF for review, plus QA report. AutoCAD not needed."""
    return api.preview(job)

@mcp.tool()
def cad_prepare(job:dict) -> dict:
    """Freeze a job for user approval. Returns a ticket and a command human must run in local PowerShell."""
    return prepare(job)

@mcp.tool()
def cad_create_dwg(ticket:str) -> dict:
    """Create a NEW DWG with AutoCAD 2025, ONLY when a human has approved ticket via CLI. Never overwrite."""
    return api.create_dwg(ticket)

@mcp.tool()
def cad_audit_dxf(filename:str) -> dict:
    """Structural audit of an agent-generated preview DXF; pass filename only, not arbitrary path."""
    return api.audit_dxf(filename)

@mcp.tool()
def cad_catalog(discipline:str='all') -> dict:
    """Look up candidate TCVN/QCVN catalog entries by discipline. Catalog is not legal compliance evidence."""
    return api.catalog(discipline)

@mcp.tool()
def cad_check_project_rules(job:dict,project_rules:dict) -> dict:
    """Run measurable PROJECT rules with PASS/FAIL. These are NOT verified TCVN rules."""
    return api.validate(job,project_rules)

@mcp.tool()
def cad_screen_standards(job:dict) -> dict:
    """Check that requested TCVN/QCVN references exist in catalog and are potentially applicable; does NOT verify clauses."""
    return api.screen_standards(job)

@mcp.tool()
def cad_probe_autocad() -> dict:
    """Check AutoCAD COM connectivity, including version. Diagnostic only; doesn't edit drawing."""
    return api.probe_autocad()



@mcp.tool()
def cad_quality_gate(job:dict,project_rules:dict|None=None)->dict:
    """Show blocking issues before preparing an AutoCAD job; never equate release with TCVN compliance."""
    return api.quality_gate(job,project_rules)

@mcp.tool()
def cad_check_clause_rules(job:dict,rule_pack_name:str)->dict:
    """Evaluate a locally installed, reviewer-attested TCVN clause rule pack; NOT a standards certificate."""
    return api.check_clause_rules(job,rule_pack_name)

@mcp.tool()
def cad_plot_plan(job:dict)->dict:
    """Mathematically verify requested paper-space drawing fits sheet at specified scale; no AutoCAD needed."""
    return api.plot_plan(job)


@mcp.tool()
def cad_reference_profiles()->dict:
    """List locally installed native drawing profiles and sheet/component counts."""
    from .reference_profiles import list_profiles
    return list_profiles()


@mcp.tool()
def cad_reference_profile(profile_id:str,sheet_ids:list[str]|None=None,include_viewport_details:bool=False)->dict:
    """Inspect a hashed profile: native layouts, viewports, title attributes, Xrefs, fonts and CTBs."""
    from .reference_profiles import profile_info
    return profile_info(profile_id,sheet_ids,include_viewport_details)


@mcp.tool()
def cad_reference_plan(job:dict)->dict:
    """Preflight a native reference package. Completeness required by default; missing fonts block unless explicitly accepted."""
    from .reference_profiles import reference_plan
    plan=reference_plan(job)
    plan['sheets']=[{'id':s['id'],'drawing':s['drawing'],'layout':s['layout'],'role':s['role'],
                     'viewport_count':len(s['viewports'])} for s in plan['sheets']]
    return plan


@mcp.tool()
def cad_reference_prepare(job:dict)->dict:
    """Freeze selected sheets, metadata and profile hash for one-time human approval."""
    from .reference_runtime import prepare_reference
    return prepare_reference(job)


@mcp.tool()
def cad_reference_export(ticket:str)->dict:
    """Publish a NEW native reference package from an approved ticket. No source editing; reference geometry remains."""
    from .reference_runtime import export_reference
    return export_reference(ticket)

@mcp.tool()
def cad_fitout_example()->dict:
    """Explicit demo inputs for NEW studio drawings; do not reuse demo inputs for a real project."""
    from .fitout_design import demo_spec
    return {'spec':demo_spec(),'temporary_brand':'boyxpxt.io.vn'}

@mcp.tool()
def cad_fitout_plan(spec:dict,branding:dict|None=None)->dict:
    """Validate a NEW parametric studio set: 11 sheets, dimensions, details, schedules. No reference geometry copied."""
    from .design_api import plan
    return plan(spec,branding)

@mcp.tool()
def cad_fitout_preview(spec:dict,branding:dict|None=None)->dict:
    """Create 11-sheet vector PDF/DXF preview of a NEW studio. Review before native export."""
    from .design_api import preview
    return preview(spec,branding)

@mcp.tool()
def cad_fitout_prepare(spec:dict,branding:dict|None=None)->dict:
    """Freeze NEW design and logo hashes for one-use human approval. Ask real-project branding before confirmed=true."""
    from .design_runtime import prepare_design
    return prepare_design(spec,branding)

@mcp.tool()
def cad_fitout_export(ticket:str)->dict:
    """Native NEW DWG/PDF set with real dimensions/hatches/tables, after CLI approval."""
    from .design_runtime import export_design
    return export_design(ticket)

@mcp.tool()
def cad_brand_assets()->dict:
    """List locally registered logo/frame assets. Default temporary wordmark is boyxpxt.io.vn."""
    from .branding import list_assets
    return list_assets()

@mcp.tool()
def cad_project_catalog()->dict:
    """14-stage drawing roles, dependencies and explicit capability limits."""
    from .project_api import catalog
    return catalog()

@mcp.tool()
def cad_project_example()->dict:
    """Explicit two-storey DEMO data for the 14-stage building generator. Not surveyed/engineered project data."""
    from .building_model import example
    return {'spec':example(),'purpose':'DEMO / all engineering values illustrative','temporary_brand':'boyxpxt.io.vn'}

@mcp.tool()
def cad_project_plan(spec:dict)->dict:
    """Build all 14-stage drawing jobs with per-floor coverage, takeoff and QA; no reference geometry copied."""
    from .project_api import plan
    return plan(spec)

@mcp.tool()
def cad_project_check(spec:dict)->dict:
    """Check missing sheets/details/floors, stale reviews, broken references, route/structure AABB clashes and open issues."""
    from .project_api import check
    return check(spec)

@mcp.tool()
def cad_project_change_impact(before:dict,after:dict)->dict:
    """Identify directly changed stages and downstream sheets/reviews to rebuild before release."""
    from .project_workflow import change_impact
    return change_impact(before,after)

@mcp.tool()
def cad_project_preview(spec:dict,branding:dict|None=None)->dict:
    """Create multi-discipline 14-stage vector PDF/DXF review package; not native AutoCAD verification."""
    from .project_api import preview
    return preview(spec,branding)

@mcp.tool()
def cad_project_prepare(spec:dict,branding:dict|None=None)->dict:
    """Freeze model, implementation and branding hashes; blocks modeled errors and asks real-project branding."""
    from .project_api import prepare
    return prepare(spec,branding)

@mcp.tool()
def cad_project_export(ticket:str)->dict:
    """Export a new native multi-discipline DWG/PDF review set from an externally approved one-use ticket."""
    from .design_runtime import export_design
    return export_design(ticket)

@mcp.tool()
def cad_project_verify_delivery(project_id:str)->dict:
    """Verify native delivery files against a local SHA256 manifest; missing or altered files block handover."""
    from .project_delivery import verify_delivery
    return verify_delivery(project_id)

if __name__=='__main__':mcp.run(transport='stdio')
