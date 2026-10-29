"""Trusted read-only audit; optional safe repairs always write a NEW copy."""
import argparse,json,hashlib
from pathlib import Path
import ezdxf
from autocad_agent.dxf_spatial_audit import audit_document,repair_hosted_openings


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',required=True);p.add_argument('--repair-copy');a=p.parse_args()
    source=Path(a.input).resolve();report_path=Path(a.output);doc=ezdxf.readfile(source)
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'before':audit_document(doc)}
    if a.repair_copy:
        target=Path(a.repair_copy).resolve()
        if target==source or target.exists():raise FileExistsError('Repairs require a new, exclusive output path')
        target.parent.mkdir(parents=True,exist_ok=True);report['actions']=repair_hosted_openings(doc);doc.saveas(target)
        report['after']=audit_document(ezdxf.readfile(target));report['repair_copy']=str(target)
        report['release_status']='BLOCKED' if any(f['severity']=='ERROR' for s in report['after']['layouts'] for f in s['findings']) else 'REQUIRES_VISUAL_AND_ENGINEERING_REVIEW'
    report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'before':report['before']['counts'],'after':report.get('after',{}).get('counts'),'report':str(report_path),'release_status':report.get('release_status','AUDIT_ONLY')},ensure_ascii=True))
