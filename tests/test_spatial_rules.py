from copy import deepcopy
import pytest,ezdxf
from autocad_agent.building_model import example,normalize
from autocad_agent.spatial_rules import check_spatial,resolve_openings,cut_walls,overlap,RULES
from autocad_agent.design_dispatch import build_project
from autocad_agent.design_runtime import prepare_design
from autocad_agent.dxf_spatial_audit import audit_document,repair_hosted_openings
from tools.make_villa_example import villa_example


def kinds(s):return {f['type'] for f in check_spatial(normalize(s))['findings']}


def test_shared_host_cut_leaves_no_wall_solid_in_openings():
    s=normalize(example())
    for floor in (1,2):
        walls,ops,issues=resolve_openings(s,floor);assert not issues
        solids=cut_walls(walls,ops)
        assert all(not any(overlap(op['cut'],r) for r in solids) for op in ops)
        assert check_spatial(s)['findings']==[]


@pytest.mark.parametrize('change,expected',[
    (lambda s:s['extensions']['openings'][0].update(position=[8000,3000]),'OPENING_HOST_MISSING'),
    (lambda s:s['extensions']['openings'][0].update(vertical=True),'OPENING_HOST_MISSING'),
    (lambda s:s['extensions']['openings'][0].update(position=[5700,0]),'OPENING_INTERSECTS_COLUMN'),
    (lambda s:s['extensions']['openings'].append(dict(s['extensions']['openings'][0],id='duplicate')),'OPENINGS_OVERLAP'),
    (lambda s:s['extensions']['furniture'][0].update(position=[8100,300]),'DOOR_SWING_INTERSECTS_OBJECT'),
    (lambda s:s['extensions']['fixtures'][0].update(position=[17800,10000]),'PLACEMENT_INTERSECTS_WALL'),
    (lambda s:s['extensions']['openings'].__setitem__(slice(None),[v for v in s['extensions']['openings'] if v['position']!=[5000,8500]]),'ROOM_UNREACHABLE_THROUGH_OPENINGS'),
    (lambda s:next(v for v in s['extensions']['openings'] if v['position']==[5000,8500]).update(kind='window'),'ROOM_UNREACHABLE_THROUGH_OPENINGS'),
    (lambda s:s['extensions']['fixtures'][0].update(host_room='R1_0'),'SANITARY_FIXTURE_NOT_IN_BATHROOM'),
    (lambda s:s['extensions']['fixtures'][0].pop('host_room'),'OBJECT_ROOM_OR_BOUNDARY_REQUIRED'),
    (lambda s:s['extensions']['furniture'][0].update(host_room='R1_0'),'BED_NOT_IN_BEDROOM'),
])
def test_bad_inputs_are_detected_by_named_rules(change,expected):
    s=villa_example();change(s);assert expected in kinds(s)


def test_spatial_error_blocks_export_preparation(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));s=villa_example();s['extensions']['openings'][0]['position']=[8000,3000]
    with pytest.raises(ValueError,match='QUALITY_GATE'):prepare_design(s)
    assert not list(tmp_path.rglob('*.dwg'))


def test_label_cannot_be_placed_outside_declared_zone():
    s=villa_example();s['extensions']['rooms'][0]['label_zone']=[2500,3000,10,10]
    result=build_project(s)['workflow']
    assert any(i['type']=='ROOM_LABEL_HAS_NO_CLEAR_POSITION_IN_ZONE' for i in result['issues'])


def legacy_door_doc(orphan=False):
    d=ezdxf.new('R2013',setup=True)
    d.layers.new('A-TUONG');d.layers.new('A-HATCH');d.layers.new('A-CUA')
    block=d.blocks.new('CUA-1');block.add_line((0,0),(0,900));block.add_arc((0,0),900,0,90)
    m=d.modelspace();m.add_lwpolyline([(0,0),(110,0),(110,5000),(0,5000)],close=True,dxfattribs={'layer':'A-TUONG'})
    h=m.add_hatch(dxfattribs={'layer':'A-HATCH'});h.set_pattern_fill('ANSI31',scale=25);h.paths.add_polyline_path([(0,0),(110,0),(110,5000),(0,5000)],is_closed=True)
    m.add_blockref('CUA-1',(55 if not orphan else 4000,1000))
    return d


def test_legacy_safe_repair_rotates_door_and_cuts_hatch_and_outline(tmp_path):
    d=legacy_door_doc();before=audit_document(d)['counts']
    assert before['OPENING_ROTATION_NOT_PARALLEL_TO_HOST']==1 and before['WALL_FILL_NOT_CUT_AT_OPENING']==1
    assert len(repair_hosted_openings(d))==1
    path=tmp_path/'roundtrip.dxf';d.saveas(path);d=ezdxf.readfile(path)
    assert not audit_document(d)['counts']
    assert len(d.modelspace().query('HATCH'))==2
    door=next(iter(d.modelspace().query('INSERT')));assert door.dxf.rotation==90 and door.dxf.yscale<0


def test_orphan_is_reported_and_not_silently_snapped():
    d=legacy_door_doc(True);e=next(iter(d.modelspace().query('INSERT')));before=tuple(e.dxf.insert)
    assert 'OPENING_WITHOUT_VERIFIED_HOST' in audit_document(d)['counts']
    assert not repair_hosted_openings(d)
    assert tuple(e.dxf.insert)==before


def test_rule_pack_matches_gate_and_has_no_normative_claim():
    assert RULES['authority']=='PROJECT_GEOMETRY_RULES_NOT_TCVN_CERTIFICATION'
    assert 'OPENING_HOST_MISSING' in RULES['blocking_rules']


def test_text_crossing_panel_frame_is_flagged():
    d=ezdxf.new('R2013',setup=True);d.layers.new('GB-KHUNG');m=d.modelspace()
    m.add_line((0,100),(200,100),dxfattribs={'layer':'GB-KHUNG'})
    m.add_text('HEADER',dxfattribs={'height':20,'insert':(50,95)})
    assert 'TEXT_CROSSES_PANEL_FRAME' in audit_document(d)['counts']


def test_viewport_initialization_uses_typed_api_and_does_not_plot():
    from types import SimpleNamespace
    from autocad_agent.autocad_session import initialize_sheet_viewports
    vp=SimpleNamespace(Width=228,Height=241,Center=(128,153.5,0),DisplayLocked=False,ViewportOn=False)
    vp.Display=lambda on:setattr(vp,'ViewportOn',on)
    raw=SimpleNamespace(ObjectName='AcDbViewport')
    block=SimpleNamespace(Count=1,Item=lambda i:raw)
    layout=SimpleNamespace(Block=block)
    doc=SimpleNamespace(Layouts=SimpleNamespace(Item=lambda name:layout),Regen=lambda mode:None)
    api=SimpleNamespace(constants=SimpleNamespace(acPaperSpace=0,acAllViewports=1),CastTo=lambda obj,name:vp)
    assert initialize_sheet_viewports(doc,{'code':'AR-101','views':[{'rect':[14,33,228,241]}]},api,lambda fn:fn()) is layout
    assert vp.ViewportOn and vp.DisplayLocked
