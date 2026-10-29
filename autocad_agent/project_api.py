"""User-facing fourteen-stage project tools."""
from .building_model import example,normalize,digest
from .building_design import build_building_set
from .project_workflow import STAGES,check_project,change_impact

def catalog():
    from .spatial_rules import RULES
    return {'stages':[{'id':i,'title':t,'dependencies':deps,'required_roles':roles} for i,t,deps,roles in STAGES],
            'supported_generator':'Rectangular low-rise house, 1–3 storeys, explicit engineering inputs',
            'output_mode':'SINGLE_DWG_MULTIPLE_LAYOUTS',
            'live_native_drawing':True,'progress_tool':'cad_project_progress','active_space':'Model','pdf_default':False,'separate_drawing_exports':False,
            'spatial_rules':RULES,
            'extension_schema_example':'examples/villa_18x17_explicit_demo.json',
            'example_templates':['house','villa_18x17'],
            'extension_limits':'Pool footprint/elevator reservation only; explicit fixtures/devices/partitions/openings/furniture; engineering not automated',
            'reference_presentation':['multi-scale viewports','native dimensions/hatches/leaders/symbols/tables',
                                      'detail views and cross-sheet references','per-floor discipline coverage'],
            'not_implemented':['arbitrary building synthesis','structural analysis and automatic reinforcement sizing',
                               'electrical protection coordination','hydraulic sizing','full BIM clash detection',
                               'automatic legal/TCVN certification'],
            'branding':'boyxpxt.io.vn temporary; ask user before real export'}

def plan(spec):
    project=build_building_set(spec)
    return {'project_id':project['spec']['project_id'],'input_sha256':digest(project['spec']),
            'generator':project['generator'],'workflow':project['workflow'],
            'sheets':[{k:s[k] for k in ('code','title','stage','role','floor','references','input_hash')} for s in project['sheets']],
            'takeoff':project['takeoff'],'reference_geometry_read':False}

def check(spec):return build_building_set(spec)['workflow']

def preview(spec,branding=None,export_pdf=False):
    from .design_api import preview as generate
    normalize(spec)
    return generate(spec,branding,export_pdf)

def prepare(spec,branding=None,export_pdf=False):
    from .design_runtime import prepare_design
    normalize(spec)
    return prepare_design(spec,branding,export_pdf)
