"""User-selected title block identity and local logo/frame assets."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import shutil
from .schema import text,finite,JobError
from .reference_profiles import checked_id
from .runtime import workspace,atomic_json


def asset_root():
    root=Path(os.environ.get('CAD_BRAND_DIR',str(workspace()/'brand_assets'))).resolve();root.mkdir(parents=True,exist_ok=True);return root


def normalize_brand(raw=None):
    raw=raw or {}
    if not isinstance(raw,dict):raise JobError('branding must be an object')
    allowed={'company','wordmark','owner','designer','checker','revision','project_code','confirmed','logo_asset','frame_asset','column_width','contact'}
    if set(raw)-allowed:raise JobError('Unknown branding field')
    result={'company':'boyxpxt.io.vn','wordmark':'boyxpxt.io.vn','owner':'DEMO',
            'designer':'DEMO','checker':'CHƯA DUYỆT','revision':'A','project_code':'BXP-STUDIO',
            'confirmed':False,'logo_asset':None,'frame_asset':None,'column_width':64,'contact':'boyxpxt.io.vn'}
    result.update(raw)
    for key in ('company','wordmark','owner','designer','checker','revision','project_code','contact'):
        value=text(result[key],'branding.'+key,100)
        if any(c in value for c in ('\n','\r','\\','%<')):raise JobError('Branding fields must be plain text')
    if len(result['wordmark'])>40 or len(result['project_code'])>24:raise JobError('Wordmark/project code is too long for the title column')
    if type(result['confirmed'])is not bool:raise JobError('branding.confirmed must be boolean')
    result['column_width']=finite(result['column_width'],'column_width',positive=True)
    if not 58<=result['column_width']<=70:raise JobError('Title column must be 58..70mm')
    for key,kind in (('logo_asset','logo'),('frame_asset','frame')):
        if result[key] is not None:
            info=load_asset(result[key])
            if info['kind']!=kind:raise JobError('Asset kind mismatch')
    return result


def register_asset(asset_id,path,kind='logo'):
    """Trusted CLI registration, only after user supplies the intended file path."""
    checked_id(asset_id)
    if kind not in ('logo','frame'):raise JobError('kind must be logo or frame')
    source=Path(path).resolve(strict=True)
    suffix=source.suffix.lower()
    if suffix not in ({'.png','.jpg','.jpeg','.dxf'} if kind=='logo' else {'.dxf'}):
        raise JobError('Logos support PNG/JPG/DXF; title frames support DXF')
    if not source.is_file() or source.stat().st_size>20*1024*1024:raise JobError('Brand asset must be a file <=20MB')
    info={'id':asset_id,'kind':kind,'source_name':source.name,'suffix':suffix}
    if suffix=='.dxf':
        import ezdxf
        from ezdxf import bbox
        doc=ezdxf.readfile(source);audit=doc.audit()
        if audit.errors:raise JobError('Brand DXF failed structural audit')
        if any(b.block.dxf.flags&4 for b in doc.blocks):raise JobError('Brand asset cannot depend on Xrefs')
        ext=bbox.extents(doc.modelspace())
        if not ext.has_data:raise JobError('Brand DXF has no bounded geometry')
        info['bounds']=[ext.extmin.x,ext.extmin.y,ext.extmax.x,ext.extmax.y]
        if ext.size.x<=0 or ext.size.y<=0:raise JobError('Brand DXF must have two-dimensional extents')
        if kind=='frame' and (ext.size.x>421 or ext.size.y>298 or ext.size.x<300 or ext.size.y<200 or ext.extmin.x<-.5 or ext.extmin.y<-.5):
            raise JobError('Frame DXF must be drawn in paper mm inside A3 with origin near (0,0)')
        if kind=='frame' and any(e.dxftype() not in ('LINE','LWPOLYLINE','POLYLINE') for e in doc.modelspace()):
            raise JobError('Frame assets must be blank linework backgrounds matching the generated A3 right-column grid; filled title blocks are unsupported')
    else:
        from PIL import Image
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:info['pixel_size']=list(image.size)
    home=asset_root()/asset_id;home.mkdir() # never replace an existing asset
    dest=home/('asset'+suffix);shutil.copy2(source,dest)
    info.update({'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    atomic_json(home/'asset.json',info);return info


def load_asset(asset_id):
    checked_id(asset_id);home=asset_root()/asset_id
    info=json.loads((home/'asset.json').read_text(encoding='utf-8'))
    path=(home/info['file']).resolve()
    if path.parent!=home.resolve() or hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
        raise JobError('Brand asset modified or unsafe')
    return {**info,'path':str(path)}


def list_assets():
    return {'assets':[{k:v for k,v in load_asset(p.parent.name).items() if k!='path'} for p in asset_root().glob('*/asset.json')]}


def _import_vector(doc,asset,block_name):
    import ezdxf
    from ezdxf.addons import Importer
    source=ezdxf.readfile(asset['path']);block=doc.blocks.new(block_name)
    importer=Importer(source,doc);importer.import_modelspace(target_layout=block);importer.finalize()
    return block


def draw_titleblock(doc,layout,brand,spec,sheet,index,total,assets_directory):
    """Paper-space native vectors/attributes; no borrowed client identities."""
    assets_directory=Path(assets_directory);assets_directory.mkdir(parents=True,exist_ok=True)
    if brand['frame_asset']:
        frame=load_asset(brand['frame_asset']);_import_vector(doc,frame,'USER_TITLE_FRAME')
        layout.add_blockref('USER_TITLE_FRAME',(0,0))
    W,H=420,297;x=W-10-brand['column_width'];right=410
    for name,weight in [('P-FRAME',50),('P-TEXT',18),('P-VIEW-TITLE',25),('P-VPORT',0)]:
        if name not in doc.layers:doc.layers.new(name,dxfattribs={'color':7,'lineweight':weight,'plot':0 if name=='P-VPORT' else 1})
    a={'layer':'P-FRAME'}
    def line(p,q):layout.add_line(p,q,dxfattribs=a)
    def label(value,xx,yy,height=2.2,width=None,bold=False):
        return layout.add_mtext(value,dxfattribs={'layer':'P-TEXT','insert':(xx,yy),
                                'char_height':height,'width':width or brand['column_width']-6,
                                'style':'BRAND_BOLD' if bold else 'Standard'})
    if 'BRAND_BOLD' not in doc.styles:doc.styles.new('BRAND_BOLD',dxfattribs={'font':'arialbd.ttf'})
    if not brand['frame_asset']:
        layout.add_lwpolyline([(8,8),(412,8),(412,289),(8,289)],close=True,dxfattribs=a)
        line((x,8),(x,289))
        for y in (252,219,185,158,123,76,39,22):line((x,y),(412,y))
    if brand['logo_asset']:
        logo=load_asset(brand['logo_asset'])
        if logo['suffix']=='.dxf':
            _import_vector(doc,logo,'USER_LOGO')
            box=logo['bounds'];scale=min((brand['column_width']-10)/(box[2]-box[0]),23/(box[3]-box[1]))
            layout.add_blockref('USER_LOGO',(x+5-box[0]*scale,258-box[1]*scale),dxfattribs={'xscale':scale,'yscale':scale,'layer':'P-TEXT'})
        else:
            filename=logo['id']+logo['suffix'];shutil.copy2(logo['path'],assets_directory/filename)
            pw,ph=logo['pixel_size'];w=brand['column_width']-10;h=w*ph/pw
            if h>23:h=23;w=h*pw/ph
            image_def=doc.add_image_def('assets/'+filename,size_in_pixel=(pw,ph))
            layout.add_image(image_def,insert=(x+5,258),size_in_units=(w,h),dxfattribs={'layer':'P-TEXT'})
    else:
        wordmark=doc.blocks.new('CUSTOM_WORDMARK')
        letter_height=min(3.5,(brand['column_width']-8)/(.65*len(brand['wordmark'])))
        wordmark.add_text(brand['wordmark'],dxfattribs={'height':letter_height,'style':'BRAND_BOLD'})
        layout.add_blockref('CUSTOM_WORDMARK',(x+4,273),dxfattribs={'layer':'P-TEXT'})
    label(brand['company'],x+4,263,2.2)
    label('PROJECT / DỰ ÁN',x+3,248,1.6)
    label(spec['project_name'],x+3,241,2.5,bold=True)
    label('OWNER / CHỦ ĐẦU TƯ',x+3,215,1.6);label(brand['owner'],x+3,208)
    label('DESIGN / THIẾT KẾ',x+3,181,1.6);label(brand['designer'],x+3,174)
    label('CHECK / KIỂM TRA',x+3,154,1.6);label(brand['checker'],x+3,147)
    label('DRAWING / TÊN BẢN VẼ',x+3,119,1.6);label(sheet['title'],x+3,111,2.6,bold=True)
    # Editable block attributes for document identity.
    fields=doc.blocks.new('DRAWING_ID_FIELDS')
    fields.add_attdef('DRAWING_NO',(0,0),height=3,dxfattribs={'style':'BRAND_BOLD'})
    ref=layout.add_blockref('DRAWING_ID_FIELDS',(x+4,60),dxfattribs={'layer':'P-TEXT'})
    ref.add_auto_attribs({'DRAWING_NO':brand['project_code']+'-'+sheet['code']})
    label('REV '+brand['revision']+'   |   '+str(index)+' / '+str(total),x+4,51,2.3)
    scales=sorted({v['scale'] for v in sheet['views']})
    label('SCALE: '+('AS SHOWN' if len(scales)>1 else '1:'+f'{scales[0]:g}'),x+3,35,2.1)
    label('A3 / mm    |    '+('DEMO' if spec['mode']=='demo' else 'DESIGN REVIEW'),x+3,27,1.8)
    label(brand['contact'],x+3,18,2)
    label('KÍCH THƯỚC TỪ THÔNG SỐ ĐẦU VÀO / KIỂM TRA TRƯỚC THI CÔNG',10,294,1.7,width=x-12)
    return {'content_right':x-7,'logo':'asset' if brand['logo_asset'] else 'native_wordmark','company':brand['company']}
