"""Fail-closed checks for preflight. No normative standard is certified here."""
from __future__ import annotations
from .schema import validate_job
from .qa import geometry_report
from .standards_engine import screen_standards
from .discipline_review import review

def assess(job, project_rules=None):
    job=validate_job(job)
    geometry=geometry_report(job)
    screen=screen_standards(job)
    eng=review(job)
    blocking=[]
    if job['plot']['enabled']:
        from .presentation import presentation_report
        presentation=presentation_report(job)
        if presentation['status']=='FAIL':
            blocking.append({'id':'PRESENTATION_FAIL','findings':presentation['findings']})
    if geometry['status'] != 'GEOMETRY_CHECKED':
        blocking.append({'id':'GEO_NOT_CLEAR','result':geometry['status'], 'findings':geometry['findings']})
    if job['purpose'] != 'concept_only':
        if not job['standards']:
            blocking.append({'id':'STANDARDS_NOT_DECLARED'})
        for standard in screen['standard_checks']:
            if standard['catalog_status']=='NOT_FOUND' or standard['applicability']=='POSSIBLY_MISMATCHED_DISCIPLINE':
                blocking.append({'id':'STANDARD_UNSUPPORTED','standard':standard['id']})
        if eng['missing']:
            blocking.append({'id':'ENGINEERING_INPUT_MISSING','fields':eng['missing']})
    if job['purpose'] in ('manufacture_review','construction_review'):
        # No independently signed engineering approval or normative checks in this version.
        blocking.append({'id':'DESIGN_RELEASE_NOT_SUPPORTED','reason':'Engineering signoff and clause-level TCVN verification are unavailable.'})
    results=None
    if project_rules is None: project_rules=job.get('project_rules')
    if project_rules is not None:
        from .qa import check_project_rules
        results=check_project_rules(job,project_rules)
        if results['status'] == 'FAIL':
            blocking.append({'id':'PROJECT_RULE_FAIL'})
    clause_reports=[]
    for filename in job['clause_rule_packs']:
        from .clause_rules import evaluate,load_rule_pack
        try:
            report=evaluate(job,load_rule_pack(filename))
        except (ValueError,FileNotFoundError,KeyError,TypeError) as exc:
            report={'status':'NOT_CHECKED','error':str(exc),'tcvn_compliance':'NOT_CERTIFIED'}
        clause_reports.append({'rule_pack':filename,'report':report})
        if report['status'] in ('FAIL','NOT_CHECKED'):
            blocking.append({'id':'CLAUSE_RULEPACK_NOT_CLEAR','rule_pack':filename,'result':report['status']})
    return {'status':'BLOCKED'  if blocking else 'READY_FOR_CONCEPT_DWG' if job['purpose']=='concept_only' else 'READY_FOR_DESIGN_REVIEW_DWG',
            'blocking':blocking,'geometry':geometry,'engineering':eng,'standards':screen,
            'project_rules':results,'clause_rule_reports':clause_reports,'tcvn_compliance':'NOT_CHECKED'}
