"""New parametric studio workflow, separate from reference reissue."""
from pathlib import Path
import hashlib,json
from .fitout_design import demo_spec
from .design_dispatch import build_project,project_quantities
from .branding import normalize_brand,load_asset
from .runtime import workspace,atomic_json

def frozen(spec,branding=None,export_pdf=False):
    if type(export_pdf) is not bool:raise ValueError('export_pdf must be boolean')
    project=build_project(spec);brand=normalize_brand(branding)
    assets={k:load_asset(brand[k])['sha256'] for k in ('logo_asset','frame_asset') if brand[k]}
    implementation=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
    return {'kind':'NEW_DESIGN','spec':project['spec'],'branding':brand,'assets':assets,'generator':project['generator'],
            'output_options':{'export_pdf':export_pdf,'drawing_mode':'ONE_DWG_MODEL_AND_LAYOUTS','execution':'LIVE_NATIVE_BATCHES'},
            'implementation_sha256':implementation}

def plan(spec,branding=None):
    value=frozen(spec,branding);project=build_project(value['spec'])
    return {'status':'NEW_DESIGN_PLANNED','reference_geometry_read':False,'spec':value['spec'],
            'branding':value['branding'],'quantities':project_quantities(project),'workflow':project.get('workflow'),
            'sheets':[{'code':s['code'],'title':s['title'],'views':len(s['views']),
                       'entities':len(s['job']['geometry'])} for s in project['sheets']],
            'limitations':['Detailed template library; project engineering review required.',
                            'Real export requires user-confirmed title block and logo.'],
            'tcvn_compliance':'NOT_CHECKED'}

def preview(spec,branding=None,export_pdf=False):
    from .single_drawing import compose_project
    value=frozen(spec,branding,export_pdf)
    key=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    target=workspace()/'design_previews'/key
    if not (target/'GENERATION_REPORT.json').exists():
        import contextlib,sys
        project=build_project(value['spec']);target.mkdir(parents=True,exist_ok=True)
        with contextlib.redirect_stdout(sys.stderr):compose_project(project,value['branding'],target/'PROJECT.dxf')
        report={'sheets':[{'code':s['code']} for s in project['sheets']],'pdf_exported':export_pdf}
        if export_pdf:
            from .detailed_sheets import render_sheet_pdf
            from pypdf import PdfWriter
            writer=PdfWriter();(target/'PDF').mkdir()
            for sheet in project['sheets']:
                pdf=target/'PDF'/(sheet['code']+'.pdf')
                render_sheet_pdf(target/'PROJECT.dxf',pdf,sheet['code']);writer.append(pdf)
            with (target/'PREVIEW.pdf').open('xb') as f:writer.write(f)
        atomic_json(target/'GENERATION_REPORT.json',report)
    report=json.loads((target/'GENERATION_REPORT.json').read_text(encoding='utf-8'))
    return {'status':'OFFLINE_PREVIEW','reference_geometry_read':False,'design_id':key,
            'dxf':str(target/'PROJECT.dxf'),'pdf':str(target/'PREVIEW.pdf') if export_pdf else None,'pdf_exported':export_pdf,'sheet_count':len(report['sheets']),
            'native_verified':False,'note':'Review preview before preparing native export.'}
