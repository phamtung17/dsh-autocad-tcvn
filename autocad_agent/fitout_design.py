"""Parametric NEW studio fit-out drawings. No reference DWG geometry is read.

Project dimensions come from the normalized specification; fittings use template defaults.
The demo is illustrative, not an approved engineering design.
"""
from __future__ import annotations
import math
from copy import deepcopy
from .schema import finite,text,validate_job,JobError
from .reference_profiles import checked_id


MATERIALS=[
    ['W01','Tường xây / vách nền','ANSI31'],
    ['W02','Sơn nước hoàn thiện','ANSI31'],
    ['F01','Sàn gỗ kỹ thuật','ANSI37'],
    ['F02','Gạch porcelain chống trượt','NET'],
    ['C01','Trần thạch cao','ANSI31'],
    ['WD01','Ván MDF chống ẩm phủ laminate','ANSI37'],
    ['ST01','Mặt bàn đá nhân tạo','AR-CONC'],
    ['MT01','Nẹp / phụ kiện kim loại','ANSI31'],
]
COMPONENT_DEFAULTS={'door_height':2200,'bath_door_height':2100,'door_leaf':35,'gypsum_board':12.5,'window_sill':1400,'window_height':1100,
                    'kitchen_plinth':100,'upper_cabinet_gap':650,'upper_cabinet_height':750,'skirting_thickness':12}


def demo_spec():
    return {'project_id':'boyxpxt_new_studio_demo','project_name':'STUDIO S-01 / THIẾT KẾ MINH HỌA',
            'mode':'demo','width':4200,'depth':8400,'height':2900,'wall_thickness':150,
            'door_width':900,'door_offset':300,'window_width':2400,
            'bath_width':2100,'bath_depth':2400,'bath_door_width':800,
            'ceiling_height':2700,'floor_finish':15,'floor_screed':40,'floor_slab':150,
            'waterproofing':3,'skirting_height':100,
            'kitchen_length':2700,'kitchen_depth':600,'kitchen_height':900,
            'counter_thickness':30,'cabinet_panel':18,'wardrobe_width':1800,'wardrobe_depth':600,
            'bed_width':1600,'bed_length':2000,
            'components':dict(COMPONENT_DEFAULTS),
            'assumptions':['Kích thước, vật liệu, điểm điện và cấu tạo là dữ liệu demo do phần mềm cung cấp; cần chốt lại cho dự án thật.']}


def normalize_spec(raw):
    if not isinstance(raw,dict):raise JobError('Fit-out specification must be an object')
    required=set(demo_spec())-{'assumptions','components'}
    if set(raw)-set(demo_spec()):raise JobError('Unknown fit-out specification fields: '+str(sorted(set(raw)-set(demo_spec()))))
    missing=required-set(raw)
    if missing:raise JobError('Required project parameters: '+', '.join(sorted(missing)))
    s=deepcopy(raw);checked_id(s['project_id']);text(s['project_name'],'project name',90)
    if s['mode'] not in ('demo','design_review'):raise JobError('mode must be demo or design_review')
    for key in required-{'project_id','project_name','mode'}:s[key]=finite(s[key],key,positive=True)
    components=s.get('components',{})
    if not isinstance(components,dict) or set(components)-set(COMPONENT_DEFAULTS):raise JobError('Unknown component dimension')
    s['components']={k:finite(components.get(k,v),k,positive=True) for k,v in COMPONENT_DEFAULTS.items()}
    if not 3000<=s['width']<=12000 or not 5000<=s['depth']<=18000:raise JobError('Studio footprint outside supported 3..12m x 5..18m envelope')
    if not 2400<=s['height']<=4500 or not 2200<=s['ceiling_height']<s['height']:raise JobError('Invalid ceiling or storey height')
    if not 70<=s['wall_thickness']<=400:raise JobError('Unsupported wall thickness')
    if not 700<=s['door_width']<=1500 or s['door_offset']+s['door_width']>s['width']-s['wall_thickness']:raise JobError('Entry door does not fit wall')
    if s['window_width']>s['width']-2*s['wall_thickness']:raise JobError('Window does not fit facade')
    if not 1400<=s['bath_width']<=s['width']-1600 or not 1800<=s['bath_depth']<=s['depth']*.4:raise JobError('Bathroom does not fit studio')
    if s['bath_door_width']>s['bath_depth']-600:raise JobError('Bathroom door does not fit')
    if s['kitchen_length']>s['depth']-s['bath_depth']-2200:raise JobError('Kitchen overlaps bedroom zone')
    if s['kitchen_depth']+s['bath_width']>s['width']-500:raise JobError('Kitchen circulation is too narrow for this template')
    if s['bed_width']>s['width']-s['kitchen_depth']-800 or s['bed_length']>s['depth']-s['bath_depth']-1000:raise JobError('Bed does not fit bedroom zone')
    if s['wardrobe_width']>s['depth']-s['bath_depth']-s['kitchen_length']+1200:raise JobError('Wardrobe exceeds reserved zone')
    if not 10<=s['cabinet_panel']<=40 or s['counter_thickness']>=s['kitchen_height']/3:raise JobError('Invalid cabinet assembly thickness')
    if s['components']['kitchen_plinth']>=s['kitchen_height']-s['counter_thickness']-200:raise JobError('Cabinet plinth leaves insufficient carcass height')
    if s['kitchen_height']>=s['ceiling_height']-1000:raise JobError('Kitchen height conflicts with upper cabinet zone')
    if s['kitchen_height']+s['components']['upper_cabinet_gap']+s['components']['upper_cabinet_height']>s['ceiling_height']-100:
        raise JobError('Upper cabinets do not fit below the ceiling')
    if s['components']['window_sill']<1250 or s['components']['window_sill']+s['components']['window_height']>s['ceiling_height']-100:
        raise JobError('Window conflicts with headboard or ceiling')
    if s['door_offset']+s['door_width']>s['width']-s['bath_width']-s['wall_thickness']:
        raise JobError('Entry door overlaps bathroom partition')
    if s['width']-s['wall_thickness']-s['wardrobe_depth']-450-s['bed_width']<600:
        raise JobError('Bed and wardrobe leave less than the template 600mm circulation allowance')
    s['assumptions']=s.get('assumptions',[])
    if not isinstance(s['assumptions'],list) or not all(isinstance(v,str) and len(v)<=500 for v in s['assumptions']):raise JobError('Invalid assumptions')
    return s


def floor_zones(s):
    W,D,t,bw,bd=s['width'],s['depth'],s['wall_thickness'],s['bath_width'],s['bath_depth']
    return [('F01',(t,t,W-bw-t,bd)),('F01',(t,bd+t,W-2*t,D-bd-2*t)),
            ('F02',(W-bw+t,t,bw-2*t,bd-t)),('F02',(W-bw,600,t,s['bath_door_width']))]


def quantities(s):
    areas={'F01':0.,'F02':0.}
    for code,(x,y,w,h) in floor_zones(s):areas[code]+=w*h/1e6
    return {**areas,'C01':(s['width']-2*s['wall_thickness'])*(s['depth']-2*s['wall_thickness'])/1e6,
            'K01':s['kitchen_length']/1000}


class Builder:
    def __init__(self,code,title,scale=40):
        self.code=code;self.title=title;self.geometry=[];self.blocks=[];self.views=[];self.scale=scale
    def add(self,kind,layer,**kw):
        entity={'id':f'e{len(self.geometry)+1:05d}','type':kind,'layer':layer,**kw};self.geometry.append(entity);return entity
    def panel(self,offset=(0,0),scale=None):return Panel(self,offset,scale or self.scale)
    def view(self,title,rect,bounds,scale):
        x,y,w,h=rect;a,b,c,d=bounds
        if (c-a)/scale>w-2 or (d-b)/scale>h-2:raise JobError(f'View {title} does not fit at 1:{scale:g}')
        self.views.append({'title':title,'rect':list(rect),'bounds':list(bounds),'scale':scale,
                           'target':[(a+c)/2,(b+d)/2]})
    def job(self):
        return validate_job({'discipline':'architectural','units':'mm','output_name':self.code.replace('-','_')+'.dwg',
                             'geometry':self.geometry,'blocks':self.blocks,'purpose':'concept_only',
                             'sheet':{'format':'A3','orientation':'landscape','scale_denominator':self.scale}})


class Panel:
    def __init__(self,builder,offset,scale):self.b=builder;self.offset=offset;self.scale=scale
    def p(self,p):return [p[0]+self.offset[0],p[1]+self.offset[1]]
    def line(self,a,b,layer='A-OUTLINE'):return self.b.add('line',layer,start=self.p(a),end=self.p(b))
    def rect(self,x,y,w,h,layer='A-OUTLINE'):
        return self.poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],layer,True)
    def poly(self,points,layer='A-OUTLINE',closed=False):return self.b.add('polyline',layer,points=[self.p(p) for p in points],closed=closed)
    def circle(self,x,y,r,layer='A-SYMBOL'):return self.b.add('circle',layer,center=self.p((x,y)),radius=r)
    def arc(self,x,y,r,start,end,layer='A-DOOR'):return self.b.add('arc',layer,center=self.p((x,y)),radius=r,start_angle=start,end_angle=end)
    def text(self,value,x,y,paper=2.5,layer='A-TEXT'):
        return self.b.add('text',layer,text=value,position=self.p((x,y)),height=paper*self.scale)
    def mtext(self,value,x,y,width,paper=2.5,layer='A-TEXT'):
        return self.b.add('mtext',layer,text=value,position=self.p((x,y)),height=paper*self.scale,width=width)
    def dim(self,a,b,position):
        return self.b.add('dim_aligned','A-DIM',start=self.p(a),end=self.p(b),position=self.p(position),text_height=2.1*self.scale)
    def hatch(self,x,y,w,h,pattern='ANSI31',spacing=10,layer='A-HATCH',angle=0):
        return self.b.add('hatch',layer,points=[self.p(p) for p in [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]],
                          pattern=pattern,pattern_scale=spacing,angle=angle)
    def leader(self,points,value,width=1000,paper=2.3):
        return self.b.add('leader','A-ANNO',points=[self.p(p) for p in points],text=value,height=paper*self.scale,text_width=width,
                          align='right' if points[-1][0]<points[-2][0] else 'left')
    def table(self,title,columns,rows,x,y,widths,paper=2.2,row=7):
        return self.b.add('table','A-TABLE',position=self.p((x,y)),title=title,columns=columns,rows=rows,
                          widths=[v*self.scale for v in widths],height=paper*self.scale,row_height=row*self.scale)
    def tag(self,label,x,y,r=3.5):
        size=r*self.scale;name=f'TAG_{label}_{r:g}_{self.scale:g}'.replace('.','p')
        if not any(b['name']==name for b in self.b.blocks):
            self.b.blocks.append({'name':name,'entities':[
                {'id':'ring','type':'circle','center':[0,0],'radius':size},
                {'id':'label','type':'text','text':label,'position':[-size*.55,-size*.35],'height':1.9*self.scale}]})
        self.b.add('insert','A-SYMBOL',block=name,position=self.p((x,y)),scale=1,rotation=0)
    def furniture(self,x,y,w,h,kind):
        name=f'FURN_{kind}_{w:g}_{h:g}'.replace('.','p')
        if not any(b['name']==name for b in self.b.blocks):
            temporary=Builder('BLOCK','BLOCK',self.scale)
            temporary.panel()._furniture_geometry(0,0,w,h,kind)
            self.b.blocks.append({'name':name,'entities':temporary.geometry})
        self.b.add('insert','A-FURNITURE',block=name,position=self.p((x,y)),scale=1,rotation=0)
    def _furniture_geometry(self,x,y,w,h,kind):
        self.rect(x,y,w,h,'A-FURNITURE')
        if kind=='bed':
            self.rect(x+60,y+60,w-120,h-120,'A-FURNITURE')
            self.rect(x+100,y+h-500,w/2-150,360,'A-FURNITURE');self.rect(x+w/2+50,y+h-500,w/2-150,360,'A-FURNITURE')
            self.line((x+60,y+h-600),(x+w-60,y+h-600),'A-FURNITURE')
        elif kind=='sofa':
            self.rect(x+100,y+100,w-200,h-250,'A-FURNITURE')
            self.line((x+w/2,y+100),(x+w/2,y+h-150),'A-FURNITURE')
            self.rect(x,y,100,h,'A-FURNITURE');self.rect(x+w-100,y,100,h,'A-FURNITURE')
        elif kind=='wardrobe':
            for j in range(1,3):self.line((x,y+h*j/3),(x+w,y+h*j/3),'A-FURNITURE')
            self.line((x+30,y+30),(x+w-30,y+h-30),'A-HIDDEN')
    def basin(self,x,y,w=500,h=420):
        self.rect(x,y,w,h,'P-FIXTURE');self.rect(x+50,y+50,w-100,h-120,'P-FIXTURE')
        self.circle(x+w/2,y+h*.45,22,'P-FIXTURE');self.line((x+w/2,y+h),(x+w/2,y+h-90),'P-FIXTURE')
    def toilet(self,x,y):
        self.rect(x,y,360,180,'P-FIXTURE');self.rect(x+30,y-450,300,440,'P-FIXTURE')
        self.arc(x+180,y-300,145,180,360,'P-FIXTURE')
    def door(self,x,y,w,vertical=False):
        if vertical:
            self.rect(x,y,35,w,'A-DOOR');self.arc(x,y,w,0,90)
            self.line((x,y),(x+w,y),'A-DOOR')
        else:
            self.rect(x,y,w,35,'A-DOOR');self.arc(x,y,w,0,90)
            self.line((x,y),(x,y+w),'A-DOOR')


def plan_scale(s):
    needed=max((s['depth']+1300)/243,(s['width']+1750)/188)
    return next((v for v in (25,30,40,50,75,100) if v>=needed),100)


def base_plan(p,s,furniture=True,dimensions=True,wall_hatch=True):
    W,D,t=s['width'],s['depth'],s['wall_thickness'];bw,bd=s['bath_width'],s['bath_depth']
    door,dx=s['door_width'],s['door_offset'];ww=s['window_width'];wx=(W-ww)/2
    walls=[(0,0,t,D),(W-t,0,t,D),(t,0,dx-t,t),(dx+door,0,W-t-dx-door,t),
           (t,D-t,wx-t,t),(wx+ww,D-t,W-t-wx-ww,t),
           (W-bw,bd,bw-t,t),(W-bw,t,t,600),(W-bw,600+s['bath_door_width'],t,bd-600-s['bath_door_width'])]
    for x,y,w,h in walls:
        p.rect(x,y,w,h,'A-WALL')
        if wall_hatch:p.hatch(x,y,w,h,'ANSI31',t/25)
    for j in (0,.5,1):p.line((wx,D-t+j*t),(wx+ww,D-t+j*t),'A-WINDOW')
    p.door(dx,t,door);p.door(W-bw+t,600,s['bath_door_width'],True)
    if furniture:
        bedx=450;bedy=D-t-s['bed_length']-250
        p.furniture(bedx,bedy,s['bed_width'],s['bed_length'],'bed')
        p.rect(bedx+s['bed_width']+100,D-t-650,300,400,'A-FURNITURE')
        p.furniture(W-t-s['wardrobe_depth'],D-t-s['wardrobe_width'],s['wardrobe_depth'],s['wardrobe_width'],'wardrobe')
        kx=W-t-s['kitchen_depth'];ky=bd+500
        p.rect(kx,ky,s['kitchen_depth'],s['kitchen_length'],'A-FURNITURE')
        for j in range(1,3):p.line((kx,ky+j*s['kitchen_length']/3),(W-t,ky+j*s['kitchen_length']/3),'A-FURNITURE')
        p.basin(kx+50,ky+120,480,480)
        for cx,cy in [(kx+180,ky+1400),(kx+420,ky+1400),(kx+180,ky+1640),(kx+420,ky+1640)]:p.circle(cx,cy,65,'A-FURNITURE')
        p.furniture(350,bd+300,800,1700,'sofa');p.circle(1600,bd+1400,300,'A-FURNITURE')
        p.toilet(W-t-700,bd-350);p.basin(W-bw+t+150,bd-750,600,450)
        p.rect(W-t-1000,t+100,900,900,'P-FIXTURE');p.circle(W-t-550,t+550,50,'P-FIXTURE')
    if dimensions:
        p.dim((0,0),(W,0),(W/2,-600));p.dim((0,0),(0,D),(-650,D/2))
        p.dim((0,D),(wx,D),(wx/2,D+350));p.dim((wx,D),(wx+ww,D),(W/2,D+350));p.dim((wx+ww,D),(W,D),((W+wx+ww)/2,D+350))
        p.dim((W,0),(W,bd),(W+400,bd/2));p.dim((W,bd),(W,D),(W+400,(D+bd)/2))
        p.dim((W-bw,0),(W,0),(W-bw/2,-300))
        p.dim((dx,0),(dx+door,0),(dx+door/2,-300))
    p.mtext('STUDIO S-01\n'+f"{quantities(s)['F01']:.2f} m²",W*.33,D*.59,W*.4,2.5)
    p.mtext('VỆ SINH\n'+f'{(bw-2*t)*(bd-t)/1e6:.2f} m²',W-t-850,bd-1000,780,1.8)
    p.tag('D1',dx+door*.7,t+door*.55);p.tag('D2',W-bw+350,650+s['bath_door_width']*.5)
    p.tag('W1',W/2,D-t-220)
    if furniture:
        p.tag('E1',W-t-s['kitchen_depth']-350,bd+500+s['kitchen_length']/2,4.5)
        p.text('A-401',W-t-s['kitchen_depth']-550,bd+500+s['kitchen_length']/2-300,paper=2)
        p.tag('E2',W*.28,D-2650,4.5);p.text('A-402',W*.28-200,D-2950,paper=2)


def plan_view(b,s,paper_rect=(14,30,190,245)):
    S=b.scale;W,D=s['width'],s['depth']
    b.view('MẶT BẰNG / PLAN',paper_rect,[-850,-700,W+900,D+600],S)


def paper_notes(b,heading,rows,y=273):
    p=b.panel((50000,0),1)
    p.table(heading,['MÃ','NỘI DUNG'],rows,0,240,[17,102],paper=2.1,row=12)
    b.view(heading,[210,133,122,142],[50000,104,50119,242],1)


def floor_plan(s):
    S=plan_scale(s);b=Builder('A-101','MẶT BẰNG BỐ TRÍ / FURNITURE PLAN',S);p=b.panel()
    base_plan(p,s)
    paper_notes(b,'GHI CHÚ & THỐNG KÊ',[
        ['D1',f"Cửa vào {s['door_width']:g} x {s['components']['door_height']:g} mm"],['D2',f"Cửa vệ sinh {s['bath_door_width']:g} x {s['components']['bath_door_height']:g} mm"],
        ['W1',f"Cửa sổ {s['window_width']:g} mm; kiểm tra hiện trường"],
        ['WD01',f"Giường {s['bed_width']:g} x {s['bed_length']:g} mm"],
        ['WD02',f"Tủ áo dài {s['wardrobe_width']:g}, sâu {s['wardrobe_depth']:g} mm"],
        ['K01',f"Bếp dài {s['kitchen_length']:g}, sâu {s['kitchen_depth']:g} mm"],
        ['REF','Đối chiếu mặt đứng A-401 / A-402'],['NOTE','Đơn vị mm. Không đo kích thước trực tiếp trên bản in.']])
    plan_view(b,s);return b


def wall_plan(s):
    S=plan_scale(s);b=Builder('A-102','MẶT BẰNG CẤU TẠO VÁCH / WALL PLAN',S);p=b.panel()
    base_plan(p,s,False,True)
    W,D=s['width'],s['depth'];p.tag('W01',W-250,D*.7,r=4.5);p.tag('W02',W-s['bath_width']+100,s['bath_depth']-150,r=4.5)
    paper_notes(b,'CẤU TẠO & ĐỊNH VỊ',[
        ['W01',f"Vách bao dày {s['wall_thickness']:g} mm; loại kết cấu cần chốt"],
        ['W02','Vách khu ướt: lớp nền + chống thấm + gạch hoàn thiện'],
        ['P1','Mép vách lấy từ trục kích thước tổng và cửa'],
        ['S1','Xem chi tiết chân tường trên A-501'],
        ['S2','Xem chi tiết đỉnh vách / trần A-501'],
        ['NOTE','Cấu tạo liên kết và tải trọng do người phụ trách xác nhận.']])
    plan_view(b,s);return b


def finishes_plan(s):
    S=plan_scale(s);b=Builder('A-201','MẶT BẰNG HOÀN THIỆN SÀN / FLOOR FINISHES',S);p=b.panel();W,D,t=s['width'],s['depth'],s['wall_thickness']
    bw,bd=s['bath_width'],s['bath_depth'];base_plan(p,s,False,True,False)
    for code,(x,y,w,h) in floor_zones(s):p.hatch(x,y,w,h,'ANSI37' if code=='F01' else 'NET',45 if code=='F01' else 120,layer='A-FINISH-HATCH')
    p.tag('F01',W*.36,D*.72,5);p.tag('F02',W-bw*.45,bd*.25,5)
    p.line((W-bw+t+150,t+300),(W-t-550,t+550),'A-ANNO')
    paper_notes(b,'VẬT LIỆU HOÀN THIỆN',[
        ['F01',f"Sàn gỗ {s['floor_finish']:g} mm trên lớp vữa {s['floor_screed']:g} mm"],
        ['F02','Gạch porcelain khu ướt; kích thước viên cần chốt'],
        ['SK1',f"Len chân tường cao {s['skirting_height']:g} mm"],
        ['DT1','Mạch chuyển vật liệu tại cửa vệ sinh: xem A-502'],
        ['DT2','Phễu thu sàn / cấu tạo chống thấm: xem A-502'],
        ['NOTE','Cao độ, độ dốc và quy cách vật liệu là thông số cần duyệt cho dự án thật.']])
    plan_view(b,s);return b


def ceiling_plan(s):
    S=plan_scale(s);b=Builder('A-301','MẶT BẰNG TRẦN & ĐÈN / REFLECTED CEILING',S);p=b.panel();W,D,t=s['width'],s['depth'],s['wall_thickness']
    base_plan(p,s,False,False,False)
    p.rect(t+100,t+100,W-2*t-200,D-2*t-200,'A-CEILING')
    p.rect(t+300,s['bath_depth']+300,W-2*t-600,D-s['bath_depth']-2*t-600,'A-CEILING')
    light_points=[(W*.3,y) for y in (s['bath_depth']+900,D*.62,D-900)]+[(W*.7,y) for y in (s['bath_depth']+900,D*.62,D-900)]
    for x,y in light_points:
        p.circle(x,y,60,'E-LIGHT');p.line((x-100,y),(x+100,y),'E-LIGHT');p.line((x,y-100),(x,y+100),'E-LIGHT')
    for y in (s['bath_depth']+900,D*.62,D-900):p.dim((W*.3,y),(W*.7,y),(W/2,y+250))
    p.circle(W-s['bath_width']/2,s['bath_depth']/2,75,'E-LIGHT')
    p.tag('C01',W/2,D*.8,5)
    paper_notes(b,'TRẦN / THIẾT BỊ',[
        ['C01',f"Trần thạch cao; cao độ +{s['ceiling_height']:g} mm"],
        ['L01','Đèn downlight: 6 vị trí trong phòng chính'],['L02','Đèn khu vệ sinh: 1 vị trí'],
        ['LED','Khe hắt / viền trần: xem chi tiết A-501'],
        ['MEP','Kiểm tra vị trí điều hòa, đầu báo, sprinkler và cửa thăm trước khi chốt'],
        ['NOTE','Đây là bố trí minh họa; công suất, mạch và phối hợp MEP cần dữ liệu dự án.']])
    plan_view(b,s);return b


def electrical_plan(s):
    S=plan_scale(s);b=Builder('E-101','MẶT BẰNG ĐIỂM ĐIỆN / SOCKET & SWITCH PLAN',S);p=b.panel();W,D=s['width'],s['depth'];base_plan(p,s,True,False,False)
    points=[(300,D-1200,'E01'),(2100,D-1200,'E01'),(W-300,D-2600,'E02'),
            (W-300,s['bath_depth']+900,'E03'),(W-300,s['bath_depth']+2200,'E04'),(350,1500,'S01')]
    for x,y,code in points:
        p.circle(x,y,100,'E-SOCKET');p.line((x-50,y-70),(x-50,y+70),'E-SOCKET');p.line((x+50,y-70),(x+50,y+70),'E-SOCKET')
        p.mtext(code,x+140,y+80,600,2)
    p.dim((0,0),(0,1500),(-450,750));p.dim((0,0),(W,0),(W/2,-550))
    paper_notes(b,'KÝ HIỆU ĐIỂM ĐIỆN',[
        ['E01','Ổ cắm đầu giường; cao độ demo +300 mm'],['E02','Ổ cắm tủ / TV; cao độ demo +300 mm'],
        ['E03','Ổ cắm bàn bếp; cao độ demo +1100 mm'],['E04','Điểm cấp thiết bị bếp; vị trí theo shop thiết bị'],
        ['S01','Công tắc lối vào; cao độ demo +1200 mm'],
        ['NOTE','Chưa tính phụ tải, dây dẫn, CB, bảo vệ và vùng an toàn điện. Cần kỹ sư điện xác nhận.']])
    plan_view(b,s);return b


def kitchen_elevation(s):
    L,H,top,panel=s['kitchen_length'],s['kitchen_height'],s['counter_thickness'],s['cabinet_panel']
    h=s['ceiling_height'];S=next(v for v in (20,25,30,40,50,75,100) if v>=max((L+1600)/218,(h+450)/178))
    b=Builder('A-401','MẶT ĐỨNG BẾP / KITCHEN ELEVATION',S);p=b.panel()
    plinth=s['components']['kitchen_plinth']
    p.rect(0,0,L,h,'A-WALL');p.rect(0,0,L,plinth,'A-JOINERY');p.rect(0,plinth,L,H-top-plinth,'A-JOINERY');p.rect(0,H-top,L,top,'A-OUTLINE')
    p.hatch(0,plinth,L,H-top-plinth,'ANSI37',10,layer='A-FINISH-HATCH')
    for x in (L/3,2*L/3):p.line((x,plinth),(x,H-top),'A-JOINERY')
    for x in (L/6,L/2,5*L/6):
        p.rect(x-70,H-120,140,12,'A-HARDWARE')
    p.rect(0,H,L,600,'A-FINISH');p.hatch(0,H,L,600,'ANSI31',20,layer='A-FINISH-HATCH')
    gap=s['components']['upper_cabinet_gap'];upper=s['components']['upper_cabinet_height']
    p.rect(0,H+gap,L,upper,'A-JOINERY')
    for j in range(1,6):p.line((j*L/6,H+gap),(j*L/6,H+gap+upper),'A-JOINERY')
    p.rect(L*.36,110,L*.27,520,'A-APPLIANCE');p.rect(L*.38,200,L*.23,340,'A-APPLIANCE')
    for j in range(3):p.circle(L*.42+j*L*.07,590,12,'A-APPLIANCE')
    p.line((L*.12,H),(L*.12,H+180),'P-FIXTURE');p.line((L*.12,H+180),(L*.21,H+180),'P-FIXTURE')
    p.dim((0,0),(L,0),(L/2,-250))
    for a,c in zip((0,L/3,2*L/3),(L/3,2*L/3,L)):p.dim((a,0),(c,0),((a+c)/2,-120))
    p.dim((L,0),(L,H),(L+220,H/2));p.dim((0,0),(0,h),(-260,h/2))
    p.leader([(L*.8,H-top/2),(L+100,H+100),(L+350,H+100)],'ST01 / đá mặt bàn\n'+f'Dày {top:g} mm',900)
    p.leader([(L*.8,500),(L+100,450),(L+350,450)],'WD01 / MDF chống ẩm\n'+f'Ván {panel:g} mm; phủ laminate',900)
    b.view('MẶT ĐỨNG BẾP / ELEVATION',[15,90,220,180],[-350,-300,L+1250,h+150],S)
    q=b.panel((20000,0),20);d=s['kitchen_depth'];q.rect(0,0,panel,H-top,'A-OUTLINE');q.rect(d-panel,0,panel,H-top,'A-OUTLINE')
    q.rect(-20,H-top,d+40,top,'A-OUTLINE');q.hatch(-20,H-top,d+40,top,'AR-CONC',1)
    q.rect(panel,plinth,d-2*panel,panel,'A-OUTLINE');q.rect(panel,H-top-panel,d-2*panel,panel,'A-OUTLINE')
    q.dim((0,H),(d,H),(d/2,H+75));q.dim((-20,H-top),(-20,H),(-80,H-top/2))
    q.leader([(d*.55,H-top/2),(d+40,H+90),(d+90,H+90)],'ST01 / MẶT ĐÁ',230,2.1)
    q.leader([(panel/2,450),(-90,480),(-180,480)],'WD01\nMDF chống ẩm',200,2.1)
    b.view('MẶT CẮT TỦ BẾP / SECTION',[240,155,90,112],
           [19600,-60,20000+d+340,H+170],20)
    joint=b.panel((30000,0),2)
    joint.rect(0,0,100,top,'A-OUTLINE');joint.hatch(0,0,100,top,'AR-CONC',.6)
    joint.rect(15,-40,panel,40,'A-OUTLINE');joint.hatch(15,-40,panel,40,'ANSI31',.6)
    joint.poly([(panel+15,-30),(panel+15,0),(75,0)],'A-HARDWARE')
    joint.circle(panel+20,-18,2,'A-HARDWARE')
    joint.dim((100,0),(100,top),(115,top/2))
    joint.text('ST01',35,38,paper=2)
    b.view('CT05 / MÉP BÀN',[240,95,94,54],[29990,-45,30172,48],2)
    r=b.panel((40000,0),1);r.table('VẬT LIỆU & CẤU TẠO',['MÃ','MÔ TẢ'],[
        ['WD01',f'MDF {panel:g} mm; phụ kiện theo hãng'],['ST01',f'Đá {top:g} mm; mép nhô 20 mm'],
        ['MT01','Tay nắm và liên kết; màu theo duyệt'],['NOTE','Cao độ và kích thước thiết bị cần đối chiếu thực tế.']],0,45,[35,270],paper=2.2,row=8)
    b.view('THÔNG TIN KỸ THUẬT',[17,28,312,55],[40000,-5,40305,45],1)
    return b


def bedroom_elevation(s):
    W,H=s['width'],s['ceiling_height'];S=next(v for v in (20,25,30,40,50,75,100) if v>=max((W+1800)/308,(H+550)/168))
    b=Builder('A-402','MẶT ĐỨNG ĐẦU GIƯỜNG / BEDROOM ELEVATION',S);p=b.panel();bed=s['bed_width'];x=450
    p.rect(0,0,W,H,'A-WALL');p.rect(0,0,W,s['skirting_height'],'A-JOINERY')
    p.rect(x-200,100,bed+400,1100,'A-JOINERY');p.hatch(x-200,100,bed+400,1100,'ANSI37',10,layer='A-FINISH-HATCH')
    p.rect(x,0,bed,450,'A-FURNITURE');p.rect(x+40,450,bed-80,120,'A-FURNITURE')
    p.rect(x+bed+100,0,300,500,'A-JOINERY')
    wx=(W-s['window_width'])/2;ws=s['components']['window_sill'];wh=s['components']['window_height']
    p.rect(wx,ws,s['window_width'],wh,'A-WINDOW');p.line((W/2,ws),(W/2,ws+wh),'A-WINDOW')
    p.rect(W-s['wall_thickness']-s['wardrobe_depth'],0,s['wardrobe_depth'],H-150,'A-JOINERY')
    for xx in (x-200,x+bed+200):p.line((xx,1200),(xx,H-150),'A-FINISH')
    p.rect(100,H-150,W-200,100,'A-CEILING')
    p.dim((0,0),(W,0),(W/2,-250));p.dim((x,0),(x+bed,0),(W/2,-120));p.dim((W,0),(W,H),(W+240,H/2))
    p.leader([(x+bed*.8,1000),(W+150,1100),(W+450,1100)],'WD01 / đầu giường\nMDF phủ laminate',900)
    b.view('MẶT ĐỨNG / ELEVATION',[15,103,310,170],[-300,-350,W+1500,H+200],S)
    q=b.panel((30000,0),1);q.table('BẢNG HOÀN THIỆN',['MÃ','VẬT LIỆU / YÊU CẦU'],[
        ['WD01','Đầu giường và tủ đầu giường: MDF chống ẩm phủ laminate'],
        ['W02','Tường sơn; xử lý nền trước khi hoàn thiện'],['L01','Đèn trang trí: phối hợp điểm cấp điện'],
        ['NOTE','Đối chiếu kích thước đặt hàng, mẫu màu và phụ kiện trước chế tạo.']],0,45,[35,270],row=8)
    b.view('HOÀN THIỆN / FINISHES',[16,30,311,55],[30000,-5,30305,45],1);return b


def construction_details(s):
    b=Builder('A-501','CHI TIẾT CHÂN TƯỜNG & TRẦN / WALL DETAILS',7.5);p=b.panel(scale=7.5)
    t=s['wall_thickness'];finish=s['floor_finish'];screed=s['floor_screed'];slab=s['floor_slab'];skirt=s['skirting_height']
    p.rect(0,-screed-slab-finish,650,slab,'A-OUTLINE');p.hatch(0,-screed-slab-finish,650,slab,'AR-CONC',2)
    p.rect(0,-screed-finish,650,screed,'A-OUTLINE');p.hatch(0,-screed-finish,650,screed,'AR-SAND',1)
    p.rect(0,-finish,650,finish,'A-OUTLINE');p.hatch(0,-finish,650,finish,'ANSI37',1)
    p.rect(0,0,t,600,'A-WALL');p.hatch(0,0,t,600,'ANSI31',2)
    p.rect(t,0,s['components']['skirting_thickness'],skirt,'A-OUTLINE')
    p.dim((650,-finish),(650,0),(740,-finish/2));p.dim((650,-finish-screed),(650,-finish),(810,-finish-screed/2))
    p.dim((0,0),(t,0),(t/2,690));p.dim((t,0),(t,skirt),(t+100,skirt/2))
    p.leader([(430,-finish/2),(700,100),(850,100)],f'F01 / sàn hoàn thiện {finish:g} mm',750,2.2)
    p.leader([(450,-finish-screed/2),(720,-50),(850,-50)],f'Lớp vữa {screed:g} mm',750,2.2)
    p.leader([(430,-finish-screed-slab/2),(720,-220),(850,-220)],f'Sàn nền / slab {slab:g} mm',750,2.2)
    b.view('CT01 / CHÂN TƯỜNG',[15,117,318,150],[-100,-300,1700,700],7.5)
    gypsum=s['components']['gypsum_board']
    q=b.panel((10000,0),7.5);q.rect(0,0,t,450,'A-WALL');q.hatch(0,0,t,450,'ANSI31',2)
    q.rect(t,120,950,gypsum,'A-OUTLINE');q.rect(t,120+gypsum,950,35,'A-HARDWARE')
    for xx in (t+200,t+650):q.line((xx,155+gypsum),(xx,450),'A-HARDWARE');q.circle(xx,440,5,'A-HARDWARE')
    q.rect(t+880,120,70,80,'A-OUTLINE');q.dim((t,120),(t+950,120),(t+475,30))
    q.leader([(t+500,120+gypsum/2),(t+650,250),(t+850,250)],f'C01 / Tấm thạch cao {gypsum:g} mm',700,2.2)
    q.leader([(t+650,330),(t+800,400),(t+1000,400)],'Ty treo / liên kết theo nhà cung cấp',700,2.2)
    b.view('CT02 / ĐỈNH VÁCH - TRẦN',[15,25,318,82],[9900,-10,11800,470],7.5)
    return b


def wet_details(s):
    b=Builder('A-502','CHI TIẾT SÀN KHU ƯỚT / WET AREA DETAILS',5);p=b.panel(scale=7.5)
    f,sc,sl,wp=s['floor_finish'],s['floor_screed'],s['floor_slab'],s['waterproofing'];z=f+sc
    p.rect(0,-z-sl,1500,sl,'A-OUTLINE');p.hatch(0,-z-sl,1500,sl,'AR-CONC',3)
    p.rect(0,-z,1500,sc,'A-OUTLINE');p.hatch(0,-z,1500,sc,'AR-SAND',2)
    p.rect(0,-f,700,f,'A-OUTLINE');p.hatch(0,-f,700,f,'ANSI37',1)
    p.rect(700,-f,800,f,'A-OUTLINE');p.hatch(700,-f,800,f,'ANSI31',1)
    p.poly([(700,-f-sc),(1500,-f-sc),(1500,300)],'A-WATERPROOF')
    p.rect(680,-f,40,f+5,'A-HARDWARE');p.dim((680,0),(720,0),(700,100));p.dim((1500,-z),(1500,0),(1580,-z/2))
    p.leader([(680,-5),(550,180),(150,180)],'MT01 / nẹp chuyển vật liệu',550,2.2)
    p.leader([(1200,-z),(1100,-200),(600,-200)],f'Lớp chống thấm {wp:g} mm; phạm vi theo dự án',700,2.2)
    b.view('CT03 / NGƯỠNG CỬA - CHUYỂN SÀN',[15,162,318,100],[-100,-300,1800,320],7.5)
    q=b.panel((10000,0),6);q.rect(0,-160,700,100,'A-OUTLINE');q.hatch(0,-160,700,100,'AR-CONC',2)
    q.poly([(0,10),(300,0),(400,0),(700,10)],'A-OUTLINE');q.rect(300,-90,100,90,'P-FIXTURE')
    q.rect(290,0,120,10,'P-FIXTURE');q.line((350,-90),(350,-160),'P-PIPE')
    for x in range(300,410,20):q.line((x,0),(x,10),'P-FIXTURE')
    q.dim((290,10),(410,10),(350,100));q.leader([(350,-50),(550,130),(700,130)],'Phễu thu sàn / cổ chống thấm',600,2.2)
    q.leader([(150,5),(-100,160),(-350,160)],'Độ dốc về phễu: cần chốt',500,2.2)
    b.view('CT04 / PHỄU THU SÀN',[15,49,318,103],[9600,-190,11350,240],6)
    return b


def schedules(s,sheets):
    b=Builder('A-601','BẢNG VẬT LIỆU & THỐNG KÊ / SCHEDULES',1);p=b.panel(scale=1)
    q=quantities(s)
    rows=[['F01','Sàn gỗ',f"{q['F01']:.2f}",'m²'],['F02','Gạch khu ướt + cửa',f"{q['F02']:.2f}",'m²'],
          ['C01','Trần chiếu bằng',f"{q['C01']:.2f}",'m²'],['K01','Tủ bếp',f"{q['K01']:.2f}",'m'],
          ['D1','Cửa vào','1','bộ'],['D2','Cửa vệ sinh','1','bộ'],['W1','Cửa sổ','1','bộ'],
            ['L01','Đèn phòng chính','6','cái'],['L02','Đèn vệ sinh','1','cái']]
    p.table('KHỐI LƯỢNG HÌNH HỌC / GEOMETRIC TAKE-OFF',['MÃ','HẠNG MỤC','KL','ĐV'],rows,0,235,[28,153,45,35],row=10)
    p.table('VẬT LIỆU / MATERIAL REGISTER',['MÃ','MÔ TẢ'],[[a,b] for a,b,c in MATERIALS],0,110,[28,233],row=9)
    b.view('THỐNG KÊ TỪ THÔNG SỐ ĐẦU VÀO',[14,29,317,244],[-4,0,265,239],1)
    return b


def index_sheet(s,items):
    b=Builder('A-000','DANH MỤC HỒ SƠ / DRAWING INDEX',1);p=b.panel(scale=1)
    p.mtext('HỒ SƠ FIT-OUT STUDIO\n'+s['project_name'],0,245,300,paper=5)
    p.table('DANH MỤC BẢN VẼ / SHEET INDEX',['MÃ TỜ','TÊN BẢN VẼ'],[[x.code,x.title] for x in items],0,195,[28,275],paper=2.3,row=10)
    p.mtext('BẢN VẼ SINH MỚI TỪ THÔNG SỐ\nĐơn vị: mm. Mô hình vẽ 1:1; tỷ lệ từng hình ghi trên tờ.\nDữ liệu demo cần người phụ trách xác nhận trước khi dùng cho công trình.',0,49,303,paper=2.5)
    b.view('HỒ SƠ MINH HỌA / GENERATED DESIGN',[14,27,318,249],[-3,15,306,250],1)
    return b


def plan_local_detail(b,s):
    """A project-related enlarged construction/symbol panel beside each plan."""
    scale=5;p=b.panel((100000,0),scale);t=s['wall_thickness']
    if b.code in ('A-101','A-102'):
        p.rect(0,0,t,200,'A-WALL');p.hatch(0,0,t,200,'ANSI31',1)
        p.rect(t,0,20,200,'A-JOINERY');p.rect(t+25,25,s['components']['door_leaf'],140,'A-DOOR')
        p.dim((0,200),(t,200),(t/2,250))
        p.leader([(t+10,130),(250,190),(300,190)],'KHUNG / NẸP\nCần chốt quy cách',180,2)
        p.leader([(t+45,80),(250,70),(300,70)],'CÁNH CỬA\n'+f"Dày {s['components']['door_leaf']:g}",180,2)
        title='J01 / NGUYÊN LÝ KHUNG CỬA'
    elif b.code=='A-201':
        f,sc,sl=s['floor_finish'],s['floor_screed'],s['floor_slab']
        p.rect(0,0,240,sl,'A-OUTLINE');p.hatch(0,0,240,sl,'AR-CONC',1)
        p.rect(0,sl,240,sc,'A-OUTLINE');p.hatch(0,sl,240,sc,'AR-SAND',1)
        p.rect(0,sl+sc,240,f,'A-OUTLINE');p.hatch(0,sl+sc,240,f,'ANSI37',1)
        p.leader([(200,sl+sc+f/2),(270,270),(310,270)],f'F01 / {f:g} mm',170,2)
        p.leader([(200,sl+sc/2),(270,170),(310,170)],f'Vữa / {sc:g} mm',170,2)
        p.leader([(200,sl/2),(270,70),(310,70)],f'Nền / {sl:g} mm',170,2)
        title='F01 / LỚP CẤU TẠO SÀN'
    elif b.code=='A-301':
        board=s['components']['gypsum_board']
        p.rect(0,0,30,270,'A-WALL');p.hatch(0,0,30,270,'ANSI31',1)
        p.rect(30,120,230,board,'A-OUTLINE');p.rect(30,120+board,230,25,'A-HARDWARE')
        p.line((130,120+board+25),(130,270),'A-HARDWARE')
        p.leader([(200,120),(280,70),(320,70)],f'Tấm TC {board:g} mm',160,2)
        p.leader([(130,240),(240,250),(320,250)],'TY TREO\nTheo hệ trần',160,2)
        title='C01 / NGUYÊN LÝ MÉP TRẦN'
    else:
        p.rect(30,0,30,280,'A-WALL');p.rect(60,110,30,65,'E-SOCKET')
        p.line((0,0),(260,0),'A-OUTLINE');p.dim((120,0),(120,150),(220,75))
        p.leader([(75,150),(250,230),(300,230)],'Ổ CẮM / SYMBOL\nCao độ theo E-101',180,2)
        title='E01 / NGUYÊN LÝ ĐIỂM ĐIỆN'
    b.view(title,[210,31,122,90],[99950,-30,100500,300],5)


def build_studio_set(raw):
    s=normalize_spec(raw)
    sheets=[floor_plan(s),wall_plan(s),finishes_plan(s),ceiling_plan(s),electrical_plan(s),
            kitchen_elevation(s),bedroom_elevation(s),construction_details(s),wet_details(s)]
    sheets.append(schedules(s,sheets));sheets.insert(0,index_sheet(s,sheets))
    result=[]
    for sheet in sheets:
        if sheet.code in ('A-101','A-102','A-201','A-301','E-101'):plan_local_detail(sheet,s)
        job=sheet.job()
        result.append({'code':sheet.code,'title':sheet.title,'job':job,'views':sheet.views})
    return {'generator':'parametric_studio_v1','spec':s,'sheets':result,
            'provenance':'NEW_GEOMETRY_FROM_SPEC; no reference DWG or DXF is opened by this generator',
            'engineering_status':'DEMO' if s['mode']=='demo' else 'REQUIRES_DISCIPLINE_REVIEW'}
