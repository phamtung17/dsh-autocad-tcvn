import json
from copy import deepcopy
import pytest,ezdxf
from autocad_agent.fitout_design import demo_spec,build_studio_set,normalize_spec,quantities,floor_zones
from autocad_agent.branding import normalize_brand,register_asset,load_asset
from autocad_agent.detailed_sheets import make_sheet_dxf
from autocad_agent.design_runtime import prepare_design,export_design,_read,approve_design
from autocad_agent.schema import JobError

def test_new_set_has_native_rich_geometry_and_no_reference_dependency(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_PROFILE_DIR',str(tmp_path/'nonexistent'))
    project=build_studio_set(demo_spec());assert len(project['sheets'])==11
    kinds={e['type'] for s in project['sheets'] for e in s['job']['geometry']}
    assert {'hatch','leader','table','insert','dim_aligned'}<=kinds
    for n,s in enumerate(project['sheets'],1):
        path=tmp_path/(s['code']+'.dxf');make_sheet_dxf(s,project['spec'],normalize_brand(),path,n,11)
        doc=ezdxf.readfile(path);assert not doc.audit().errors
        assert doc.layouts.get(s['code']).query('VIEWPORT')
        assert not any(b.block.dxf.flags&4 for b in doc.blocks)

def test_parameters_change_geometry_and_takeoff():
    s=demo_spec();a=build_studio_set(s);s['width']=4600;s['counter_thickness']=40
    s['components']['upper_cabinet_gap']=700
    b=build_studio_set(s);assert a['sheets']!=b['sheets']
    assert quantities(b['spec'])['F01']>quantities(a['spec'])['F01']
    assert 4600 in [e['end'][0] for e in b['sheets'][1]['job']['geometry'] if e['type']=='dim_aligned']

def test_takeoff_is_same_geometry_as_floor_zones():
    s=normalize_spec(demo_spec());q=quantities(s)
    for code in ('F01','F02'):assert q[code]==pytest.approx(sum(w*h/1e6 for c,(x,y,w,h) in floor_zones(s) if c==code))

def test_invalid_circulation_and_brand_width():
    s=demo_spec();s['wardrobe_depth']=1600
    with pytest.raises(JobError):normalize_spec(s)
    with pytest.raises(JobError):normalize_brand({'column_width':78})
    assert normalize_brand()['wordmark']=='boyxpxt.io.vn'

def test_real_export_needs_explicit_brand_confirmation(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));s=demo_spec();s['mode']='design_review'
    with pytest.raises(ValueError,match='BRANDING_CONFIRMATION_REQUIRED'):prepare_design(s)
    assert prepare_design(s,{'confirmed':True})['status']=='PREPARED_NEW_DESIGN'

def test_unapproved_export_and_tamper_rejected(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));monkeypatch.setenv('CAD_APPROVAL_MODE','manual')
    ticket=prepare_design(demo_spec())['ticket']
    with pytest.raises(FileNotFoundError):export_design(ticket)
    assert not (tmp_path/'cad_worker.lock').exists()
    with pytest.raises(ValueError):approve_design(ticket,interactive=False)
    p=tmp_path/'design_jobs'/'pending'/(ticket+'.json');v=json.loads(p.read_text());v['spec']['width']=4500;p.write_text(json.dumps(v))
    with pytest.raises(PermissionError):_read(ticket)

def test_logo_hash_frozen_into_design_ticket(tmp_path,monkeypatch):
    from PIL import Image
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path/'out'));monkeypatch.setenv('CAD_BRAND_DIR',str(tmp_path/'assets'))
    logo=tmp_path/'test.png';Image.new('RGB',(240,80),'blue').save(logo)
    register_asset('test-logo',logo);brand={'logo_asset':'test-logo'}
    ticket=prepare_design(demo_spec(),brand)['ticket'];_read(ticket)
    Path=type(logo);Path(load_asset('test-logo')['path']).write_bytes(b'changed')
    with pytest.raises(JobError):_read(ticket)
