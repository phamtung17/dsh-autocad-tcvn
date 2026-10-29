"""Check the actual saved combined DXF against composition, including offsets."""
import math
from collections import Counter
import ezdxf


def verify_combined(source_path,native_path,project,rows):
    source=ezdxf.readfile(source_path);native=ezdxf.readfile(native_path)
    audit=native.audit()
    if audit.errors or any(f.code==103 for f in audit.fixes):raise ValueError('Native audit removed invalid block/dimension references')
    measurements=lambda doc:sorted(round(float(e.get_measurement()),5) for e in doc.modelspace().query('DIMENSION'))
    if measurements(source)!=measurements(native):raise ValueError('Native dimension measurements changed')
    from .native_geometry import primitive_keys
    geometry=[e for e in source.modelspace() if e.dxf.layer!='_PREVIEW_TABLE']
    if primitive_keys(geometry,True)!=primitive_keys(native.modelspace(),True):raise ValueError('Native primitive coordinates changed')
    for block in source.blocks:
        if block.name.upper().startswith('*') or block.name not in native.blocks:continue
        if primitive_keys(block,True)!=primitive_keys(native.blocks.get(block.name),True):raise ValueError('Native block geometry changed: '+block.name)
    for typ in ('HATCH','LEADER','INSERT','CIRCLE','ARC'):
        if len(source.modelspace().query(typ))!=len(native.modelspace().query(typ)):raise ValueError('Native entity count changed: '+typ)
    view_count=0
    for sheet,row in zip(project['sheets'],rows):
        ports=[v for v in native.layouts.get(sheet['code']).query('VIEWPORT') if v.dxf.id!=1]
        if len(ports)!=len(sheet['views']):raise ValueError('Viewport count mismatch')
        for vp,view in zip(ports,sheet['views']):
            # This exporter explicitly initializes every layout before saving.
            # Imported id/status 0 is therefore a failed exporter postcondition.
            if vp.dxf.id<=1 or vp.dxf.status<1:raise ValueError('Generated layout viewport was not initialized')
            if vp.dxf.flags&131072:raise ValueError('Native layout viewport is explicitly disabled')
            expected=(view['target'][0]+row['offset'][0],view['target'][1]+row['offset'][1])
            actual=vp.dxf.view_center_point
            if not math.isclose(vp.dxf.view_height/vp.dxf.height,view['scale'],rel_tol=1e-7):raise ValueError('Native viewport scale mismatch')
            if abs(actual.x-expected[0])>.01 or abs(actual.y-expected[1])>.01:raise ValueError('Native viewport targets wrong sheet geometry')
            if not vp.dxf.flags&16384:raise ValueError('Native viewport is not locked')
            view_count+=1
    return {'status':'NATIVE_COORDINATES_DIMENSIONS_LAYOUTS_CHECKED','dimension_count':len(measurements(native)),
            'viewport_count':view_count,'model_entity_types':dict(Counter(e.dxftype() for e in native.modelspace())),
            'audit_errors':len(audit.errors),'visual_review':'NOT_CHECKED','engineering_approval':False}
