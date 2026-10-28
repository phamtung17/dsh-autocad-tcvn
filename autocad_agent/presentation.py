"""Shared project drafting conventions, not authenticated TCVN requirements."""
from __future__ import annotations
import math
import re


def layer_style(name):
    """ACI colour, physical lineweight in 1/100 mm, linetype."""
    role=name.upper()
    if 'CENTER' in role or 'GRID' in role:return 1,18,'CENTER'
    if 'HIDDEN' in role:return 8,18,'DASHED'
    if any(x in role for x in ('DIM','TEXT','ANNO','NOTE')):return 7,18,'Continuous'
    if any(x in role for x in ('OUTLINE','WALL','COLUMN','FRAME')):return 7,50,'Continuous'
    return 7,25,'Continuous'


def annotation_height(job):
    from .plotting import MM_PER_UNIT
    return 2.5*job['sheet']['scale_denominator']/MM_PER_UNIT[job['units']]


def transformed_block_boxes(entity, blocks, bbox):
    block=next(b for b in blocks if b['name']==entity['block'])
    angle=math.radians(entity['rotation']);c=math.cos(angle);s=math.sin(angle)
    base=block['base'];scale=entity['scale'];pos=entity['position'];points=[]
    for child in block['entities']:
        box=bbox(child)
        if box is None:continue
        for x,y in ((box[0],box[1]),(box[0],box[3]),(box[2],box[1]),(box[2],box[3])):
            x=(x-base[0])*scale;y=(y-base[1])*scale
            points.append((pos[0]+x*c-y*s,pos[1]+x*s+y*c))
    return [min(p[0] for p in points),min(p[1] for p in points),
            max(p[0] for p in points),max(p[1] for p in points)]


def text_box(e):
    """Conservative envelope. MTEXT uses its default top-left attachment.

    This is an estimate for preflight, never a replacement for CAD font metrics.
    Raw MTEXT formatting needs renderer review.
    """
    h=e['height'];pos=e['position'];value=e['text'].replace('\\P','\n')
    lines=value.splitlines() or ['']
    width=max(len(line.expandtabs(4)) for line in lines)*h
    if e['type']=='mtext':
        available=e['width']
        rows=sum(max(1,math.ceil(len(line.expandtabs(4))*h/available)) for line in lines)
        return [pos[0],pos[1]-rows*h*1.7,pos[0]+min(width,available),pos[1]]
    corners=[(0,-h*.3),(width,-h*.3),(width,h*1.3),(0,h*1.3)]
    a=math.radians(e['rotation']);c=math.cos(a);s=math.sin(a)
    points=[(pos[0]+x*c-y*s,pos[1]+x*s+y*c) for x,y in corners]
    return [min(p[0] for p in points),min(p[1] for p in points),
            max(p[0] for p in points),max(p[1] for p in points)]


def presentation_report(job):
    from .schema import validate_job
    from .plotting import MM_PER_UNIT,viewport_plan
    from .qa import bbox
    job=validate_job(job);factor=MM_PER_UNIT[job['units']]/job['sheet']['scale_denominator']
    findings=[];texts=[]
    for e in job['geometry']:
        if e['type'] not in ('text','mtext'):continue
        paper_height=e['height']*factor
        if paper_height<2.5:
            findings.append({'id':'TEXT_SMALL','entity':e['id'],'paper_height_mm':paper_height,'level':'WARNING'})
        if '\\' in e['text'] or '\n' in e['text'] and e['type']=='text':
            findings.append({'id':'TEXT_FORMAT_REVIEW','entity':e['id'],'level':'WARNING'})
        texts.append((e['id'],bbox(e)))
    # Bounded sweep instead of an unbounded quadratic annotation check.
    active=[];pairs=0
    for entity,b in sorted(texts,key=lambda item:item[1][0]):
        active=[(other,a) for other,a in active if a[2]>b[0]]
        for other,a in active:
            if min(a[3],b[3])>max(a[1],b[1]):
                findings.append({'id':'TEXT_OVERLAP_POSSIBLE','entities':[other,entity],'level':'WARNING'})
            pairs+=1
            if pairs>=10000:break
        if pairs>=10000:
            findings.append({'id':'TEXT_CHECK_LIMIT','level':'NOT_CHECKED'});break
        active.append((entity,b))
    try:plan=viewport_plan(job)
    except ValueError as exc:
        plan=None;findings.append({'id':'SHEET_CLIPPED','level':'FAIL','detail':str(exc)})
    return {'status':'FAIL' if any(f['level']=='FAIL' for f in findings) else 'NEEDS_REVIEW' if findings else 'PRESENTATION_CHECKED',
            'findings':findings,'plot_plan':plan,'tcvn_compliance':'NOT_CHECKED',
            'scope':'Project conventions: 2.5mm minimum paper text, estimated text envelopes, transformed blocks and sheet fit. Dimension/text-to-geometry collisions require visual review.'}
