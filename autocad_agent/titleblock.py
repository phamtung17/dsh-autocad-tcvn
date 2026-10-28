"""Reusable parametric project border/title block in paper millimetres.

No ISO/TCVN compliance assertion: customer templates can replace this module.
"""
from __future__ import annotations


def apply_project_titleblock(doc,job,pt,retry):
    from .plotting import sheet_size_mm
    sw,sh=sheet_size_mm(job);meta=job.get('titleblock')
    if not meta:return
    # Keep titleblock as one reusable native block reference in paper space.
    name='CAD_AGENT_PROJECT_TITLE'
    block=retry(lambda:doc.Blocks.Add(pt((0,0)),name))
    def line(a,b):
        obj=retry(lambda:block.AddLine(pt(a),pt(b)))
        retry(lambda:setattr(obj,'Lineweight',25))
    def label(value,x,y,height=2.5):
        obj=retry(lambda:block.AddText(value,pt((x,y)),height))
        retry(lambda:setattr(obj,'StyleName','Standard'))
    for a,b in (((10,10),(sw-10,10)),((sw-10,10),(sw-10,sh-10)),
                ((sw-10,sh-10),(10,sh-10)),((10,sh-10),(10,10))):line(a,b)
    x=sw-190;y=10
    line((x,y),(x,y+40));line((x,y+40),(sw-10,y+40))
    line((x,y+15),(sw-10,y+15));line((x,y+28),(sw-10,y+28))
    line((x+90,y),(x+90,y+15));line((x+135,y),(x+135,y+28))
    label(meta['title'],x+4,y+32,3.5)
    label('No. '+meta['drawing_number'],x+4,y+20)
    label('Rev. '+meta.get('revision','A'),x+139,y+20)
    label('Material: '+meta.get('material','TBD'),x+4,y+7)
    label('1:'+f"{job['sheet']['scale_denominator']:g}"+' | '+job['units'],x+94,y+7)
    label(job['sheet']['format']+' | 1/1',x+139,y+7)
    label('Drawn: '+meta.get('author','TBD'),14,15)
    return retry(lambda:doc.PaperSpace.InsertBlock(pt((0,0)),name,1.,1.,1.,0.))
