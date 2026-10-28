"""Measured, hashed native drawing profiles; no synthetic compliance claims.

Profiles keep proprietary DWG/CTB assets local. Geometry remains in native DWG
so dynamic blocks, hatches, tables, leaders, viewport overrides and Xrefs survive.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path,PureWindowsPath
import hashlib
import json
import os
import re
import shutil
from .runtime import atomic_json,workspace

ID_RE=re.compile(r'^[a-z][a-z0-9_-]{0,47}$')
ASSET_SUFFIXES={'.dwg','.ctb','.pc3','.dst','.txt'}


def profile_root():
    root=Path(os.environ.get('CAD_PROFILE_DIR',str(workspace()/'profiles'))).resolve()
    root.mkdir(parents=True,exist_ok=True)
    return root


def checked_id(value):
    if not isinstance(value,str) or not ID_RE.fullmatch(value):raise ValueError('Invalid profile/project ID')
    return value


def basename(value):
    return PureWindowsPath(str(value).replace('/','\\')).name


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_asset(root,name):
    if not isinstance(name,str) or basename(name)!=name or name in ('.','..') or ':' in name:
        raise ValueError('Asset must be a basename')
    root=Path(root).resolve();path=(root/name).resolve()
    if path.parent!=root:raise ValueError('Asset escapes profile')
    return path


def role_for(filename,layout):
    name=(filename+' '+layout).upper()
    if 'TO BIA' in name:return 'cover'
    if 'DRAWING LIST' in name:return 'drawing_list'
    if 'WALL SECTION' in name:return 'wall_section'
    if 'WALL DETAILS' in name:return 'wall_detail'
    if 'FLOOR DETAILS' in name:return 'floor_detail'
    if 'CEILING DETAILS' in name:return 'ceiling_detail'
    if filename.startswith('104'):return 'elevation_location' if layout.lower()=='mb' else 'elevation'
    for word,role in [('EXISTING','existing'),('DIMENSION','dimension'),('WALL CONSTRUCTION','wall_construction'),
                      ('WALL FINISHED','wall_finish'),('SKIRTING','skirting'),('FLOOR PLAN','floor'),
                      ('COMBINE','mep_coordination'),('LIGHTING','lighting'),('CEILING FINISHED','ceiling'),('SOCKET','socket')]:
        if word in name:return role
    return 'other'


def _font_files():
    roots=[Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts',
           Path(os.environ.get('PROGRAMFILES',r'C:\Program Files'))/'Autodesk'/'AutoCAD 2025'/'Fonts',
           Path(os.environ.get('PROGRAMFILES',r'C:\Program Files'))/'Autodesk'/'AutoCAD 2025'/'Support']
    names=set()
    for root in roots:
        if root.is_dir():
            for p in root.iterdir():
                if p.is_file():names.update((p.name.casefold(),p.stem.casefold()))
    return names


def native_model_viewports(layout):
    ports=list(layout.query('VIEWPORT'))
    primary=layout.main_viewport()
    # AutoCAD writes id=status=0 for every viewport in inactive native layouts.
    # In those layouts the first VIEWPORT is the primary paper display. It is
    # affected by window size and must not be mistaken for a model viewport.
    if primary is None and ports and ports[0].dxf.id==0 and ports[0].dxf.status==0:
        primary=ports[0]
    return [p for p in ports if p is not primary]


def import_inspected_profile(profile_id,inspection_dir):
    """Trusted local CLI import after native inspection of user-selected files."""
    import ezdxf
    checked_id(profile_id);inspection=Path(inspection_dir).resolve(strict=True)
    inventory=json.loads((inspection/'native_inventory.json').read_text(encoding='utf-8'))
    if not inventory.get('originals_unchanged'):raise ValueError('Native inventory must verify unchanged originals')
    home=profile_root()/profile_id
    if home.exists():raise FileExistsError('Profile already exists; use a new ID')
    home.mkdir();assets=home/'assets';assets.mkdir()
    manifest={'id':profile_id,'schema_version':1,'source_directory':inventory['source'],
              'cad_version':inventory['cad_version'],'assets':[],'drawings':[],'sheets':[],
              'required_roles':[],'issues':[],'tcvn_compliance':'NOT_CHECKED'}
    try:
        for asset in inventory['assets']:
            source=safe_asset(inspection/'source',asset['name'])
            if digest(source)!=asset['sha256']:raise ValueError('Inspected asset changed: '+asset['name'])
            shutil.copy2(source,assets/source.name)
            manifest['assets'].append(asset)
        available={x['name'].casefold() for x in manifest['assets']};font_files=_font_files()
        for row in inventory['drawings']:
            if row['status']!='EXPORTED_FOR_INSPECTION':raise ValueError('Drawing inspection failed: '+row['name'])
            doc=ezdxf.readfile(row['dxf']);is_reference=row['name'].casefold().startswith(('xref','frame'))
            drawing={'name':row['name'],'reference_only':is_reference,'layers':len(doc.layers),
                     'blocks':len(doc.blocks),'model_entity_types':dict(Counter(e.dxftype() for e in doc.modelspace())),
                     'xrefs':[],'fonts':[]}
            for block in doc.blocks:
                if block.block.dxf.flags&4:
                    ref={'block':block.name,'path':block.block.dxf.get('xref_path','')}
                    ref['asset']=basename(ref['path']);ref['resolved']=ref['asset'].casefold() in available
                    drawing['xrefs'].append(ref)
                    if not ref['resolved']:manifest['issues'].append({'level':'BLOCKING','kind':'XREF_MISSING','file':row['name'],**ref})
            for style in doc.styles:
                for key in ('font','bigfont'):
                    value=style.dxf.get(key,'')
                    if not value:continue
                    font=basename(value);resolved=font.casefold() in font_files or Path(font).stem.casefold() in font_files
                    drawing['fonts'].append({'style':style.dxf.name,'file':font,'resolved':resolved})
                    if not resolved:manifest['issues'].append({'level':'WARNING','kind':'FONT_MISSING','file':row['name'],'style':style.dxf.name,'font':font})
            manifest['drawings'].append(drawing)
            if is_reference:continue
            for layout in sorted((l for l in doc.layouts if l.name!='Model'),key=lambda l:l.dxf.taborder):
                settings=layout.dxf;attribute_blocks=[]
                for insert in layout.query('INSERT'):
                    if insert.attribs:
                        attribute_blocks.append({'handle':insert.dxf.handle,'name':insert.dxf.name,
                                                 'attributes':{a.dxf.tag:a.dxf.text for a in insert.attribs}})
                native_layout=next((l for l in row.get('layouts',[]) if l.get('Name')==layout.name),{})
                if 'title_blocks' in native_layout:attribute_blocks=native_layout['title_blocks']
                ports=[]
                for vp in native_model_viewports(layout):
                    ports.append({'handle':vp.dxf.handle,'center':list(vp.dxf.center),
                                  'width':vp.dxf.width,'height':vp.dxf.height,'view_height':vp.dxf.view_height,
                                  'view_center':list(vp.dxf.view_center_point),'target':list(vp.dxf.view_target_point),
                                  'custom_scale':vp.dxf.height/vp.dxf.view_height if vp.dxf.view_height else None,
                                  'frozen_layers':list(vp.frozen_layers)})
                sheet={'id':f"s{len(manifest['sheets'])+1:03d}",'drawing':row['name'],'layout':layout.name,
                       'tab_order':settings.taborder,'role':role_for(row['name'],layout.name),
                       'entity_types':dict(Counter(e.dxftype() for e in layout)),
                       'title_blocks':attribute_blocks,'viewports':ports,
                       'plot':{k:settings.get(k) for k in ('plot_configuration_file','paper_size','paper_width','paper_height',
                                'plot_rotation','plot_type','plot_window_x1','plot_window_y1','plot_window_x2','plot_window_y2',
                                'scale_numerator','scale_denominator','plot_layout_flags','current_style_sheet')}}
                ctb=sheet['plot']['current_style_sheet']
                if ctb and basename(ctb).casefold() not in available:
                    manifest['issues'].append({'level':'BLOCKING','kind':'CTB_MISSING','sheet':sheet['id'],'ctb':ctb})
                if not sheet['plot']['paper_width'] or not sheet['plot']['paper_height']:
                    manifest['issues'].append({'level':'BLOCKING','kind':'PAPER_UNDEFINED','sheet':sheet['id']})
                manifest['sheets'].append(sheet)
        # Covers precede the drawing index; native tab order is retained within
        # each source file. IDs remain stable handles, independent of PDF order.
        manifest['sheets'].sort(key=lambda s:0 if s['role']=='cover' else 1 if s['role']=='drawing_list' else 2)
        manifest['required_roles']=sorted({s['role'] for s in manifest['sheets']})
        manifest['asset_fingerprint']=hashlib.sha256(json.dumps(manifest['assets'],sort_keys=True).encode()).hexdigest()
        atomic_json(home/'profile.json',manifest)
    except Exception:
        atomic_json(home/'IMPORT_FAILED.json',{'status':'INCOMPLETE_IMPORT_DO_NOT_USE'})
        raise
    return manifest


def load_profile(profile_id,verify=True):
    checked_id(profile_id);home=profile_root()/profile_id
    if (home/'IMPORT_FAILED.json').exists():raise ValueError('Incomplete profile import')
    manifest=json.loads((home/'profile.json').read_text(encoding='utf-8'))
    if manifest.get('id')!=profile_id:raise ValueError('Profile identity mismatch')
    if verify:
        for asset in manifest['assets']:
            if digest(safe_asset(home/'assets',asset['name']))!=asset['sha256']:
                raise ValueError('Profile asset modified: '+asset['name'])
    return manifest


def list_profiles():
    result=[]
    for p in sorted(profile_root().glob('*/profile.json')):
        m=json.loads(p.read_text(encoding='utf-8'))
        result.append({'id':m['id'],'sheets':len(m['sheets']),'drawings':len(m['drawings']),
                       'roles':m['required_roles'],'issues':dict(Counter(x['level'] for x in m['issues']))})
    return {'profiles':result}


def profile_info(profile_id,sheet_ids=None,include_viewport_details=False):
    profile=load_profile(profile_id)
    if sheet_ids is not None:
        available={s['id'] for s in profile['sheets']}
        if not isinstance(sheet_ids,list) or not all(isinstance(s,str) and s in available for s in sheet_ids):
            raise ValueError('Unknown sheet ID')
        profile['sheets']=[s for s in profile['sheets'] if s['id'] in sheet_ids]
    if not include_viewport_details:
        for sheet in profile['sheets']:
            sheet['viewport_count']=len(sheet['viewports'])
            sheet['viewports']=[{'handle':v['handle'],'custom_scale':v['custom_scale'],
                                'frozen_layer_count':len(v['frozen_layers'])} for v in sheet['viewports']]
    return profile


def reference_plan(job):
    """No writes. Select native sheets and validate explicit attribute changes."""
    if not isinstance(job,dict):raise ValueError('Reference job must be an object')
    allowed={'profile_id','project_id','sheet_ids','attributes','accept_font_substitution','mode','require_complete'}
    if set(job)-allowed:raise ValueError('Unknown reference job field')
    profile=load_profile(job.get('profile_id'));checked_id(job.get('project_id'))
    if job.get('mode','reference_reissue')!='reference_reissue':
        raise ValueError('Only reference_reissue is implemented; new design requires project geometry')
    ids=job.get('sheet_ids',[s['id'] for s in profile['sheets']])
    if not isinstance(ids,list) or not ids or not all(isinstance(s,str) for s in ids) or len(set(ids))!=len(ids):
        raise ValueError('sheet_ids must be a nonempty unique list')
    by_id={s['id']:s for s in profile['sheets']}
    if any(s not in by_id for s in ids):raise ValueError('Unknown sheet ID')
    sheets=[by_id[s] for s in ids];selected_files={s['drawing'] for s in sheets}
    attributes=job.get('attributes',{})
    if not isinstance(attributes,dict) or any(k not in ids for k in attributes):raise ValueError('Attribute overrides must target selected sheet IDs')
    for key,overrides in attributes.items():
        if not isinstance(overrides,dict):raise ValueError('attributes must map sheet IDs to tag/value objects')
        tags={t for block in by_id[key]['title_blocks'] for t in block['attributes']}
        for tag,value in overrides.items():
            if tag not in tags:raise ValueError('Unknown attribute tag: '+tag)
            if not isinstance(value,str) or not value.strip() or len(value)>200 or any(c in value for c in ('\n','\r','%<','\\')):
                raise ValueError('Attribute values must be plain text, maximum 200 characters')
    accept=job.get('accept_font_substitution',False)
    if type(accept)is not bool:raise ValueError('accept_font_substitution must be boolean')
    issues=[]
    for issue in profile['issues']:
        if 'sheet' in issue and issue['sheet'] not in ids:continue
        # Every source DWG remains packaged, including Xrefs. Resource issues
        # therefore remain visible even when they originate in a reference.
        entry=dict(issue)
        if entry['kind']=='FONT_MISSING' and not accept:entry['level']='BLOCKING'
        issues.append(entry)
    roles={s['role'] for s in sheets};missing=sorted(set(profile['required_roles'])-roles)
    complete=job.get('require_complete',True)
    if type(complete)is not bool:raise ValueError('require_complete must be boolean')
    if complete and (missing or len(sheets)!=len(profile['sheets'])):
        issues.append({'level':'BLOCKING','kind':'INCOMPLETE_SET','missing_roles':missing,
                       'selected_sheets':len(sheets),'required_sheets':len(profile['sheets'])})
    normalized={'profile_id':profile['id'],'project_id':job['project_id'],'sheet_ids':ids,
                'attributes':attributes,'accept_font_substitution':accept,'mode':'reference_reissue','require_complete':complete}
    return {'status':'BLOCKED' if any(x['level']=='BLOCKING' for x in issues) else 'READY_FOR_REFERENCE_REISSUE',
            'job':normalized,'sheets':sheets,'sheet_count':len(sheets),'issues':issues,'missing_roles':missing,
            'completeness':'COMPLETE_PROFILE' if not missing and len(sheets)==len(profile['sheets']) else 'SELECTED_SUBSET',
            'scope':'Native reference reissue; retains reference design. Not a new engineered design or TCVN approval.'}
