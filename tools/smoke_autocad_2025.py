"""Run manually in Windows with AutoCAD 2025 OPEN. Creates a NEW demo drawing.
No existing file is modified. This test is NOT a CAD standards certification.
"""
import json
import sys
import uuid
from autocad_agent.api import probe_autocad
from autocad_agent.templates import create_template
from autocad_agent.cad_com import create_dwg
from autocad_agent.runtime import workspace


def main():
    print(json.dumps(probe_autocad(),ensure_ascii=False,indent=2),flush=True)
    if sys.platform!='win32':raise SystemExit('Windows required for AutoCAD smoke test')
    name='AUTOCAD2025_SMOKE_'+uuid.uuid4().hex[:8]+'.dwg'
    job=create_template('mechanical',name=name,width=200,height=100)
    result=create_dwg(job,workspace())
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['status']!='DWG_CREATED_NEEDS_VISUAL_REVIEW':raise SystemExit(2)
    print('Open the new DWG in AutoCAD; inspect geometry, dimensions, units and layers manually.')

if __name__=='__main__':main()
