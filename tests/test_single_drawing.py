from copy import deepcopy
import ezdxf
import pytest
from autocad_agent.single_drawing import compose_project
from autocad_agent.design_dispatch import build_project
from autocad_agent.fitout_design import demo_spec
from autocad_agent.building_model import normalize,service_routes
from autocad_agent.building_extensions import roof_geometry
from tools.make_villa_example import villa_example


def test_single_atlas_layout_targets_dimensions_and_blocks(tmp_path):
    project=build_project(demo_spec());project['sheets']=project['sheets'][:2]
    path=tmp_path/'PROJECT.dxf';rows=compose_project(project,{},path);doc=ezdxf.readfile(path)
    assert not doc.audit().errors
    assert {l.name for l in doc.layouts}=={'Model',*[s['code'] for s in project['sheets']]}
    for sheet,row in zip(project['sheets'],rows):
        vps=[v for v in doc.layouts.get(sheet['code']).query('VIEWPORT') if v.dxf.id!=1]
        assert len(vps)==len(sheet['views'])
        for vp,view in zip(vps,sheet['views']):
            assert vp.dxf.view_center_point.y==pytest.approx(view['target'][1]+row['offset'][1])
    dims=list(doc.modelspace().query('DIMENSION'))
    assert len(dims)==sum(e['type'].startswith('dim_') for s in project['sheets'] for e in s['job']['geometry'])
    assert all(e.get_measurement()>0 for e in dims)
    assert all(not b.block.dxf.flags&4 for b in doc.blocks)
    assert len({e.dxf.geometry for e in dims})==len(dims)


def test_villa_explicit_geometry_counts_routes_and_hip():
    s=normalize(villa_example())
    assert s['building']['width']==18000 and s['building']['depth']==17000
    assert len(s['systems']['circuits'])==7
    assert sum(v['kind']=='wc' for v in s['extensions']['fixtures'])==4
    assert sum(v['kind']=='ac' for v in s['extensions']['devices'])==8
    roof=roof_geometry(s)
    assert roof['peak']==pytest.approx(7800+9100*.22)
    routes=service_routes(s,2)
    assert any('wc_2_1' in r['id'] for r in routes)
    assert any(r.get('circuit')=='C07' for r in routes)


@pytest.mark.parametrize('change',[
    lambda s:s['extensions']['pool'].update(origin=[6000,6000]),
    lambda s:s['extensions']['fixtures'][0].update(position=[50000,0]),
    lambda s:s['systems']['fixtures_per_floor'].update(wc=4),
    lambda s:s['systems']['routes'][-1].update(circuit='NO_CIRCUIT'),
    lambda s:s['extensions']['openings'][0].update(position=[17900,0]),
    lambda s:next(v for v in s['extensions']['devices'] if v['kind']=='ac').update(position=[13000,7000]),
])
def test_invalid_villa_inputs_not_silently_drawn(change):
    s=villa_example();change(s)
    with pytest.raises(ValueError):normalize(s)


def test_villa_all_stages_and_ceiling_clearance():
    project=build_project(villa_example())
    assert len(project['sheets'])==58 and not project['workflow']['issues']
    s=villa_example();s['finishes']['ceiling_drop']=500
    assert any(i['type']=='CEILING_SERVICE_CLEARANCE' for i in build_project(s)['workflow']['issues'])


def test_native_verifier_detects_coordinate_change(tmp_path):
    from autocad_agent.single_verify import verify_combined
    project=build_project(demo_spec());project['sheets']=project['sheets'][:2]
    source=tmp_path/'PROJECT.dxf';rows=compose_project(project,{},source)
    native=ezdxf.readfile(source)
    for e in list(native.modelspace()):
        if e.dxf.layer=='_PREVIEW_TABLE':native.modelspace().delete_entity(e)
    path=tmp_path/'PROJECT_native.dxf';native.saveas(path)
    assert verify_combined(source,path,project,rows)['dimension_count']==10
    line=next(iter(native.modelspace().query('LINE')));line.dxf.start=(line.dxf.start.x+1,line.dxf.start.y,0)
    native.saveas(path)
    with pytest.raises(ValueError,match='coordinates'):verify_combined(source,path,project,rows)
