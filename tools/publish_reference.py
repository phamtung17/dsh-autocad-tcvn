"""Trusted local CLI: import an inspected profile, plan or publish a new package."""
import argparse
import json
import sys
from pathlib import Path
from autocad_agent.reference_profiles import import_inspected_profile,reference_plan


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='command',required=True)
    imp=sub.add_parser('import');imp.add_argument('profile_id');imp.add_argument('inspection_directory')
    plan=sub.add_parser('plan');plan.add_argument('job')
    publish=sub.add_parser('publish');publish.add_argument('job')
    a=p.parse_args()
    if a.command=='import':
        profile=import_inspected_profile(a.profile_id,a.inspection_directory)
        print(json.dumps({'id':profile['id'],'sheets':len(profile['sheets']),'issues':len(profile['issues'])}));return
    job=json.loads(Path(a.job).read_text(encoding='utf-8'))
    if a.command=='plan':print(json.dumps(reference_plan(job),ensure_ascii=False,indent=2));return
    from autocad_agent.reference_publish import publish_reference
    def progress(row):print(f"Published {row['id']}: {row['drawing']} / {row['layout']}",flush=True)
    report=publish_reference(job,progress)
    print(json.dumps({'status':report['status'],'pages':report['page_count'],'pdf':report['combined_pdf']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
