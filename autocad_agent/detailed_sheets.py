"""Compose new detailed design geometry into branded multi-scale CAD sheets."""
from __future__ import annotations
from pathlib import Path
import json
import math
from .render import export_dxf
from .branding import normalize_brand,draw_titleblock
from .qa import geometry_report
from .schema import JobError


def make_sheet_dxf(sheet,spec,branding,path,index,total):
    import ezdxf
    from ezdxf import zoom
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    qa=geometry_report(sheet['job'])
    if qa['status']!='GEOMETRY_CHECKED':raise JobError('Generated geometry failed quality gate: '+json.dumps(qa['findings']))
    export_dxf(sheet['job'],path)
    doc=ezdxf.readfile(path)
    for layer in doc.layers:
        name=layer.dxf.name
        if 'HATCH' in name:layer.dxf.lineweight=9
        elif any(k in name for k in ('DIM','ANNO','TEXT')):layer.dxf.lineweight=13
        elif 'FURNITURE' in name or 'FIXTURE' in name:layer.dxf.lineweight=18
    layout=doc.layouts.new(sheet['code'])
    layout.page_setup(size=(420,297),margins=(0,0,0,0),units='mm')
    layout.dxf.plot_type=5
    layout.dxf.current_style_sheet='monochrome.ctb'
    frame=draw_titleblock(doc,layout,branding,spec,sheet,index,total,path.parent/'assets')
    for n,view in enumerate(sheet['views'],1):
        x,y,w,h=view['rect'];scale=view['scale']
        if x<9 or x+w>frame['content_right']+1 or y<20 or y+h>287:raise JobError('Generated view overlaps title block or sheet border')
        vp=layout.add_viewport(center=(x+w/2,y+h/2),size=(w,h),view_center_point=view['target'],view_height=h*scale,
                               dxfattribs={'layer':'P-VPORT'})
        vp.dxf.flags|=16384 # viewport zoom lock
        layout.add_text(f"{n:02d}  {view['title']}  |  1:{scale:g}",dxfattribs={
            'layer':'P-VIEW-TITLE','height':2.3,'insert':(x+1,y-3),'style':'Standard'})
    # Small gaps are intentional between view panels; never silently cover a view.
    for i,a in enumerate(sheet['views']):
        ax,ay,aw,ah=a['rect']
        for b in sheet['views'][i+1:]:
            bx,by,bw,bh=b['rect']
            if min(ax+aw,bx+bw)>max(ax,bx)+.01 and min(ay+ah,by+bh)>max(ay,by)+.01:
                raise JobError('Generated paper-space viewports overlap')
    doc.layouts.set_active_layout(sheet['code'])
    doc.header['$TILEMODE']=0;doc.header['$INSUNITS']=4;doc.header['$LWDISPLAY']=True
    zoom.extents(layout)
    doc.saveas(path)
    audit=ezdxf.readfile(path).audit()
    if audit.errors:raise JobError('Detailed DXF failed structural audit')
    return {'dxf':str(path),'code':sheet['code'],'entity_count':len(sheet['job']['geometry']),
            'views':len(sheet['views']),'branding':frame,'audit_errors':len(audit.errors)}


def render_sheet_pdf(dxf_path,pdf_path,layout_name):
    import ezdxf,pymupdf
    from ezdxf.addons.drawing import RenderContext,Frontend,layout
    from ezdxf.addons.drawing.config import Configuration,ColorPolicy,BackgroundPolicy
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
    from ezdxf.math import BoundingBox2d
    doc=ezdxf.readfile(dxf_path);backend=PyMuPdfBackend()
    config=Configuration(color_policy=ColorPolicy.BLACK,background_policy=BackgroundPolicy.WHITE)
    Frontend(RenderContext(doc),backend,config=config).draw_layout(doc.layouts.get(layout_name),finalize=True)
    page=layout.Page(420,297,layout.Units.mm,layout.Margins.all(0))
    data=backend.get_pdf_bytes(page,settings=layout.Settings(fit_page=False,scale=1),render_box=BoundingBox2d([(0,0),(420,297)]))
    with pymupdf.open(stream=data,filetype='pdf') as pdf:
        pdf[0].set_mediabox(pymupdf.Rect(0,0,420*72/25.4,297*72/25.4));pdf.save(pdf_path)
    return {'file':str(pdf_path),'page_mm':[420,297],'scale_is_native_autocad_verified':False,
            'note':'Offline vector preview. Native DWG/PDF must be measured separately.'}
