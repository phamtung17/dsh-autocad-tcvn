"""Real Windows/AutoCAD 2025 integration test. NOT run by public CI.

Starts only after a human invokes this script; creates NEW unique DWG,
opens it again, measures geometry/dims/blocks; optionally produces PDF.
Never modifies existing drawings or shuts down AutoCAD.
"""
from __future__ import annotations
import argparse
import json
import sys
import uuid
from pathlib import Path


def run(pdf=False,dwt=None):
    if sys.platform!='win32':raise RuntimeError('Windows + AutoCAD 2025 required; cannot run on Linux')
    from autocad_agent.templates import create_template
    from autocad_agent.cad_com import create_dwg,retry_com
    from autocad_agent.runtime import workspace
    import pythoncom
    import win32com.client
    name='INTEGRATION_2025_'+uuid.uuid4().hex[:12]+'.dwg'
    job=create_template('mechanical',name=name,width=200,height=100)
    job['blocks']=[{'name':'TEST_MARK','entities':[{'id':'b-line','type':'line','start':[0,0],'end':[4,0]}]}]
    job['geometry'].append({'id':'test-insert','type':'insert','block':'TEST_MARK','layer':'TEST_BLOCK',
                            'position':[40,40],'rotation':0,'scale':1})
    job['plot']={'enabled':bool(pdf),'pdf':bool(pdf),'dwt':dwt}
    home=workspace()
    result=create_dwg(job,home)  # explicit developer smoke test, not model-exposed MCP tool
    path=Path(result['output'])
    if not path.is_file():raise RuntimeError('DWG output missing')
    pythoncom.CoInitialize()
    inspected=None
    try:
        app=win32com.client.GetActiveObject('AutoCAD.Application')
        if not str(app.Version).startswith('25.'):
            raise RuntimeError('Expected AutoCAD 2025 COM version 25.x')
        inspected=retry_com(lambda:app.Documents.Open(str(path)))
        actual_units=retry_com(lambda:inspected.GetVariable('INSUNITS'))
        if actual_units!=4:raise AssertionError(f'expected mm INSUNITS 4; got {actual_units}')
        space=retry_com(lambda:inspected.ModelSpace)
        entities=[retry_com(lambda i=i:space.Item(i)) for i in range(retry_com(lambda:space.Count))]
        types={}
        circles=[]; dimensions=[]; blockrefs=[]; polylines=[]
        for entity in entities:
            kind=retry_com(lambda:str(entity.ObjectName))
            types[kind]=types.get(kind,0)+1
            if kind=='AcDbCircle':circles.append(win32com.client.CastTo(entity,'IAcadCircle'))
            if kind.startswith('AcDb') and 'Dimension' in kind:
                interface={'AcDbAlignedDimension':'IAcadDimAligned',
                           'AcDbDiametricDimension':'IAcadDimDiametric',
                           'AcDbRotatedDimension':'IAcadDimRotated',
                           'AcDbRadialDimension':'IAcadDimRadial'}.get(kind)
                if not interface:raise AssertionError('unhandled dimension interface: '+kind)
                dimensions.append(win32com.client.CastTo(entity,interface))
            if kind=='AcDbBlockReference':blockrefs.append(win32com.client.CastTo(entity,'IAcadBlockReference'))
            if kind=='AcDbPolyline':polylines.append(win32com.client.CastTo(entity,'IAcadLWPolyline'))
        if not any(abs(float(c.Radius)-13.0)<1e-6 for c in circles):
            raise AssertionError('expected template hole circle R13 not found')
        if not any(str(b.Name)=='TEST_MARK' for b in blockrefs):
            raise AssertionError('block insert TEST_MARK not found')
        if len(dimensions)<3:raise AssertionError('expected at least 3 associative dimension entities')
        if not any(bool(p.Closed) for p in polylines):raise AssertionError('expected closed outline polyline')
        # Verify dimensions by their actual AutoCAD Measurement, NOT displayed dimension text.
        measured=[]
        for dim in dimensions:
            measured.append(retry_com(lambda:float(dim.Measurement)))
        if not any(abs(v-200)<0.01 for v in measured):
            raise AssertionError(f'width dimension Measurement != 200mm: {measured}')
        if not any(abs(v-100)<0.01 for v in measured):
            raise AssertionError(f'height dimension Measurement != 100mm: {measured}')
        layers={str(l.Name) for l in inspected.Layers}
        for layer in ('M-OUTLINE','M-HOLE','M-DIM','TEST_BLOCK'):
            if layer not in layers:raise AssertionError(f'missing layer {layer}')
        pages=[]
        if pdf:
            if not result.get('pdf_output') or not Path(result['pdf_output']).is_file():
                raise AssertionError('PDF output missing')
            from pypdf import PdfReader
            pages=PdfReader(result['pdf_output']).pages
            if len(pages)!=1:raise AssertionError('PDF pages should be one')
        return {'status':'REAL_AUTOCAD_2025_REGRESSION_PASS_REQUIRES_VISUAL_REVIEW',
                'cad_version':str(app.Version),'dwg':str(path),'entity_types':types,
                'dimension_measurements':measured,'circle_radii':[float(c.Radius) for c in circles],
                'block_names':[str(b.Name) for b in blockrefs],
                'pdf':result.get('pdf_output'),'pdf_page_count':len(pages),
                'tcvn_compliance':'NOT_CHECKED',
                'note':'Script confirmed sampled CAD geometry after reopening. Engineer must still review dimension placement, layout, fonts, lineweights, print scale and TCVN.'}
    finally:
        # Don't close any document; keep output visible for operator review.
        pythoncom.CoUninitialize()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',action='store_true',help='Require installed DWG To PDF.pc3 and matching A3 media')
    parser.add_argument('--dwt',default=None,help='Optional approved DWT filename (in CAD_DWT_DIR)')
    args=parser.parse_args()
    result=run(pdf=args.pdf,dwt=args.dwt)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    from autocad_agent.runtime import atomic_json,workspace
    atomic_json(workspace()/'reports'/'autocad_2025_real_regression_latest.json',result)

if __name__=='__main__':main()
