"""Conceptual 2D starter drawings for eight disciplines; not engineering calculations.
All supplied numbers are schematic defaults or user inputs, never official standards.
"""
from __future__ import annotations
from .schema import finite,validate_job,JobError

def create_template(discipline:str, name:str|None=None, width:float=120, height:float=80, units:str='mm'):
    if discipline not in {'mechanical','architectural','structural','electrical','hvac','plumbing','civil','fire_safety'}:
        raise JobError('unsupported template discipline')
    w=finite(width,'width',positive=True);h=finite(height,'height',positive=True)
    if min(w,h)<10:raise JobError('template min width/height is 10 drawing units')
    geo=[];idx=0
    def add(kind,layer,**kwargs):
        nonlocal idx
        idx+=1;geo.append({'id':f'e{idx:04d}','type':kind,'layer':layer,**kwargs})
    def line(a,b,layer):add('line',layer,start=a,end=b)
    def rect(x1,y1,x2,y2,layer):add('polyline',layer,points=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]],closed=True)
    def txt(message,pos,layer,sz=None):add('text',layer,text=message,position=pos,height=sz or max(min(w,h)*0.045,1))
    def circ(x,y,r,layer):add('circle',layer,center=[x,y],radius=r)
    if discipline=='mechanical':
        rect(0,0,w,h,'M-OUTLINE');circ(w/2,h/2,min(w,h)*0.13,'M-HOLE')
        line([w/2,-h*.12],[w/2,h*1.12],'M-CENTER');line([-w*.12,h/2],[w*1.12,h/2],'M-CENTER')
        add('dim_aligned','M-DIM',start=[0,0],end=[w,0],position=[w/2,-h*.18]);add('dim_aligned','M-DIM',start=[w,0],end=[w,h],position=[w*1.18,h/2])
        add('dim_diametric','M-DIM',center=[w/2,h/2],radius=min(w,h)*.13,angle=45,leader=h*.12)
    elif discipline=='architectural':
        rect(0,0,w,h,'A-WALL');rect(w*.03,h*.04,w*.97,h*.96,'A-WALL')
        line([w*.52,0],[w*.52,h*.72],'A-PARTITION');line([w*.52,h*.82],[w*.52,h],'A-PARTITION')
        line([w*.12,0],[w*.28,0],'A-OPENING');line([w*.12,0],[w*.12,h*.17],'A-DOOR')
        txt('ROOM A',[w*.16,h*.5],'A-TEXT');txt('ROOM B',[w*.67,h*.5],'A-TEXT');txt('CONCEPT - NOT FOR CONSTRUCTION',[0,-h*.22],'A-TEXT')
    elif discipline=='structural':
        for x in (w*.12,w*.5,w*.88):
            line([x,-h*.08],[x,h*1.08],'S-GRID')
            for y in (h*.12,h*.5,h*.88):rect(x-w*.033,y-h*.045,x+w*.033,y+h*.045,'S-COLUMN')
        for y in (h*.12,h*.5,h*.88):line([0,y],[w,y],'S-BEAM')
        txt('SCHEMATIC GRID - ENGINEER REVIEW',[0,-h*.18],'S-TEXT')
    elif discipline=='electrical':
        line([0,h*.65],[w,h*.65],'E-BUS')
        for x in (w*.2,w*.5,w*.8):
            line([x,h*.65],[x,h*.3],'E-WIRE');rect(x-w*.045,h*.43,x+w*.045,h*.51,'E-DEVICE');circ(x,h*.22,h*.055,'E-DEVICE')
        txt('ONE-LINE SCHEMATIC - VERIFY PROTECTION',[0,h*.89],'E-TEXT')
    elif discipline=='hvac':
        rect(0,h*.3,w*.22,h*.7,'M-EQUIP');rect(w*.77,h*.3,w,h*.7,'M-EQUIP')
        rect(w*.22,h*.45,w*.77,h*.57,'M-DUCT');line([w*.28,h*.51],[w*.72,h*.51],'M-AIRFLOW')
        txt('AHU',[w*.05,h*.5],'M-ANNO');txt('SUPPLY',[w*.4,h*.65],'M-ANNO')
    elif discipline=='plumbing':
        for y in (h*.25,h*.5,h*.75):line([0,y],[w,y-h*.08],'P-PIPE')
        for x in (w*.2,w*.8):line([x,0],[x,h],'P-RISER')
        circ(w*.5,h*.46,min(w,h)*.05,'P-VALVE');txt('SCHEMATIC PIPE ROUTE',[0,h*.92],'P-TEXT')
    elif discipline=='civil':
        line([0,h*.18],[w*.25,h*.48],'C-TERRAIN');line([w*.25,h*.48],[w*.7,h*.43],'C-TERRAIN');line([w*.7,h*.43],[w,h*.23],'C-TERRAIN')
        line([0,h*.55],[w*.5,h*.55],'C-ROAD');line([w*.5,h*.55],[w,h*.55],'C-ROAD');line([w*.5,h*.39],[w*.5,h*.72],'C-CENTER')
        txt('ROAD CROSS SECTION - NOT SURVEY DATA',[0,h*.82],'C-TEXT')
    else:
        rect(0,0,w,h,'F-ROOM');
        for x in (w*.25,w*.5,w*.75):circ(x,h*.6,min(w,h)*.04,'F-SPRINKLER')
        line([w*.5,h*.3],[w*.5,0],'F-ESCAPE');txt('CONCEPT - FIRE ENGINEER REVIEW',[0,h*.88],'F-TEXT')
    output=name or f'{discipline}_concept.dwg'
    job={'discipline':discipline,'units':units,'output_name':output,'purpose':'concept_only',
         'sheet':{'format':'A3','orientation':'landscape','scale_denominator':1},
         'geometry':geo,'standards':[],'assumptions':['Conceptual schematic only; no verified sizing, loads, clearances or TCVN clauses.']}
    return validate_job(job)
