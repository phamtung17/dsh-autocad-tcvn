import math
import pytest
import ezdxf
from autocad_agent.presentation import presentation_report
from autocad_agent.qa import geometry_report,bbox
from autocad_agent.templates import create_template
from autocad_agent.render import export_dxf
from autocad_agent.schema import validate_job,JobError


def test_block_fit_includes_rotation_scale_and_base():
    job=create_template('mechanical')
    job['blocks']=[{'name':'BIG','base':[10,10],'entities':[{'id':'l','type':'line','start':[10,10],'end':[610,10]}]}]
    job['geometry']=[{'id':'insert','type':'insert','block':'BIG','position':[5,5],'rotation':90,'scale':2}]
    bounds=geometry_report(job)['bounds']
    assert bounds==pytest.approx([5,5,5,1205])
    assert presentation_report(job)['status']=='FAIL'


def test_text_rotation_has_nonzero_envelope():
    entity={'type':'text','position':[0,0],'text':'ABC','height':3,'rotation':90}
    box=bbox(entity)
    assert box[3]-box[1]==pytest.approx(9)
    assert box[2]-box[0]>4


def test_small_text_and_overlaps_reported():
    job=create_template('mechanical')
    for i in range(2):job['geometry'].append({'id':f't{i}','type':'text','position':[10,10],'text':'Note','height':1})
    report=presentation_report(job)
    assert {'TEXT_SMALL','TEXT_OVERLAP_POSSIBLE'}<={f['id'] for f in report['findings']}


def test_dxf_native_dimensions_and_layer_conventions(tmp_path):
    job=create_template('mechanical')
    export_dxf(job,tmp_path/'drawing.dxf')
    doc=ezdxf.readfile(tmp_path/'drawing.dxf')
    assert doc.layers.get('M-OUTLINE').dxf.lineweight==50
    assert doc.layers.get('M-CENTER').dxf.linetype=='CENTER'
    dims=list(doc.modelspace().query('DIMENSION'))
    assert len(dims)==3
    assert sorted(round(d.get_measurement(),2) for d in dims)==[20.8,80,120]
    assert all(d.dxf.geometry in doc.blocks for d in dims)


def test_titleblock_reserves_paper_space():
    job=create_template('mechanical')
    baseline=presentation_report(job)['plot_plan']['viewport_mm'][1]
    job['titleblock']={'title':'Tấm lắp','drawing_number':'M-001'}
    job=validate_job(job)
    assert presentation_report(job)['plot_plan']['viewport_mm'][1]<baseline
    job['titleblock']['title']='bad\\Pformat'
    with pytest.raises(JobError):validate_job(job)
