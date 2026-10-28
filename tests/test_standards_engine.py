from autocad_agent.templates import create_template
from autocad_agent.standards_engine import screen_standards

def test_standard_routing_vs_certification():
    j=create_template('mechanical');j['standards']=['TCVN 7285:2003']
    r=screen_standards(j)
    assert r['standard_checks'][0]['applicability']=='POTENTIALLY_APPLICABLE'
    assert r['overall']=='NOT_CHECKED'

def test_unknown_reference_is_not_pass():
    j=create_template('mechanical');j['standards']=['TCVN IMAGINARY:9999']
    r=screen_standards(j)
    assert r['standard_checks'][0]['catalog_status']=='NOT_FOUND'
    assert r['overall']=='NOT_CHECKED'

def test_mismatched_sector_detected():
    j=create_template('mechanical');j['standards']=['TCVN 5574:2018']
    r=screen_standards(j)
    assert r['standard_checks'][0]['applicability']=='POSSIBLY_MISMATCHED_DISCIPLINE'
