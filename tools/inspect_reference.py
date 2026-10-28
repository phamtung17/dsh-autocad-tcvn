"""Read user-authorized DWG package via isolated copies; never save originals."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time
import sys
from autocad_agent.runtime import atomic_json
from autocad_agent.cad_com import retry_com as retry


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def native_title_blocks(layout,win32):
    blocks=[];space=retry(lambda:layout.Block)
    for i in range(retry(lambda:space.Count)):
        entity=retry(lambda i=i:space.Item(i))
        if retry(lambda:str(entity.ObjectName))!='AcDbBlockReference':continue
        insert=win32.CastTo(entity,'IAcadBlockReference')
        if not retry(lambda:insert.HasAttributes):continue
        attributes=retry(lambda:insert.GetAttributes())
        values={retry(lambda a=a:str(a.TagString)):retry(lambda a=a:str(a.TextString)) for a in attributes}
        if values:blocks.append({'handle':retry(lambda:str(insert.Handle)),'name':retry(lambda:str(insert.Name)),'attributes':values})
    return blocks


def inspect(source,output):
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    import pythoncom
    import win32com.client as win32
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    staged=output/'source';exports=output/'dxf'
    staged.mkdir(parents=True,exist_ok=True);exports.mkdir(exist_ok=True)
    inventory=[]
    for path in source.iterdir():
        if path.is_file() and path.suffix.lower() in {'.dwg','.ctb','.pc3','.dst','.txt'}:
            dest=staged/path.name;digest=sha(path)
            if dest.exists() and sha(dest)!=digest:raise FileExistsError('Different staged asset: '+str(dest))
            if not dest.exists():shutil.copy2(path,dest)
            inventory.append({'name':path.name,'bytes':path.stat().st_size,'sha256':digest})
    report={'source':str(source),'staged':str(staged),'assets':inventory,'drawings':[]}
    previous={}
    if (output/'native_inventory.json').exists():
        previous={row['name']:row for row in json.loads((output/'native_inventory.json').read_text(encoding='utf-8'))['drawings']}
    pythoncom.CoInitialize()
    try:
        app=win32.gencache.EnsureDispatch(win32.GetActiveObject('AutoCAD.Application'))
        retry(lambda:setattr(app,'Visible',True))
        report['cad_version']=retry(lambda:str(app.Version))
        for asset in inventory:
            if not asset['name'].lower().endswith('.dwg'):continue
            path=staged/asset['name'];dxf=exports/(path.stem+'.dxf')
            if path.name in previous and dxf.is_file() and previous[path.name]['status']=='EXPORTED_FOR_INSPECTION':
                cached=previous[path.name]
                if path.name.casefold().startswith(('xref','frame')) or all('title_blocks' in l for l in cached['layouts'] if not l['ModelType']):
                    report['drawings'].append(cached);continue
            item={'name':path.name,'dxf':str(dxf),'layouts':[]}
            doc=None
            try:
                doc=retry(lambda:app.Documents.Open(str(path),True),timeout=30)
                layouts=retry(lambda:doc.Layouts)
                for i in range(retry(lambda:layouts.Count)):
                    layout=retry(lambda i=i:layouts.Item(i))
                    data={}
                    for attr in ('Name','TabOrder','ModelType','ConfigName','CanonicalMediaName',
                                 'StyleSheet','PlotRotation','PaperUnits','PlotType','UseStandardScale','StandardScale'):
                        try:data[attr]=retry(lambda attr=attr:getattr(layout,attr))
                        except Exception as exc:data[attr]={'error':str(exc)[:150]}
                    if not data['ModelType'] and not path.name.casefold().startswith(('xref','frame')):
                        # Native 2018 multilined attributes can acquire synthetic
                        # *_001 tags when saved as 2013 DXF. Use actual COM tags.
                        data['title_blocks']=native_title_blocks(layout,win32)
                    item['layouts'].append(data)
                if not dxf.exists():retry(lambda:doc.SaveAs(str(dxf),win32.constants.ac2013_dxf),timeout=30)
                item['status']='EXPORTED_FOR_INSPECTION'
                print('Inspected '+path.name+' layouts='+str(len(item['layouts'])),flush=True)
            except Exception as exc:
                item['status']='FAILED';item['error']=str(exc)
                print('FAILED '+path.name+': '+str(exc),flush=True)
            finally:
                if doc is not None:
                    try:retry(lambda:doc.Close(False))
                    except Exception:pass
            report['drawings'].append(item)
            atomic_json(output/'native_inventory.json',report)
    finally:pythoncom.CoUninitialize()
    report['originals_unchanged']=all(sha(source/entry['name'])==entry['sha256'] for entry in inventory)
    atomic_json(output/'native_inventory.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
    inspect(a.source,a.output)
