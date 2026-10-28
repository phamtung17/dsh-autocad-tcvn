"""Read native output back and compare it with the current shared model."""
import argparse,json,math
from collections import Counter
from pathlib import Path
import ezdxf,pymupdf
from autocad_agent.runtime import workspace,atomic_json
from autocad_agent.reference_profiles import checked_id
from autocad_agent.design_dispatch import build_project
from autocad_agent.detailed_verify import verify_sheet
from autocad_agent.project_delivery import seal_delivery,verify_delivery

def primitive_keys(entities,native=False):
    def point(p):return (round(float(p[0]),5),round(float(p[1]),5))
    result=Counter()
    for e in entities:
        kind=e.dxftype().lower() if native else e['type'];layer=e.dxf.layer if native else e.get('layer','0')
        if kind=='line':
            ends=sorted([point(e.dxf.start),point(e.dxf.end)] if native else [point(e['start']),point(e['end'])]);key=('line',*ends)
        elif kind in ('polyline','lwpolyline'):
            points=tuple(point(p) for p in (e.get_points('xy') if native else e['points']));closed=e.closed if native else e['closed']
            if closed:points=min([points[i:]+points[:i] for i in range(len(points))]+[points[::-1][i:]+points[::-1][:i] for i in range(len(points))])
            key=('polyline',bool(closed),points)
        elif kind in ('circle','arc'):
            key=(kind,point(e.dxf.center) if native else point(e['center']),round(float(e.dxf.radius if native else e['radius']),5))
            if kind=='arc':key+=tuple(round(float(e.dxf.get(k) if native else e[k])%360,5) for k in ('start_angle','end_angle'))
        elif kind=='insert':
            key=('insert',(e.dxf.name if native else e['block']).casefold(),point(e.dxf.insert) if native else point(e['position']),
                 round(float(e.dxf.xscale if native else e['scale']),5),round(float(e.dxf.rotation if native else e['rotation'])%360,5))
        else:continue
        result[(layer.casefold(),key)]+=1
    return result

def verify(project_id):
    checked_id(project_id);root=workspace()/'generated_projects'/project_id
    report=json.loads((root/'GENERATION_REPORT.json').read_text(encoding='utf-8'))
    data=json.loads((root/'DESIGN_INPUT.json').read_text(encoding='utf-8'));project=build_project(data['spec'])
    assert not project['workflow']['issues'],project['workflow']['issues']
    assert len(report['sheets'])==len(project['sheets'])
    expected={s['code']:s for s in project['sheets']};assert set(expected)=={s['code'] for s in report['sheets']}
    total=Counter();checked=[]
    for row in report['sheets']:
        sheet=expected[row['code']];dxf=root/'DWG'/(row['code']+'_native.dxf');pdf=root/'PDF'/(row['code']+'.pdf')
        result=verify_sheet(dxf,pdf,row['code'],sheet['views']);assert not result['audit_errors']
        doc=ezdxf.readfile(dxf);counts=Counter(e.dxftype() for e in doc.modelspace());total.update(counts)
        geometry=sheet['job']['geometry']
        for kind,native in [('hatch','HATCH'),('leader','LEADER'),('table','ACAD_TABLE'),('dim_aligned','DIMENSION'),('insert','INSERT')]:
            assert counts[native]==sum(e['type']==kind for e in geometry),(row['code'],kind)
        assert not any(e.dxf.layer=='_PREVIEW_TABLE' for e in doc.modelspace())
        assert primitive_keys(doc.modelspace(),True)==primitive_keys(geometry),(row['code'],'primitive coordinates differ from current model')
        for block in sheet['job']['blocks']:
            assert primitive_keys(doc.blocks.get(block['name']),True)==primitive_keys(block['entities']),(row['code'],block['name'],'block geometry differs')
        actual=sorted(round(float(e.get_measurement()),5) for e in doc.modelspace().query('DIMENSION'))
        values=sorted(round(math.dist(e['start'],e['end']),5) for e in geometry if e['type']=='dim_aligned')
        assert actual==values,(row['code'],'dimension values')
        checked.append({'sheet':row['code'],'stage':sheet['stage'],'role':sheet['role'],'native_checks':result})
    pdf=pymupdf.open(root/'NEW_DESIGN_DRAWING_SET.pdf');assert len(pdf)==len(expected);pdf.close()
    scale_checks=[]
    for code,axis,size in [('AR-101','height',project['spec']['building']['depth']),('ST-202','width',project['spec']['structure']['beam_width'])]:
        scale=expected[code]['views'][0]['scale'];value=size/scale
        doc=pymupdf.open(root/'PDF'/(code+'.pdf'))
        lengths=[getattr(p['rect'],axis)*25.4/72 for p in doc[0].get_drawings()]
        measured=min(lengths,key=lambda v:abs(v-value));assert abs(measured-value)<.15,(code,value,measured)
        scale_checks.append({'sheet':code,'expected_mm':value,'measured_mm':measured,'tolerance_mm':.15});doc.close()
    result={'status':'NATIVE_OUTPUT_VERIFIED','sheet_count':len(checked),'stage_count':len({r['stage'] for r in checked}),
            'native_entity_totals':dict(total),'sheets':checked,'pdf_outline_scale_checks':scale_checks,
            'reference_geometry_read':False,'tcvn_compliance':'NOT_CHECKED','construction_release':False,
            'visual_review':'SEPARATE_VISUAL_REVIEW_REQUIRED','workflow':project['workflow']}
    result['primitive_coordinates_and_block_geometry_checked']=True
    atomic_json(root/'NATIVE_VERIFICATION.json',result);seal_delivery(root)
    assert verify_delivery(project_id)['status']=='INTEGRITY_CHECKED'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project_id');a=p.parse_args();r=verify(a.project_id)
    print(json.dumps({k:r[k] for k in ('status','sheet_count','stage_count','native_entity_totals','pdf_outline_scale_checks')},ensure_ascii=True))
