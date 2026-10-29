"""Write explicit demonstration input, never survey/engineering evidence."""
import json
from pathlib import Path
from autocad_agent.building_model import example


def villa_example():
    s=example();s['project_id']='boyxpxt_villa_18x17_demo';s['project_name']='BIỆT THỰ 18 × 17 / DEMO ĐẦU VÀO'
    s['site'].update(width=30000,depth=40000,building_origin=[6000,6000],survey_points=[[0,0,0],[30000,0,0],[30000,40000,0],[0,40000,0]])
    s['building'].update(width=18000,depth=17000,grids_x=[0,6000,12000,18000],grids_y=[0,5500,11000,17000],levels=[0,3900,7800],roof_slope=.22,roof_overhang=600,stair_origin=[9000,6000])
    s['finishes']['ceiling_drop']=900
    s['systems']['routes'][0]['points']=[[1000,10000,500],[17000,10000,500]]
    s['systems']['routes'][1]['points']=[[1000,9000,-700],[17000,9000,-1020]]
    ext={'roof_type':'hip','pool':{'origin':[2000,27500],'width':10000,'depth':5000},
         'elevator':{'origin':[12500,6500],'width':2000,'depth':2200},'ceiling_service_zone':300,
         'fixtures':[],'devices':[],'partitions':[],'rooms':[],'openings':[],'furniture':[]}
    for floor in (1,2):
        for index,(x,y) in enumerate([(2000,10000),(14000,10000)],1):
            for kind,dx,dy in [('wc',0,0),('basin',700,-500),('shower',-1000 if index==1 else 3000,-500)]:
                ext['fixtures'].append(dict(id=f'{kind}_{floor}_{index}',floor=floor,kind=kind,position=[x+dx,y+dy],host_room=f'R{floor}_{3+index}'))
        for kind,points in {'lights':[(3000,3000),(9000,3000),(15000,3000),(3000,14000),(9000,14000),(15000,14000)],
                            'sockets':[(500,2000),(500,14000),(7000,16500),(17500,2000),(17500,14000),(11000,500)],
                            'ac':[(2500,5000),(6500,5000),(13000,5000),(16500,5000)],
                            'data':[(350,3000),(350,16200)],'camera':[(12600,500)]}.items():
            for i,point in enumerate(points):ext['devices'].append(dict(id=f'{kind}_{floor}_{i}',floor=floor,kind=kind,position=list(point)))
        for i,(a,b) in enumerate([([150,8500],[8000,8500]),([12500,8500],[17850,8500]),([8000,8650],[8000,16850]),
                                  ([150,11000],[4000,11000]),([4000,8650],[4000,11000]),([13000,11000],[17850,11000]),([13000,8650],[13000,11000])]):
            ext['partitions'].append(dict(id=f'W{floor}_{i}',floor=floor,start=a,end=b))
        for i,(name,point) in enumerate([('KHÁCH / SHC',[2500,3000]),('BẾP / ĂN',[13000,2500]),('NGỦ 1',[2000,14500]),('NGỦ 2',[13500,14500]),('WC 1',[1200,10500]),('WC 2',[15000,10500])]):
            boundaries=[[150,150,7700,8000],[8150,150,9700,5600],[150,11150,7700,5700],[8150,11150,9700,5700],[150,8650,3850,2350],[13150,8650,4700,2350]]
            usage=['living','kitchen','bedroom','bedroom','bathroom','bathroom'][i]
            ext['rooms'].append(dict(id=f'R{floor}_{i}',floor=floor,name=name,position=point,usage=usage,boundary=boundaries[i]))
        for i,x in enumerate([2500,14000]):
            ext['furniture'].append(dict(id=f'BED{floor}_{i}',floor=floor,kind='bed',position=[x,12000],width=1600,depth=2000,host_room=f'R{floor}_{2+i}'))
        for i,(kind,x,y,w,vertical) in enumerate([('door',8000,0,1200,False),('window',2000,16850,1800,False),('window',14000,16850,1800,False),('door',4000,9000,900,True),('door',13000,9000,900,True),('door',5000,8500,900,False)]):
            ext['openings'].append(dict(id=f'O{floor}_{i}',floor=floor,kind=kind,position=[x,y],width=w,vertical=vertical))
    s['systems']['fixtures_per_floor'].update(wc=2,basin=2,shower=2,ac=4)
    # Supplied circuits/routes, no inference that CB or cable values are safe.
    for i,(x,y) in enumerate([(2500,5000),(6500,5000),(13000,5000),(16500,5000)],4):
        s['systems']['circuits'].append(dict(id=f'C{i:02}',use=f'AC {i-3} / DEMO',power_w=1800,voltage=230,breaker_a=20,cable_mm2=2.5))
        s['systems']['routes'].append(dict(id=f'P{i:02}',system='power',circuit=f'C{i:02}',diameter=20,points=[[500,500,2600],[x,500,2600],[x,y,2600]]))
        s['systems']['routes'].append(dict(id=f'AC{i:02}',system='hvac',diameter=200,points=[[500,y,2800],[x,y,2800]]))
    s['systems']['routes']=[r for r in s['systems']['routes'] if r['id']!='AC01']
    s['extensions']=ext
    return s


if __name__=='__main__':
    path=Path('examples/villa_18x17_explicit_demo.json')
    path.write_text(json.dumps({'spec':villa_example(),'branding':{'project_code':'BXP-VILLA'}},ensure_ascii=False,indent=2),encoding='utf-8')
    print(path)
