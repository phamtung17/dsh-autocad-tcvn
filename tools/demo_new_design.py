"""Generate a brand-new detailed studio set. No reference drawing is loaded."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from autocad_agent.fitout_design import demo_spec
from autocad_agent.design_dispatch import build_project
from autocad_agent.branding import normalize_brand
from autocad_agent.detailed_sheets import make_sheet_dxf,render_sheet_pdf
from autocad_agent.runtime import atomic_json


def generate(output,spec=None,branding=None):
    from pypdf import PdfWriter
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    project=build_project(spec or demo_spec());brand=normalize_brand(branding)
    report={'generator':project['generator'],'spec':project['spec'],'brand':brand,'sheets':[],
            'source_geometry':'Generated from parameters. No reference DWG/DXF input.','workflow':project.get('workflow'),
            'counts':dict(Counter(e['type'] for s in project['sheets'] for e in s['job']['geometry']))}
    writer=PdfWriter()
    for i,sheet in enumerate(project['sheets'],1):
        dxf=output/(sheet['code']+'.dxf');pdf=output/(sheet['code']+'.pdf')
        result=make_sheet_dxf(sheet,project['spec'],brand,dxf,i,len(project['sheets']))
        result['pdf']=render_sheet_pdf(dxf,pdf,sheet['code']);report['sheets'].append(result)
        writer.append(pdf,outline_item=sheet['code']+' '+sheet['title'])
        print(sheet['code']+' '+str(len(sheet['job']['geometry']))+' generated entities',flush=True)
    with (output/'NEW_STUDIO_PREVIEW.pdf').open('wb') as f:writer.write(f)
    atomic_json(output/'GENERATION_REPORT.json',report)
    atomic_json(output/'DESIGN_INPUT.json',{'spec':project['spec'],'branding':brand})
    return project,report


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    p=argparse.ArgumentParser();p.add_argument('output');args=p.parse_args();generate(args.output)
