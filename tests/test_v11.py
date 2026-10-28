"""Regression coverage for the P0 fixes, clause engine, scale-safe plotting plan."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import os
import pytest
from autocad_agent.templates import create_template
from autocad_agent.schema import validate_job, JobError
from autocad_agent.gates import assess
from autocad_agent.runtime import prepare, approve, consume, consume_worker_permit, issue_worker_permit
from autocad_agent.plotting import viewport_plan,sheet_size_mm, dwt_path
from autocad_agent.clause_rules import evaluate,load_rule_pack
from autocad_agent.api import capabilities,plot_plan
from autocad_agent.qa import geometry_report

@pytest.fixture(autouse=True)
def temp_home(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path))
    monkeypatch.delenv('CAD_APPROVAL_MODE',raising=False)


def test_block_default_layer_normalized():
    j=create_template('mechanical')
    j['blocks']=[{'name':'MARK','entities':[{'id':'c','type':'circle','center':[0,0],'radius':3}]}]
    j['geometry'].append({'id':'ins','type':'insert','layer':'M-BLOCK','block':'MARK','position':[3,3]})
    got=validate_job(j)
    assert got['blocks'][0]['entities'][0]['layer']=='0'
    assert got['blocks'][0]['base']==[0.,0.]


def test_block_duplicate_internal_id_rejected():
    j=create_template('mechanical')
    c={'id':'c','type':'circle','center':[0,0],'radius':3}
    j['blocks']=[{'name':'M','entities':[c,c]}]
    with pytest.raises(JobError,match='duplicate block entity'):validate_job(j)


def test_gate_fails_closed_for_self_intersection():
    j=create_template('mechanical')
    j['geometry'][0]['points']=[[0,0],[100,100],[0,100],[100,0]]
    assert assess(j)['status']=='BLOCKED'
    assert prepare(j)['status']=='REJECTED_QUALITY_GATE'


def test_gate_blocks_large_unchecked_polyline():
    j=create_template('mechanical')
    j['geometry'][0]['points']=[[float(i),float(i%2)] for i in range(702)]
    j['geometry'][0]['closed']=False
    assert any(f['level']=='NOT_CHECKED' for f in geometry_report(j)['findings'])
    assert assess(j)['status']=='BLOCKED'


def test_gate_review_requires_engineering_inputs():
    j=create_template('structural')
    j['purpose']='design_review'
    assert 'ENGINEERING_INPUT_MISSING' in [x['id'] for x in assess(j)['blocking']]


def test_gate_construction_requires_human_release():
    j=create_template('mechanical')
    j['purpose']='manufacture_review'
    assert 'DESIGN_RELEASE_NOT_SUPPORTED' in [x['id'] for x in assess(j)['blocking']]


def test_gate_unknown_standard_rejected_for_review():
    j=create_template('mechanical')
    j['purpose']='design_review'
    j['standards']=['TCVN NEVER EXISTED']
    j['engineering_inputs']={'material':'steel','tolerance_basis':'project','manufacturing_process':'laser'}
    assert 'STANDARD_UNSUPPORTED' in [x['id'] for x in assess(j)['blocking']]


def test_gate_bad_project_rules_rejected():
    j=create_template('mechanical')
    rules={'kind':'PROJECT_RULE','project_id':'a','checks':[{'type':'required_layers','layers':['ABSENT']}]}
    assert 'PROJECT_RULE_FAIL' in [x['id'] for x in assess(j,rules)['blocking']]


def test_worker_rejects_pending_without_signed_permit():
    j=create_template('mechanical');ticket=prepare(j)['ticket']
    with pytest.raises(PermissionError):consume_worker_permit(ticket)
    # No permit exists just because job is pending.
    assert not (Path(os.getenv('CAD_OUTPUT_DIR'))/'working'/(ticket+'.permit.json')).exists()


def test_worker_permit_signed_single_use():
    j=create_template('mechanical');ticket=prepare(j)['ticket']
    with patch('builtins.input',return_value='VE'):approve(ticket)
    authorized=consume(ticket)
    permit=issue_worker_permit(ticket,authorized)
    assert consume_worker_permit(permit)['output_name']==authorized['output_name']
    with pytest.raises(FileNotFoundError):consume_worker_permit(permit)


def test_worker_permit_tamper_detected(tmp_path):
    j=create_template('mechanical');ticket=prepare(j)['ticket'];permit=issue_worker_permit(ticket,j)
    path=tmp_path/'working'/(permit+'.permit.json')
    data=json.loads(path.read_text(encoding='utf-8'))
    data['payload']['job']['geometry'][0]['layer']='INJECTED'
    path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(PermissionError,match='signature'):consume_worker_permit(permit)


def test_auto_new_allowed_concept_only(monkeypatch):
    j=create_template('mechanical');ticket=prepare(j)['ticket']
    monkeypatch.setenv('CAD_APPROVAL_MODE','auto_new')
    assert consume(ticket)['output_name']==j['output_name']


def test_no_auto_new_on_review(monkeypatch):
    j=create_template('mechanical');j['purpose']='design_review'
    j['engineering_inputs']={'material':'steel','tolerance_basis':'project','manufacturing_process':'laser'}
    j['standards']=['TCVN 7285:2003']
    ticket=prepare(j)['ticket']
    monkeypatch.setenv('CAD_APPROVAL_MODE','auto_new')
    with pytest.raises(PermissionError):consume(ticket)


def test_plot_a3_dimensions_and_scale():
    j=create_template('mechanical',width=200,height=100)
    j['plot']={'enabled':True,'pdf':True}
    plan=viewport_plan(validate_job(j))
    assert plan['sheet_mm']==(420,297)
    assert plan['custom_scale']==pytest.approx(1.0)
    assert plot_plan(j)['status']=='MATHEMATICAL_FIT_CHECKED_NOT_PLOTTED'


def test_plot_scale_metric_conversion():
    j=create_template('civil',width=120,height=80,units='m')
    j['sheet']['scale_denominator']=1000
    j['plot']={'enabled':True}
    assert viewport_plan(validate_job(j))['custom_scale']==pytest.approx(1.0)


def test_plot_rejects_oversize():
    j=create_template('mechanical',width=1000,height=1000)
    j['plot']={'enabled':True,'pdf':True}
    with pytest.raises(ValueError,match='clipped'):viewport_plan(validate_job(j))


def test_plot_rejects_arbitrary_template_path():
    j=create_template('mechanical');j['plot']={'enabled':True,'dwt':'../../evil.dwt'}
    with pytest.raises(JobError):validate_job(j)


def test_plot_rejects_bad_boolean():
    j=create_template('mechanical');j['plot']={'enabled':'true'}
    with pytest.raises(JobError):validate_job(j)


def test_dwt_requires_admin_configured_directory():
    j=create_template('mechanical');j['plot']={'enabled':True,'dwt':'approved.dwt'}
    with pytest.raises(ValueError,match='CAD_DWT_DIR'):dwt_path(validate_job(j))


def test_clause_example_is_not_checked():
    j=create_template('mechanical');j['standards']=['TCVN 7285:2003']
    result=evaluate(j,load_rule_pack('EXAMPLE_NOT_VERIFIED.json'))
    assert result['checks'][0]['result']=='NOT_CHECKED'
    assert result['status']=='NOT_CHECKED'


def test_clause_missing_source_never_passes():
    j=create_template('mechanical');j['standards']=['TCVN 7285:2003']
    pack=load_rule_pack('EXAMPLE_NOT_VERIFIED.json')
    pack['rules'][0]['attested']=True
    assert evaluate(j,pack)['checks'][0]['result']=='NOT_CHECKED'


def test_clause_attested_rule_measured_but_not_certified():
    j=create_template('mechanical');j['standards']=['TCVN 7285:2003']
    pack=load_rule_pack('EXAMPLE_NOT_VERIFIED.json')
    pack['standard'].update({'source_sha256':'a'*64,'source_title':'Mock sourced rule',
                             'reviewed_at':'2026-01-01','reviewed_by':'Test reviewer'})
    pack['rules'][0].update({'attested':True,'reviewed_by':'Test reviewer','clause':'mock clause'})
    result=evaluate(j,pack)
    assert result['checks'][0]['result']=='PASS'
    assert result['tcvn_compliance']=='NOT_CERTIFIED'
    pack['rules'][0]['expected']='A4'
    assert evaluate(j,pack)['checks'][0]['result']=='FAIL'


def test_clause_standard_mismatch_not_checked():
    j=create_template('mechanical');j['standards']=['TCVN 5574:2018']
    pack=load_rule_pack('EXAMPLE_NOT_VERIFIED.json')
    pack['standard'].update({'id':'TCVN 5574:2018','source_sha256':'a'*64,
                             'reviewed_at':'2026-01-01','reviewed_by':'Mock'})
    pack['rules'][0].update({'attested':True,'reviewed_by':'Mock'})
    assert evaluate(j,pack)['checks'][0]['result']=='NOT_CHECKED'


def test_clause_reject_path_traversal():
    with pytest.raises(ValueError):load_rule_pack('../EXAMPLE_NOT_VERIFIED.json')


def test_capabilities_updated():
    c=capabilities();assert c['version']=='1.4.0-local'
    assert len(c['tools'])==34


def test_gate_embedded_project_rules_enforced():
    j=create_template('mechanical')
    j['project_rules']={'kind':'PROJECT_RULE','project_id':'PROJ-A',
                       'checks':[{'type':'required_layers','layers':['SHOULD_NOT_EXIST']}]}
    result=assess(j)
    assert 'PROJECT_RULE_FAIL' in [x['id'] for x in result['blocking']]
    assert prepare(j)['status']=='REJECTED_QUALITY_GATE'


def test_gate_explicit_unknown_or_unverified_clause_pack_fails():
    j=create_template('mechanical')
    j['standards']=['TCVN 7285:2003']
    j['clause_rule_packs']=['EXAMPLE_NOT_VERIFIED.json']
    result=assess(j)
    assert 'CLAUSE_RULEPACK_NOT_CLEAR' in [x['id'] for x in result['blocking']]


def test_gate_unknown_rule_pack_fails_closed():
    j=create_template('mechanical')
    j['clause_rule_packs']=['MY_FAKE_RULES.json']
    assert assess(j)['status']=='BLOCKED'
