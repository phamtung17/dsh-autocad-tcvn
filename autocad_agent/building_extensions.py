"""Explicit placed equipment and hip roofs; no automatic engineering sizing."""
from .schema import JobError, finite, pt, text


def normalize_extensions(s):
    ext=s.get('extensions',{})
    allowed={'roof_type','pool','fixtures','devices','elevator','partitions','rooms','openings','furniture','ceiling_service_zone'}
    if not isinstance(ext,dict) or set(ext)-allowed: raise JobError('Unknown building extension')
    for key in ('fixtures','devices','partitions','rooms','openings','furniture'):
        if key in ext and (not isinstance(ext[key],list) or len(ext[key])>500):raise JobError('Expected bounded placement list: '+key)
    b=s['building']; n=len(b['levels'])-1
    if ext.get('roof_type','flat') not in ('flat','hip'): raise JobError('roof_type must be flat or hip')
    ids=set()
    for group in ('fixtures','devices','partitions','rooms'):
        for item in ext.get(group,[]):
            fields={'id','floor','kind','position'} if group in ('fixtures','devices') else {'id','floor','start','end'} if group=='partitions' else {'id','floor','name','position'}
            optional={'label_zone','boundary','usage'} if group=='rooms' else {'host_room'} if group=='fixtures' else set()
            if not isinstance(item,dict) or not fields<=set(item) or set(item)-fields-optional: raise JobError('Invalid '+group+' placement')
            text(item['id'],'placement id',40)
            if item['id'] in ids: raise JobError('Duplicate placement id')
            ids.add(item['id'])
            if type(item['floor']) is not int or not 1<=item['floor']<=n: raise JobError('Invalid placement floor')
            for key in ('position',) if group!='partitions' else ('start','end'):
                item[key]=pt(item[key])
                x,y=item[key]
                if not 150<=x<=b['width']-150 or not 150<=y<=b['depth']-150: raise JobError('Placement outside footprint')
            if group=='fixtures' and item['kind'] not in ('wc','basin','shower'): raise JobError('Unknown fixture kind')
            if group=='devices' and item['kind'] not in ('lights','sockets','ac','data','camera'): raise JobError('Unknown device kind')
            if group=='rooms':
                text(item['name'],'room name',60)
                if 'usage' in item and item['usage'] not in ('bathroom','bedroom','kitchen','living','hall','technical'):raise JobError('Invalid room usage')
                for field in ('label_zone','boundary'):
                    if field not in item:continue
                    zone=item[field]
                    if not isinstance(zone,list) or len(zone)!=4:raise JobError('label_zone requires x,y,width,height')
                    zone=[finite(v,'label zone') for v in zone];x,y,w,h=zone
                    if min(x,y)<0 or min(w,h)<=0 or x+w>b['width'] or y+h>b['depth']:raise JobError('Invalid label zone')
                    item[field]=zone
            if 'host_room' in item:text(item['host_room'],'host room',40)
            if group=='partitions' and (item['start']==item['end'] or item['start'][0]!=item['end'][0] and item['start'][1]!=item['end'][1]): raise JobError('Partitions must be nonzero and orthogonal; leave explicit door gaps')
    for key in ('pool','elevator'):
        if not ext.get(key): continue
        value=ext[key]
        if not isinstance(value,dict) or set(value)!={'origin','width','depth'}: raise JobError('Invalid '+key+' rectangle')
        value['origin']=pt(value['origin'])
        for k in ('width','depth'): value[k]=finite(value[k],key+'.'+k,positive=True)
        x,y=value['origin'];W,D=value['width'],value['depth']
        if key=='pool':
            site=s['site'];ox,oy=site['building_origin']
            if min(x,y)<0 or x+W>site['width'] or y+D>site['depth']: raise JobError('Pool outside site')
            if min(x+W,ox+b['width'])>max(x,ox) and min(y+D,oy+b['depth'])>max(y,oy): raise JobError('Pool intersects building')
        elif x<150 or y<150 or x+W>b['width']-150 or y+D>b['depth']-150: raise JobError('Elevator outside building')
    if 'ceiling_service_zone' in ext: ext['ceiling_service_zone']=finite(ext['ceiling_service_zone'],'ceiling_service_zone',positive=True)
    if ext.get('elevator'):
        lift=ext['elevator'];x,y=lift['origin']
        for item in ext.get('fixtures',[])+ext.get('devices',[]):
            u,v=item['position']
            if item['kind'] in ('ac','wc','basin','shower') and x<u<x+lift['width'] and y<v<y+lift['depth']:
                raise JobError('Fixture/AC placement intersects elevator reservation')
    for item in ext.get('openings',[]):
        required={'id','floor','kind','position','width','vertical'}
        if not required<=set(item) or set(item)-required-{'host_wall','hinge','swing'} or item['kind'] not in ('door','window') or type(item['vertical']) is not bool: raise JobError('Invalid opening')
        if item.get('hinge','start') not in ('start','end') or type(item.get('swing',1)) is not int or item.get('swing',1) not in (-1,1):raise JobError('Invalid hinge or swing')
        if 'host_wall' in item:text(item['host_wall'],'host wall',40)
        text(item['id'],'opening id',40)
        if item['id'] in ids: raise JobError('Duplicate opening id')
        ids.add(item['id'])
        if type(item['floor']) is not int or not 1<=item['floor']<=n: raise JobError('Invalid opening floor')
        item['position']=pt(item['position']);item['width']=finite(item['width'],'opening width',positive=True)
        x,y=item['position'];w=item['width'];t=b['wall']
        if min(x,y)<0 or x+(t if item['vertical'] else w)>b['width'] or y+(w if item['vertical'] else t)>b['depth']:raise JobError('Opening outside footprint')
    for item in ext.get('furniture',[]):
        required={'id','floor','kind','position','width','depth'}
        if not required<=set(item) or set(item)-required-{'host_room'} or item['kind'] not in ('bed','sofa','wardrobe','table'):raise JobError('Invalid furniture')
        if 'host_room' in item:text(item['host_room'],'host room',40)
        if type(item['floor']) is not int or not 1<=item['floor']<=n:raise JobError('Invalid furniture floor')
        text(item['id'],'furniture id',40)
        if item['id'] in ids:raise JobError('Duplicate furniture id')
        ids.add(item['id']);item['position']=pt(item['position'])
        for key in ('width','depth'):item[key]=finite(item[key],'furniture '+key,positive=True)
        x,y=item['position']
        if min(x,y)<b['wall'] or x+item['width']>b['width']-b['wall'] or y+item['depth']>b['depth']-b['wall']:raise JobError('Furniture outside interior')
    s['extensions']=ext


def engineering_summary(s):
    """Arithmetic observations only, with explicit evidence gaps."""
    b=s['building'];st=s['structure'];drop=s['finishes']['ceiling_drop']
    return {'status':'ENGINEERING_REVIEW_REQUIRED',
            'connected_circuit_power_w':sum(c['power_w'] for c in s['systems']['circuits']),
            'load_basis':'Supplied circuit schedule, no diversity/startup/phase/protection calculation; do not multiply without floor scope review',
            'clear_ceiling_heights_mm':[z2-z1-drop for z1,z2 in zip(b['levels'],b['levels'][1:])],
            'beam_depth_mm':st['beam_depth'],'ceiling_drop_mm':drop,
            'required_evidence':['geotechnical bearing/settlement report','structural load and member checks',
                                 'electrical demand, cable and protection calculations','fire/egress review',
                                 'MEP ceiling coordination','responsible professional release'],
            'elevator_scope':'Placed shaft reservation only; pit, headroom, supports, doors and power require supplier design' if s.get('extensions',{}).get('elevator') else 'not requested',
            'pool_scope':'Site footprint only; structure, waterproofing, circulation and safety require project design' if s.get('extensions',{}).get('pool') else 'not requested',
            'construction_release':False}


def roof_geometry(s):
    b=s['building'];o=b['roof_overhang'];W=b['width']+2*o;D=b['depth']+2*o
    run=min(W,D)/2
    if W>=D: ridge=[(-o+run,-o+D/2),(-o+W-run,-o+D/2)]
    else: ridge=[(-o+W/2,-o+run),(-o+W/2,-o+D-run)]
    return {'ridge':ridge,'eaves':b['levels'][-1],'rise':run*b['roof_slope'],'peak':b['levels'][-1]+run*b['roof_slope']}


def placed(s,group,floor):
    return [item for item in s.get('extensions',{}).get(group,[]) if item['floor']==floor]


def draw_hip_elevation(p,s,side=False):
    b=s['building'];g=roof_geometry(s);span=b['depth'] if side else b['width'];o=b['roof_overhang']
    a,c=g['ridge'];axis=1 if side else 0
    pts=[(-o,g['eaves']),(a[axis],g['peak']),(c[axis],g['peak']),(span+o,g['eaves'])]
    p.poly([point for i,point in enumerate(pts) if i==0 or point!=pts[i-1]],'A-ROOF')
    p.line((-o,g['eaves']),(span+o,g['eaves']),'A-ROOF')
    p.text(f"ĐỈNH MÁI +{g['peak']/1000:.3f}",span*.4,g['peak']+250,paper=2)


def draw_hip_plan(p,s):
    b=s['building'];o=b['roof_overhang'];W,D=b['width'],b['depth'];a,c=roof_geometry(s)['ridge']
    p.rect(-o,-o,W+2*o,D+2*o,'A-ROOF');p.hatch(-o,-o,W+2*o,D+2*o,'ANSI37',300)
    p.line(a,c,'A-RIDGE')
    corners=[(-o,-o),(W+o,-o),(W+o,D+o),(-o,D+o)]
    for corner in corners: p.line(corner,min((a,c),key=lambda v:(v[0]-corner[0])**2+(v[1]-corner[1])**2),'A-HIP')
    for x,y in [(W*.5,700),(W*.5,D-700),(700,D*.5),(W-2000,D*.5)]:
        p.text(f"DỐC {b['roof_slope']*100:g}%",x,y,paper=2)
    p.leader([(W,0),(W+400,-300),(W+800,-300)],'MÁI 4 MẶT / MÉP MÁI ĐỒNG CAO\nChi tiết liên kết chờ kỹ sư duyệt',2300,2)


def draw_custom_plan(p,s,floor,furniture=False):
    b=s['building'];W,D,t=b['width'],b['depth'],b['wall']
    from .spatial_rules import resolve_openings,cut_walls,draw_opening
    walls,ops,issues=resolve_openings(s,floor)
    for op in ops:draw_opening(p,op)
    for x,y,w,h in cut_walls(walls,ops):
        p.rect(x,y,w,h,'A-WALL');p.hatch(x,y,w,h,'ANSI31',8)
    from .annotation_rules import place_room_labels
    place_room_labels(p,s,floor,placed(s,'rooms',floor))
    if furniture:
        for item in placed(s,'furniture',floor):p.furniture(*item['position'],item['width'],item['depth'],item['kind'])
    for item in placed(s,'fixtures',floor):
        x,y=item['position']
        if item['kind']=='wc': p.toilet(x,y)
        elif item['kind']=='basin': p.basin(x,y,500,400)
        else: p.rect(x-450,y-450,900,900,'P-FIXTURE')
    lift=s.get('extensions',{}).get('elevator')
    if lift:
        x,y=lift['origin'];p.rect(x,y,lift['width'],lift['depth'],'A-LIFT')
        p.line((x,y),(x+lift['width'],y+lift['depth']),'A-LIFT');p.text('Ô THANG MÁY',x+100,y+lift['depth']-700,paper=1.7)


def subtract_rect(rect,cut):
    x,y,w,h=rect;X,Y,W,H=cut
    a,b=max(x,X),max(y,Y);c,d=min(x+w,X+W),min(y+h,Y+H)
    if a>=c or b>=d:return [rect]
    return [(u,v,ww,hh) for u,v,ww,hh in [(x,y,a-x,h),(c,y,x+w-c,h),(a,y,c-a,b-y),(a,d,c-a,y+h-d)] if ww>0 and hh>0]


def custom_floor_rects(s,floor):
    b=s['building'];t=b['wall']
    parts=[(t,t,b['width']-2*t,b['depth']-2*t)]
    cuts=[]
    for wall in placed(s,'partitions',floor):
        x,y=wall['start'];X,Y=wall['end'];cuts.append((min(x,X),min(y,Y),abs(X-x) or t,abs(Y-y) or t))
    x,y=b['stair_origin'];cuts.append((x,y,2*b['stair_width']+150,(b['stair_risers']/2-1)*b['stair_run']+b['stair_width']))
    lift=s.get('extensions',{}).get('elevator')
    if lift:cuts.append((*lift['origin'],lift['width'],lift['depth']))
    for cut in cuts:parts=[piece for part in parts for piece in subtract_rect(part,cut)]
    return parts


def custom_floor_area(s):
    return sum(w*h for floor in range(1,len(s['building']['levels'])) for x,y,w,h in custom_floor_rects(s,floor))/1e6


def draw_custom_elevation(p,s,side=False,rear=False):
    b=s['building'];span=b['depth'] if side else b['width'];height=b['levels'][-1]
    p.rect(0,0,span,height,'A-ELEVATION')
    for floor,z in enumerate(b['levels'][:-1],1):
        p.line((0,z),(span,z),'A-FLOOR')
        for item in placed(s,'openings',floor):
            x,y=item['position'];coordinate=x if side else y
            boundary=(b['width']-b['wall'] if rear else 0) if side else (b['depth']-b['wall'] if rear else 0)
            if item['vertical']!=side or abs(coordinate-boundary)>1:continue
            along=y if side else x
            if rear:along=span-along-item['width']
            sill=b['window_sill'] if item['kind']=='window' else 0
            h=b['window_height'] if item['kind']=='window' else b['door_height']
            p.rect(along,z+sill,item['width'],h,'A-WINDOW' if sill else 'A-DOOR')
    if s.get('extensions',{}).get('roof_type')=='hip':draw_hip_elevation(p,s,side)
    else:p.rect(0,height,span,b['parapet_height'],'A-PARAPET')
    p.dim((0,0),(span,0),(span/2,-500));p.dim((0,0),(0,height),(-600,height/2))
    p.leader([(span*.8,height*.5),(span+300,height*.6),(span+700,height*.6)],'MẶT ĐỨNG TỪ Ô MỞ ĐÃ KHAI BÁO',1800)
