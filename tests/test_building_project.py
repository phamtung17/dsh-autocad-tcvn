from copy import deepcopy
import json,math
import pytest,ezdxf
from autocad_agent.building_model import example,normalize,takeoff,digest
from autocad_agent.building_design import build_building_set
from autocad_agent.project_workflow import STAGES,check_project,change_impact,stage_hash,clash_check
from autocad_agent.detailed_sheets import make_sheet_dxf
from autocad_agent.branding import normalize_brand
from autocad_agent.schema import JobError

@pytest.fixture(scope='module')
def project():return build_building_set(example())

def test_all_fourteen_stages_complete_per_floor(project):
    assert len(project['sheets'])==58
    assert {x['stage'] for x in project['sheets']}==set(range(1,15))
    assert project['workflow']['issues']==[]
    assert project['workflow']['release_status']=='BLOCKED'
    assert 'DEMO_NOT_FOR_CONSTRUCTION' in {x['type'] for x in project['workflow']['release_blockers']}
    assert set(project['workflow']['stages'][3]['missing_roles'])==set()

def test_each_generated_sheet_composes_and_audits(tmp_path,project):
    for n,sheet in enumerate(project['sheets'],1):
        path=tmp_path/(sheet['code']+'.dxf');make_sheet_dxf(sheet,project['spec'],normalize_brand(),path,n,len(project['sheets']))
        d=ezdxf.readfile(path);assert not d.audit().errors
        assert len(d.layouts.get(sheet['code']).query('VIEWPORT'))>=3

def test_missing_floor_and_detail_block_content(project):
    p=deepcopy(project);p['sheets']=[x for x in p['sheets'] if x['code']!='PL-102']
    qa=check_project(p);assert any(x['type']=='FLOOR_COVERAGE' and x['role']=='water' for x in qa['issues'])
    p=deepcopy(project);sheet=next(x for x in p['sheets'] if x['code']=='ST-202');sheet['job']['geometry']=[e for e in sheet['job']['geometry'] if e['type']!='dim_aligned']
    assert any(x['type']=='MISSING_DETAIL_CONTENT' for x in check_project(p)['issues'])

def test_empty_main_view_cannot_pass_by_having_a_detail_and_notes(project):
    p=deepcopy(project);sheet=next(x for x in p['sheets'] if x['code']=='AR-101');main=set(sheet['main_entity_ids'])
    sheet['job']['geometry']=[e for e in sheet['job']['geometry'] if e['id'] not in main]
    assert any(x['type']=='MISSING_MAIN_CONTENT' and x['sheet']=='AR-101' for x in check_project(p)['issues'])

def test_broken_references_and_stale_sheets(project):
    p=deepcopy(project);p['sheets'][0]['references'].append('DOES-NOT-EXIST');p['spec']['site']['width']+=100
    kinds={x['type'] for x in check_project(p)['issues']};assert {'BROKEN_SHEET_REFERENCE','STALE_SHEET'}<=kinds

def test_price_change_only_rebuilds_budget_and_qa():
    a=example();b=deepcopy(a);b['prices']['floor_finish']*=2
    result=change_impact(a,b);assert result['rebuild_stages']==[13,14]
    old=takeoff(normalize(a));new=takeoff(normalize(b))
    assert [r['quantity'] for r in old]==[r['quantity'] for r in new]
    assert sum(r['amount'] for r in new)>sum(r['amount'] for r in old)

def test_geometry_change_propagates_downstream():
    a=example();b=deepcopy(a);b['building']['width']=10000;b['building']['grids_x'][-1]=10000
    result=change_impact(a,b);assert set(range(2,15))<=set(result['rebuild_stages'])
    b=deepcopy(a);b['revision']='B';assert change_impact(a,b)['rebuild_stages']==list(range(1,15))

def test_route_hits_column_and_fix_clears():
    s=example();assert not clash_check(normalize(s))['findings']
    s['systems']['routes'][0]['points']=[[50,50,500],[50,500,500]]
    assert any(x['type']=='ROUTE_STRUCTURE_INTERSECTION' for x in clash_check(normalize(s))['findings'])

def test_route_crosses_slab_detected():
    s=example();s['systems']['routes'][0]['points']=[[1000,1000,3100],[1000,1000,3400]]
    assert any('SLAB' in x.get('element','') for x in clash_check(normalize(s))['findings'])

def test_reversed_waste_slope_detected():
    s=example();route=next(r for r in s['systems']['routes'] if r['system']=='waste');route['points'].reverse()
    assert any(x['type']=='DRAIN_SLOPE_OR_DIRECTION' for x in clash_check(normalize(s))['findings'])

def test_slab_and_column_quantities_do_not_count_joint_twice():
    s=normalize(example());q={r['code']:r for r in takeoff(s)};b=s['building'];st=s['structure']
    opening=(2*b['stair_width']+150)*((b['stair_risers']/2-1)*b['stair_run']+b['stair_width'])/1e6
    assert q['slab_concrete']['quantity']==pytest.approx((72-opening)*.12*2,abs=1e-6)
    assert q['column_concrete']['quantity']==pytest.approx(9*.25*.25*(6.6-2*.12),abs=1e-6)
    internal=b['wall']*((b['depth']-2*b['wall']-b['door_width'])+(b['width']/2-b['wall']-b['door_width'])+(3000-b['wall']-b['door_width'])+1800-b['wall'])/1e6
    assert q['floor_finish']['quantity']==pytest.approx(((9-.3)*(8-.3)-opening-internal)*2,abs=1e-6)

def test_fixture_branches_and_circuit_quantities_share_drawn_network():
    from autocad_agent.building_model import service_routes,route_length,circuit_routes,device_points
    s=normalize(example());routes=service_routes(s,1)
    assert {'CW01_WC','CW01_BASIN','CW01_SHOWER','CW01_SINK','SW01_SINK','LV01_DATA2','LV01_CAM'}<={r['id'] for r in routes}
    for sockets,circuit in [(False,'C01'),(True,'C02')]:
        path=next(r for r in circuit_routes(s) if r['circuit']==circuit)['points']
        assert set(device_points(s,sockets))<={tuple(p[:2]) for p in path}
        assert len(path)==len({tuple(p) for p in path})
    q={r['code']:r['quantity'] for r in takeoff(s)}
    for system,code in [('water','water_pipe'),('waste','waste_pipe'),('power','power_conduit'),('data','data_conduit')]:
        assert q[code]==pytest.approx(sum(route_length(r) for floor in (1,2) for r in service_routes(s,floor) if r['system']==system),abs=1e-6)

@pytest.mark.parametrize('levels',[[0,3300],[0,3300,6600,9900]])
def test_supported_floor_counts_are_complete(levels):
    s=example();s['building']['levels']=levels;p=build_building_set(s)
    assert p['workflow']['issues']==[]
    for role in ('architecture','water','waste','lighting','sockets','low_voltage','hvac','interior','ceiling','finishes'):
        assert {x['floor'] for x in p['sheets'] if x['role']==role}==set(range(1,len(levels)))

def test_rebar_view_is_enlarged_and_column_bars_on_perimeter(project):
    sheet=next(s for s in project['sheets'] if s['code']=='ST-202')
    assert [v['scale'] for v in sheet['views'][:2]]==[5,5]
    circles=[e for e in sheet['job']['geometry'] if e['type']=='circle' and e['center'][0]>9000]
    assert len(circles)==8

def test_room_names_do_not_cover_furniture_in_architecture_plans(project):
    from autocad_agent.qa import bbox
    from autocad_agent.presentation import transformed_block_boxes
    for sheet in [x for x in project['sheets'] if x['role']=='architecture']:
        job=sheet['job'];furniture=[transformed_block_boxes(e,job['blocks'],bbox) for e in job['geometry'] if e['type']=='insert' and e['layer']=='A-FURNITURE']
        labels=[e for e in job['geometry'] if e['type']=='mtext' and e['text'].startswith('PHÒNG NGỦ')]
        for e in labels:
            x,y=e['position'];box=[x,y-e['height'],x+min(e['width'],len(e['text'])*e['height']*.65),y]
            assert all(min(box[2],f[2])<=max(box[0],f[0]) or min(box[3],f[3])<=max(box[1],f[1]) for f in furniture)

def test_electrical_captions_do_not_cover_distribution_board(project):
    from autocad_agent.qa import bbox
    from autocad_agent.presentation import transformed_block_boxes
    for sheet in [x for x in project['sheets'] if x['role'] in ('lighting','sockets','ceiling')]:
        job=sheet['job'];board=next(e for e in job['geometry'] if e['type']=='insert' and e['block'].startswith('TAG_DB_'))
        f=transformed_block_boxes(board,job['blocks'],bbox)
        for e in [x for x in job['geometry'] if x['type']=='leader']:
            x,y=e['points'][-1];w=e['text_width'];box=[x-w if e['align']=='right' else x,y-3*e['height'],x if e['align']=='right' else x+w,y]
            assert min(box[2],f[2])<=max(box[0],f[0]) or min(box[3],f[3])<=max(box[1],f[1])

def test_complete_index_contains_itself_and_all_sheets(project):
    index={row[0] for s in project['sheets'] if s['role']=='drawing_index' for e in s['job']['geometry'] if e['type']=='table' and e['title'].startswith('DANH MỤC') for row in e['rows']}
    assert index=={s['code'] for s in project['sheets']}

def test_long_estimate_is_paginated():
    s=example();s['estimate_scope']['additional_items']=[{'code':f'X{i}','description':'Hạng mục bổ sung','quantity':1,'unit':'bộ','unit_price':1000,'basis':'Đầu vào demo'} for i in range(25)]
    p=build_building_set(s);assert not p['workflow']['issues']
    assert len([x for x in p['sheets'] if x['role']=='estimate'])==3
    assert sum(r['amount'] for r in p['takeoff'] if r['code'].startswith('X'))==25000

def test_reviews_are_not_self_referential_and_stale_review_invalidates():
    s=example();s['mode']='design_review';s['source']={k:'USER DOCUMENT REF-001' for k in s['source']};s['estimate_scope']['scope_confirmed']=True
    for i in range(1,15):s['reviews'][str(i)]={'reviewer':'External engineer (user attestation)','reference':'REVIEW-001','input_hash':stage_hash(s,i)}
    p=build_building_set(s);assert p['workflow']['release_status']=='READY_FOR_HUMAN_RELEASE'
    s['structure']['cover']=40;p=build_building_set(s)
    assert any(x['type']=='ENGINEERING_REVIEW_REQUIRED' and x['stage']==7 for x in p['workflow']['release_blockers'])

def test_open_issue_blocks_until_resolved():
    s=example();s['issues']=[{'id':'CLASH-1','stage':8,'description':'Kiểm tra tuyến','status':'open','resolution':''}]
    assert any(x['type']=='OPEN_PROJECT_ISSUE' for x in build_building_set(s)['workflow']['issues'])
    s['issues'][0].update(status='resolved',resolution='Đã sửa và kiểm lại tuyến')
    assert not build_building_set(s)['workflow']['issues']

@pytest.mark.parametrize('mutate',[
    lambda s:s['building'].update(grids_x=[0,8000,4500,9000]),
    lambda s:s['building'].update(door_width=3000),
    lambda s:s['building'].update(levels=[0,3300,3200]),
    lambda s:s['finishes'].update(cabinet_length=5000),
    lambda s:s['structure'].update(column_bars=7),
    lambda s:s['systems']['routes'][0].update(points=[[50000,0,0],[50000,1000,0]]),
])
def test_invalid_shared_geometry_rejected(mutate):
    s=example();mutate(s)
    with pytest.raises((JobError,ValueError)):normalize(s)

def test_real_branding_and_unapproved_export_blocked(tmp_path,monkeypatch):
    from autocad_agent.design_runtime import prepare_design,export_design
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));monkeypatch.setenv('CAD_APPROVAL_MODE','manual')
    s=example();s['mode']='design_review'
    with pytest.raises(ValueError,match='BRANDING_CONFIRMATION_REQUIRED'):prepare_design(s)
    s['mode']='demo';ticket=prepare_design(s)['ticket']
    with pytest.raises(FileNotFoundError):export_design(ticket)

def test_delivery_integrity_detects_change(tmp_path,monkeypatch):
    from autocad_agent.project_delivery import seal_delivery,verify_delivery
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));root=tmp_path/'generated_projects'/'demo';root.mkdir(parents=True)
    (root/'DWG').mkdir();(root/'PDF').mkdir()
    for name in ('DWG/A.dwg','DWG/A_native.dxf','PDF/A.pdf'):(root/name).write_bytes(b'demo')
    (root/'GENERATION_REPORT.json').write_text(json.dumps({'sheets':[{'code':'A'}]}));seal_delivery(root)
    assert verify_delivery('demo')['status']=='INTEGRITY_CHECKED'
    (root/'PDF/A.pdf').write_bytes(b'changed');assert verify_delivery('demo')['status']=='HANDOVER_BLOCKED'
