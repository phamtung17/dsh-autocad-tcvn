"""Trusted CLI: save an existing combined DXF as one DWG; never plots PDF."""
from pathlib import Path
import argparse,json,hashlib
from collections import Counter
import ezdxf
from autocad_agent.autocad_session import connect,wait_idle
from autocad_agent.cad_com import retry_com
from autocad_agent.native_geometry import primitive_keys
from autocad_agent.runtime import atomic_json


def convert(source,target,cache):
    source=Path(source).resolve();target=Path(target).resolve();cache=Path(cache).resolve()
    if target.exists():raise FileExistsError('Existing output will not be overwritten')
    if source.suffix.lower()!='.dxf' or target.suffix.lower()!='.dwg':raise ValueError('Expected DXF input and DWG output')
    original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    original=ezdxf.readfile(source);audit=original.audit()
    if audit.errors:raise ValueError('Source DXF has unresolved audit errors')
    target.parent.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=False)
    staged=cache/'combined.dxf';native_path=cache/'readback_native.dxf'
    original.header['$TILEMODE']=1;original.saveas(staged)
    import pythoncom,win32com.client as win32
    pythoncom.CoInitialize();retry=lambda fn:retry_com(fn,45)
    try:
        app=connect();doc=retry(lambda:app.Documents.Open(str(staged)));wait_idle(app)
        retry(lambda:setattr(app,'Visible',True));retry(lambda:setattr(app,'WindowState',win32.constants.acMax))
        retry(lambda:doc.SetVariable('TILEMODE',1));retry(lambda:setattr(doc,'ActiveSpace',win32.constants.acModelSpace))
        retry(lambda:doc.Activate());retry(lambda:app.ZoomExtents());retry(lambda:doc.Regen(win32.constants.acAllViewports))
        retry(lambda:doc.SaveAs(str(target),win32.constants.ac2018_dwg))
        if target.read_bytes()[:6]!=b'AC1032':raise ValueError('Not a native DWG')
        retry(lambda:doc.SaveAs(str(native_path),win32.constants.ac2013_dxf))
        native=ezdxf.readfile(native_path);check=native.audit()
        if check.errors:raise ValueError('Native readback failed audit')
        if primitive_keys(original.modelspace(),True)!=primitive_keys(native.modelspace(),True):raise ValueError('Model primitive geometry changed')
        expected_layouts={l.name for l in original.layouts};actual_layouts={l.name for l in native.layouts}
        if expected_layouts!=actual_layouts:raise ValueError('Layout inventory changed')
        for name in expected_layouts-{'Model'}:
            if primitive_keys(original.layouts.get(name),True)!=primitive_keys(native.layouts.get(name),True):raise ValueError('Layout primitive geometry changed: '+name)
        expected=sorted(round(float(e.get_measurement()),5) for e in original.modelspace().query('DIMENSION'))
        actual=sorted(round(float(e.get_measurement()),5) for e in native.modelspace().query('DIMENSION'))
        if expected!=actual:raise ValueError('Dimension values changed')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=original_hash:raise ValueError('Source file changed during conversion')
        retry(lambda:doc.Close(False));doc=retry(lambda:app.Documents.Open(str(target)));wait_idle(app)
        report={'status':'ONE_DWG_NATIVE_READBACK_CHECKED','source':str(source),'dwg':str(target),'pdf_exported':False,
                'source_sha256':original_hash,'dwg_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                'layout_count':len(expected_layouts)-1,'model_entities':len(native.modelspace()),'model_types':dict(Counter(e.dxftype() for e in native.modelspace())),
                'active_space':'Model','dxf_audit_errors':len(check.errors),'source_audit_fixes':len(audit.fixes),'construction_release':False}
        atomic_json(cache/'CONVERSION_REPORT.json',report);return report
    finally:pythoncom.CoUninitialize()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('target');p.add_argument('--cache',required=True);a=p.parse_args()
    print(json.dumps(convert(a.source,a.target,a.cache),ensure_ascii=True))
