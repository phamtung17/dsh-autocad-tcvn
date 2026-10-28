"""Deterministic geometry and project-rule quality checks.
This is NOT a TCVN certificate; every source of rule is recorded.
"""
from __future__ import annotations
import math
from collections import Counter
from .schema import validate_job, JobError

EPS=1e-8

def distance(a,b): return math.hypot(b[0]-a[0],b[1]-a[1])

def orient(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def onseg(a,b,c):
    return min(a[0],b[0])-EPS<=c[0]<=max(a[0],b[0])+EPS and min(a[1],b[1])-EPS<=c[1]<=max(a[1],b[1])+EPS

def intersect(a,b,c,d):
    x,y,z,w=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if (x>EPS and y<-EPS or x<-EPS and y>EPS) and (z>EPS and w<-EPS or z<-EPS and w>EPS):return True
    return any(abs(v)<EPS and onseg(p,q,r) for v,p,q,r in [(x,a,b,c),(y,a,b,d),(z,c,d,a),(w,c,d,b)])

def self_intersections(points,closed):
    segments=list(zip(points,points[1:]))
    if closed:segments.append((points[-1],points[0]))
    n=len(segments)
    if n>700:return -1 # Complexity guard; validation result becomes NOT_CHECKED
    count=0
    for i,(a,b) in enumerate(segments):
        for j in range(i+1,n):
            if j==i+1 or (closed and i==0 and j==n-1):continue
            c,d=segments[j]
            if intersect(a,b,c,d):count+=1
    return count

def bbox(e):
    t=e['type']
    if t in ('line','dim_aligned','dim_rotated'):
        pts=[e['start'],e['end']]+([e['position']] if 'position' in e else [])
    elif t in ('polyline','hatch'): pts=e['points']
    elif t in ('circle','arc','dim_radial','dim_diametric'):
        c=e['center'];r=e['radius'];return [c[0]-r,c[1]-r,c[0]+r,c[1]+r]
    elif t in ('text','mtext'):
        from .presentation import text_box
        return text_box(e)
    elif t=='insert':pts=[e['position']]
    elif t=='leader':
        pts=e['points'];p=pts[-1]
        pts=pts+[[p[0]+(-1 if e.get('align')=='right' else 1)*e['text_width'],p[1]-e['height']*3]]
    elif t=='table':
        p=e['position'];return [p[0],p[1]-(len(e['rows'])+2)*e['row_height'],p[0]+sum(e['widths']),p[1]]
    else:return None
    return [min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]

def geometry_report(job):
    job=validate_job(job)
    warnings=[];boxes=[];measurements=[];geometry_signatures=set()
    counts=Counter()
    for e in job['geometry']:
        counts[e['type']]+=1
        # Exact coordinate duplicates within the same layer are suspicious.
        if e['type'] in ('line','circle','arc','polyline'):
            import json
            signature=json.dumps({k:v for k,v in e.items() if k!='id'},sort_keys=True)
            if signature in geometry_signatures:
                warnings.append({'id':'GEO-DUPLICATE','entity':e['id'],'level':'FAIL'})
            geometry_signatures.add(signature)
        if e['type']=='line':
            measurements.append({'id':e['id'],'length':round(distance(e['start'],e['end']),6)})
        elif e['type']=='circle':
            measurements.append({'id':e['id'],'radius':e['radius'],'diameter':2*e['radius']})
        elif e['type']=='dim_aligned':
            measurements.append({'id':e['id'],'measured_distance':round(distance(e['start'],e['end']),6)})
        b=bbox(e)
        if e['type']=='insert':
            from .presentation import transformed_block_boxes
            b=transformed_block_boxes(e,job['blocks'],bbox)
        if b:boxes.append(b)
        if e['type']=='polyline':
            intersections=self_intersections(e['points'],e['closed'])
            if intersections==-1:warnings.append({'id':'GEO-SELF-UNKNOWN','entity':e['id'],'level':'NOT_CHECKED','detail':'too many segments'})
            elif intersections:warnings.append({'id':'GEO-SELF-INTERSECTION','entity':e['id'],'level':'FAIL','count':intersections})
            segments=list(zip(e['points'],e['points'][1:]))
            if e['closed']:segments.append((e['points'][-1],e['points'][0]))
            if any(distance(a,b)<EPS for a,b in segments):warnings.append({'id':'GEO-ZERO-SEGMENT','entity':e['id'],'level':'FAIL'})
            if e['closed']:
                pts=e['points'];area=abs(sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))/2)
                if area<EPS:warnings.append({'id':'GEO-ZERO-AREA','entity':e['id'],'level':'FAIL'})
        if e['type']=='hatch':
            for loop in [e['points']]+e['holes']:
                if self_intersections(loop,True):warnings.append({'id':'HATCH-BOUNDARY-INVALID','entity':e['id'],'level':'FAIL'})
                area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(loop,loop[1:]+loop[:1])))/2
                if area<EPS:warnings.append({'id':'HATCH-ZERO-AREA','entity':e['id'],'level':'FAIL'})
    bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)] if boxes else None
    failed=any(w['level']=='FAIL' for w in warnings)
    return {'status':'FAIL' if failed else 'NEEDS_REVIEW' if warnings else 'GEOMETRY_CHECKED',
            'units':job['units'],'entity_count':len(job['geometry']),'by_type':dict(counts),
            'bounds':bounds,'measurements':measurements,'findings':warnings,'tcvn_compliance':'NOT_CHECKED'}

SAFE_RULES={'required_layers','max_extent','min_text_height','max_text_height','min_line_length','min_circle_radius'}

def validate_rules(rules):
    if not isinstance(rules,dict) or rules.get('kind')!='PROJECT_RULE':
        raise JobError('rule pack must declare kind=PROJECT_RULE; no automatic TCVN certification')
    if not isinstance(rules.get('project_id'),str) or not rules['project_id'].strip():raise JobError('project_id required')
    checks=rules.get('checks')
    if not isinstance(checks,list) or len(checks)>100:raise JobError('checks must be a list of <=100 entries')
    for c in checks:
        if not isinstance(c,dict) or c.get('type') not in SAFE_RULES:raise JobError('unknown project rule')
        if c['type']=='required_layers':
            layers=c.get('layers')
            if not isinstance(layers,list) or len(layers)>100 or not all(isinstance(s,str) for s in layers):raise JobError('invalid required layers')
        else:
            from .schema import finite
            c['value']=finite(c.get('value'),c['type'],positive=True)
    return rules

def check_project_rules(job,rules):
    job=validate_job(job);rules=validate_rules(rules)
    outcomes=[]
    for i,c in enumerate(rules['checks']):
        k=c['type'];actual=None;expected=c.get('value')
        if k=='required_layers':
            present={e['layer'] for e in job['geometry']};missing=sorted(set(c['layers'])-present)
            ok=not missing;actual=sorted(present);expected=c['layers']
        elif k=='max_extent':
            bounds=geometry_report(job)['bounds'];actual=max(abs(x) for x in bounds) if bounds else 0;ok=actual<=expected
        elif k in {'min_text_height','max_text_height'}:
            data=[e['height'] for e in job['geometry'] if e['type'] in ('text','mtext')]
            actual=min(data) if k=='min_text_height' and data else max(data) if data else None
            ok=None if actual is None else (actual>=expected if k=='min_text_height' else actual<=expected)
        elif k=='min_line_length':
            data=[distance(e['start'],e['end']) for e in job['geometry'] if e['type']=='line']
            actual=min(data) if data else None;ok=None if actual is None else actual>=expected
        else:
            data=[e['radius'] for e in job['geometry'] if e['type']=='circle']
            actual=min(data) if data else None;ok=None if actual is None else actual>=expected
        outcomes.append({'id':f'PROJECT-{i+1:03d}','check':k,'expected':expected,'measured':actual,
                         'result':'PASS' if ok is True else 'FAIL' if ok is False else 'NOT_APPLICABLE',
                         'authority':'PROJECT_RULE'})
    return {'project_id':rules['project_id'],'status':'FAIL' if any(c['result']=='FAIL' for c in outcomes) else 'PROJECT_RULES_CHECKED',
            'checks':outcomes,'tcvn_compliance':'NOT_CHECKED','note':'Passed project rules are not verified TCVN clauses.'}
