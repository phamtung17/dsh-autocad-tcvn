"""Auditable, conservative clause-linked rule execution.

No normative threshold is bundled. A local rule pack can be reviewed against
lawfully acquired text; PASS means only that this measured constraint passed,
not legal/engineering certification or authenticity of the reviewed source.
"""
from __future__ import annotations
import json
import math
import os
import re
from datetime import date
from pathlib import Path
from .schema import validate_job
from .qa import distance
from .standards_engine import REGISTRY

RULE_TYPES={'sheet_format','sheet_scale_denominator','max_entity_count',
            'min_line_length','min_circle_diameter','required_layers','all_polylines_closed'}
HEX64=re.compile(r'[0-9a-f]{64}\Z')
SAFE_PACK=re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\.json\Z')


def load_rule_pack(name: str) -> dict:
    if not isinstance(name,str) or not SAFE_PACK.fullmatch(name) or '..' in name:
        raise ValueError('Use an approved rule-pack filename only, not an arbitrary path')
    directory=Path(os.environ.get('CAD_RULES_DIR',str(Path(__file__).resolve().parents[1]/'standards'/'verified_rules'))).resolve()
    target=directory/name
    if not target.is_file() or target.is_symlink():raise FileNotFoundError('Approved rule-pack file not found')
    return json.loads(target.read_text(encoding='utf-8'))


def provenance(pack,entry,job,registry):
    std=pack.get('standard',{})
    if not isinstance(std,dict):return False,'missing standard metadata'
    sid=std.get('id')
    if not isinstance(sid,str) or sid not in registry:return False,'standard absent from catalog'
    if sid not in job['standards']:return False,'standard not declared by drawing'
    scope=registry[sid].get('discipline',[])
    if job['discipline'] not in scope and 'all' not in scope:return False,'standard is outside its catalog discipline'
    # A reviewer-approved clause is *user-provided evidence*. This code cannot
    # authenticate a copyrighted source or attest the rule is substantively correct.
    metadata=['edition','source_sha256','source_title','reviewed_by','reviewed_at']
    if any(not isinstance(std.get(k),str) or not std[k].strip() for k in metadata):
        return False,'incomplete source provenance'
    if not HEX64.fullmatch(std['source_sha256']):return False,'invalid source SHA-256'
    try:date.fromisoformat(std['reviewed_at'])
    except ValueError:return False,'invalid source review date'
    if std['reviewed_at']>date.today().isoformat():return False,'source review date is in the future'
    if not isinstance(entry.get('clause'),str) or not entry['clause'].strip():return False,'no clause locator'
    if not isinstance(entry.get('method'),str) or not entry['method'].strip():return False,'no measurement method'
    if not isinstance(entry.get('reviewed_by'),str) or not entry['reviewed_by'].strip():return False,'no rule reviewer'
    if entry.get('attested') is not True:return False,'rule was not manually attested'
    return True,'review metadata supplied by local rule pack; independently verify original text'


def measure(job,rule):
    typ=rule['type']
    geometries=job['geometry']
    if typ=='sheet_format':return job['sheet']['format']
    if typ=='sheet_scale_denominator':return job['sheet']['scale_denominator']
    if typ=='max_entity_count':return len(geometries)
    if typ=='required_layers':return sorted({e['layer'] for e in geometries})
    if typ=='min_line_length':
        xs=[distance(e['start'],e['end']) for e in geometries if e['type']=='line']
        return min(xs) if xs else None
    if typ=='min_circle_diameter':
        xs=[e['radius']*2 for e in geometries if e['type']=='circle']
        return min(xs) if xs else None
    if typ=='all_polylines_closed':
        xs=[e['closed'] for e in geometries if e['type']=='polyline']
        return all(xs) if xs else None
    raise ValueError('unsupported rule type')


def evaluate(job,pack):
    job=validate_job(job)
    if not isinstance(pack,dict) or pack.get('kind')!='TCVN_CLAUSE_RULEPACK':
        raise ValueError('requires kind=TCVN_CLAUSE_RULEPACK')
    all_standards=json.loads(REGISTRY.read_text(encoding='utf-8'))['standards']
    registry={s['id']:s for s in all_standards}
    rules=pack.get('rules')
    if not isinstance(rules,list) or not 1<=len(rules)<=100:
        raise ValueError('expected 1..100 rules')
    results=[]
    for i,r in enumerate(rules):
        if not isinstance(r,dict) or r.get('type') not in RULE_TYPES:raise ValueError('unsupported rule')
        ok_provenance,explanation=provenance(pack,r,job,registry)
        actual=measure(job,r)
        target=r.get('expected')
        outcome='NOT_CHECKED'
        if ok_provenance and actual is not None:
            t=r['type']
            if t in ('sheet_format',):
                if not isinstance(target,str):raise ValueError('sheet_format expected string')
                outcome='PASS' if actual==target else 'FAIL'
            elif t=='required_layers':
                if not isinstance(target,list) or not all(isinstance(x,str) for x in target):
                    raise ValueError('required_layers expected list')
                outcome='PASS' if set(target).issubset(actual) else 'FAIL'
            elif t=='all_polylines_closed':
                if type(target) is not bool:raise ValueError('all_polylines_closed expected boolean')
                outcome='PASS' if actual==target else 'FAIL'
            else:
                if isinstance(target,bool) or not isinstance(target,(int,float)) or not math.isfinite(target):
                    raise ValueError('numeric threshold required')
                op='le' if t in ('sheet_scale_denominator','max_entity_count') else 'ge'
                # `comparison` must be explicit in a real clause rule; otherwise fail closed.
                if r.get('comparison') != op:
                    outcome='NOT_CHECKED';explanation=f'missing/invalid comparison; expected {op}'
                else:
                    outcome='PASS' if ((actual<=target) if op=='le' else (actual>=target)) else 'FAIL'
        elif actual is None:
            explanation='no matching measurable entities (cannot mark PASS)'
        results.append({'id':r.get('id',f'RULE-{i+1:03d}'),'standard_id':pack.get('standard',{}).get('id'),
                        'edition':pack.get('standard',{}).get('edition'), 'clause':r.get('clause'),
                        'rule_type':r['type'],'expected':target,'measured':actual,
                        'method':r.get('method'),'result':outcome,'provenance_note':explanation})
    statuses={x['result'] for x in results}
    overall='FAIL' if 'FAIL' in statuses else 'NOT_CHECKED' if 'NOT_CHECKED' in statuses else 'RULES_MEASURED_NEEDS_ENGINEER_APPROVAL'
    return {'status':overall,'checks':results,'source_document_sha256':pack.get('standard',{}).get('source_sha256'),
            'tcvn_compliance':'NOT_CERTIFIED',
            'disclaimer':'Rule-pass means the declared measurement matched locally supplied review metadata; no independent verification of original TCVN clauses or legal applicability.'}
