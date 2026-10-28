"""Trusted CLI for new parametric design. Does not read reference drawings."""
import argparse,json,sys
from pathlib import Path
from autocad_agent.fitout_design import demo_spec
from autocad_agent.detailed_publish import publish_new_design

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    p=argparse.ArgumentParser();p.add_argument('--input');p.add_argument('--project-id');p.add_argument('--sheets',help='Trusted CLI regeneration only; comma-separated sheet codes, not a full delivery');a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding='utf-8')) if a.input else {'spec':demo_spec(),'branding':{}}
    if a.project_id:data['spec']['project_id']=a.project_id
    result=publish_new_design(data['spec'],data.get('branding'),progress=lambda r:print(r['code']+' native tables='+str(r['native_tables']),flush=True),sheet_codes=a.sheets.split(',') if a.sheets else None)
    print(json.dumps({'status':result['status'],'pdf':result['combined_pdf'],'sheets':result['sheet_count']},ensure_ascii=True))
