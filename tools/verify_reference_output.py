"""Check published native PDF set, original assets and representative DWG content."""
import argparse
from collections import Counter
import json
from pathlib import Path
import uuid
import zipfile
from autocad_agent.reference_profiles import load_profile,profile_root,digest
from autocad_agent.runtime import atomic_json
from autocad_agent.cad_com import retry_com as retry


def verify(profile_id,project_dir,native_files=None):
    import pymupdf
    from PIL import Image,ImageDraw
    profile=load_profile(profile_id);target=Path(project_dir).resolve(strict=True)
    publication=json.loads((target/'PUBLISH_REPORT.json').read_text(encoding='utf-8'))
    if publication['status']!='PUBLISHED_REFERENCE_REQUIRES_VISUAL_REVIEW':raise ValueError('Publication incomplete')
    sheets={s['id']:s for s in profile['sheets']}
    images=target/'QA';images.mkdir(exist_ok=True)
    evidence={'status':'PDF_AND_ORIGINALS_CHECKED','sheets':[],'native_drawings':[],
              'profile_id':profile_id,'tcvn_compliance':'NOT_CHECKED'}
    originals=Path(profile['source_directory'])
    evidence['originals_unchanged']=all(digest(originals/a['name'])==a['sha256'] for a in profile['assets'])
    assert evidence['originals_unchanged']
    with pymupdf.open(publication['combined_pdf']) as book:
        assert len(book)==publication['page_count']==len(publication['sheets'])
        thumbnails=[]
        for i,row in enumerate(publication['sheets']):
            page=book[i];pix=page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2),colorspace=pymupdf.csRGB)
            path=images/(row['id']+'.png');pix.save(str(path))
            image=Image.open(path).convert('RGB')
            extrema=image.convert('L').getextrema()
            assert extrema[0]<180,'Blank rendered page: '+row['id']
            thumb=image.copy();thumb.thumbnail((390,285))
            cell=Image.new('RGB',(410,320),'#e8ebee');cell.paste(thumb,((410-thumb.width)//2,8))
            draw=ImageDraw.Draw(cell);draw.text((8,298),f"{i+1:02d} {row['id']} {row['role']}",fill='black')
            thumbnails.append(cell)
            evidence['sheets'].append({'id':row['id'],'page':i+1,'page_mm':row['page_mm'],
                                      'rendered':str(path),'nonblank':True,'viewport_count':row['viewport_count']})
        for start in range(0,len(thumbnails),12):
            batch=thumbnails[start:start+12];canvas=Image.new('RGB',(410*3,320*4),'white')
            for j,thumb in enumerate(batch):canvas.paste(thumb,((j%3)*410,(j//3)*320))
            canvas.save(images/f'CONTACT_{start//12+1:02d}.png')
    if native_files:
        import ezdxf
        import pythoncom
        import win32com.client as win32
        pythoncom.CoInitialize()
        try:
            app=win32.gencache.EnsureDispatch(win32.GetActiveObject('AutoCAD.Application'))
            for name in native_files:
                source=next(d for d in profile['drawings'] if d['name']==name)
                path=target/'DWG'/name;doc=None
                exported=images/(Path(name).stem+'_'+uuid.uuid4().hex[:6]+'.dxf')
                try:
                    doc=retry(lambda:app.Documents.Open(str(path),True),timeout=45)
                    retry(lambda:doc.SaveAs(str(exported),win32.constants.ac2013_dxf),timeout=45)
                finally:
                    if doc is not None:retry(lambda:doc.Close(False),timeout=45)
                cad=ezdxf.readfile(exported)
                model=dict(Counter(e.dxftype() for e in cad.modelspace()))
                assert model==source['model_entity_types'],(name,'Model entity types differ')
                for s in (s for s in profile['sheets'] if s['drawing']==name):
                    layout=cad.layouts.get(s['layout'])
                    actual=dict(Counter(e.dxftype() for e in layout))
                    assert actual==s['entity_types'],(name,s['layout'],'Layout entities differ')
                    for expected in s['viewports']:
                        vp=cad.entitydb.get(expected['handle'])
                        assert vp is not None and vp.dxftype()=='VIEWPORT'
                        assert abs(vp.dxf.view_height-expected['view_height'])<1e-6
                        # AutoCAD may reorder stored layer handles on save;
                        # frozen-layer membership, not list order, is semantic.
                        assert set(vp.frozen_layers)==set(expected['frozen_layers'])
                evidence['native_drawings'].append({'name':name,'model_types':model,'layout_types_match':True,
                                                    'viewport_scale_and_frozen_layers_match':True,'dxf':str(exported)})
        finally:pythoncom.CoUninitialize()
    evidence['page_count']=len(evidence['sheets'])
    evidence['visual_review']='Contact sheets and selected full-resolution pages require inspection'
    atomic_json(target/'VERIFICATION.json',evidence)
    archive=target.with_suffix('.zip')
    if archive.exists():raise FileExistsError(archive)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in target.rglob('*'):
            if not file.is_file() or file.suffix.lower() in {'.dwl','.dwl2','.bak','.log','.dxf'}:continue
            z.write(file,file.relative_to(target))
    print(json.dumps({'status':evidence['status'],'pages':evidence['page_count'],'originals_unchanged':True,
                      'native_drawings_checked':len(evidence['native_drawings']),'package':str(archive)},ensure_ascii=True))
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('project_dir');p.add_argument('--native',nargs='*')
    a=p.parse_args();verify(a.profile,a.project_dir,a.native)
