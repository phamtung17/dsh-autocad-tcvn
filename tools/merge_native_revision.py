"""Trusted local assembly of a full verified base and selected regenerated sheets.

Always creates a new directory, preserves ordinal sheet labels, and rechecks the
entire resulting set against the CURRENT model before sealing the handover.
"""
import argparse,json,shutil,hashlib
from copy import deepcopy
from pypdf import PdfWriter
from autocad_agent.runtime import workspace,atomic_json
from autocad_agent.reference_profiles import checked_id
from autocad_agent.design_dispatch import build_project
from autocad_agent.project_delivery import verify_delivery,write_delivery_index,seal_delivery
from tools.verify_building_output import verify

def merge(base_id,revision_id,target_id):
    for value in (base_id,revision_id,target_id):checked_id(value)
    home=workspace()/'generated_projects';base=home/base_id;revision=home/revision_id;target=home/target_id
    assert verify_delivery(base_id)['status']=='INTEGRITY_CHECKED'
    read=lambda root,name:json.loads((root/name).read_text(encoding='utf-8'))
    original=read(base,'GENERATION_REPORT.json');patch=read(revision,'GENERATION_REPORT.json')
    assert patch['status']=='PARTIAL_NATIVE_REGEN_NOT_A_FULL_DELIVERY'
    left=read(base,'DESIGN_INPUT.json');right=read(revision,'DESIGN_INPUT.json')
    a,b=deepcopy(left),deepcopy(right);a['spec'].pop('project_id');b['spec'].pop('project_id')
    assert a==b,'Input model or branding changed; full regeneration required'
    left['spec']['project_id']=target_id;project=build_project(left['spec']);assert not project['workflow']['issues']
    ids={s['code'] for s in project['sheets']};assert {r['code'] for r in original['sheets']}==ids
    assert patch['source_sheet_count']==len(ids) and {r['code'] for r in patch['sheets']}<=ids
    target.mkdir();(target/'DWG').mkdir();(target/'PDF').mkdir()
    selected={r['code']:r for r in patch['sheets']};report=deepcopy(original);rows=[];origins=[]
    for old in original['sheets']:
        code=old['code'];source=revision if code in selected else base;row=deepcopy(selected.get(code,old))
        for key,folder,filename in [('dwg','DWG',code+'.dwg'),('dxf','DWG',code+'_native.dxf'),('pdf','PDF',code+'.pdf')]:
            src=source/folder/filename;dest=target/folder/filename;shutil.copy2(src,dest);row[key]=str(dest)
            origins.append({'path':dest.relative_to(target).as_posix(),'source_project':source.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        rows.append(row)
    for root in (base,revision):
        assets=root/'DWG'/'assets'
        if assets.exists():shutil.copytree(assets,target/'DWG'/'assets',dirs_exist_ok=True)
    writer=PdfWriter()
    for row in rows:writer.append(row['pdf'],outline_item=row['code']+' '+row['title'])
    combined=target/'NEW_DESIGN_DRAWING_SET.pdf'
    with combined.open('xb') as f:writer.write(f)
    report.update(spec=project['spec'],sheets=rows,workflow=project['workflow'],quantities=project['takeoff'],
                  output_directory=str(target),combined_pdf=str(combined),sheet_count=len(rows),
                  status='NATIVE_REVISION_ASSEMBLED_NEEDS_VISUAL_REVIEW',revision_sources=origins)
    atomic_json(target/'DESIGN_INPUT.json',left);report['delivery']=write_delivery_index(target,report,project)
    atomic_json(target/'GENERATION_REPORT.json',report);seal_delivery(target);result=verify(target_id)
    return {'status':result['status'],'sheets':result['sheet_count'],'regenerated':list(selected),'pdf':str(combined)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('revision');p.add_argument('target');a=p.parse_args()
    print(json.dumps(merge(a.base,a.revision,a.target),ensure_ascii=True))
