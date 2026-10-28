import pytest
from autocad_agent.qa import geometry_report,check_project_rules,self_intersections
from autocad_agent.templates import create_template

@pytest.mark.parametrize('sector',['mechanical','architectural','structural','electrical','hvac','plumbing','civil','fire_safety'])
def test_geometry_report(sector):
    report=geometry_report(create_template(sector))
    assert report['entity_count']>2
    assert report['bounds'][2]>report['bounds'][0]
    assert report['tcvn_compliance']=='NOT_CHECKED'

def test_detect_bowtie():
    assert self_intersections([[0,0],[1,1],[0,1],[1,0]],True)==1

def test_detect_bad_polyline_in_qa():
    job=create_template('mechanical');job['geometry'][0]['points']=[[0,0],[1,1],[0,1],[1,0]]
    result=geometry_report(job)
    assert result['status']=='FAIL'
    assert any(x['id']=='GEO-SELF-INTERSECTION' for x in result['findings'])

def test_project_rules_pass_and_fail():
    job=create_template('mechanical')
    rules={'kind':'PROJECT_RULE','project_id':'PROJECT-X','checks':[{'type':'required_layers','layers':['M-OUTLINE']},{'type':'min_circle_radius','value':100}]}
    qa=check_project_rules(job,rules)
    assert qa['status']=='FAIL';assert [x['result'] for x in qa['checks']]==['PASS','FAIL']
    assert qa['tcvn_compliance']=='NOT_CHECKED'

def test_no_tcvn_relabel_allowed():
    job=create_template('mechanical')
    with pytest.raises(ValueError):check_project_rules(job,{'kind':'TCVN_CERTIFIED','project_id':'X','checks':[]})

def test_missing_entity_rule_not_applicable():
    job=create_template('architectural')
    rules={'kind':'PROJECT_RULE','project_id':'ARCH','checks':[{'type':'min_circle_radius','value':3}]}
    assert check_project_rules(job,rules)['checks'][0]['result']=='NOT_APPLICABLE'


def test_discipline_missing_engineering_inputs_not_cleared():
    from autocad_agent.discipline_review import review
    job=create_template('structural')
    job['purpose']='construction_review'
    result=review(job)
    assert result['status']=='INCOMPLETE'
    assert result['gate']=='NOT_APPROVED'

def test_declared_inputs_not_approved():
    from autocad_agent.discipline_review import review
    job=create_template('structural')
    job['purpose']='design_review'
    job['engineering_inputs']={'load_case_reference':'REF-1','design_calculation_reference':'REF-2','material_grade':'REF-3'}
    result=review(job)
    assert result['status']=='NEEDS_ENGINEER_VERIFICATION'
    assert result['gate']=='NOT_APPROVED'

def test_duplicate_geometry_detected():
    job=create_template('mechanical')
    dup=dict(job['geometry'][1]);dup['id']='duplicate_hole';job['geometry'].append(dup)
    result=geometry_report(job)
    assert result['status']=='FAIL'
    assert any(x['id']=='GEO-DUPLICATE' for x in result['findings'])

def test_circle_measurement():
    job=create_template('mechanical')
    report=geometry_report(job)
    circles=[x for x in report['measurements'] if 'radius' in x]
    assert circles and abs(circles[0]['diameter']-20.8)<1e-7
