"""One editable model-space atlas and named paper layouts, without Xrefs."""
from pathlib import Path
from copy import deepcopy
import ezdxf
from ezdxf.addons import Importer
from ezdxf.math import Matrix44
from .detailed_sheets import make_sheet_dxf


def _compose_project(project, branding, path, staging):
    from .branding import normalize_brand
    branding = normalize_brand(branding)
    path = Path(path)
    output = ezdxf.new('R2013', setup=True)
    output.header['$INSUNITS'] = 4
    rows = []
    for ordinal, sheet in enumerate(project['sheets'], 1):
        source = staging / (sheet['code'] + '.dxf')
        make_sheet_dxf(sheet, project['spec'], branding, source, ordinal, len(project['sheets']))
        doc = ezdxf.readfile(source)
        if any(e.dxftype()=='IMAGE' for e in doc.entitydb.values()):
            raise ValueError('SINGLE_DWG_RASTER_LOGO_UNSUPPORTED: use a vector DXF logo or wordmark; no bitmap logo will be silently omitted')
        if 'VIEWPORTS' not in doc.layers: doc.layers.new('VIEWPORTS')
        # Prefix all source blocks, including anonymous dimension picture blocks:
        # identical furniture names and *D1 on different sheets must never alias.
        names = {b.name: sheet['code'] + '_' + b.name.replace('*', 'ANON_')
                 for b in doc.blocks if not b.name.upper().startswith('*MODEL_SPACE')
                 and not b.name.upper().startswith('*PAPER_SPACE')}
        for old, new in names.items():
            doc.blocks.rename_block(old, new)
        for entity in doc.entitydb.values():
            if entity.dxftype() == 'INSERT' and entity.dxf.name in names:
                entity.dxf.name = names[entity.dxf.name]
            elif entity.dxftype() == 'DIMENSION' and entity.dxf.get('geometry') in names:
                entity.dxf.geometry = names[entity.dxf.geometry]
        # Compact atlas cells; preserve all real dimensions (translation only).
        offset = (((ordinal - 1) % 4) * 300000, ((ordinal - 1) // 4) * 100000)
        matrix = Matrix44.translate(*offset, 0)
        for entity in list(doc.modelspace()):
            entity.transform(matrix)
        source_layout = doc.layouts.get(sheet['code'])
        for vp in source_layout.query('VIEWPORT'):
            if vp.dxf.id != 1:
                x, y = vp.dxf.view_center_point.x, vp.dxf.view_center_point.y
                vp.dxf.view_center_point = (x + offset[0], y + offset[1])
        importer = Importer(doc, output)
        prior_handles = {e.dxf.handle for e in output.modelspace()}
        importer.import_modelspace()
        imported=[e for e in output.modelspace() if e.dxf.handle not in prior_handles]
        originals=list(doc.modelspace())
        if len(imported)!=len(originals):raise ValueError('Model import entity inventory changed')
        handle_map={old.dxf.handle:new.dxf.handle for old,new in zip(originals,imported)}
        # Importer does not remap LEADER annotation references. Stale handles
        # may point at erased entities and make native deep-cloning fail.
        for old,new in zip(originals,imported):
            if old.dxftype()=='LEADER':
                annotation=old.dxf.get('annotation_handle','0')
                new.dxf.annotation_handle=handle_map.get(annotation,'0')
        importer.import_paperspace_layout(sheet['code'])
        importer.finalize()
        # Importer stores DIMENSION picture content virtually. Materialize it
        # before DXF serialization, otherwise audit silently drops the dimensions.
        for dim in output.modelspace().query('DIMENSION'):
            if not dim.dxf.get('geometry'): dim.render()
        tables = []
        for entity in sheet['job']['geometry']:
            if entity['type'] == 'table':
                if entity['layer'] not in output.layers: output.layers.new(entity['layer'])
                item = deepcopy(entity)
                item['position'] = [entity['position'][0] + offset[0], entity['position'][1] + offset[1]]
                tables.append(item)
        rows.append({'code': sheet['code'], 'offset': offset, 'tables': tables,
                     'model_handles':[e.dxf.handle for e in output.modelspace()
                                      if e.dxf.handle not in prior_handles and e.dxf.layer!='_PREVIEW_TABLE']})
    for layout in list(output.layouts):
        if layout.name not in {'Model'} | {s['code'] for s in project['sheets']}:
            output.layouts.delete(layout.name)
    output.layouts.set_active_layout(project['sheets'][0]['code'])
    output.header['$TILEMODE'] = 1
    output.saveas(path)
    audit = ezdxf.readfile(path).audit()
    if audit.errors:
        raise ValueError('Combined DXF failed audit')
    return rows


def compose_project(project, branding, path):
    from tempfile import TemporaryDirectory
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='dsh-compose-',dir=path.parent) as temporary:
        staging=Path(temporary).resolve()
        if not staging.is_relative_to(path.parent.resolve()):raise ValueError('Unsafe composition directory')
        return _compose_project(project,branding,path,staging)
