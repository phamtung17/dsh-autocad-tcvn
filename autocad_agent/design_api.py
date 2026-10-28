"""New parametric studio workflow, separate from reference reissue."""
from pathlib import Path
import hashlib,json
from .fitout_design import demo_spec
from .design_dispatch import build_project,project_quantities
from .branding import normalize_brand,load_asset
from .runtime import workspace,atomic_json

def frozen(spec,branding=None):
    project=build_project(spec);brand=normalize_brand(branding)
    assets={k:load_asset(brand[k])['sha256'] for k in ('logo_asset','frame_asset') if brand[k]}
    implementation=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
    return {'kind':'NEW_DESIGN','spec':project['spec'],'branding':brand,'assets':assets,'generator':project['generator'],
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

def preview(spec,branding=None):
    from tools.demo_new_design import generate
    value=frozen(spec,branding)
    key=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    target=workspace()/'design_previews'/key
    if not (target/'GENERATION_REPORT.json').exists():
        import contextlib,sys
        with contextlib.redirect_stdout(sys.stderr):generate(target,value['spec'],value['branding'])
    report=json.loads((target/'GENERATION_REPORT.json').read_text(encoding='utf-8'))
    return {'status':'OFFLINE_PREVIEW','reference_geometry_read':False,'design_id':key,
            'pdf':str(target/'NEW_STUDIO_PREVIEW.pdf'),'sheet_count':len(report['sheets']),
            'native_verified':False,'note':'Review preview before preparing native export.'}
