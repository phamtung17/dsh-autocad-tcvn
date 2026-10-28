"""Reopen delivered demo, export native DXF and verify paper/model properties."""
from pathlib import Path
import json
import math
import uuid
from collections import Counter
import pythoncom
import win32com.client as win32
from autocad_agent.cad_com import retry_com as retry
from autocad_agent.runtime import atomic_json


def main():
    import ezdxf
    import pymupdf
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/'output/demo/reports/drafting_demo.json').read_text(encoding='utf-8'))
    path=Path(report['native']['output']);dxf=path.with_name(path.stem+'_verified_'+uuid.uuid4().hex[:6]+'.dxf')
    if dxf.exists():raise FileExistsError(dxf)
    pythoncom.CoInitialize()
    try:
        app=win32.gencache.EnsureDispatch(win32.GetActiveObject('AutoCAD.Application'))
        doc=retry(lambda:app.Documents.Open(str(path)))
        assert retry(lambda:doc.GetVariable('INSUNITS'))==4
        retry(lambda:doc.SaveAs(str(dxf),win32.constants.ac2013_dxf))
        # Keep the delivered DWG, rather than the DXF export, visible afterwards.
        retry(lambda:app.Documents.Open(str(path)))
    finally:pythoncom.CoUninitialize()
    cad=ezdxf.readfile(dxf);audit=cad.audit();assert not audit.errors
    msp=cad.modelspace();counts=dict(Counter(e.dxftype() for e in msp))
    assert len(msp)==50 and counts['CIRCLE']==5
    radii=sorted(round(e.dxf.radius,6) for e in msp.query('CIRCLE'))
    assert radii==[4.5,4.5,4.5,4.5,13.]
    dims=sorted(round(float(e.get_measurement()),6) for e in msp.query('DIMENSION'))
    assert dims==[12.,12.,20.,20.,20.,20.,26.,60.,100.,160.,200.]
    layout=cad.layouts.get('CAD_AGENT_SHEET')
    ports=[vp for vp in layout.query('VIEWPORT') if vp.dxf.id>1]
    assert len(ports)==1
    vp=ports[0]
    scale=vp.dxf.height/vp.dxf.view_height
    assert abs(scale-1)<1e-8
    expected=report['native']['plot_result']['viewport']['target_center']
    actual=vp.dxf.view_center_point+vp.dxf.view_target_point
    assert abs(actual.x-expected[0])<1e-6 and abs(actual.y-expected[1])<1e-6
    assert not cad.layers.get('CAD_AGENT_VIEWPORT').dxf.plot
    assert any(e.dxf.name=='CAD_AGENT_PROJECT_TITLE' for e in layout.query('INSERT'))
    with pymupdf.open(report['native']['pdf_output']) as pdf:
        page=pdf[0]
        # A 200mm horizontal outline edge must measure 200mm on the plotted PDF.
        lengths=[]
        for drawing in page.get_drawings():
            for item in drawing['items']:
                if item[0]=='l':
                    a,b=item[1:3]
                    if abs(a.y-b.y)<.05:lengths.append(abs(a.x-b.x)*25.4/72)
                elif item[0]=='qu':lengths.append(item[1].rect.width*25.4/72)
        assert any(abs(value-200)<.1 for value in lengths)
        page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(root/'output/demo/FINAL_PREVIEW.png'))
        page_mm=[round(page.rect.width*25.4/72,2),round(page.rect.height*25.4/72,2)]
    result={'status':'NATIVE_DEMO_VERIFIED','dwg':str(path),'dxf':str(dxf),
            'pdf':report['native']['pdf_output'],'entity_types':counts,'circle_radii_mm':radii,
            'dimension_measurements_mm':dims,'viewport_scale':scale,'viewport_center':list(actual),
            'pdf_page_mm':page_mm,'pdf_200mm_edge_checked':True,'dxf_audit_errors':len(audit.errors),
            'tcvn_compliance':'NOT_CHECKED','visual_review':'review FINAL_PREVIEW.png'}
    atomic_json(root/'output/demo/VERIFICATION.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
