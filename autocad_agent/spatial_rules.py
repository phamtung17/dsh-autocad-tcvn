"""Executable project geometry rules. These are not statutory clearance rules."""
import math,json
from pathlib import Path
from .schema import JobError

RULES=json.loads((Path(__file__).resolve().parents[1]/'standards/rules/spatial_geometry_v1.json').read_text(encoding='utf-8'))
TOL=RULES['tolerance_mm'] # project mm; contact at a boundary is permitted


def overlap(a,b,tol=TOL):
    return min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])>tol and min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])>tol


def subtract(rect,cut):
    x,y,w,h=rect;X,Y,W,H=cut;a,b=max(x,X),max(y,Y);c,d=min(x+w,X+W),min(y+h,Y+H)
    if a>=c or b>=d:return [rect]
    return [r for r in [(x,y,a-x,h),(c,y,x+w-c,h),(a,y,c-a,b-y),(a,d,c-a,y+h-d)] if min(r[2:])>1e-7]


def walls_for(s,floor):
    b=s['building'];W,D,t=b['width'],b['depth'],b['wall']
    walls=[dict(id='OUT_W',rect=(0,0,t,D),vertical=True),dict(id='OUT_E',rect=(W-t,0,t,D),vertical=True),
           dict(id='OUT_S',rect=(t,0,W-2*t,t),vertical=False),dict(id='OUT_N',rect=(t,D-t,W-2*t,t),vertical=False)]
    if 'partitions' in s.get('extensions',{}):
        for item in s['extensions']['partitions']:
            if item['floor']!=floor:continue
            x,y=item['start'];X,Y=item['end']
            walls.append(dict(id=item['id'],rect=(min(x,X),min(y,Y),abs(X-x) or t,abs(Y-y) or t),vertical=x==X))
    else:
        walls += [dict(id='MID_V',rect=(W/2,t,t,D-2*t),vertical=True),dict(id='MID_H',rect=(t,D/2,W/2-t,t),vertical=False),
                  dict(id='BATH_V',rect=(W-1800,t,t,3000-t),vertical=True),dict(id='BATH_H',rect=(W-1800,3000,1800-t,t),vertical=False)]
    return walls


def openings_for(s,floor):
    if 'partitions' in s.get('extensions',{}):return [dict(o) for o in s['extensions'].get('openings',[]) if o['floor']==floor]
    b=s['building'];W,D,t=b['width'],b['depth'],b['wall'];dw,ww=b['door_width'],b['window_width']
    return [dict(id='ENTRY',kind='door' if floor==1 else 'window',position=[W*.25-(dw if floor==1 else ww)/2,0],width=dw if floor==1 else ww,vertical=False),
            dict(id='MID',kind='door',position=[W/2,1300],width=dw,vertical=True,swing=-1),
            dict(id='BED',kind='door',position=[W*.25-dw/2,D/2],width=dw,vertical=False),
            dict(id='BATH',kind='door',position=[W-1800,1400],width=dw,vertical=True,hinge='end',swing=-1),
            *[dict(id='WIN'+str(i),kind='window',position=[x,y],width=ww,vertical=False) for i,(x,y) in enumerate([(W*.7-ww/2,0),(W*.25-ww/2,D-t),(W*.7-ww/2,D-t)])]]


def resolve_openings(s,floor):
    walls=walls_for(s,floor);resolved=[];issues=[]
    for op in openings_for(s,floor):
        x,y=op['position'];w=op['width'];vertical=op['vertical'];candidates=[]
        for wall in walls:
            X,Y,W,H=wall['rect']
            if wall['vertical']!=vertical or op.get('host_wall') not in (None,wall['id']):continue
            match=(abs(x-X)<=TOL and y>=Y-TOL and y+w<=Y+H+TOL) if vertical else (abs(y-Y)<=TOL and x>=X-TOL and x+w<=X+W+TOL)
            if match:candidates.append(wall)
        if len(candidates)!=1:
            issues.append(dict(type='OPENING_HOST_MISSING' if not candidates else 'OPENING_HOST_AMBIGUOUS',stage=3,floor=floor,opening=op['id'],candidate_hosts=[v['id'] for v in candidates]));continue
        wall=candidates[0];X,Y,W,H=wall['rect'];cut=(X,y,W,w) if vertical else (x,Y,w,H)
        item=dict(op,host=wall,cut=cut)
        for other in resolved:
            if overlap(cut,other['cut']):issues.append(dict(type='OPENINGS_OVERLAP',stage=3,floor=floor,opening=op['id'],other=other['id']))
        for other in walls:
            if other['id']!=wall['id'] and overlap(cut,other['rect']):issues.append(dict(type='OPENING_AT_WALL_JUNCTION',stage=3,floor=floor,opening=op['id'],wall=other['id']))
        st=s['structure']
        for u in s['building']['grids_x']:
            for v in s['building']['grids_y']:
                if overlap(cut,(u-st['column_width']/2,v-st['column_depth']/2,st['column_width'],st['column_depth'])):
                    issues.append(dict(type='OPENING_INTERSECTS_COLUMN',stage=3,floor=floor,opening=op['id'],column=[u,v]))
        resolved.append(item)
    return walls,resolved,issues


def cut_walls(walls,openings):
    result=[]
    for wall in walls:
        pieces=[wall['rect']]
        for op in openings:
            if op['host']['id']==wall['id']:pieces=[p for r in pieces for p in subtract(r,op['cut'])]
        result.extend(pieces)
    return result


def door_pose(op):
    x,y,w,h=op['cut'];vertical=op['vertical'];end=op.get('hinge','start')=='end';side=op.get('swing',1)
    if vertical:
        hinge=(x+w if side==1 else x,y+h if end else y);axis=(0,-1 if end else 1);normal=(side,0)
    else:
        hinge=(x+w if end else x,y+h if side==1 else y);axis=(-1 if end else 1,0);normal=(0,side)
    return hinge,axis,normal


def draw_opening(p,op):
    x,y,w,h=op['cut'];width=op['width']
    if op['kind']=='window':
        for k in (0,.5,1):
            if op['vertical']:p.line((x+w*k,y),(x+w*k,y+h),'A-WINDOW')
            else:p.line((x,y+h*k),(x+w,y+h*k),'A-WINDOW')
        return
    hinge,axis,normal=door_pose(op);closed=(hinge[0]+width*axis[0],hinge[1]+width*axis[1]);opened=(hinge[0]+width*normal[0],hinge[1]+width*normal[1])
    p.line(hinge,closed,'A-DOOR-OPENING');p.line(hinge,opened,'A-DOOR')
    a=math.degrees(math.atan2(axis[1],axis[0]))%360;c=math.degrees(math.atan2(normal[1],normal[0]))%360
    if (c-a)%360>180:a,c=c,a
    p.arc(*hinge,width,a,c,'A-DOOR')
    # Jambs follow the entire wall thickness, not an unrelated 35mm strip.
    if op['vertical']:
        p.line((x,y),(x+w,y),'A-DOOR');p.line((x,y+h),(x+w,y+h),'A-DOOR')
    else:p.line((x,y),(x,y+h),'A-DOOR');p.line((x+w,y),(x+w,y+h),'A-DOOR')


def sector(op):
    hinge,axis,normal=door_pose(op);w=op['width']
    n=max(16,math.ceil((math.pi/2)/(2*math.acos(max(-1,1-TOL/(4*w))))))
    return [hinge]+[(hinge[0]+w*(axis[0]*math.cos(i*math.pi/(2*n))+normal[0]*math.sin(i*math.pi/(2*n))),
                     hinge[1]+w*(axis[1]*math.cos(i*math.pi/(2*n))+normal[1]*math.sin(i*math.pi/(2*n)))) for i in range(n+1)]


def polygon_rect_overlap(poly,rect):
    x,y,w,h=rect;q=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    for shape in (poly,q):
        for a,b in zip(shape,shape[1:]+shape[:1]):
            axis=(-(b[1]-a[1]),b[0]-a[0]);norm=math.hypot(*axis)
            if not norm:continue
            axis=(axis[0]/norm,axis[1]/norm)
            p1=[u*axis[0]+v*axis[1] for u,v in poly];p2=[u*axis[0]+v*axis[1] for u,v in q]
            if min(max(p1),max(p2))-max(min(p1),min(p2))<=TOL:return False
    return True


def furniture_rect(item):return (*item['position'],item['width'],item['depth'])


def fixture_rect(item):
    x,y=item['position']
    return (x,y-450,360,630) if item['kind']=='wc' else (x,y,500,400) if item['kind']=='basin' else (x-450,y-450,900,900)


def room_access(s,floor,solid,ops,voids):
    """Connectivity of orthogonal free space through actual wall openings.

    This checks reachability, not statutory escape length or clear passage width.
    """
    from bisect import bisect_right
    from collections import deque
    b=s['building'];t=b['wall'];W,D=b['width'],b['depth']
    rooms=[r for r in s.get('extensions',{}).get('rooms',[]) if r['floor']==floor]
    if not rooms:return []
    obstacles=solid+[r for name,r in voids]
    xs=sorted({t,W-t,*[max(t,min(W-t,x)) for r in obstacles for x in (r[0],r[0]+r[2])]})
    ys=sorted({t,D-t,*[max(t,min(D-t,y)) for r in obstacles for y in (r[1],r[1]+r[3])]})
    free=set()
    for i,(x,X) in enumerate(zip(xs,xs[1:])):
        for j,(y,Y) in enumerate(zip(ys,ys[1:])):
            u,v=(x+X)/2,(y+Y)/2
            if X-x>1e-6 and Y-y>1e-6 and not any(a<u<a+w and c<v<c+h for a,c,w,h in obstacles):free.add((i,j))
    def cell(p):return (bisect_right(xs,p[0])-1,bisect_right(ys,p[1])-1)
    seeds=[]
    if floor==1:
        for op in ops:
            if op['kind']!='door':continue
            x,y,w,h=op['cut'];host=op['host']['id']
            p={'OUT_S':(x+w/2,t+2),'OUT_N':(x+w/2,D-t-2),'OUT_W':(t+2,y+h/2),'OUT_E':(W-t-2,y+h/2)}.get(host)
            if p and cell(p) in free:seeds.append(cell(p))
    else:
        sx,sy=b['stair_origin']
        for p in [(sx-100,sy+100),(sx+100,sy-100)]:
            if cell(p) in free:seeds=[cell(p)];break
    seen=set(seeds);queue=deque(seeds)
    while queue:
        i,j=queue.popleft()
        for node in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
            if node in free and node not in seen:seen.add(node);queue.append(node)
    issues=[]
    for r in rooms:
        node=cell(r['position'])
        if node not in free:kind='ROOM_LABEL_INSIDE_WALL_OR_VOID'
        elif not seeds:kind='NO_VERIFIED_FLOOR_ENTRANCE'
        elif node not in seen:kind='ROOM_UNREACHABLE_THROUGH_OPENINGS'
        else:continue
        issues.append(dict(type=kind,stage=3,floor=floor,room=r['id']))
    return issues


def check_spatial(s):
    findings=[];checked=[];ext=s.get('extensions',{})
    for floor in range(1,len(s['building']['levels'])):
        walls,ops,issues=resolve_openings(s,floor);findings.extend(issues);solid=cut_walls(walls,ops)
        objects=[(v['id'],furniture_rect(v),'FURNITURE') for v in ext.get('furniture',[]) if v['floor']==floor]
        objects += [(v['id'],fixture_rect(v),'FIXTURE') for v in ext.get('fixtures',[]) if v['floor']==floor]
        objects += [(v['id'],(v['position'][0]-450,v['position'][1]-150,900,300),'AC') for v in ext.get('devices',[]) if v['floor']==floor and v['kind']=='ac']
        if 'partitions' not in ext:
            b=s['building'];W,D=b['width'],b['depth'];t=b['wall'];f=s['finishes']
            if 'fixtures' not in ext:objects += [('WC',(W-1000,2150,360,630),'FIXTURE'),('BASIN',(W-1500,2200,500,400),'FIXTURE'),('SHOWER',(W-1400,350,900,900),'FIXTURE')]
            if 'furniture' not in ext:
                objects += [('BED_UPPER',(500,D-2600,1600,2000),'FURNITURE'),('WARDROBE',(W/2-850,D-2400,600,1800),'FURNITURE')]
                if floor==1:objects += [('SOFA',(500,600,800,2000),'FURNITURE'),('COFFEE',(1700,2800,1100,600),'FURNITURE'),('KITCHEN',(W/2+t+100,400,f['cabinet_length'],f['cabinet_depth']),'FURNITURE'),('DINING',(W*.55,2400,1400,750),'FURNITURE')]
                else:objects += [('BED_FRONT',(500,600,1600,2000),'FURNITURE'),('BED_RIGHT',(W/2+t,600,1600,2000),'FURNITURE')]
        lift=ext.get('elevator');b=s['building'];sx,sy=b['stair_origin'];voids=[('STAIR',(sx,sy,2*b['stair_width']+150,(b['stair_risers']/2-1)*b['stair_run']+b['stair_width']))]
        if lift:voids.append(('ELEVATOR',(*lift['origin'],lift['width'],lift['depth'])))
        findings.extend(room_access(s,floor,cut_walls(walls,[o for o in ops if o['kind']=='door']),ops,voids))
        rooms={r['id']:r for r in ext.get('rooms',[]) if r['floor']==floor}
        for group in ('fixtures','furniture'):
            for item in ext.get(group,[]):
                if item['floor']!=floor:continue
                room=rooms.get(item.get('host_room'))
                if not room or 'boundary' not in room:
                    findings.append(dict(type='OBJECT_ROOM_OR_BOUNDARY_REQUIRED',stage=8 if group=='fixtures' else 11,floor=floor,entity=item['id']));continue
                if group=='fixtures' and room.get('usage')!='bathroom':findings.append(dict(type='SANITARY_FIXTURE_NOT_IN_BATHROOM',stage=8,floor=floor,entity=item['id'],room=room['id']))
                if group=='furniture' and item['kind']=='bed' and room.get('usage')!='bedroom':findings.append(dict(type='BED_NOT_IN_BEDROOM',stage=11,floor=floor,entity=item['id'],room=room['id']))
                x,y,w,h=fixture_rect(item) if group=='fixtures' else furniture_rect(item);X,Y,W,H=room['boundary']
                if x<X-TOL or y<Y-TOL or x+w>X+W+TOL or y+h>Y+H+TOL:findings.append(dict(type='OBJECT_OUTSIDE_DECLARED_ROOM',stage=8 if group=='fixtures' else 11,floor=floor,entity=item['id'],room=room['id']))
        for i,(name,rect,kind) in enumerate(objects):
            if any(overlap(rect,r) for r in solid):findings.append(dict(type='PLACEMENT_INTERSECTS_WALL',stage=11 if kind=='FURNITURE' else 8 if kind=='FIXTURE' else 10,floor=floor,entity=name))
            for other,r in voids:
                if overlap(rect,r):findings.append(dict(type='PLACEMENT_INTERSECTS_RESERVED_VOID',stage=11,floor=floor,entity=name,other=other))
            for other,r,k in objects[:i]:
                if overlap(rect,r):findings.append(dict(type='PLACEMENTS_OVERLAP',stage=11,floor=floor,entity=name,other=other))
        for op in ops:
            if op['kind']!='door':continue
            swept=sector(op)
            for name,rect,kind in objects:
                if polygon_rect_overlap(swept,rect):findings.append(dict(type='DOOR_SWING_INTERSECTS_OBJECT',stage=3,floor=floor,opening=op['id'],entity=name))
            for name,rect in voids:
                if polygon_rect_overlap(swept,rect):findings.append(dict(type='DOOR_SWING_INTERSECTS_RESERVED_VOID',stage=3,floor=floor,opening=op['id'],entity=name))
            if any(polygon_rect_overlap(swept,r) for r in solid):findings.append(dict(type='DOOR_SWING_INTERSECTS_WALL',stage=3,floor=floor,opening=op['id']))
        checked.append(dict(floor=floor,wall_count=len(walls),hosted_openings=len(ops),placed_objects=len(objects)))
    return {'status':'SPATIAL_ERRORS_FOUND' if findings else 'CHECKED_IN_MODELED_SCOPE','ruleset':'DSH_SPATIAL_1.0','tolerance_mm':TOL,
            'floors':checked,'findings':[dict(severity='ERROR',**v) for v in findings],
            'not_checked':['statutory accessibility/fire/egress requirements','unmodeled equipment','room connectivity where room points or entrances are not supplied']}
