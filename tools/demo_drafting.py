"""New, dimensioned three-view concept plate and native A3 plot.

Run: python -m tools.demo_drafting. All dimensions are demonstration inputs.
"""
from pathlib import Path
import json
import uuid
from autocad_agent.templates import create_template
from autocad_agent.schema import validate_job
from autocad_agent import api
from autocad_agent.cad_com import create_dwg
from autocad_agent.runtime import workspace,atomic_json


def demo_job(name=None):
    job=create_template('mechanical',name=name or 'PLATE_DEMO_'+uuid.uuid4().hex[:8]+'.dwg',width=200,height=100)
    geo=job['geometry']
    # Short centre crosses, preserving the principal axes.
    geo[2]['start']=[100,-5];geo[2]['end']=[100,105]
    geo[3]['start']=[-5,50];geo[3]['end']=[205,50]
    geo[4]['position']=[100,-18];geo[5]['position']=[222,50]
    def add(kind,layer,**kwargs):
        geo.append({'id':'demo_'+str(len(geo)),'type':kind,'layer':layer,**kwargs})
    def line(a,b,layer='M-OUTLINE'):add('line',layer,start=a,end=b)
    def text(value,pos,height=3):add('text','M-TEXT',text=value,position=pos,height=height)
    def rectangle(x,y,w,h):add('polyline','M-OUTLINE',points=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]],closed=True)
    def dim(a,b,p):add('dim_aligned','M-DIM',start=a,end=b,position=p)
    for x in (20,180):
        for y in (20,80):
            add('circle','M-HOLE',center=[x,y],radius=4.5)
            line([x-7,y],[x+7,y],'M-CENTER');line([x,y-7],[x,y+7],'M-CENTER')
    dim([0,100],[20,100],[10,112]);dim([20,100],[180,100],[100,112]);dim([180,100],[200,100],[190,112])
    dim([0,0],[0,20],[-12,10]);dim([0,20],[0,80],[-12,50]);dim([0,80],[0,100],[-12,90])
    text('HÌNH CHIẾU BẰNG',[50,126],3.5)
    rectangle(0,-50,200,12);rectangle(260,0,12,100)
    for x in (15.5,24.5,87,113,175.5,184.5):line([x,-50],[x,-38],'M-HIDDEN')
    for y in (15.5,24.5,37,63,75.5,84.5):line([260,y],[272,y],'M-HIDDEN')
    dim([200,-50],[200,-38],[222,-44]);dim([260,0],[272,0],[266,-18])
    text('HÌNH CHIẾU ĐỨNG',[50,-62]);text('CẠNH',[260,110])
    text('4 lỗ Ø9 xuyên',[260,-32]);text('Tâm: X=20/180',[260,-42]);text('Y=20/80; mm',[260,-52])
    text('DEMO / CONCEPT',[260,-62]);text('Vật liệu, dung sai:',[260,-72]);text('cần người dùng chốt',[260,-82])
    job['titleblock']={'title':'TẤM LẮP - BẢN MẪU','drawing_number':'DEMO-M-001','revision':'A','author':'CAD AGENT','material':'TBD'}
    job['plot']={'enabled':True,'pdf':True,'ctb':'monochrome.ctb'}
    return validate_job(job)


def main():
    home=workspace();job=demo_job()
    check=api.validate(job)
    if check['status']!='VALID_INPUT':raise RuntimeError(check)
    preview=api.preview(job)
    result=create_dwg(job,home)
    report={'job':job,'validation':check,'preview':preview,'native':result}
    atomic_json(home/'reports'/'drafting_demo.json',report)
    print(json.dumps(result,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
