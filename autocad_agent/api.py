"""Pure callable layer behind MCP tools. Works offline except create_dwg/probe."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from .schema import validate_job,DISCIPLINES
from .qa import geometry_report,check_project_rules
from .templates import create_template
from .render import export_dxf,export_pdf_preview
from .runtime import workspace,prepare,consume,read_pending,atomic_json,DIGEST_RE,issue_worker_permit

ROOT=Path(__file__).resolve().parents[1]

def capabilities():
    return {'plugin':'DSH AutoCAD Engineering Agent','version':'1.4.0-local',
            'target':'Autodesk AutoCAD 2025 English on Windows',
            'tools':['cad_capabilities','cad_template','cad_validate','cad_preview','cad_prepare','cad_create_dwg','cad_audit_dxf','cad_catalog','cad_check_project_rules','cad_screen_standards','cad_probe_autocad','cad_quality_gate','cad_check_clause_rules','cad_plot_plan',
                     'cad_reference_profiles','cad_reference_profile','cad_reference_plan','cad_reference_prepare','cad_reference_export',
                     'cad_fitout_example','cad_fitout_plan','cad_fitout_preview','cad_fitout_prepare','cad_fitout_export','cad_brand_assets',
                     'cad_project_catalog','cad_project_example','cad_project_plan','cad_project_check','cad_project_change_impact',
                     'cad_project_preview','cad_project_prepare','cad_project_export','cad_project_verify_delivery'],
            'fourteen_stage_building':['1-3 storey rectangular house template with explicit survey and engineering inputs',
                                      'per-floor architectural/structural/MEP/interior/ceiling coverage',
                                      'four elevations, sections, roof and enlarged construction details',
                                      'stage dependencies, stale-review detection and change impact',
                                      'route/column/beam/slab AABB checks and drain-slope checks',
                                      'modeled quantities and scoped cost estimate from supplied prices',
                                      'SHA256 handover manifest, sheet index, quantities CSV and release blockers'],
            'new_fitout':['11-sheet parametric studio design generated without reference geometry',
                          'native dimensions, hatches, leaders, furniture blocks and editable ACAD_TABLE',
                          'multi-scale A3 viewports and native AutoCAD DWG/PDF export',
                          'temporary boyxpxt.io.vn branding; ask final branding for real projects'],
            'reference_profiles':['hashed native DWG/CTB/Xref assets','multi-layout sheet inventory and required component checks',
                                  'native hatches, leaders, tables, symbols and viewport overrides preserved',
                                  'title attribute updates by tag','per-sheet native PDF and bookmarked combined PDF',
                                  'CSV sheet index and portable DWG/resource package','read-only original references'],
            'entity_types':['line','polyline','circle','arc','text','mtext','dim_aligned','dim_rotated','dim_radial','dim_diametric','insert','hatch','leader','table'],
            'available_disciplines':sorted(DISCIPLINES),
            'outputs':['DWG via COM (Windows)','DXF (offline)','schematic PDF (offline)','optional AutoCAD layout/PDF via COM','QA JSON'],
            'drafting':['Unicode TrueType text','layer lineweights and center/hidden linetypes',
                        'paper-sized dimension text and arrows','optional project paper-space titleblock',
                        'vector DXF preview with native dimensions and transformed blocks',
                        'estimated text overlap/small-text and sheet-fit preflight'],
            'approval_mode':os.environ.get('CAD_APPROVAL_MODE','manual'),
            'unsupported':['arbitrary existing DWG editing (reference copies support title attribute updates)',
                           'automatic new fit-out design from a reference alone','dimension layout collision solver',
                           'certified plot without real AutoCAD integration testing','3D solids','clash detection 3D','verified clause-level TCVN certification'],
            'tcvn_compliance':'NOT_CHECKED'}

def template(discipline,width=120,height=80,output_name=None,units='mm'):
    return create_template(discipline,output_name,width,height,units)

def validate(job,project_rules=None):
    normalized=validate_job(job)
    geo=geometry_report(normalized)
    from .discipline_review import review
    from .gates import assess
    gate=assess(normalized,project_rules)
    from .presentation import presentation_report
    result={'status':'VALID_INPUT' if gate['status']!='BLOCKED' else 'BLOCKED_QUALITY_GATE',
            'presentation':presentation_report(normalized),
            'geometry':geo,'gate':gate,'discipline_review':review(normalized),'tcvn_compliance':'NOT_CHECKED',
            'rule_scope':'PROJECT_RULES_AND_OPTIONAL_REVIEWER_ATTESTED_CLAUSE_RULES_NOT_CERTIFIED'}
    if project_rules is not None:
        result['project_rules']=check_project_rules(normalized,project_rules)
    return result

def preview(job):
    normalized=validate_job(job)
    qa=geometry_report(normalized)
    if qa['status']!='GEOMETRY_CHECKED':return {'status':'BLOCKED_BY_GEOMETRY','qa':qa}
    from .runtime import fingerprint
    stem=Path(normalized['output_name']).stem+'_'+fingerprint(normalized)[:12]
    target=workspace()/'previews'
    dxf=export_dxf(normalized,target/(stem+'.dxf'))
    pdf=export_pdf_preview(normalized,target/(stem+'.pdf'))
    from .standards_engine import screen_standards
    from .discipline_review import review
    standards_manifest=screen_standards(normalized)
    review_result=review(normalized)
    from .presentation import presentation_report
    report={'status':'PREVIEW_CREATED','dxf':dxf,'pdf':pdf,'qa':qa,
            'presentation':presentation_report(normalized),
            'standards_manifest':standards_manifest,'discipline_review':review_result,
            'tcvn_compliance':'NOT_CHECKED',
            'warnings':['PDF is auto-fit schematic, NOT a scale-verified production plot','Any industry calculations require engineering sign-off.']}
    atomic_json(workspace()/'reports'/(stem+'.json'),report)
    atomic_json(workspace()/'reports'/(stem+'.standards.json'),standards_manifest)
    return report

def catalog(discipline='all'):
    if discipline!='all' and discipline not in DISCIPLINES:raise ValueError('unknown discipline')
    registry=json.loads((ROOT/'standards'/'registry.json').read_text(encoding='utf-8'))
    matches=[row for row in registry['standards'] if discipline=='all' or 'all' in row['discipline'] or discipline in row['discipline']]
    return {'discipline':discipline,'standards':matches,'tcvn_compliance':'NOT_CHECKED',
            'note':'Index of standards only. Must check official current validity, amendments, applicable clauses and original legally obtained text.'}

def audit_dxf(filename):
    from ezdxf import readfile
    from .schema import FILENAME_RE
    # only inspect a DXF produced by this agent under its previews directory
    import re
    if not isinstance(filename,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}\.dxf',filename,re.I) or '..' in filename:
        raise ValueError('unsafe filename')
    path=workspace()/'previews'/filename
    if not path.is_file():raise FileNotFoundError('preview DXF not found')
    doc=readfile(str(path));audit=doc.audit();msp=doc.modelspace()
    return {'file':str(path),'audit_errors':len(audit.errors),'audit_fixes':len(audit.fixes),
            'entities':len(msp),'status':'PASS_STRUCTURE' if not audit.errors else 'FAIL_STRUCTURE',
            'tcvn_compliance':'NOT_CHECKED'}

def probe_autocad():
    if sys.platform!='win32':return {'status':'NOT_AVAILABLE','reason':'AutoCAD COM requires Windows'}
    script=('import pythoncom,win32com.client,json\n'
            'pythoncom.CoInitialize()\n'
            'try:\n'
            ' app=win32com.client.GetActiveObject("AutoCAD.Application")\n'
            ' result={"status":"CONNECTED","version":str(app.Version),"name":str(app.Name)}\n'
            ' app=None\n'
            'finally:\n'
            ' pythoncom.CoUninitialize()\n'
            'print(json.dumps(result),flush=True)\n')
    try:
        p=subprocess.run([sys.executable,'-c',script],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15)
        if p.returncode:return {'status':'FAIL','error':p.stderr[-600:]}
        return json.loads(p.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return {'status':'TIMEOUT','note':'COM call stuck; AutoCAD process was NOT terminated.'}
    except Exception as exc:return {'status':'FAIL','error':str(exc)}

def create_dwg(ticket,timeout=120):
    if sys.platform!='win32':return {'status':'NOT_EXECUTED','error':'Windows AutoCAD 2025 required'}
    if not isinstance(ticket,str) or not DIGEST_RE.fullmatch(ticket):raise ValueError('invalid ticket')
    home=workspace()
    if (home/'HALTED_AFTER_TIMEOUT').exists():
        return {'status':'MANUAL_INSPECTION_REQUIRED','note':'Previous COM worker timed out; inspect AutoCAD and remove HALTED_AFTER_TIMEOUT manually only after confirming safe state.'}
    lock=home/'cad_worker.lock'
    try:
        with lock.open('x') as f:f.write(str(os.getpid()))
    except FileExistsError:return {'status':'BUSY','note':'Another CAD operation is in progress or lock needs manual inspection.'}
    try:
        job=consume(ticket)
        permit=issue_worker_permit(ticket,job)
        try:
            p=subprocess.run([sys.executable,'-m','autocad_agent.worker',permit],cwd=ROOT,stdin=subprocess.DEVNULL,timeout=timeout,capture_output=True,text=True)
        except subprocess.TimeoutExpired:
            (home/'HALTED_AFTER_TIMEOUT').write_text('Inspect AutoCAD document and working directory before retrying.\n',encoding='utf-8')
            return {'status':'TIMEOUT_NEEDS_INSPECTION','tcvn_compliance':'NOT_CHECKED',
                    'warning':'Worker timed out, AutoCAD NOT killed. A partially modified new drawing may remain open.'}
        try:response=json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError,IndexError):response={'status':'FAIL','error':'worker output not valid JSON','stderr':p.stderr[-800:]}
        atomic_json(home/'reports'/(ticket+'.execution.json'),response)
        return response
    finally:lock.unlink(missing_ok=True)


def screen_standards(job):
    from .standards_engine import screen_standards as screen
    return screen(job)


def quality_gate(job,project_rules=None):
    from .gates import assess
    return assess(job,project_rules)

def check_clause_rules(job,rule_pack_name):
    from .clause_rules import load_rule_pack,evaluate
    return evaluate(job,load_rule_pack(rule_pack_name))

def plot_plan(job):
    from .plotting import viewport_plan
    j=validate_job(job)
    if not j['plot']['enabled']:
        return {'status':'NOT_REQUESTED','note':'Set plot.enabled=true in job to request project layout; COM printing must be verified on AutoCAD.'}
    return {'status':'MATHEMATICAL_FIT_CHECKED_NOT_PLOTTED','plan':viewport_plan(j),'tcvn_compliance':'NOT_CHECKED'}
