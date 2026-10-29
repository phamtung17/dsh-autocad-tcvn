"""Traceable handover files; demonstration is never labelled construction release."""
import csv,hashlib
from .runtime import atomic_json

def write_delivery_index(target,report,project):
    with (target/'SHEET_INDEX.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['code','title','stage','role','floor','dwg','pdf','revision'])
        for row in report['sheets']:writer.writerow([row['code'],row['title'],row['stage'],row['role'],row['floor'],
                                                   report.get('dwg_relative_path','DWG/PROJECT.dwg') if report.get('output_mode')=='SINGLE_DWG_MULTIPLE_LAYOUTS' else 'DWG/'+row['code']+'.dwg',
                                                   'PDF/'+row['code']+'.pdf' if report.get('pdf_exported',True) else '',project['spec']['revision']])
    with (target/'TAKEOFF_COST.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(project['takeoff'][0]));writer.writeheader();writer.writerows(project['takeoff'])
    atomic_json(target/'WORKFLOW_QA.json',project['workflow'])
    return {'status':'DEMO_REVIEW_PACKAGE' if project['spec']['mode']=='demo' else 'DESIGN_REVIEW_PACKAGE',
            'construction_release':False,'release_status':project['workflow']['release_status'],
            'sheet_index':str(target/'SHEET_INDEX.csv'),'quantities_cost':str(target/'TAKEOFF_COST.csv'),
            'release_blockers':project['workflow']['release_blockers']}

def seal_delivery(target):
    rows=[]
    for path in sorted(target.rglob('*')):
        if not path.is_file() or path.name=='DELIVERY_MANIFEST.json':continue
        if path.suffix.lower()=='.dxf' and not path.name.endswith('_native.dxf'):continue
        if path.suffix.lower() in ('.bak','.dwl','.dwl2','.log'):continue
        rows.append({'path':path.relative_to(target).as_posix(),'bytes':path.stat().st_size,
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    atomic_json(target/'DELIVERY_MANIFEST.json',{'files':rows,'construction_release':False,'reference_geometry_read':False})
    return rows

def verify_delivery(project_id):
    import json
    from .runtime import workspace
    from .reference_profiles import checked_id
    checked_id(project_id);root=(workspace()/'generated_projects'/project_id).resolve()
    for name in ('DELIVERY_MANIFEST.json','GENERATION_REPORT.json'):
        if not (root/name).is_file():return {'status':'HANDOVER_BLOCKED','issues':[{'path':name,'type':'MISSING_FILE'}],'construction_release':False}
    value=json.loads((root/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'));problems=[]
    for row in value['files']:
        path=(root/row['path']).resolve()
        if not path.is_relative_to(root):raise ValueError('Unsafe delivery manifest path')
        if not path.is_file():problems.append({'path':row['path'],'type':'MISSING_FILE'})
        elif path.stat().st_size!=row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            problems.append({'path':row['path'],'type':'FILE_CHANGED'})
    report=json.loads((root/'GENERATION_REPORT.json').read_text(encoding='utf-8'))
    if report.get('sheet_count',len(report['sheets']))!=len(report['sheets']):problems.append({'type':'SHEET_COUNT_MISMATCH'})
    if report.get('workflow') and {r.get('stage') for r in report['sheets']}!=set(range(1,15)):
        problems.append({'type':'INCOMPLETE_WORKFLOW_STAGES'})
    for sheet in report['sheets']:
        for folder,suffix in [('DWG','.dwg'),('PDF','.pdf'),('DWG','_native.dxf')]:
            if folder=='PDF' and not report.get('pdf_exported',True):continue
            if suffix=='_native.dxf' and not report.get('native_dxf_delivery',True):continue
            code='PROJECT' if report.get('output_mode')=='SINGLE_DWG_MULTIPLE_LAYOUTS' and folder=='DWG' else sheet['code']
            path=f"{folder}/{code}{suffix}"
            if suffix=='.dwg' and report.get('dwg_relative_path'):path=report['dwg_relative_path']
            if not any(r['path']==path for r in value['files']):problems.append({'path':path,'type':'MISSING_MANIFEST_ENTRY'})
    return {'status':'INTEGRITY_CHECKED' if not problems else 'HANDOVER_BLOCKED','sheet_count':len(report['sheets']),
            'checked_files':len(value['files']),'issues':problems,'construction_release':False,
            'note':'Integrity against local manifest; engineering approval is a separate requirement.'}
