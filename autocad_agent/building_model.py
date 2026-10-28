"""Shared, explicit model for a small rectangular low-rise building.

Engineering sizes are inputs, never automatically sized or certified.
"""
from copy import deepcopy
import hashlib,json,math
from .schema import JobError,finite,text,pt,seq,IDENT_RE
from .reference_profiles import checked_id

def digest(value):
    def canonical(v):
        if isinstance(v,float) and v.is_integer():return int(v)
        if isinstance(v,list):return [canonical(x) for x in v]
        if isinstance(v,dict):return {k:canonical(x) for k,x in v.items()}
        return v
    return hashlib.sha256(json.dumps(canonical(value),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def example():
    return {'engine':'building_v1','project_id':'boyxpxt_building_demo','project_name':'NHÀ Ở / HỒ SƠ ĐA BỘ MÔN DEMO',
      'mode':'demo','revision':'A','units':'mm',
      'source':{'survey':'DEMO / không phải khảo sát thực địa','structural':'DEMO / chưa có tính toán kỹ sư',
                'mep':'DEMO / chưa tính tải và thủy lực','prices':'DEMO / đơn giá minh họa'},
      'site':{'width':15000,'depth':18000,'building_origin':[3000,4000],'north_degrees':0,
              'datum':'MỐC DEMO ±0.000','survey_points':[[0,0,-150],[15000,0,-120],[15000,18000,100],[0,18000,80]],
              'road_width':5000,'paving_thickness':80},
      'building':{'width':9000,'depth':8000,'wall':150,'levels':[0,3300,6600],
                  'grids_x':[0,4500,9000],'grids_y':[0,4000,8000],
                  'door_width':900,'door_height':2200,'window_width':1800,'window_sill':900,'window_height':1400,
                  'stair_width':1100,'stair_run':280,'stair_risers':20,'stair_origin':[5000,4100],
                  'roof_overhang':400,'roof_slope':.02,'parapet_height':900},
      'structure':{'foundation_width':1600,'foundation_depth':450,'foundation_bottom':-1600,
                   'blinding':100,'column_width':250,'column_depth':250,'beam_width':220,'beam_depth':450,
                   'slab_thickness':120,'cover':35,'main_bar_diameter':18,'column_bars':8,
                   'stirrup_diameter':8,'stirrup_spacing':150,'footing_bar_diameter':12,'footing_bar_spacing':150},
      'finishes':{'tile':10,'screed':40,'waterproofing':3,'gypsum':12.5,'ceiling_drop':350,'skirting':100,
                  'cabinet_length':2400,'cabinet_depth':600,'cabinet_height':900,'panel':18,'counter':30},
      'systems':{'water_diameter':25,'waste_diameter':110,'drain_slope':.02,'water_pressure_kpa':200,
                 'routes':[{'id':'CW01','system':'water','points':[[8000,500,500],[8000,3000,500],[7500,3000,500]],'diameter':25},
                           {'id':'SW01','system':'waste','points':[[7500,3000,-200],[8000,3000,-210],[8000,500,-260]],'diameter':110},
                           {'id':'EL01','system':'power','points':[[500,500,2600],[500,3000,2600],[3500,3000,2600]],'diameter':20},
                           {'id':'LV01','system':'data','points':[[1000,500,2400],[1000,2500,2400],[3500,2500,2400]],'diameter':20},
                           {'id':'AC01','system':'hvac','points':[[500,7000,2800],[3500,7000,2800]],'diameter':200}],
                 'circuits':[{'id':'C01','use':'Chiếu sáng','power_w':600,'voltage':230,'breaker_a':10,'cable_mm2':1.5},
                             {'id':'C02','use':'Ổ cắm','power_w':2500,'voltage':230,'breaker_a':20,'cable_mm2':2.5},
                             {'id':'C03','use':'Điều hòa','power_w':1800,'voltage':230,'breaker_a':20,'cable_mm2':2.5}],
                 'fixtures_per_floor':{'lights':6,'sockets':6,'wc':1,'basin':1,'shower':1,'data':2,'camera':1,'ac':1},
                 'earthing_resistance_target_ohm':4,'inspection_chamber_size':600},
      'prices':{'slab_concrete':1500000,'column_concrete':1700000,'beam_concrete':1700000,
                'foundation_concrete':1500000,'floor_finish':350000,'roof_waterproof':180000,
                'water_pipe':65000,'waste_pipe':180000,'power_conduit':25000,'data_conduit':28000,
                'light':350000,'socket':120000,'wc':3500000,'basin':1500000,'cabinet':3200000,'paving':280000},
      'estimate_scope':{'coverage_note':'Khối lượng các hạng mục đã dựng trong mô hình demo',
                        'excluded_items':['Cốt thép tổng hợp, xây trát, cửa và hạng mục chưa mô hình hóa','Nhân công, chi phí chung, thuế'],
                        'additional_items':[],'scope_confirmed':False},
      'reviews':{},'issues':[]}

def normalize(raw):
    if not isinstance(raw,dict):raise JobError('Building specification must be an object')
    s=deepcopy(raw);template=example()
    if set(s)!=set(template):raise JobError('Building specification must explicitly provide: '+', '.join(sorted(set(template))))
    if s['engine']!='building_v1' or s['units']!='mm':raise JobError('Expected building_v1 with shared mm coordinates')
    checked_id(s['project_id']);text(s['project_name'],'project name',90);text(s['revision'],'revision',12)
    if s['mode'] not in ('demo','design_review'):raise JobError('mode must be demo or design_review')
    for key in ('source','site','building','structure','finishes','systems','prices'):
        if not isinstance(s[key],dict) or set(s[key])!=set(template[key]):raise JobError('Missing or unknown fields in '+key)
    for key in ('survey','structural','mep','prices'):text(s['source'][key],'source.'+key,300)
    for group in ('site','building','structure','finishes','systems','prices'):
        for key,value in s[group].items():
            if isinstance(template[group][key],(float,int)):
                s[group][key]=finite(value,group+'.'+key,positive=key not in ('north_degrees','foundation_bottom'))
    b=s['building'];site=s['site'];st=s['structure'];f=s['finishes'];sy=s['systems']
    if not 9000<=b['width']<=12000 or not 7000<=b['depth']<=14000:raise JobError('Current low-rise template supports width 9..12m and depth 7..14m')
    if not 100<=b['wall']<=300:raise JobError('Unsupported wall thickness')
    if not 700<=b['door_width']<=1200 or b['window_width']>b['width']*.3:raise JobError('Door/window does not fit the supported facade bays')
    if f['cabinet_length']>b['width']/2-1800-b['wall']-100:raise JobError('Kitchen cabinet intersects bathroom wall')
    b['levels']=[finite(v,'level') for v in seq(b['levels'],'levels',2,4)]
    if b['levels'][0]!=0 or any(not 2800<=c-a<=4200 for a,c in zip(b['levels'],b['levels'][1:])):raise JobError('Levels must start at zero and increase 2.8..4.2m')
    for key,maximum in [('grids_x',b['width']),('grids_y',b['depth'])]:
        b[key]=[finite(v,key) for v in seq(b[key],key,2,8)]
        if b[key][0]!=0 or b[key][-1]!=maximum or any(c-a<2000 for a,c in zip(b[key],b[key][1:])):raise JobError('Grid does not cover footprint with ordered bays >=2m')
    site['building_origin']=pt(site['building_origin']);b['stair_origin']=pt(b['stair_origin'])
    ox,oy=site['building_origin']
    if min(ox,oy)<0 or ox+b['width']>site['width'] or oy+b['depth']>site['depth']:raise JobError('Building is outside the site')
    site['survey_points']=[[finite(x,'survey coordinate') for x in seq(p,'survey XYZ',3,3)] for p in seq(site['survey_points'],'survey points',3,300)]
    if any(not 0<=x<=site['width'] or not 0<=y<=site['depth'] for x,y,z in site['survey_points']):raise JobError('Survey point outside site')
    text(site['datum'],'datum',120)
    if b['window_sill']+b['window_height']>min(c-a for a,c in zip(b['levels'],b['levels'][1:]))-st['beam_depth']:raise JobError('Window conflicts with beam zone')
    if b['stair_risers']!=int(b['stair_risers']) or int(b['stair_risers'])%2 or not 14<=b['stair_risers']<=24:raise JobError('Two-flight stair requires 14..24 even risers')
    x,y=b['stair_origin']
    if x+2*b['stair_width']+150>b['width']-b['wall'] or y+(b['stair_risers']/2-1)*b['stair_run']+b['stair_width']>b['depth']-b['wall']:raise JobError('Stair does not fit footprint')
    if st['foundation_bottom']>=-st['foundation_depth'] or st['cover']*2>=min(st['column_width'],st['beam_width']):raise JobError('Invalid foundation or reinforcement cover')
    if st['column_bars'] not in (4,8,12,16):raise JobError('Rectangular column requires 4, 8, 12 or 16 perimeter bars')
    if not 0<b['roof_slope']<=.1 or not 0<sy['drain_slope']<=.2:raise JobError('Unsupported slope')
    if f['panel']*2>=f['cabinet_depth'] or f['counter']>=f['cabinet_height']/3:raise JobError('Invalid cabinet assembly')
    if set(sy['fixtures_per_floor'])!=set(template['systems']['fixtures_per_floor']):raise JobError('Fixture schedule fields missing')
    # Fixture placements are a declared template. Counts cannot silently diverge.
    if sy['fixtures_per_floor']!=template['systems']['fixtures_per_floor']:raise JobError('Current template fixture counts are fixed; custom placement requires a new template')
    ids=set()
    for route in seq(sy['routes'],'routes',1,100):
        if set(route)!={'id','system','points','diameter'} or route['system'] not in ('water','waste','power','data','hvac'):raise JobError('Invalid route')
        if not isinstance(route['id'],str) or not IDENT_RE.fullmatch(route['id']):raise JobError('Invalid route id')
        if route['id'] in ids:raise JobError('Duplicate route id')
        ids.add(route['id']);route['diameter']=finite(route['diameter'],'diameter',positive=True)
        route['points']=[[finite(v,'route coordinate') for v in seq(p,'route XYZ',3,3)] for p in seq(route['points'],'route points',2,100)]
        if any(a==c for a,c in zip(route['points'],route['points'][1:])):raise JobError('Zero-length route')
        if any(not 0<=x<=b['width'] or not 0<=y<=b['depth'] for x,y,z in route['points']):raise JobError('Route outside building')
    if set(r['system'] for r in sy['routes'])!={'water','waste','power','data','hvac'}:raise JobError('All five route systems must be explicit')
    ids=set()
    for c in seq(sy['circuits'],'circuits',1,20):
        if set(c)!={'id','use','power_w','voltage','breaker_a','cable_mm2'}:raise JobError('Invalid circuit')
        if not isinstance(c['id'],str) or not IDENT_RE.fullmatch(c['id']):raise JobError('Invalid circuit id')
        text(c['use'],'circuit use',80)
        if c['id'] in ids:raise JobError('Duplicate circuit id')
        ids.add(c['id'])
        for k in ('power_w','voltage','breaker_a','cable_mm2'):c[k]=finite(c[k],k,positive=True)
    if ids!={'C01','C02','C03'}:raise JobError('This template requires exactly C01 lighting, C02 sockets and C03 air-conditioning')
    if not isinstance(s['reviews'],dict) or not isinstance(s['issues'],list):raise JobError('reviews/issues must be explicit')
    scope=s['estimate_scope']
    if not isinstance(scope,dict) or set(scope)!={'coverage_note','excluded_items','additional_items','scope_confirmed'}:raise JobError('Explicit estimate scope required')
    text(scope['coverage_note'],'estimate coverage',300)
    if type(scope['scope_confirmed'])is not bool:raise JobError('scope_confirmed must be boolean')
    for item in seq(scope['excluded_items'],'excluded items',0,50):text(item,'estimate exclusion',300)
    seen=set(s['prices'])
    for item in seq(scope['additional_items'],'additional estimate items',0,200):
        if not isinstance(item,dict) or set(item)!={'code','description','quantity','unit','unit_price','basis'}:raise JobError('Invalid additional estimate item')
        for k in ('code','description','unit','basis'):text(item[k],k,200)
        if item['code'] in seen:raise JobError('Duplicate estimate code')
        seen.add(item['code']);item['quantity']=finite(item['quantity'],'quantity',positive=True);item['unit_price']=finite(item['unit_price'],'price',positive=True)
    for key,review in s['reviews'].items():
        if key not in {str(i) for i in range(1,15)} or not isinstance(review,dict) or set(review)!={'reviewer','reference','input_hash'}:raise JobError('Review must identify stage, reviewer, evidence reference and input hash')
        for k in review:text(review[k],'review.'+k,300)
    for issue in s['issues']:
        if not isinstance(issue,dict) or set(issue)!={'id','stage','description','status','resolution'}:raise JobError('Issue requires id, stage, description, status, resolution')
        if type(issue['stage'])is not int or not 1<=issue['stage']<=14 or issue['status'] not in ('open','resolved'):raise JobError('Invalid issue stage/status')
        text(issue['id'],'issue id',80);text(issue['description'],'description',300)
        if issue['status']=='resolved':text(issue['resolution'],'resolution',300)
    return s

def floor_count(s):return len(s['building']['levels'])-1
def route_length(route):return sum(math.dist(a,b) for a,b in zip(route['points'],route['points'][1:]))/1000

def device_points(s,sockets=False):
    W,D=s['building']['width'],s['building']['depth']
    if sockets:return [(350,1500),(350,D-1500),(W/2-350,D-1500),(W*.62,350),(W-350,3500),(W-350,D-1000)]
    return [(W*k,D*j) for k in (.2,.7) for j in (.2,.45,.8)]

def low_voltage_points(s):
    b=s['building']
    return [('DATA1',[350,3000]),('DATA2',[350,b['depth']-800]),('CAM',[b['width']*.7,500])]

def circuit_routes(s):
    result=[]
    for sockets,circuit in [(False,'C01'),(True,'C02')]:
        nodes=device_points(s,sockets);nodes=[(500,500)]+[nodes[i] for i in (0,1,2,5,4,3)];pts=[[500,500,2600]]
        for step,(x,y) in enumerate(nodes[1:],1):
            if pts[-1][0]!=x and pts[-1][1]!=y:
                pts.append([pts[-1][0],y,2600] if sockets and step==4 else [x,pts[-1][1],2600])
            if pts[-1][:2]!=[x,y]:pts.append([x,y,2600])
        result.append({'id':circuit+'_LAYOUT','circuit':circuit,'parent':'EL01','system':'power','points':pts,'diameter':20})
    result.append({'id':'C03_LAYOUT','circuit':'C03','parent':'EL01','system':'power','points':[[500,500,2600],[500,7000,2600],[3500,7000,2600]],'diameter':20})
    return result

def service_routes(s,floor=1):
    """Explicit trunks plus template fixture branches, shared by drawing/QA/takeoff.

    Branch diameters inherit supplied inputs; this performs no hydraulic sizing.
    """
    routes=deepcopy(s['systems']['routes']);b=s['building'];W=b['width'];t=b['wall']
    fixtures=[('WC',[W-820,2600]),('BASIN',[W-1250,2400]),('SHOWER',[W-950,1100])]
    if floor==1:fixtures.append(('SINK',[W/2+t+500,675]))
    for system in ('water','waste'):
        trunks=[r for r in routes if r['system']==system and 'parent' not in r]
        for label,point in fixtures:
            best=None
            for route in trunks:
                for a,c in zip(route['points'],route['points'][1:]):
                    dx,dy=c[0]-a[0],c[1]-a[1];den=dx*dx+dy*dy
                    f=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den)) if den else 0
                    anchor=[a[i]+f*(c[i]-a[i]) for i in range(3)];dist=math.dist(point,anchor[:2])
                    if best is None or dist<best[0]:best=(dist,route,anchor)
            length,parent,anchor=best
            if length<1:continue
            start=[point[0],point[1],anchor[2]+(length*s['systems']['drain_slope'] if system=='waste' else 0)]
            routes.append({'id':parent['id']+'_'+label,'parent':parent['id'],'system':system,
                           'points':[start,anchor],'diameter':s['systems']['water_diameter'] if system=='water' else s['systems']['waste_diameter']})
    data_trunk=next(r for r in routes if r['system']=='data' and 'parent' not in r)
    for label,point in low_voltage_points(s):
        candidates=[]
        for a,c in zip(data_trunk['points'],data_trunk['points'][1:]):
            dx,dy=c[0]-a[0],c[1]-a[1];den=dx*dx+dy*dy
            f=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den)) if den else 0
            anchor=[a[i]+f*(c[i]-a[i]) for i in range(3)];candidates.append((math.dist(point,anchor[:2]),anchor))
        distance,anchor=min(candidates,key=lambda x:x[0])
        if distance<1:continue
        points=[anchor,[point[0],anchor[1],anchor[2]],[point[0],point[1],anchor[2]]]
        points=[p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
        if len(points)>1:routes.append({'id':data_trunk['id']+'_'+label,'parent':data_trunk['id'],'system':'data','points':points,'diameter':data_trunk['diameter']})
    return routes+circuit_routes(s)

def takeoff(s):
    b,st,f=s['building'],s['structure'],s['finishes'];n=floor_count(s);W,D=b['width'],b['depth'];columns=len(b['grids_x'])*len(b['grids_y'])
    # Beam length is net between column faces; columns are clear of beams.
    beam_length=(len(b['grids_y'])*(W-(len(b['grids_x'])-1)*st['column_width'])+
                 len(b['grids_x'])*(D-(len(b['grids_y'])-1)*st['column_depth']))/1000*n
    stair_opening=(2*b['stair_width']+150)*((b['stair_risers']/2-1)*b['stair_run']+b['stair_width'])/1e6
    rows=[('slab_concrete','Bê tông bản sàn, trừ ô thang',max(0,W*D/1e6-stair_opening)*st['slab_thickness']/1000*n,'m³'),
          ('column_concrete','Bê tông cột, đến đáy bản sàn',columns*st['column_width']*st['column_depth']*sum(z2-z1-st['slab_thickness'] for z1,z2 in zip(b['levels'],b['levels'][1:]))/1e9,'m³'),
          ('beam_concrete','Bê tông phần dầm dưới bản sàn',beam_length*st['beam_width']*(st['beam_depth']-st['slab_thickness'])/1e6,'m³'),
          ('foundation_concrete','Bê tông móng đơn demo',columns*st['foundation_width']**2*st['foundation_depth']/1e9,'m³'),
          ('floor_finish','Sàn hoàn thiện, trừ ô thang và vách',max(0,(W-2*b['wall'])*(D-2*b['wall'])/1e6-stair_opening-
              b['wall']*((D-2*b['wall']-b['door_width'])+(W/2-b['wall']-b['door_width'])+(3000-b['wall']-b['door_width'])+(1800-b['wall']))/1e6)*n,'m²'),
          ('roof_waterproof','Diện tích mái chiếu bằng',(W+2*b['roof_overhang'])*(D+2*b['roof_overhang'])/1e6,'m²'),
          ('cabinet','Tủ bếp',f['cabinet_length']/1000,'m'),
          ('paving','Sân lát sau khi trừ nhà và bồn cây',max(0,(s['site']['width']*s['site']['depth']-W*D)/1e6-12),'m²')]
    for system,code,label in [('water','water_pipe','Ống cấp nước'),('waste','waste_pipe','Ống thoát'),('power','power_conduit','Ống điện'),('data','data_conduit','Ống dữ liệu')]:
        rows.append((code,label,sum(route_length(r) for floor in range(1,n+1) for r in service_routes(s,floor) if r['system']==system),'m'))
    for key,field in [('light','lights'),('socket','sockets'),('wc','wc'),('basin','basin')]:rows.append((key,field,s['systems']['fixtures_per_floor'][field]*n,'cái'))
    result=[{'code':code,'description':label,'quantity':round(q,6),'unit':unit,'unit_price':s['prices'][code],
             'amount':round(q*s['prices'][code],2),'basis':'MODELED_SCOPE_ONLY'} for code,label,q,unit in rows]
    for row in result:
        if row['code'] in ('power_conduit','data_conduit'):row['basis']='MODELED_ROUTES_SEPARATE_CONDUITS'
    for item in s['estimate_scope']['additional_items']:result.append({**item,'amount':round(item['quantity']*item['unit_price'],2)})
    return result
