"""Read legacy plan geometry, report and conservatively repair hosted openings.

Only axis-aligned rectangular walls and the declared BT01 CUA blocks are known.
Missing/ambiguous hosts are never guessed or deleted. Repairs operate on copies.
"""
import math,json
from collections import Counter
from .spatial_rules import subtract,overlap

BLOCK_WIDTH={'CUA-1':900,'CUA-2':1600,'CUA-SO':1800}


def wall_rect(e):
    if e.dxftype()!='LWPOLYLINE' or not e.closed or e.dxf.layer.upper() not in ('A-TUONG','A-WALL'):return None
    pts=list(e.get_points('xy'))
    if len(pts)!=4:return None
    xs=sorted({round(p[0],7) for p in pts});ys=sorted({round(p[1],7) for p in pts})
    if len(xs)!=2 or len(ys)!=2:return None
    return (xs[0],ys[0],xs[1]-xs[0],ys[1]-ys[0])


def kind_of(e):
    if e.dxftype()!='INSERT':return None
    name=e.dxf.name.upper()
    return next((n for n in BLOCK_WIDTH if name==n or name.endswith('_'+n)),None)


def resolve_legacy(layout):
    physical=[(e,wall_rect(e)) for e in layout if wall_rect(e)]
    resolved=[];issues=[]
    for e in layout:
        kind=kind_of(e)
        if not kind:continue
        x,y=e.dxf.insert.x,e.dxf.insert.y;width=BLOCK_WIDTH[kind]*abs(e.dxf.xscale)
        if width<=0:issues.append({'rule':'ZERO_OPENING_WIDTH','handle':e.dxf.handle});continue
        tolerance=max(.02,width*.002);limit=width*.65;candidates=[]
        if e.has_xdata('DSH_SPATIAL'):
            try:
                data=json.loads(e.get_xdata('DSH_SPATIAL')[0].value);r=tuple(data['wall'])
                candidates=[(0,r,r[3]>r[2])]
            except (ValueError,KeyError,IndexError):pass
        if not candidates:
            for wall,r in physical:
                X,Y,W,H=r;vertical=H>W
                axis=y if vertical else x;lo=Y if vertical else X;span=H if vertical else W
                # Prefer the existing closed-axis direction when already parallel.
                angle=math.radians(e.dxf.rotation);direction=math.sin(angle) if vertical else math.cos(angle)
                sign=-1 if direction<-.5 else 1
                start=axis-width if sign<0 else axis
                d=abs(x-(X+W/2)) if vertical else abs(y-(Y+H/2))
                if start>=lo-tolerance and start+width<=lo+span+tolerance and d<=limit:candidates.append((d,r,vertical))
        candidates.sort(key=lambda c:c[0])
        if not candidates:
            issues.append({'rule':'OPENING_WITHOUT_VERIFIED_HOST','handle':e.dxf.handle,'block':kind,'position':[x,y]});continue
        if len(candidates)>1 and abs(candidates[0][0]-candidates[1][0])<tolerance and candidates[0][1]!=candidates[1][1]:
            issues.append({'rule':'OPENING_HOST_AMBIGUOUS','handle':e.dxf.handle,'block':kind});continue
        dist,r,vertical=candidates[0];X,Y,W,H=r;theta=math.radians(e.dxf.rotation)
        parallel=abs(math.sin(theta))>.999 if vertical else abs(math.cos(theta))>.999
        direction=math.sin(theta) if vertical else math.cos(theta);sign=-1 if direction<-.5 else 1
        start=(y if vertical else x)-(width if sign<0 else 0)
        cut=(X,start,W,width) if vertical else (start,Y,width,H)
        if not parallel:issues.append({'rule':'OPENING_ROTATION_NOT_PARALLEL_TO_HOST','handle':e.dxf.handle,'block':kind})
        desired=(X+W/2 if vertical else Y+H/2) if kind=='CUA-SO' else ((X+W if x>=X+W/2 else X) if vertical else (Y+H if y>=Y+H/2 else Y))
        normal=x if vertical else y
        if abs(normal-desired)>tolerance:issues.append({'rule':'OPENING_NORMAL_ALIGNMENT','handle':e.dxf.handle,'block':kind,'distance':abs(normal-desired)})
        if any(overlap(cut,q,tolerance) for wall,q in physical):issues.append({'rule':'WALL_FILL_NOT_CUT_AT_OPENING','handle':e.dxf.handle,'block':kind})
        unsafe=False
        for wall,q in physical:
            if q!=r and (q[3]>q[2])!=vertical and overlap(cut,q,tolerance):
                issues.append({'rule':'OPENING_CONFLICTS_WALL_JUNCTION','handle':e.dxf.handle,'wall':wall.dxf.handle});unsafe=True
        for column in layout.query('LWPOLYLINE'):
            if column.dxf.layer.upper() not in ('KC-COT','S-COLUMN'):continue
            points=list(column.get_points('xy'))
            if not points:continue
            a,b=min(p[0] for p in points),min(p[1] for p in points);A,B=max(p[0] for p in points),max(p[1] for p in points)
            if overlap(cut,(a,b,A-a,B-b),tolerance):issues.append({'rule':'OPENING_INTERSECTS_COLUMN','handle':e.dxf.handle,'column':column.dxf.handle});unsafe=True
        for old in resolved:
            if overlap(cut,old['cut'],tolerance):issues.append({'rule':'OPENINGS_OVERLAP','handle':e.dxf.handle,'other':old['entity'].dxf.handle})
        resolved.append(dict(entity=e,kind=kind,wall=r,vertical=vertical,cut=cut,width=width,desired=desired,parallel=parallel,sign=sign,unsafe=unsafe))
    return physical,resolved,issues


def text_checks(layout):
    from ezdxf import bbox
    texts=[];findings=[];frame_segments=[]
    for e in layout:
        if not (e.dxf.layer.upper().startswith('GB-') or e.dxf.layer.upper()=='P-FRAME'):continue
        if e.dxftype()=='LINE':frame_segments.append((e.dxf.start,e.dxf.end))
        elif e.dxftype()=='LWPOLYLINE':
            points=list(e.get_points('xy'))
            frame_segments.extend(zip(points,points[1:]+(points[:1] if e.closed else [])))
    paper=layout.name!='Model'
    W=layout.dxf.get('paper_width',0) if paper else 0;H=layout.dxf.get('paper_height',0) if paper else 0
    for e in layout:
        if e.dxftype() not in ('TEXT','MTEXT'):continue
        value=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
        if not str(value).strip():continue
        try:
            bounds=bbox.extents([e],fast=True)
            if not bounds.has_data:continue
            r=(bounds.extmin.x,bounds.extmin.y,bounds.size.x,bounds.size.y)
        except Exception:continue
        if paper and W>0 and H>0 and (r[0]<-1 or r[1]<-1 or r[0]+r[2]>W+1 or r[1]+r[3]>H+1):findings.append(dict(rule='TEXT_OUTSIDE_PAPER',handle=e.dxf.handle,text=str(value)[:90]))
        crosses=False
        for a,b in frame_segments:
            if abs(a[1]-b[1])<.01 and r[1]+r[3]*.2<a[1]<r[1]+r[3]*.8 and min(max(a[0],b[0]),r[0]+r[2])-max(min(a[0],b[0]),r[0])>r[2]*.2:crosses=True
            if abs(a[0]-b[0])<.01 and r[0]+r[2]*.2<a[0]<r[0]+r[2]*.8 and min(max(a[1],b[1]),r[1]+r[3])-max(min(a[1],b[1]),r[1])>r[3]*.2:crosses=True
        if crosses:findings.append(dict(rule='TEXT_CROSSES_PANEL_FRAME',handle=e.dxf.handle,text=str(value)[:90]))
        for old,other in texts:
            if not overlap(r,other,.05):continue
            area=(min(r[0]+r[2],other[0]+other[2])-max(r[0],other[0]))*(min(r[1]+r[3],other[1]+other[3])-max(r[1],other[1]))
            if area>min(r[2]*r[3],other[2]*other[3])*.2:findings.append(dict(rule='TEXT_TEXT_OVERLAP_ESTIMATE',handle=e.dxf.handle,other=old.dxf.handle,text=str(value)[:90]))
        texts.append((e,r))
    return findings


def audit_document(doc,include_model=True):
    results=[];totals=Counter()
    for layout in doc.layouts:
        if layout.name=='Model' and not include_model:continue
        if not len(layout):continue
        walls,ops,issues=resolve_legacy(layout)
        issues+=text_checks(layout)
        # Bounding boxes are conservative warnings, not exact curved-body checks.
        from ezdxf import bbox
        for e in layout:
            if e.dxftype()!='INSERT' or not any(k in e.dxf.name.upper() for k in ('GIUONG','SOFA','BAN-AN','BEP-DAO','WC-BON-CAU','LAVABO','SEN-TAM','THANG-MAY')):continue
            try:
                b=bbox.extents([e],fast=True)
                if b.has_data:
                    r=(b.extmin.x,b.extmin.y,b.size.x,b.size.y)
                    if any(overlap(r,w,max(.02,min(r[2:])*.01)) for ent,w in walls):issues.append(dict(rule='OBJECT_WALL_OVERLAP_AABB',handle=e.dxf.handle,block=e.dxf.name))
            except Exception:issues.append(dict(rule='OBJECT_BOUNDS_NOT_CHECKED',handle=e.dxf.handle))
        for i in issues:i['severity']='WARNING' if i['rule'] in ('TEXT_TEXT_OVERLAP_ESTIMATE','OBJECT_WALL_OVERLAP_AABB','OBJECT_BOUNDS_NOT_CHECKED') else 'ERROR'
        totals.update(i['rule'] for i in issues)
        results.append(dict(layout=layout.name,wall_rectangles=len(walls),resolved_openings=len(ops),findings=issues))
    return dict(status='REQUIRES_CORRECTION' if totals else 'NO_FINDINGS_IN_CHECKED_SCOPE',ruleset='DSH_LEGACY_DXF_1.0',
                layouts=results,counts=dict(totals),construction_release=False,
                not_checked=['semantic floor/room IDs absent in legacy DXF','plan/elevation/section equivalence without shared opening IDs','escape distances and legal requirements','exact curved equipment clearances'])


def repair_hosted_openings(doc):
    """Normal-only snapping within a declared width-relative bound; no orphan fixes."""
    actions=[]
    if 'DSH_SPATIAL' not in doc.appids:doc.appids.new('DSH_SPATIAL')
    for layout in doc.layouts:
        physical,ops,issues=resolve_legacy(layout)
        ops=[op for op in ops if not op['unsafe']]
        for op in ops:
            e=op['entity'];old=(list(e.dxf.insert),e.dxf.rotation,e.dxf.xscale,e.dxf.yscale)
            x,y=e.dxf.insert.x,e.dxf.insert.y;X,Y,W,H=op['wall'];vertical=op['vertical'];sign=op['sign']
            angle=(90 if sign>0 else 270) if vertical else (0 if sign>0 else 180)
            if op['kind']=='CUA-SO':
                if vertical:x=op['desired']
                else:y=op['desired']
            else:
                side=1 if (x if vertical else y)>=(X+W/2 if vertical else Y+H/2) else -1
                if vertical:x=X+W if side>0 else X
                else:y=Y+H if side>0 else Y
                # Local +Y is the open leaf: independent normal-side control.
                normal=(-math.sin(math.radians(angle))) if vertical else math.cos(math.radians(angle))
                e.dxf.yscale=abs(e.dxf.yscale)*(1 if normal*side>0 else -1)
            e.dxf.insert=(x,y,0);e.dxf.rotation=angle
            e.set_xdata('DSH_SPATIAL',[(1000,json.dumps({'wall':op['wall']},separators=(',',':')))])
            actions.append(dict(layout=layout.name,handle=e.dxf.handle,rule='HOST_AND_CUT_OPENING',old=old,new=[x,y,angle],host=op['wall']))
        for wall,r in physical:
            pieces=[r]
            for op in ops:
                if r==op['wall']:pieces=[p for piece in pieces for p in subtract(piece,op['cut'])]
            if pieces==[r]:continue
            attr=wall.dxf.all_existing_dxf_attribs();attr={k:attr[k] for k in ('layer','color','lineweight','linetype') if k in attr}
            layout.delete_entity(wall)
            for x,y,w,h in pieces:layout.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=True,dxfattribs=attr)
        # Rebuild only known wall hatches, preserving their pattern properties.
        for hatch in list(layout.query('HATCH')):
            if hatch.dxf.layer.upper() not in ('A-HATCH','A-HATCH-WALL'):continue
            if len(hatch.paths)!=1 or not hasattr(hatch.paths[0],'vertices'):continue
            points=hatch.paths[0].vertices;xs=sorted({round(p[0],7) for p in points});ys=sorted({round(p[1],7) for p in points})
            if len(xs)!=2 or len(ys)!=2:continue
            r=(xs[0],ys[0],xs[1]-xs[0],ys[1]-ys[0])
            if not any(all(abs(a-b)<.01 for a,b in zip(r,w)) for ent,w in physical):continue
            pieces=[r]
            for op in ops:
                if r==op['wall']:pieces=[p for piece in pieces for p in subtract(piece,op['cut'])]
            if pieces==[r]:continue
            for x,y,w,h in pieces:
                clone=hatch.copy();clone.paths.clear();clone.dxf.associative=0
                clone.paths.add_polyline_path([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],is_closed=True);layout.add_entity(clone)
            layout.delete_entity(hatch)
    # Correct the demonstrably invalid single-leaf block's floating top line.
    for block in doc.blocks:
        if block.name.upper()=='CUA-1' or block.name.upper().endswith('_CUA-1'):
            for e in list(block):block.delete_entity(e)
            block.add_line((0,0),(0,900),dxfattribs={'layer':'A-CUA'})
            block.add_line((0,0),(900,0),dxfattribs={'layer':'A-CUA'})
            block.add_arc((0,0),900,0,90,dxfattribs={'layer':'A-CUA'})
    return actions
