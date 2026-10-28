"""Deterministic offline DXF and schematic PDF exporters.
DXF is a CAD exchange format. PDF output is a schematic PREVIEW, not AutoCAD PLOT.
"""
from __future__ import annotations
import math
from pathlib import Path
from .schema import validate_job, SHEETS
from .qa import bbox

def export_dxf(job, path):
    import ezdxf
    job=validate_job(job)
    path=Path(path)
    doc=ezdxf.new('R2013',setup=True)
    doc.header['$INSUNITS']={'mm':4,'m':6,'inch':1,'feet':2}[job['units']]
    doc.header['$MEASUREMENT']=1 if job['units'] in ('mm','m') else 0
    from .presentation import layer_style,annotation_height
    height=annotation_height(job)
    doc.styles.get('Standard').dxf.font='arial.ttf'
    doc.dimstyles.get('Standard').update_dxf_attribs({
        'dimtxt':height,'dimasz':height,'dimexo':height*.4,
        'dimexe':height*.6,'dimgap':height*.3,'dimtad':1,
        'dimdec':2,'dimzin':8,'dimtxsty':'Standard'})
    def ensure(layer):
        if layer not in doc.layers:
            color,weight,linetype=layer_style(layer)
            if linetype not in doc.linetypes:linetype='Continuous'
            doc.layers.new(layer,dxfattribs={'color':color,'lineweight':weight,'linetype':linetype})
    for block in job['blocks']:
        ensure('0')
        b=doc.blocks.new(block['name'],base_point=(*block.get('base',[0,0]),0))
    msp=doc.modelspace()
    for e in job['geometry']:ensure(e['layer'])
    # Add block primitives in a second pass after helper definition
    # (block creation above intentionally creates empty definitions).
    for block in job['blocks']:
        b=doc.blocks.get(block['name'])
        for e in block['entities']:
            ensure(e.get('layer','0'))
            _add_dxf_entity(b,e)
    for e in job['geometry']:
        _add_dxf_entity(msp,e)
    doc.saveas(str(path))
    audit=ezdxf.readfile(str(path)).audit()
    return {'status':'DXF_CREATED','file':str(path),'entities':len(job['geometry']),
            'audit_errors':len(audit.errors),'audit_fixes':len(audit.fixes),'tcvn_compliance':'NOT_CHECKED',
            'tables':'offline preview geometry; native ACAD_TABLE is created during AutoCAD export' if any(e['type']=='table' for e in job['geometry']) else 'none'}

def _add_dxf_entity(space,e):
    from ezdxf.enums import TextEntityAlignment
    a={'layer':e.get('layer','0')}
    t=e['type']
    height=e.get('text_height')
    dim_override={'dimtxt':height,'dimasz':height,'dimexo':height*.4,'dimexe':height*.6,'dimgap':height*.3,'dimdec':0,'dimzin':8} if height else {}
    if t=='line':space.add_line(e['start'],e['end'],dxfattribs=a)
    elif t=='polyline':space.add_lwpolyline(e['points'],close=e['closed'],dxfattribs=a)
    elif t=='circle':space.add_circle(e['center'],e['radius'],dxfattribs=a)
    elif t=='arc':space.add_arc(e['center'],e['radius'],e['start_angle'],e['end_angle'],dxfattribs=a)
    elif t=='text':space.add_text(e['text'],dxfattribs={**a,'height':e['height'],'rotation':e['rotation'],'insert':e['position']})
    elif t=='mtext':space.add_mtext(e['text'],dxfattribs={**a,'char_height':e['height'],'width':e['width'],'insert':e['position']})
    elif t=='dim_aligned':space.add_aligned_dim(p1=e['start'],p2=e['end'],distance=_dim_distance(e),dimstyle='Standard',override=dim_override,dxfattribs=a).render()
    elif t=='dim_rotated':space.add_linear_dim(base=e['position'],p1=e['start'],p2=e['end'],angle=e['rotation'],dimstyle='Standard',override=dim_override,dxfattribs=a).render()
    elif t=='dim_radial':
        ang=math.radians(e['angle']);p=[e['center'][0]+math.cos(ang)*e['radius'],e['center'][1]+math.sin(ang)*e['radius']]
        space.add_radius_dim(center=e['center'],mpoint=p,radius=e['radius'],angle=e['angle'],dimstyle='Standard',override=dim_override,dxfattribs=a).render()
    elif t=='dim_diametric':
        space.add_diameter_dim(center=e['center'],radius=e['radius'],angle=e['angle'],dimstyle='Standard',override=dim_override,dxfattribs=a).render()
    elif t=='insert':space.add_blockref(e['block'],e['position'],dxfattribs={**a,'xscale':e['scale'],'yscale':e['scale'],'rotation':e['rotation']})
    elif t=='hatch':
        hatch=space.add_hatch(color=256,dxfattribs=a)
        if e['pattern']!='SOLID':hatch.set_pattern_fill(e['pattern'],color=256,angle=e['angle'],scale=e['pattern_scale'])
        hatch.paths.add_polyline_path(e['points'],is_closed=True,flags=1)
        for hole in e['holes']:hatch.paths.add_polyline_path(hole,is_closed=True,flags=0)
    elif t=='leader':
        last=e['points'][-1]
        annotation=space.add_mtext(e['text'],dxfattribs={**a,'insert':last,'char_height':e['height'],'width':e['text_width'],
                                                       'attachment_point':3 if e.get('align')=='right' else 1})
        leader=space.add_leader(e['points'],dimstyle='Standard',override={'dimasz':e['height']*.8,'dimscale':1},dxfattribs=a)
        leader.dxf.annotation_handle=annotation.dxf.handle
    elif t=='table':
        _preview_table(space,e)
    else:raise ValueError('unsupported entity '+t)


def _preview_table(space,e):
    """Portable offline table preview; replaced by a real ACAD_TABLE in DWG."""
    layer='_PREVIEW_TABLE'
    if layer not in space.doc.layers:space.doc.layers.new(layer,dxfattribs={'color':7,'lineweight':18})
    a={'layer':layer};x,y=e['position'];rh=e['row_height'];width=sum(e['widths']);height=(len(e['rows'])+2)*rh
    space.add_lwpolyline([(x,y),(x+width,y),(x+width,y-height),(x,y-height)],close=True,dxfattribs=a)
    for r in range(1,len(e['rows'])+2):space.add_line((x,y-r*rh),(x+width,y-r*rh),dxfattribs=a)
    xx=x
    for w in e['widths'][:-1]:
        xx+=w;space.add_line((xx,y-rh),(xx,y-height),dxfattribs=a)
    space.add_mtext(e['title'],dxfattribs={**a,'insert':(x+e['height']*.5,y-e['height']*.4),'char_height':e['height']*1.1,'width':width-e['height']})
    for r,row in enumerate([e['columns']]+e['rows'],1):
        xx=x
        for value,w in zip(row,e['widths']):
            space.add_mtext(value,dxfattribs={**a,'insert':(xx+e['height']*.4,y-r*rh-e['height']*.4),'char_height':e['height'],'width':w-e['height']*.8})
            xx+=w

def _dim_distance(e):
    a=e['start'];b=e['end'];p=e['position']
    dx=b[0]-a[0];dy=b[1]-a[1]
    return (dx*(p[1]-a[1])-dy*(p[0]-a[0]))/math.hypot(dx,dy)

def export_pdf_preview(job,path):
    """Render actual DXF primitives, dimensions and block transforms as vectors.

    Auto-fit preview only; real plotted scale still requires AutoCAD PlotToFile.
    Text is outlined through ezdxf font resolution, preserving Vietnamese glyphs.
    """
    import tempfile
    import ezdxf
    import pymupdf
    from ezdxf.addons.drawing import RenderContext, Frontend, layout
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
    job=validate_job(job);path=Path(path)
    short,long=SHEETS[job['sheet']['format']]
    sw,sh=(long,short) if job['sheet']['orientation']=='landscape' else (short,long)
    with tempfile.TemporaryDirectory(prefix='cad-preview-') as temp:
        dxf=Path(temp)/'preview.dxf'
        export_dxf(job,dxf)
        doc=ezdxf.readfile(dxf)
        backend=PyMuPdfBackend()
        config=Configuration(color_policy=ColorPolicy.BLACK,background_policy=BackgroundPolicy.WHITE)
        Frontend(RenderContext(doc),backend,config=config).draw_layout(doc.modelspace(),finalize=True)
        page=layout.Page(sw,sh,layout.Units.mm,layout.Margins(16,14,22,14))
        content=backend.get_pdf_bytes(page)
    with pymupdf.open(stream=content,filetype='pdf') as pdf:
        page=pdf[0]
        # ezdxf rounds PDF page points to integers; restore exact ISO MediaBox.
        page.set_mediabox(pymupdf.Rect(0,0,sw*72/25.4,sh*72/25.4))
        page.insert_text((14*72/25.4,(sh-10)*72/25.4),
                         'PREVIEW ONLY - AUTO-FIT / NOT TO SCALE / NOT TCVN CERTIFIED',fontsize=7)
        pdf.save(str(path))
    from pypdf import PdfReader
    reader=PdfReader(str(path));page=reader.pages[0]
    return {'status':'PDF_PREVIEW_CREATED','file':str(path),'pages':len(reader.pages),
            'page_size_mm':[round(float(page.mediabox.width)*25.4/72,2),round(float(page.mediabox.height)*25.4/72,2)],
            'scale_is_verified':False,'tcvn_compliance':'NOT_CHECKED',
            'renderer':'ezdxf vector renderer; resolved font outlines; real DIMENSION and INSERT geometry',
            'note':'Auto-fit preview; this PDF is NOT a scale-accurate AutoCAD plot.'}
