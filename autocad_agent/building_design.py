"""Detailed drawing library for the fourteen-stage low-rise demonstration.

Drawings share one model. Values are supplied inputs, not engineering calculations.
"""
import math
from .building_model import normalize,example,floor_count,takeoff,service_routes,device_points,circuit_routes,low_voltage_points
from .fitout_design import Builder
from .project_workflow import stage_hash,check_project,STAGES
from .qa import geometry_report

SCALES=(1,2,5,7.5,10,15,20,25,30,40,50,75,100,125,150,200)

def choose(bounds,w=226,h=239):
    x,y,X,Y=bounds
    return next(v for v in SCALES if v>=max((X-x)/w,(Y-y)/h))

def grids(p,s):
    b=s['building'];W,D=b['width'],b['depth']
    for i,x in enumerate(b['grids_x']):
        p.line((x,-550),(x,D+550),'A-GRID');p.tag(str(i+1),x,D+600,3)
    for i,y in enumerate(b['grids_y']):
        p.line((-550,y),(W+550,y),'A-GRID');p.tag(chr(65+i),-650,y,3)
    p.dim((0,0),(W,0),(W/2,-950));p.dim((0,0),(0,D),(-1100,D/2))
    for a,c in zip(b['grids_x'],b['grids_x'][1:]):p.dim((a,0),(c,0),((a+c)/2,-550))
    for a,c in zip(b['grids_y'],b['grids_y'][1:]):p.dim((0,a),(0,c),(-550,(a+c)/2))

def level_mark(p,x,y,label):
    d=2*p.scale;p.poly([(x-d,y+d),(x+d,y+d),(x,y)],'A-LEVEL',True)
    p.line((x,y),(x+8*p.scale,y),'A-LEVEL');p.text(label,x+9*p.scale,y+15,paper=2)

def stair_plan(p,s):
    b=s['building'];x,y=b['stair_origin'];w=b['stair_width'];n=int(b['stair_risers']/2);run=b['stair_run'];depth=(n-1)*run+w
    p.rect(x,y,2*w+150,depth,'A-STAIR')
    for j in range(n):
        p.line((x,y+j*run),(x+w,y+j*run),'A-STAIR');p.line((x+w+150,y+j*run),(x+2*w+150,y+j*run),'A-STAIR')
    p.poly([(x+w/2,y+150),(x+w/2,y+depth-w/2),(x+1.5*w+150,y+depth-w/2),(x+1.5*w+150,y+150)],'A-STAIR')
    p.text('UP',x+100,y+350,paper=2);p.text('DN',x+w+250,y+350,paper=2)

def plan_base(p,s,floor=1,furniture=False,dim=True,references=True):
    if 'partitions' in s.get('extensions',{}):
        from .building_extensions import draw_custom_plan
        draw_custom_plan(p,s,floor,furniture);stair_plan(p,s)
        if dim:grids(p,s)
        return
    b=s['building'];W,D,t=b['width'],b['depth'],b['wall'];dw=b['door_width'];ww=b['window_width'];fw=dw if floor==1 else ww;dx=W*.25-fw/2;wx=W*.70-ww/2;wx2=W*.25-ww/2;middoor=W*.25-dw/2
    from .spatial_rules import resolve_openings,cut_walls,draw_opening
    walls,ops,issues=resolve_openings(s,floor)
    for x,y,w,h in cut_walls(walls,ops):
        if w>0 and h>0:p.rect(x,y,w,h,'A-WALL');p.hatch(x,y,w,h,'ANSI31',8)
    for op in ops:draw_opening(p,op)
    stair_plan(p,s)
    labels=[('KHÁCH / SINH HOẠT',W*.16,D*.25),('BẾP / ĂN',W*.58,D*.25)] if floor==1 else [
            ('PHÒNG NGỦ 1',W*.29,D*.2),('PHÒNG NGỦ 2',W*.58,D*.4)]
    labels.append(('PHÒNG NGỦ',W*.28,D*.8))
    from .annotation_rules import place_room_labels
    place_room_labels(p,s,floor,[{'name':label,'position':[x,y]} for label,x,y in labels])
    p.mtext('WC',W-700,1800,450,2)
    if 'fixtures' in s.get('extensions',{}):
        from .building_extensions import placed
        for item in placed(s,'fixtures',floor):
            x,y=item['position']
            if item['kind']=='wc':p.toilet(x,y)
            elif item['kind']=='basin':p.basin(x,y,500,400)
            else:p.rect(x-450,y-450,900,900,'P-FIXTURE')
    else:p.toilet(W-1000,2600);p.basin(W-1500,2200,500,400);p.rect(W-1400,350,900,900,'P-FIXTURE')
    if furniture:
        if floor==1:
            p.furniture(500,600,800,2000,'sofa');p.rect(1700,2800,1100,600,'A-FURNITURE')
        else:p.furniture(500,600,1600,2000,'bed')
        p.furniture(500,D-2600,1600,2000,'bed');p.furniture(W/2-850,D-2400,600,1800,'wardrobe')
        if floor==1:
            f=s['finishes'];kx=W/2+t+100;p.rect(kx,400,f['cabinet_length'],f['cabinet_depth'],'A-JOINERY')
            p.basin(kx+150,450,500,450);p.rect(kx+f['cabinet_length']-600,450,500,450,'A-APPLIANCE')
            p.rect(W*.55,2400,1400,750,'A-FURNITURE')
        else:p.furniture(W/2+t,600,1600,2000,'bed')
    p.tag('D1' if floor==1 else 'W1',dx+fw/2,650,3);p.tag('W1',wx+ww/2,D-650,3)
    if references:
        p.tag('1',W*.38,D*.35,4);p.text('AR-201',W*.38-150,D*.35-400,paper=1.8)
        cutx=b['stair_origin'][0]+b['stair_width']/2
        p.line((cutx,-250),(cutx,D+250),'A-CENTER-SECTION')
        p.tag('A',cutx,D+650,4);p.text('AR-301',cutx-150,D+1050,paper=1.8)
    if dim:grids(p,s)

def note_panel(builder,rows):
    p=builder.panel((100000,0),1)
    p.table('GHI CHÚ / THAM CHIẾU',['MÃ','NỘI DUNG'],rows,0,110,[13,69],paper=1.9,row=11)
    builder.view('GHI CHÚ & THÔNG SỐ',[247,157,85,118],[100000,-4,100082,112],1)

def default_detail(p,s):
    b=s['building'];t=b['wall'];f=s['finishes'];st=s['structure']
    p.rect(0,0,t,400,'A-WALL');p.hatch(0,0,t,400,'ANSI31',4)
    p.rect(t,-f['tile'],450,f['tile'],'A-FINISH');p.rect(t,-f['tile']-f['screed'],450,f['screed'],'A-FINISH')
    p.rect(t,-f['tile']-f['screed']-st['slab_thickness'],450,st['slab_thickness'],'S-CONCRETE')
    p.hatch(t,-f['tile']-f['screed']-st['slab_thickness'],450,st['slab_thickness'],'AR-CONC',1)
    p.dim((0,0),(t,0),(t/2,460))
    p.leader([(t+200,-f['tile']/2),(t+300,180),(t+410,180)],f"Sàn {f['tile']:g} / vữa {f['screed']:g}",400,2)

def add_sheet(s,items,stage,role,code,title,bounds,draw,notes=None,detail=None,floor=None,refs=()):
    scale=choose(bounds)
    for attempt in range(8):
        builder=Builder(code,title,scale);draw(builder.panel())
        measured=geometry_report(builder.job())['bounds']
        actual=[min(bounds[0],measured[0])-scale,min(bounds[1],measured[1])-scale,
                max(bounds[2],measured[2])+scale,max(bounds[3],measured[3])+scale]
        fitted=choose(actual)
        if fitted==scale:break
        scale=fitted
    else:raise ValueError('Drawing cannot fit with readable annotations')
    builder.view(title,[14,33,228,241],actual,scale)
    main_ids=[e['id'] for e in builder.geometry]
    rows=(notes or [])+[['SRC','DEMO / kiểm tra dữ liệu trước thi công' if s['mode']=='demo' else 'Theo đầu vào dự án; chờ kiểm duyệt'],
                       ['REV',s['revision']],['REF',', '.join(refs) or 'QA-102 / danh mục hồ sơ']]
    if len(rows)>8:raise ValueError('Too many sheet notes')
    note_panel(builder,rows)
    detail=detail or {1:survey_detail,2:setting_detail,5:eaves_detail,8:plumbing_detail,
                      9:electrical_detail,10:hvac_detail,11:cabinet_detail,12:paving_detail,
                      13:quantity_detail,14:coordination_detail}.get(stage,default_detail)
    detail_scale=10
    for attempt in range(8):
        temp=Builder('DETAIL','DETAIL',detail_scale);detail(temp.panel(),s)
        box=geometry_report(temp.job())['bounds'];detail_bounds=[box[0]-detail_scale,box[1]-detail_scale,box[2]+detail_scale,box[3]+detail_scale]
        fitted=choose(detail_bounds,83,108)
        if fitted==detail_scale:break
        detail_scale=fitted
    else:raise ValueError('Detail cannot fit')
    q=builder.panel((200000,0),detail_scale);detail(q,s)
    builder.view('CHI TIẾT / THÔNG SỐ BỔ SUNG',[247,33,85,110],
                 [200000+detail_bounds[0],detail_bounds[1],200000+detail_bounds[2],detail_bounds[3]],detail_scale)
    job=builder.job()
    discipline={1:'civil',2:'civil',7:'structural',8:'plumbing',9:'electrical',10:'mep',12:'civil'}.get(stage,'architectural')
    job['discipline']=discipline
    items.append({'code':code,'title':title,'stage':stage,'role':role,'floor':floor,'job':job,'views':builder.views,'spatial_label_issues':getattr(builder,'spatial_label_issues',[]),
                  'main_entity_ids':main_ids,'references':list(refs),'input_hash':stage_hash(s,stage),'required_features':['table','dim_aligned','leader']+(['hatch'] if stage not in (8,9,10) else [])})

def site_plan(p,s,survey=False,landscape=False,grading=False):
    a,b=s['site'],s['building'];W,D=a['width'],a['depth'];ox,oy=a['building_origin']
    p.rect(0,0,W,D,'C-BOUNDARY');p.rect(ox,oy,b['width'],b['depth'],'A-BUILDING')
    p.rect(0,-a['road_width'],W,a['road_width'],'C-ROAD');p.text('ĐƯỜNG HIỆN HỮU / DEMO',1000,-a['road_width']/2)
    pool=s.get('extensions',{}).get('pool')
    if pool:
        x,y=pool['origin'];p.rect(x,y,pool['width'],pool['depth'],'L-POOL')
        p.hatch(x,y,pool['width'],pool['depth'],'ANSI37',100);p.text('HỒ BƠI / CHỜ THIẾT KẾ KỸ THUẬT',x+200,y+pool['depth']/2,paper=1.8)
    p.dim((0,0),(W,0),(W/2,-1200));p.dim((0,0),(0,D),(-1600,D/2))
    p.dim((0,oy),(ox,oy),(ox/2,oy-600));p.dim((ox,0),(ox,oy),(ox-700,oy/2))
    angle=math.radians(a['north_degrees']);x,y=W-1800,D-1800
    p.line((x,y),(x+1400*math.sin(angle),y+1400*math.cos(angle)),'C-NORTH');p.text('N',x-150,y+1500)
    for i,(x,y,z) in enumerate(a['survey_points'],1):
        p.circle(x,y,70,'C-SURVEY');p.text(f'P{i} / {z/1000:+.3f}',x+100,y+200,paper=1.8)
    if survey:
        for i in range(len(a['survey_points'])):
            x,y,z=a['survey_points'][i];X,Y,Z=a['survey_points'][(i+1)%len(a['survey_points'])]
            p.line((x,y),(X,Y),'C-SURVEY')
    if landscape:
        for x,y in [(1000,3000),(1000,8000),(W-1000,3500),(W-1000,D-2000)]:
            obstacles=[(ox,oy,b['width'],b['depth'])]+([(*pool['origin'],pool['width'],pool['depth'])] if pool else [])
            if any(X-600<x<X+w+600 and Y-600<y<Y+h+600 for X,Y,w,h in obstacles):continue
            p.circle(x,y,600,'L-TREE');p.circle(x,y,90,'L-TREE')
        p.rect(1000,D-2500,6000,2000,'L-PLANTING');p.hatch(1000,D-2500,6000,2000,'EARTH',30)
        p.rect(ox+1000,0,2000,oy,'C-PAVING')
    if grading:
        for x in (1000,W-1000):
            p.line((x,D-1500),(x,1500),'C-DRAIN');p.line((x,1500),(x-300,1900),'C-DRAIN');p.line((x,1500),(x+300,1900),'C-DRAIN')
            p.text('DỐC THEO CAO ĐỘ CHỐT',x+200,D/2,paper=1.8)
        for x,y in [(1500,1500),(W-1500,1500)]:p.rect(x,y,600,600,'C-CHAMBER');p.tag('MH',x+300,y+1000,3)

def elevation(p,s,rear=False):
    if 'partitions' in s.get('extensions',{}):
        from .building_extensions import draw_custom_elevation
        draw_custom_elevation(p,s,rear=rear);return
    b=s['building'];W=b['width'];roof=b['levels'][-1];ww=b['window_width'];ws=b['window_sill'];wh=b['window_height']
    p.rect(0,0,W,roof,'A-ELEVATION')
    for i,z in enumerate(b['levels'][:-1]):
        p.rect(0,z,W,150,'A-FLOOR');p.rect(W*.70-ww/2,z+ws,ww,wh,'A-WINDOW');p.line((W*.7,z+ws),(W*.7,z+ws+wh),'A-WINDOW')
        if i or rear:p.rect(W*.25-ww/2,z+ws,ww,wh,'A-WINDOW')
        else:p.rect(W*.25-b['door_width']/2,0,b['door_width'],b['door_height'],'A-DOOR')
        level_mark(p,W+300,z,f'{z/1000:+.3f}')
    if s.get('extensions',{}).get('roof_type')=='hip':
        from .building_extensions import draw_hip_elevation
        draw_hip_elevation(p,s)
    else:p.rect(-b['roof_overhang'],roof,W+2*b['roof_overhang'],150,'A-ROOF');p.rect(0,roof,W,b['parapet_height'],'A-PARAPET')
    p.dim((0,0),(W,0),(W/2,-500));p.dim((0,0),(0,roof),(-600,roof/2))
    p.leader([(W*.8,roof*.55),(W+300,roof*.65),(W+700,roof*.65)],'W02 / sơn ngoại thất\nTheo bảng vật liệu',1200)

def section(p,s):
    b,st=s['building'],s['structure'];D=b['depth'];roof=b['levels'][-1];t=b['wall']
    for x in (0,D-t):p.rect(x,0,t,roof,'A-WALL');p.hatch(x,0,t,roof,'ANSI31',10)
    for i,z in enumerate(b['levels']):
        p.rect(0,z-st['slab_thickness'],D,st['slab_thickness'],'S-SLAB');p.hatch(0,z-st['slab_thickness'],D,st['slab_thickness'],'AR-CONC',10)
        for y in b['grids_y']:p.rect(y-st['beam_width']/2,z-st['beam_depth'],st['beam_width'],st['beam_depth'],'S-BEAM')
        level_mark(p,D+250,z,f'{z/1000:+.3f}')
        if i<len(b['levels'])-1:
            h=b['levels'][i+1]-z;r=h/b['stair_risers'];run=b['stair_run'];sx=b['stair_origin'][1]
            pts=[(sx,z)]
            for j in range(int(b['stair_risers']/2)):pts.extend([(sx+j*run,z+(j+1)*r),(sx+(j+1)*run,z+(j+1)*r)])
            p.poly(pts,'A-STAIR');p.line((sx,z-120),(sx+run*b['stair_risers']/2,z+h/2-120),'S-STAIR')
            back=[(sx+run*b['stair_risers']/2,z+h/2)]
            for j in range(int(b['stair_risers']/2)):back.extend([(sx+(b['stair_risers']/2-j)*run,z+h/2+(j+1)*r),(sx+(b['stair_risers']/2-j-1)*run,z+h/2+(j+1)*r)])
            p.poly(back,'A-STAIR');p.line((sx+run*b['stair_risers']/2,z+h/2-120),(sx,z+h-120),'S-STAIR')
            p.line((t,z+h-s['finishes']['ceiling_drop']),(D-t,z+h-s['finishes']['ceiling_drop']),'A-CEILING')
    if s.get('extensions',{}).get('roof_type')=='hip':
        from .building_extensions import draw_hip_elevation
        draw_hip_elevation(p,s,True)
    p.dim((0,0),(D,0),(D/2,-550));p.dim((0,0),(0,roof),(-600,roof/2))
    p.leader([(D*.6,roof-st['slab_thickness']/2),(D+300,roof+400),(D+650,roof+400)],f"Sàn BTCT {st['slab_thickness']:g} mm",1200)

def roof_plan(p,s):
    if s.get('extensions',{}).get('roof_type')=='hip':
        from .building_extensions import draw_hip_plan
        draw_hip_plan(p,s);grids(p,s);return
    b=s['building'];W,D,o=b['width'],b['depth'],b['roof_overhang']
    p.rect(-o,-o,W+2*o,D+2*o,'A-ROOF');p.rect(0,0,W,D,'A-PARAPET')
    p.hatch(0,0,W,D,'ANSI37',80)
    for x in (W*.25,W*.75):
        p.line((x,D*.8),(x,D*.2),'P-DRAIN');p.line((x,D*.2),(x-200,D*.2+300),'P-DRAIN');p.line((x,D*.2),(x+200,D*.2+300),'P-DRAIN')
        p.text(f"DỐC {b['roof_slope']*100:g}%",x+200,D*.5,paper=2)
        p.circle(x,450,80,'P-DRAIN');p.tag('RD',x,900,3)
    grids(p,s);p.leader([(W-100,D-100),(W+300,D+200),(W+500,D+200)],'Chi tiết sê nô / AR-504',1200)

def stair_detail(p,s):
    b=s['building'];rise=(b['levels'][1]-b['levels'][0])/b['stair_risers'];run=b['stair_run'];pts=[(0,0)]
    for j in range(6):pts.extend([(j*run,(j+1)*rise),((j+1)*run,(j+1)*rise)])
    p.poly(pts,'A-STAIR');p.line((0,-120),(6*run,6*rise-120),'S-STAIR')
    for j in range(6):p.line((j*run+30,(j+1)*rise+20),((j+1)*run-20,(j+1)*rise+20),'A-FINISH')
    p.line((0,900),(6*run,6*rise+900),'A-RAIL')
    for j in (0,2,4,6):p.line((j*run,j*rise),(j*run,j*rise+900),'A-RAIL')
    p.dim((0,rise),(run,rise),(run/2,-180));p.dim((0,0),(0,rise),(-180,rise/2))
    p.leader([(3*run,3*rise-80),(1700,300),(1900,300)],'Bản thang / cốt thép theo ST-203',1100)

def openings(p,s):
    b=s['building'];w,h=b['door_width'],b['door_height'];ww,wh=b['window_width'],b['window_height']
    p.rect(0,0,w,h,'A-DOOR');p.rect(40,40,w-80,h-80,'A-DOOR');p.circle(w-100,1000,20,'A-HARDWARE')
    p.rect(w+600,b['window_sill'],ww,wh,'A-WINDOW');p.line((w+600+ww/2,b['window_sill']),(w+600+ww/2,b['window_sill']+wh),'A-WINDOW')
    p.dim((0,0),(w,0),(w/2,-200));p.dim((0,0),(0,h),(-220,h/2))
    p.dim((w+600,0),(w+600+ww,0),(w+600+ww/2,-200))
    p.leader([(w-40,h-40),(w+200,h+200),(w+500,h+200)],'D1 / khung, cánh, gioăng\nDuyệt mẫu phụ kiện',1200)

def wet_detail(p,s):
    f,st=s['finishes'],s['structure'];t=f['tile'];sc=f['screed'];sl=st['slab_thickness'];wp=f['waterproofing']
    p.rect(0,-sl-sc-t,1600,sl,'S-SLAB');p.hatch(0,-sl-sc-t,1600,sl,'AR-CONC',2)
    p.rect(0,-sc-t,1600,sc,'A-SCREED');p.hatch(0,-sc-t,1600,sc,'AR-SAND',2)
    p.rect(0,-t,1600,t,'A-FINISH');p.rect(0,-t-wp,1600,wp,'A-WATERPROOF')
    p.rect(0,0,150,450,'A-WALL');p.poly([(150,200),(150,-t-wp),(1600,-t-wp)],'A-WATERPROOF')
    p.rect(1100,-sl-sc-t-200,110,sl+sc+t+200,'P-DRAIN');p.rect(1060,-30,190,30,'P-FIXTURE')
    p.dim((0,0),(150,0),(75,550));p.dim((1600,-sc-t),(1600,0),(1750,-(sc+t)/2))
    p.leader([(800,-t-wp),(1700,200),(1900,200)],f"Chống thấm {wp:g} mm / bo góc",1000)
    p.leader([(1155,-200),(1700,-350),(1900,-350)],f"Ống thoát Ø{s['systems']['waste_diameter']:g}",1000)

def eaves_detail(p,s):
    b,f,st=s['building'],s['finishes'],s['structure'];o=b['roof_overhang'];sl=st['slab_thickness']
    if s.get('extensions',{}).get('roof_type')=='hip':
        slope=b['roof_slope'];x0=-o;x1=1400;y0=0;y1=(x1-x0)*slope
        p.poly([(x0,y0),(x1,y1),(x1,y1-sl),(x0,y0-sl)],'S-ROOF',True)
        p.rect(0,-st['beam_depth'],st['beam_width'],st['beam_depth'],'S-BEAM');p.hatch(0,-st['beam_depth'],st['beam_width'],st['beam_depth'],'AR-CONC',3)
        for offset,layer in [(f['screed'],'A-SCREED'),(f['screed']+f['waterproofing'],'A-WATERPROOF'),(f['screed']+f['waterproofing']+f['tile'],'A-FINISH')]:p.line((x0,offset),(x1,y1+offset),layer)
        p.dim((x0,0),(0,0),(x0/2,-st['beam_depth']-250))
        for i,(label,offset) in enumerate([('Lớp lợp / vật liệu chờ chốt',f['screed']+f['waterproofing']+f['tile']),('Chống thấm / lớp nền theo đầu vào',f['screed']),('Bản / dầm mái theo tính toán',-sl)]):
            p.leader([(700,(700-x0)*slope+offset),(1600,1000-i*400),(1850,1000-i*400)],label,1500,2)
        return
    p.rect(-o,-sl,1400,sl,'S-SLAB');p.hatch(-o,-sl,1400,sl,'AR-CONC',2)
    p.rect(0,0,b['wall'],b['parapet_height'],'A-PARAPET');p.hatch(0,0,b['wall'],b['parapet_height'],'ANSI31',4)
    p.rect(150,0,900,f['screed'],'A-SCREED');p.poly([(150,200),(150,f['screed']),(1050,f['screed'])],'A-WATERPROOF')
    p.rect(-20,b['parapet_height'],b['wall']+40,30,'A-COPING')
    p.dim((-o,0),(0,0),(-o/2,-300));p.dim((0,0),(0,b['parapet_height']),(-600,b['parapet_height']/2))
    p.leader([(800,30),(1200,450),(1450,450)],f"Lớp tạo dốc {b['roof_slope']*100:g}% / chống thấm",1000)

def structure_plan(p,s,foundation=False):
    b,st=s['building'],s['structure'];grids(p,s);W,D=b['width'],b['depth']
    for x in b['grids_x']:
        for y in b['grids_y']:
            if foundation:
                fw=st['foundation_width'];p.rect(x-fw/2,y-fw/2,fw,fw,'S-FOOTING');p.hatch(x-fw/2,y-fw/2,fw,fw,'AR-CONC',25)
            p.rect(x-st['column_width']/2,y-st['column_depth']/2,st['column_width'],st['column_depth'],'S-COLUMN')
            p.tag('F1' if foundation else 'C1',x+350,y+400,3)
    for y in b['grids_y']:p.rect(0,y-st['beam_width']/2,W,st['beam_width'],'S-BEAM')
    for x in b['grids_x']:p.rect(x-st['beam_width']/2,0,st['beam_width'],D,'S-BEAM')
    if not foundation:
        stair_plan(p,s);p.mtext(f"S1 / bản {st['slab_thickness']:g} mm\nÔ thang: không đổ sàn",W*.2,D*.35,2200,2.2)
        lift=s.get('extensions',{}).get('elevator')
        if lift:
            x,y=lift['origin'];p.rect(x,y,lift['width'],lift['depth'],'S-OPENING')
            p.leader([(x,y),(x+500,y-500),(x+900,y-500)],'Ô CHỜ THANG MÁY\nDầm viền / pit theo NCC và kỹ sư',2000,2)

def footing_detail(p,s):
    st=s['structure'];fw,fd,cover=st['foundation_width'],st['foundation_depth'],st['cover'];bottom=st['foundation_bottom'];cw=st['column_width']
    p.rect(0,bottom,fw,fd,'S-CONCRETE');p.hatch(0,bottom,fw,fd,'AR-CONC',5)
    p.rect(-100,bottom-st['blinding'],fw+200,st['blinding'],'S-BLINDING');p.hatch(-100,bottom-st['blinding'],fw+200,st['blinding'],'AR-SAND',3)
    p.rect(fw/2-cw/2,bottom+fd,cw,-bottom-fd+500,'S-COLUMN')
    p.poly([(cover,bottom+cover+100),(cover,bottom+cover),(fw-cover,bottom+cover),(fw-cover,bottom+cover+100)],'S-REBAR')
    count=math.floor((fw-2*cover)/st['footing_bar_spacing'])+1
    for i in range(count):p.circle(cover+i*(fw-2*cover)/(count-1),bottom+cover+20,st['footing_bar_diameter']/2,'S-REBAR')
    p.dim((0,bottom),(fw,bottom),(fw/2,bottom-300));p.dim((fw,bottom),(fw,bottom+fd),(fw+200,bottom+fd/2))
    p.leader([(fw*.7,bottom+cover),(fw+300,bottom+fd+200),(fw+600,bottom+fd+200)],f"Ø{st['footing_bar_diameter']:g}a{st['footing_bar_spacing']:g}\nCover {cover:g}; dữ liệu kỹ sư",1000)
    level_mark(p,fw+200,bottom,f'{bottom/1000:+.3f}')

def rebar_section(p,s):
    st=s['structure'];w,h,c=st['beam_width'],st['beam_depth'],st['cover'];d=st['main_bar_diameter'];sd=st['stirrup_diameter']
    p.rect(0,0,w,h,'S-CONCRETE');p.hatch(0,0,w,h,'AR-CONC',2)
    p.rect(c,c,w-2*c,h-2*c,'S-REBAR')
    for x,y in [(c+d/2,c+d/2),(w-c-d/2,c+d/2),(c+d/2,h-c-d/2),(w-c-d/2,h-c-d/2)]:p.circle(x,y,d/2,'S-REBAR')
    p.dim((0,0),(w,0),(w/2,-120));p.dim((w,0),(w,h),(w+100,h/2))
    p.leader([(w-c,h/2),(400,400),(550,400)],f"Đai Ø{sd:g}a{st['stirrup_spacing']:g}",600)
    p.leader([(w-c-d/2,c+d/2),(400,120),(550,120)],f"4Ø{d:g} / DEMO\nNeo/nối theo tính toán",600)
    x=1100;cw,cd=st['column_width'],st['column_depth'];p.rect(x,0,cw,cd,'S-COLUMN');p.rect(x+c,c,cw-2*c,cd-2*c,'S-REBAR')
    n=int(st['column_bars']);pts=[]
    for i in range(n):
        a=2*math.pi*i/n;xx=x+cw/2+(cw/2-c-d/2)*math.cos(a);yy=cd/2+(cd/2-c-d/2)*math.sin(a);p.circle(xx,yy,d/2,'S-REBAR')
    p.text(f"C1 / {n}Ø{d:g}",x,cd+100,paper=2)

def slab_detail(p,s):
    st=s['structure'];sl,c=st['slab_thickness'],st['cover']
    p.rect(0,0,2200,sl,'S-SLAB');p.hatch(0,0,2200,sl,'AR-CONC',3)
    p.rect(0,-st['beam_depth']+sl,st['beam_width'],st['beam_depth'],'S-BEAM')
    p.line((c,c),(2200-c,c),'S-REBAR');p.line((c,sl-c),(700,sl-c),'S-REBAR')
    for x in range(150,2100,150):p.circle(x,c+10,4,'S-REBAR')
    p.dim((2200,0),(2200,sl),(2400,sl/2));p.dim((0,0),(2200,0),(1100,-500))
    p.leader([(1000,c),(2300,400),(2500,400)],'Thép bản, neo/nối theo hồ sơ tính\nKhông suy ra từ sơ đồ demo',1200)

def route_plan(p,s,system,floor,architectural_references=True):
    plan_base(p,s,floor,False,False,references=architectural_references)
    layers={'water':'P-WATER','waste':'P-WASTE','power':'E-POWER','data':'E-DATA','hvac':'M-HVAC'}
    junctions=set()
    for route in service_routes(s,floor):
        if route['system']==system:
            points=[]
            for x,y,z in route['points']:
                if not points or points[-1]!=(x,y):points.append((x,y))
            x,y=points[-1]
            if len(points)>1:p.poly(points,layers[system])
            else:p.circle(x,y,max(40,route['diameter']/2),layers[system])
            if route.get('parent'):
                if (x,y) not in junctions:p.circle(x,y,25,layers[system]);junctions.add((x,y))
                continue
            if system=='hvac':
                for a,c in zip(points,points[1:]):
                    length=math.dist(a,c);dx=-(c[1]-a[1])/length*route['diameter']/2;dy=(c[0]-a[0])/length*route['diameter']/2
                    for sign in (-1,1):p.line((a[0]+sign*dx,a[1]+sign*dy),(c[0]+sign*dx,c[1]+sign*dy),layers[system])
                if 'devices' not in s.get('extensions',{}):p.rect(points[0][0]-300,points[0][1]-150,600,300,'M-EQUIP');p.rect(x-450,y-150,900,300,'M-EQUIP')
            p.tag(route['id'],2000 if system=='data' else x-350,3100 if system=='data' else y+400,4)
            leader_points=[(x,y),(2700,3500),(3000,3500)] if system=='data' else [(x,y),(x-700,y-500),(x-1000,y-500)]
            p.leader(leader_points,f"{route['id']} / Ø{route['diameter']:g}\nZ {route['points'][-1][2]:g} mm so với tầng",1800,2)
    if system=='hvac':
        from .building_extensions import placed
        for item in placed(s,'devices',floor):
            if item['kind']=='ac':
                x,y=item['position'];p.rect(x-450,y-150,900,300,'M-EQUIP')
    grids(p,s)

def lights_plan(p,s,floor,sockets=False):
    plan_base(p,s,floor,False,False);b=s['building'];W,D=b['width'],b['depth']
    points=device_points(s,sockets,floor)
    for i,(x,y) in enumerate(points,1):
        if sockets:p.rect(x-90,y-60,180,120,'E-SOCKET');p.text(f'S{i}',x+160,y+50,paper=1.7)
        else:p.circle(x,y,80,'E-LIGHT');p.line((x-120,y),(x+120,y),'E-LIGHT');p.line((x,y-120),(x,y+120),'E-LIGHT')
    for route in circuit_routes(s,floor):
        if route['circuit']==('C02' if sockets else 'C01') or sockets and route['circuit']=='C03':p.poly([(x,y) for x,y,z in route['points']],'E-CIRCUIT')
    if sockets:
        for route in service_routes(s,floor):
            if route['system']=='power' and not route.get('parent'):p.poly([(x,y) for x,y,z in route['points']],'E-FEEDER')
    p.rect(300,300,450,180,'E-PANEL');p.tag('DB',550,950,3)
    for x in (W*.2,W*.7):p.dim((x,D*.2),(x,D*.8),(x-450,D*.5))
    # Circuit identities are given in the sheet legend and single-line diagram;
    # an inline caption here would cover the nearby DB symbol on this template.
    grids(p,s)

def riser(p,s):
    b=s['building'];sy=s['systems'];roof=b['levels'][-1]
    for x,diam,label in [(800,sy['water_diameter'],'CW'),(2600,sy['waste_diameter'],'SW')]:
        p.line((x,-800),(x,roof+1000),'P-RISER');p.text(f'{label} Ø{diam:g}',x-250,roof+1200)
        for z in b['levels'][:-1]:
            p.line((x,z+500),(x+1000,z+500),'P-BRANCH');p.circle(x+700,z+500,55,'P-VALVE')
            level_mark(p,x+1300,z,f'{z/1000:+.3f}')
    p.poly([(2600,roof+1000),(3000,roof+1000),(3000,roof+800)],'P-VENT')
    p.dim((800,0),(2600,0),(1700,-1100));p.dim((0,0),(0,roof),(-300,roof/2))
    p.leader([(2600,roof+500),(3300,roof+800),(3700,roof+800)],'Ống thông hơi / phối hợp mái',1600)

def plumbing_detail(p,s):
    sy=s['systems'];p.rect(0,0,600,900,'P-EQUIP');p.circle(300,500,160,'P-PUMP')
    p.poly([(300,-200),(300,0),(300,900),(300,1250),(1600,1250)],'P-WATER')
    for x in (700,1100):p.circle(x,1250,55,'P-VALVE')
    p.poly([(900,0),(900,-150),(1200,-150),(1200,-400),(1600,-400)],'P-WASTE')
    p.dim((0,0),(600,0),(300,-550));p.dim((600,0),(600,900),(750,450))
    p.leader([(1100,1250),(1700,1450),(1900,1450)],f"Van / đồng hồ / Ø{sy['water_diameter']:g}\nÁp lực đầu vào {sy['water_pressure_kpa']:g} kPa",1500)

def single_line(p,s):
    circuits=s['systems']['circuits'];p.rect(0,1400,700,500,'E-PANEL');p.text('DB / NGUỒN',40,1600)
    p.line((350,1400),(350,1100),'E-CABLE');p.line((350,1100),(len(circuits)*1600,1100),'E-BUSBAR')
    for i,c in enumerate(circuits,1):
        x=i*1500;p.line((x,1100),(x,200),'E-CABLE');p.rect(x-100,650,200,180,'E-BREAKER')
        p.mtext(f"{c['id']} / {c['use']}\n{c['power_w']:g} W / {c['voltage']:g} V\nCB {c['breaker_a']:g} A\nCáp {c['cable_mm2']:g} mm²",x-450,0,1200,2)
    p.dim((0,1100),(len(circuits)*1500,1100),(len(circuits)*750,2200))
    p.leader([(700,1900),(1000,2300),(1200,2300)],'Sơ đồ theo thông số được cấp\nKhông tự chọn CB hoặc tiết diện',1600)

def earth_detail(p,s):
    p.line((-300,0),(2300,0),'C-GROUND')
    for x in (0,900,1800):p.rect(x,-1800,16,1800,'E-EARTH');p.circle(x,50,35,'E-CLAMP')
    p.line((0,-150),(1800,-150),'E-EARTH');p.rect(600,-200,600,350,'C-CHAMBER')
    p.dim((0,0),(900,0),(450,450));p.dim((0,0),(0,-1800),(-500,-900))
    p.leader([(1800,-150),(2400,300),(2700,300)],f"Mạng tiếp địa DEMO\nMục tiêu R ≤ {s['systems']['earthing_resistance_target_ohm']:g} Ω; phải đo",1600)

def low_voltage(p,s,floor):
    route_plan(p,s,'data',floor,False);b=s['building'];W,D=b['width'],b['depth']
    for label,(x,y) in low_voltage_points(s,floor):
        if not label.startswith('CAM'):p.rect(x,y,180,150,'E-DATA');p.tag(label,x+300,y+450,4)
        else:p.rect(x,y,300,180,'E-CCTV');p.arc(x+150,y,900,30,150,'E-CCTV')
    p.leader([(W*.7,500),(W-1200,D*.47),(W-1500,D*.47)],'CAM / vùng nhìn minh họa\nPhối hợp nguồn, mạng và góc lắp',2200,1.8)

def hvac_detail(p,s):
    f=s['finishes'];p.rect(0,0,150,700,'A-WALL');p.hatch(0,0,150,700,'ANSI31',5)
    p.rect(150,300,850,300,'M-INDOOR');p.line((150,700-f['ceiling_drop']),(1400,700-f['ceiling_drop']),'A-CEILING')
    p.poly([(700,300),(700,100),(1300,80)],'M-CONDENSATE');p.circle(150,450,45,'M-SLEEVE')
    p.dim((150,300),(1000,300),(575,100));p.dim((150,300),(150,600),(-100,450))
    p.leader([(1300,80),(1500,300),(1750,300)],'Thoát ngưng / cách nhiệt\nCông suất và cỡ ống theo tính tải',1200)

def joinery(p,s):
    f=s['finishes'];L,H,d,top=f['cabinet_length'],f['cabinet_height'],f['panel'],f['counter']
    p.rect(0,0,L,H,'A-JOINERY');p.rect(0,H-top,L,top,'A-COUNTER');p.hatch(0,100,L,H-top-100,'ANSI37',12)
    for j in (1,2):p.line((j*L/3,100),(j*L/3,H-top),'A-JOINERY')
    p.rect(0,H+600,L,700,'A-JOINERY')
    for j in range(1,4):p.line((j*L/4,H+600),(j*L/4,H+1300),'A-JOINERY')
    p.dim((0,0),(L,0),(L/2,-200));p.dim((L,0),(L,H),(L+200,H/2))
    p.leader([(L*.6,H-top/2),(L+300,H+200),(L+600,H+200)],f"ST01 / đá {top:g} mm\nWD01 / ván {d:g} mm",1200)

def cabinet_detail(p,s):
    f=s['finishes'];w=f['cabinet_depth'];h=f['cabinet_height'];d=f['panel'];top=f['counter']
    p.rect(0,0,d,h-top,'A-JOINERY');p.rect(w-d,0,d,h-top,'A-JOINERY');p.rect(-20,h-top,w+40,top,'A-COUNTER');p.hatch(-20,h-top,w+40,top,'AR-CONC',1)
    p.rect(d,100,w-2*d,d,'A-JOINERY');p.rect(d,h/2,w-2*d,d,'A-JOINERY')
    p.dim((0,h),(w,h),(w/2,h+80));p.dim((w,0),(w,h),(w+120,h/2))
    p.leader([(w-d,400),(w+50,500),(w+150,500)],f"MDF {d:g} mm\nPhụ kiện theo duyệt",450,2)

def bathroom_elevation(p,s):
    b=s['building'];p.rect(0,0,1800,2600,'A-WALL');p.hatch(0,0,1800,2600,'NET',90)
    p.rect(200,800,600,150,'P-BASIN');p.rect(200,1200,600,800,'A-MIRROR')
    p.rect(1100,0,50,2100,'A-GLASS');p.circle(1450,1900,70,'P-SHOWER')
    p.dim((0,0),(1800,0),(900,-250));p.dim((0,0),(0,2600),(-250,1300))
    p.leader([(600,600),(2100,800),(2400,800)],'F02 / gạch chống trượt\nChống thấm xem AR-503',1000)

def finish_plan(p,s,floor=1):
    b=s['building'];plan_base(p,s,floor,False,False);t=b['wall'];W,D=b['width'],b['depth']
    if 'partitions' in s.get('extensions',{}):
        from .building_extensions import custom_floor_rects
        for x,y,w,h in custom_floor_rects(s,floor):p.hatch(x,y,w,h,'ANSI37',250)
        p.tag('F01',W*.25,D*.35,4)
        p.dim((t,t),(W-t,t),(W/2,-500))
        p.leader([(W-800,D*.75),(W+200,D*.75),(W+600,D*.75)],'Sàn trừ vách và ô thang\nVật liệu / vùng ướt chờ chốt',2400,2)
        return
    p.hatch(t,t,W/2-t,D/2-t,'ANSI37',80);p.hatch(W-1800+t,t,1800-2*t,3000-t,'NET',100)
    p.tag('F01',W*.25,D*.35,4);p.tag('F02',W-900,1500,4)
    p.dim((t,t),(W/2,t),(W/4,-500));p.dim((W-1800,t),(W,t),(W-900,-500))
    p.leader([(W*.3,D*.3),(W*.35,D*.6),(W*.4,D*.6)],'F01 / hướng lát và mạch\nTrần: phối hợp EL / ME',1800,2)

def ceiling_plan(p,s,floor):
    lights_plan(p,s,floor);b=s['building'];W,D,t=b['width'],b['depth'],b['wall']
    p.rect(t+100,t+100,W-2*t-200,D-2*t-200,'A-CEILING')
    p.rect(t+300,D/2+300,W/2-2*t-600,D/2-2*t-600,'A-CEILING')
    p.tag('C01',W*.25,D*.65,4)
    p.leader([(W*.25,D*.6),(W*.5,D*.85),(W*.55,D*.85)],f"C01 / thạch cao {s['finishes']['gypsum']:g} mm\nHạ trần {s['finishes']['ceiling_drop']:g} mm",1800,2)

def side_elevation(p,s,rear=False):
    if 'partitions' in s.get('extensions',{}):
        from .building_extensions import draw_custom_elevation
        draw_custom_elevation(p,s,True,rear);return
    b=s['building'];D=b['depth'];roof=b['levels'][-1]
    p.rect(0,0,D,roof,'A-ELEVATION')
    for z in b['levels']:
        p.line((0,z),(D,z),'A-FLOOR');level_mark(p,D+300,z,f'{z/1000:+.3f}')
    if s.get('extensions',{}).get('roof_type')=='hip':
        from .building_extensions import draw_hip_elevation
        draw_hip_elevation(p,s,True)
    else:p.rect(-b['roof_overhang'],roof,D+2*b['roof_overhang'],150,'A-ROOF');p.rect(0,roof,D,b['parapet_height'],'A-PARAPET')
    for y in b['grids_y']:p.line((y,0),(y,roof),'A-FINISH')
    p.dim((0,0),(D,0),(D/2,-500));p.dim((0,0),(0,roof),(-500,roof/2))
    p.leader([(D*.6,roof*.5),(D+300,roof*.6),(D+600,roof*.6)],'Mặt bên không ô mở\nTheo mô hình kiến trúc',1400)

def stair_rebar(p,s):
    b,st=s['building'],s['structure'];rise=(b['levels'][1]-b['levels'][0])/b['stair_risers'];run=b['stair_run'];cover=st['cover'];pts=[(0,0)]
    for j in range(5):pts.extend([(j*run,(j+1)*rise),((j+1)*run,(j+1)*rise)])
    p.poly(pts,'S-STAIR');p.line((0,-st['slab_thickness']),(5*run,5*rise-st['slab_thickness']),'S-CONCRETE')
    p.poly([(-300,-cover),(0,-cover),(5*run,5*rise-cover),(5*run+300,5*rise-cover)],'S-REBAR')
    p.poly([(-300,-st['slab_thickness']+cover),(0,-st['slab_thickness']+cover),(5*run,5*rise-st['slab_thickness']+cover),(5*run+300,5*rise-st['slab_thickness']+cover)],'S-REBAR')
    p.dim((0,0),(run,0),(run/2,-350));p.dim((0,0),(0,rise),(-500,rise/2))
    p.leader([(3*run,3*rise-cover),(1900,200),(2200,200)],f"Ø{st['main_bar_diameter']:g} / neo, nối và bước theo tính toán\nChi tiết minh họa, chưa duyệt tải trọng",1500)

def chamber_detail(p,s):
    size=s['systems']['inspection_chamber_size'];p.rect(0,0,size+240,100,'C-COVER')
    p.rect(0,-800,120,800,'C-WALL');p.rect(size+120,-800,120,800,'C-WALL');p.rect(0,-920,size+240,120,'C-BASE')
    p.hatch(0,-920,size+240,120,'AR-CONC',2);p.poly([(120,-760),(size/2+120,-820),(size+120,-760)],'C-BENCH')
    p.rect(-250,-600,370,110,'C-PIPE');p.rect(size+120,-650,400,110,'C-PIPE')
    p.dim((120,0),(size+120,0),(size/2+120,250));p.dim((0,0),(0,-920),(-400,-460))
    p.leader([(size+120,-600),(size+600,-300),(size+800,-300)],'Cao độ đáy / chiều chảy\nĐối chiếu mạng ngoài nhà',1000)

def table_draw(title,columns,rows,widths):
    def draw(p):p.table(title,columns,rows,0,225,widths,paper=2,row=10)
    return draw

def survey_detail(p,s):
    p.rect(0,-300,300,500,'C-MONUMENT');p.hatch(0,-300,300,500,'AR-CONC',2)
    p.line((-250,0),(650,0),'C-GROUND');p.line((150,180),(150,500),'C-DATUM')
    p.dim((0,-300),(300,-300),(150,-450))
    p.leader([(150,200),(500,350),(650,350)],s['site']['datum']+'\nMốc demo / xác nhận ngoài hiện trường',600,2)

def setting_detail(p,s):
    p.line((-200,0),(800,0),'A-GRID');p.line((0,-200),(0,700),'A-GRID')
    p.rect(-125,-125,250,250,'S-COLUMN');p.hatch(-125,-125,250,250,'AR-CONC',2)
    p.circle(0,0,20,'C-POINT');p.dim((0,0),(500,0),(250,450))
    p.leader([(0,0),(400,200),(550,200)],'Giao trục / tọa độ từ SP-102\nKhông đo theo hình in',650,2)

def electrical_detail(p,s):
    c=s['systems']['circuits'][0]
    p.rect(0,0,350,500,'E-PANEL');p.rect(120,200,110,160,'E-BREAKER')
    p.line((175,600),(175,360),'E-CABLE');p.line((175,200),(175,-150),'E-CABLE')
    p.circle(175,440,15,'E-TERMINAL');p.circle(175,100,15,'E-TERMINAL')
    p.dim((0,0),(350,0),(175,-250));p.hatch(0,0,50,500,'ANSI31',3)
    p.leader([(230,300),(500,400),(650,400)],f"{c['id']} / CB {c['breaker_a']:g} A\nCáp {c['cable_mm2']:g} mm² / kiểm tính tải",800,2)

def paving_detail(p,s):
    t=s['site']['paving_thickness'];p.rect(0,-t,1200,t,'C-PAVING');p.hatch(0,-t,1200,t,'BRICK',2)
    p.rect(0,-t-150,1200,150,'C-BASE');p.hatch(0,-t-150,1200,150,'EARTH',4)
    p.dim((1200,0),(1200,-t),(1400,-t/2));p.dim((0,0),(1200,0),(600,300))
    p.leader([(600,-t-80),(1400,-300),(1600,-300)],'Nền đầm chặt / lớp đệm demo\nCao độ và độ dốc xem CV-101',1000,2)

def quantity_detail(p,s):
    t=s['structure']['slab_thickness'];p.rect(0,0,1200,t,'S-CONCRETE');p.hatch(0,0,1200,t,'AR-CONC',2)
    p.dim((0,0),(1200,0),(600,-200));p.dim((1200,0),(1200,t),(1400,t/2))
    p.leader([(700,t/2),(1500,350),(1700,350)],'V = diện tích thực × chiều dày\nTrừ ô thang / không đếm chồng dầm',1100,2)

def coordination_detail(p,s):
    st=s['structure'];h=st['beam_depth'];route=s['systems']['routes'][0];z=route['points'][0][2]
    top=s['building']['levels'][1];p.rect(0,top-h,st['beam_width'],h,'S-BEAM');p.hatch(0,top-h,st['beam_width'],h,'AR-CONC',3)
    p.circle(650,z,route['diameter']/2,'P-PIPE')
    p.dim((650,z),(650,top-h),(850,(z+top-h)/2))
    p.leader([(650,z),(1000,z+500),(1200,z+500)],'Tuyến và cao độ từ model\nQA AABB không thay thế BIM clash',1100,2)

def door_frame_detail(p,s):
    p.rect(0,0,150,400,'A-WALL');p.hatch(0,0,150,400,'ANSI31',2)
    p.rect(150,70,65,100,'A-FRAME');p.rect(210,100,35,280,'A-DOOR');p.circle(210,130,8,'A-HINGE')
    p.poly([(215,90),(240,90),(240,70)],'A-GASKET')
    p.dim((210,380),(245,380),(227.5,460))
    p.leader([(240,70),(350,-40),(450,-40)],'Khung / gioăng / bản lề\nCấu kiện thư viện, duyệt mẫu',650,2)

def reinforcement_sheet(s):
    st=s['structure'];b=Builder('ST-202','MẶT CẮT DẦM / CỘT - 1:5',5);p=b.panel();w,h,c,d=st['beam_width'],st['beam_depth'],st['cover'],st['main_bar_diameter']
    p.rect(0,0,w,h,'S-CONCRETE');p.hatch(0,0,w,h,'AR-CONC',1);p.rect(c,c,w-2*c,h-2*c,'S-REBAR')
    for x,y in [(c+d/2,c+d/2),(w-c-d/2,c+d/2),(c+d/2,h-c-d/2),(w-c-d/2,h-c-d/2)]:p.circle(x,y,d/2,'S-REBAR')
    p.dim((0,0),(w,0),(w/2,-85));p.dim((w,0),(w,h),(w+75,h/2))
    p.leader([(w-c,h*.65),(330,h*.8),(370,h*.8)],f"Ø{st['stirrup_diameter']:g}a{st['stirrup_spacing']:g}",180,2)
    b.view('B1 / MẶT CẮT DẦM',[14,90,152,184],[-140,-140,600,650],5)
    q=b.panel((10000,0),5);cw,cd=st['column_width'],st['column_depth'];q.rect(0,0,cw,cd,'S-CONCRETE');q.hatch(0,0,cw,cd,'AR-CONC',1);q.rect(c,c,cw-2*c,cd-2*c,'S-REBAR')
    corners=[(c+d/2,c+d/2),(cw-c-d/2,c+d/2),(cw-c-d/2,cd-c-d/2),(c+d/2,cd-c-d/2)]
    per_side=int(st['column_bars']/4)
    for i,a in enumerate(corners):
        end=corners[(i+1)%4]
        for j in range(per_side):q.circle(a[0]+(end[0]-a[0])*j/per_side,a[1]+(end[1]-a[1])*j/per_side,d/2,'S-REBAR')
    q.dim((0,0),(cw,0),(cw/2,-85));q.dim((cw,0),(cw,cd),(cw+75,cd/2))
    q.leader([(cw-c,cd-c),(350,370),(400,370)],f"{st['column_bars']:g}Ø{d:g}",150,2)
    b.view('C1 / MẶT CẮT CỘT',[178,90,154,184],[9860,-140,10600,650],5)
    main_ids=[e['id'] for e in b.geometry]
    r=b.panel((100000,0),1)
    r.table('THÔNG SỐ / PHÊ DUYỆT KỸ THUẬT',['MỤC','THÔNG SỐ','CƠ SỞ'],[
        ['DẦM',f'{w:g}×{h:g}; 4Ø{d:g}',s['source']['structural']],
        ['CỘT',f'{cw:g}×{cd:g}; {st["column_bars"]:g}Ø{d:g}',f'Cover {c:g} mm; đai Ø{st["stirrup_diameter"]:g}a{st["stirrup_spacing"]:g}'],
        ['KIỂM TRA','Neo/nối, tổ hợp tải, vùng đai chưa được tự động tính','ST-102 / ST-201 / ST-204']],0,45,[35,110,170],row=8,paper=2)
    b.view('GHI CHÚ / THEO DỮ LIỆU ĐƯỢC CẤP',[14,28,318,48],[100000,0,100315,46],1)
    return {'code':'ST-202','title':b.title,'stage':7,'role':'reinforcement','floor':None,
            'job':b.job(),'views':b.views,'main_entity_ids':main_ids,'references':['ST-102','ST-201','ST-204'],'input_hash':stage_hash(s,7),
            'required_features':['table','dim_aligned','leader','hatch']}

def build_building_set(raw):
    s=normalize(raw);items=[];b,site,st=s['building'],s['site'],s['structure'];W,D=b['width'],b['depth'];n=floor_count(s)
    plan_bounds=[-1250,-1100,W+800,D+1250];site_bounds=[-2400,-site['road_width']-1200,site['width']+1000,site['depth']+1200]
    add=lambda *args,**kw:add_sheet(s,items,*args,**kw)
    add(1,'survey','SV-101','KHẢO SÁT / MỐC & RANH',site_bounds,lambda p:site_plan(p,s,True),[['MỐC',site['datum']],['SRC',s['source']['survey']]],refs=('SV-102','SP-101'))
    def survey_section(p):
        points=site['survey_points'][:2];p.poly([(0,points[0][2]),(site['width'],points[1][2])],'C-SURVEY')
        p.line((0,-1000),(site['width'],-1000),'C-DATUM');p.dim((0,0),(site['width'],0),(site['width']/2,-1400))
        for i,(x,y,z) in enumerate(points):level_mark(p,x,z,f'P{i+1} / {z/1000:+.3f}')
        p.leader([(site['width']/2,-100),(site['width']*.6,1000),(site['width']*.7,1000)],'Mặt cắt hiện trạng từ điểm khảo sát\nKhông nội suy địa hình ngoài dữ liệu',3000)
    add(1,'survey_section','SV-102','MẶT CẮT HIỆN TRẠNG',[-1000,-1900,site['width']+2000,3000],survey_section,refs=('SV-101',))
    add(2,'site','SP-101','TỔNG MẶT BẰNG',site_bounds,lambda p:site_plan(p,s),[['BULD',f'{W:g} × {D:g} mm'],['SET','Gốc nhà theo tọa độ khảo sát']],refs=('SP-102','AR-101'))
    setting_rows=[[f'{i+1}{chr(65+j)}',f'{site["building_origin"][0]+x:g}',f'{site["building_origin"][1]+y:g}'] for i,x in enumerate(b['grids_x']) for j,y in enumerate(b['grids_y'])]
    add(2,'setting_out','SP-102','TỌA ĐỘ ĐỊNH VỊ TRỤC',[-3,0,185,239],table_draw('TỌA ĐỘ / mm',['TRỤC','X','Y'],setting_rows,[35,70,70]),[['DATUM',site['datum']]],refs=('SP-101','ST-101'))
    for floor in range(1,n+1):
        add(3,'architecture',f'AR-{100+floor}','KIẾN TRÚC / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor:plan_base(p,s,floor,True),[['LEVEL',f"+{b['levels'][floor-1]/1000:.3f} m"],['DIM','Trục, chuỗi kích thước và ô mở']],floor=floor,refs=('AR-201','AR-301','AR-502'))
    elev_bounds=[-1000,-1000,W+2700,b['levels'][-1]+b['parapet_height']+1000]
    add(4,'elevation_front','AR-201','MẶT ĐỨNG CHÍNH',elev_bounds,lambda p:elevation(p,s),refs=('AR-101','AR-502'))
    add(4,'elevation_rear','AR-202','MẶT ĐỨNG SAU',elev_bounds,lambda p:elevation(p,s,True),refs=('AR-101','AR-502'))
    add(4,'elevation_left','AR-203','MẶT ĐỨNG BÊN TRÁI',elev_bounds,lambda p:side_elevation(p,s),refs=('AR-101','AR-301'))
    add(4,'elevation_right','AR-204','MẶT ĐỨNG BÊN PHẢI',elev_bounds,lambda p:side_elevation(p,s,True),refs=('AR-101','AR-301'))
    add(4,'section','AR-301','MẶT CẮT A-A',[-1200,-1000,D+2700,b['levels'][-1]+1800],lambda p:section(p,s),refs=('AR-501','ST-203'))
    add(5,'roof','AR-401','MÁI / THOÁT NƯỚC MÁI',plan_bounds,lambda p:roof_plan(p,s),refs=('AR-504','PL-201'))
    add(6,'stair','AR-501','CẤU TẠO CẦU THANG',[-500,-500,3300,2600],lambda p:stair_detail(p,s),[['RISE',f"{(b['levels'][1]-b['levels'][0])/b['stair_risers']:.1f} mm / bậc"],['TREAD',f"{b['stair_run']:g} mm"]],refs=('AR-301','ST-203'))
    add(6,'openings','AR-502','CHI TIẾT CỬA ĐI / CỬA SỔ',[-500,-500,b['door_width']+b['window_width']+2500,3300],lambda p:openings(p,s),[['D1',f"{b['door_width']:g} × {b['door_height']:g}"],['W1',f"{b['window_width']:g} × {b['window_height']:g}"]],detail=door_frame_detail,refs=('AR-201','AR-101'))
    add(6,'wet_detail','AR-503','CHỐNG THẤM / PHỄU THU',[-400,-700,3200,1000],lambda p:wet_detail(p,s),refs=('PL-202','IN-202'))
    add(6,'eaves','AR-504','MÉP MÁI / CHÂN TƯỜNG MÁI',[-800,-500,2700,1700],lambda p:eaves_detail(p,s),refs=('AR-401','PL-201'))
    add(7,'foundations','ST-101','ĐỊNH VỊ MÓNG / GIẰNG',[-2000,-2000,W+2000,D+2000],lambda p:structure_plan(p,s,True),[['CALC',s['source']['structural']]],detail=footing_detail,refs=('ST-201','SP-102'))
    for floor in range(1,n+1):
        add(7,'framing',f'ST-{101+floor}','DẦM SÀN / TẦNG '+str(floor),plan_bounds,lambda p:structure_plan(p,s),[['S1',f"Dày {st['slab_thickness']:g} mm"],['B1',f"{st['beam_width']:g} × {st['beam_depth']:g}"]],floor=floor,detail=rebar_section,refs=('ST-202','ST-203'))
    add(7,'footing_detail','ST-201','CẤU TẠO MÓNG ĐƠN',[-500,st['foundation_bottom']-600,3500,1000],lambda p:footing_detail(p,s),[['F1',f"{st['foundation_width']:g} × {st['foundation_width']:g} × {st['foundation_depth']:g}"]],detail=rebar_section,refs=('ST-101',))
    items.append(reinforcement_sheet(s))
    add(7,'slab_detail','ST-203','BẢN SÀN / LIÊN KẾT THANG',[-400,-800,4000,1100],lambda p:slab_detail(p,s),refs=('AR-501','ST-102'))
    add(7,'stair_reinforcement','ST-204','CỐT THÉP BẢN THANG / NEO',[-600,-600,4000,2000],lambda p:stair_rebar(p,s),refs=('AR-501','AR-301','ST-203'))
    for floor in range(1,n+1):
        for role,system,num,title in [('water','water',100,'CẤP NƯỚC'),('waste','waste',110,'THOÁT NƯỚC')]:
            diameter=s['systems']['water_diameter' if system=='water' else 'waste_diameter']
            add(8,role,f'PL-{num+floor}',title+' / TẦNG '+str(floor),plan_bounds,lambda p,system=system,floor=floor:route_plan(p,s,system,floor),[['MEP',s['source']['mep']],['NHÁNH',f'Đến thiết bị Ø{diameter:g}; cỡ ống là đầu vào, chưa tính thủy lực']],floor=floor,refs=('PL-201','PL-202'))
    add(8,'riser','PL-201','SƠ ĐỒ TRỤC CẤP / THOÁT',[-800,-1600,6000,b['levels'][-1]+2200],lambda p:riser(p,s),refs=('AR-401','PL-202'))
    add(8,'plumbing_detail','PL-202','CỤM VAN / BẪY NƯỚC',[-500,-800,3500,2200],lambda p:plumbing_detail(p,s),refs=('AR-503','PL-201'))
    for floor in range(1,n+1):
        for role,num,title in [('lighting',100,'CHIẾU SÁNG'),('sockets',110,'Ổ CẮM / CẤP ĐIỆN')]:
            add(9,role,f'EL-{num+floor}',title+' / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor,role=role:lights_plan(p,s,floor,role=='sockets'),[['CCT','C01 đèn / C02 ổ cắm / C03 điều hòa'],['KL','Chiều dài tuyến; ống riêng từng mạch trong demo']],floor=floor,refs=('EL-201','EL-202'))
    add(9,'single_line','EL-201','SƠ ĐỒ ĐƠN TUYẾN / TỦ ĐIỆN',[-500,-2000,max(6500,len(s['systems']['circuits'])*1600+2500),3100],lambda p:single_line(p,s),[['CALC','Thông số CB/cáp là dữ liệu đầu vào']],refs=('EL-101','EL-111'))
    add(9,'earthing','EL-202','TIẾP ĐỊA / CHI TIẾT ĐO',[-800,-2400,4400,1500],lambda p:earth_detail(p,s),refs=('EL-201',))
    for floor in range(1,n+1):
        add(10,'low_voltage',f'LV-{100+floor}','MẠNG / CAMERA / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor:low_voltage(p,s,floor),[['NET','2 DATA + 1 CAM; tuyến ống riêng từng điểm trong demo']],floor=floor,refs=('ME-201','EL-201'))
        add(10,'hvac',f'ME-{100+floor}','ĐIỀU HÒA / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor:route_plan(p,s,'hvac',floor),floor=floor,detail=hvac_detail,refs=('ME-201','AR-301'))
    add(10,'hvac_detail','ME-201','LẮP ĐẶT / THOÁT NGƯNG',[-400,-500,3300,1500],lambda p:hvac_detail(p,s),detail=hvac_detail,refs=('ME-101','PL-201'))
    for floor in range(1,n+1):
        add(11,'interior',f'IN-{100+floor}','NỘI THẤT / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor:plan_base(p,s,floor,True),floor=floor,detail=cabinet_detail,refs=('IN-201','IN-202','IN-203'))
    add(11,'joinery','IN-201','TỦ BẾP / MẶT ĐỨNG & CẤU TẠO',[-400,-500,s['finishes']['cabinet_length']+2600,3000],lambda p:joinery(p,s),detail=cabinet_detail,refs=('IN-101','EL-111'))
    add(11,'bathroom','IN-202','VỆ SINH / ỐP LÁT & THIẾT BỊ',[-500,-600,4000,3300],lambda p:bathroom_elevation(p,s),refs=('AR-503','PL-202'))
    for floor in range(1,n+1):
        add(11,'finishes',f'IN-{202+floor}','SÀN / VẬT LIỆU / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor:finish_plan(p,s,floor),floor=floor,refs=('EL-101','ME-101','AR-503'))
        add(11,'ceiling',f'IN-{110+floor}','TRẦN / PHỐI HỢP / TẦNG '+str(floor),plan_bounds,lambda p,floor=floor:ceiling_plan(p,s,floor),floor=floor,refs=(f'EL-{100+floor}',f'ME-{100+floor}','AR-301'))
    add(12,'landscape','LA-101','SÂN VƯỜN / LỐI ĐI',site_bounds,lambda p:site_plan(p,s,landscape=True),refs=('CV-101','SP-101'))
    add(12,'grading','CV-101','CAO ĐỘ SÂN / THOÁT NƯỚC',site_bounds,lambda p:site_plan(p,s,grading=True),detail=chamber_detail,refs=('CV-201','SV-101'))
    add(12,'chamber','CV-201','HỐ GA / CAO ĐỘ ĐẤU NỐI',[-700,-1400,2600,900],lambda p:chamber_detail(p,s),detail=chamber_detail,refs=('CV-101','PL-201'))
    q=takeoff(s)
    for page,start in enumerate(range(0,len(q),18),1):
        rows=[[r['code'],f"{r['quantity']:.3f}",r['unit']] for r in q[start:start+18]]
        add(13,'takeoff',f'QS-{100+page}','THỐNG KÊ TỪ MÔ HÌNH / '+str(page),[-3,0,185,239],table_draw('KHỐI LƯỢNG / PHẠM VI MÔ HÌNH',['MÃ','KHỐI LƯỢNG','ĐV'],rows,[85,65,35]),[['BASIS',s['estimate_scope']['coverage_note']]],refs=('QS-201','ST-101','IN-203'))
        costs=[[r['code'],f"{r['unit_price']:,.0f}",f"{r['amount']:,.0f}"] for r in q[start:start+18]]
        add(13,'estimate',f'QS-{200+page}','DỰ TOÁN / ĐƠN GIÁ / '+str(page),[-3,0,185,239],table_draw('CHI PHÍ MÔ HÌNH / VND',['MÃ','ĐƠN GIÁ','THÀNH TIỀN'],costs,[70,50,65]),[['PRICE',s['source']['prices']],['EXCL','; '.join(s['estimate_scope']['excluded_items'])[:200] or 'Phạm vi đã được xác nhận']],refs=('QS-101',))
    def coordination(p):
        structure_plan(p,s)
        for route in service_routes(s):
            points=[(x,y) for x,y,z in route['points']]
            if len(set(points))>1:p.poly(points,'Q-'+route['system'].upper())
            if not route.get('parent'):
                x,y,z=route['points'][-1];p.tag(route['id'],x,y+500,4)
        p.leader([(W*.6,D*.5),(W+500,D*.6),(W+850,D*.6)],'Kiểm AABB tuyến / cột, dầm, sàn\nKhông thay thế phối hợp 3D đầy đủ',1800,2)
    add(14,'coordination','QA-101','PHỐI HỢP / XUNG ĐỘT BỘ MÔN',plan_bounds,coordination,refs=('ST-102','PL-101','EL-101','ME-101'))
    # An index is split into pages, never squeezed into unreadable small text.
    pages=1
    while math.ceil((len(items)+pages)/18)>pages:pages=math.ceil((len(items)+pages)/18)
    indexed=list(items)+[{'code':f'QA-{101+p}','stage':14,'title':'DANH MỤC / REVISION / '+str(p)} for p in range(1,pages+1)]
    for page,start in enumerate(range(0,len(indexed),18),1):
        rows=[[x['code'],str(x['stage']),x['title']] for x in indexed[start:start+18]]
        add(14,'drawing_index',f'QA-{101+page}','DANH MỤC / REVISION / '+str(page),[-3,0,185,239],table_draw('DANH MỤC / REV '+s['revision'],['MÃ TỜ','BƯỚC','NỘI DUNG'],rows,[35,18,132]),[['STATUS','DEMO / CHƯA PHÁT HÀNH THI CÔNG' if s['mode']=='demo' else 'THIẾT KẾ / CHỜ KIỂM DUYỆT']],refs=('QA-101','QS-201'))
    project={'generator':'building_fourteen_stage_v1','spec':s,'sheets':items,'takeoff':q,
             'provenance':'NEW_GEOMETRY_FROM_SHARED_MODEL / NO REFERENCE DWG INPUT',
             'engineering_status':'DEMO' if s['mode']=='demo' else 'REVIEW_REQUIRED'}
    project['workflow']=check_project(project);return project
