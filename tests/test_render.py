from pathlib import Path
from pypdf import PdfReader
import ezdxf
import pytest
from autocad_agent.render import export_dxf,export_pdf_preview
from autocad_agent.templates import create_template
from autocad_agent.schema import validate_job

@pytest.mark.parametrize('sector',['mechanical','architectural','structural','electrical','hvac','plumbing','civil','fire_safety'])
def test_export_real_dxf_pdf(sector,tmp_path):
    job=create_template(sector)
    dxf=tmp_path/(sector+'.dxf');pdf=tmp_path/(sector+'.pdf')
    result=export_dxf(job,dxf)
    assert result['audit_errors']==0
    doc=ezdxf.readfile(dxf)
    assert len(doc.modelspace())>=len(job['geometry'])
    output=export_pdf_preview(job,pdf)
    assert output['pages']==1
    assert output['scale_is_verified'] is False
    assert output['page_size_mm']==[420.0,297.0]
    assert len(PdfReader(str(pdf)).pages)==1

def test_special_entities_and_block(tmp_path):
    job=create_template('mechanical')
    job['geometry']+=[{'id':'arc1','type':'arc','center':[10,10],'radius':5,'start_angle':0,'end_angle':180,'layer':'M-OUTLINE'},
                      {'id':'txt','type':'text','text':'NOTE','height':2,'position':[0,0],'layer':'M-TEXT'},
                      {'id':'mtxt','type':'mtext','text':'MULTILINE','height':2,'width':12,'position':[0,5],'layer':'M-TEXT'},
                      {'id':'dr','type':'dim_radial','center':[60,40],'radius':5,'leader':4,'angle':0,'layer':'M-DIM'},
                      {'id':'drot','type':'dim_rotated','start':[0,0],'end':[120,0],'position':[60,-6],'rotation':0,'layer':'M-DIM'}]
    job['blocks']=[{'name':'B1','base':[0,0],'entities':[{'id':'bline','type':'line','start':[0,0],'end':[1,1],'layer':'0'}]}]
    job['geometry'].append({'id':'br','type':'insert','block':'B1','position':[10,20],'scale':2,'layer':'M-BLOCK'})
    d=export_dxf(job,tmp_path/'special.dxf')
    assert d['audit_errors']==0
    doc=ezdxf.readfile(tmp_path/'special.dxf')
    assert any(e.dxftype()=='INSERT' for e in doc.modelspace())

def test_pdf_portrait_size(tmp_path):
    job=create_template('mechanical');job['sheet']['orientation']='portrait'
    output=export_pdf_preview(job,tmp_path/'portrait.pdf')
    assert output['page_size_mm']==[297.0,420.0]
