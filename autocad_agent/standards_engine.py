"""Standards inventory and applicability screening, NOT clause-level TCVN testing."""
from __future__ import annotations
import json
from pathlib import Path
from .schema import validate_job

REGISTRY=Path(__file__).resolve().parents[1]/'standards'/'registry.json'

def screen_standards(job):
    job=validate_job(job)
    catalog=json.loads(REGISTRY.read_text(encoding='utf-8'))
    mapping={row['id']:row for row in catalog['standards']}
    rows=[]
    for ref in job['standards']:
        entry=mapping.get(ref)
        if entry is None:
            rows.append({'id':ref,'catalog_status':'NOT_FOUND','applicability':'UNKNOWN',
                         'clause_check':'NOT_CHECKED','blocking':'VERIFY_REFERENCE'})
        else:
            disciplines=entry['discipline']
            applies='POTENTIALLY_APPLICABLE' if 'all' in disciplines or job['discipline'] in disciplines else 'POSSIBLY_MISMATCHED_DISCIPLINE'
            rows.append({'id':ref,'catalog_status':'RECHECK_OFFICIAL','applicability':applies,
                         'source':entry['source'],'clause_check':'NOT_CHECKED',
                         'blocking':'VERIFY_LATEST_EDITION_AND_CLAUSES'})
    return {'drawing':job['output_name'],'discipline':job['discipline'],
            'standard_checks':rows,'overall':'NOT_CHECKED',
            'missing_standards':not bool(rows),
            'note':'No full norm text or clause-level verified rules. This screening must not be reported as compliance.'}
