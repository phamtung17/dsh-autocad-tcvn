import pytest
from autocad_agent.schema import validate_job,JobError
from autocad_agent.templates import create_template

@pytest.mark.parametrize('sector',['mechanical','architectural','structural','electrical','hvac','plumbing','civil','fire_safety'])
def test_each_sector_template_is_valid(sector):
    job=create_template(sector)
    assert validate_job(job)['discipline']==sector
    assert job['purpose']=='concept_only'

def test_prevent_file_escape():
    with pytest.raises(JobError):create_template('mechanical',name='../evil.dwg')

def test_reject_negative_dim():
    with pytest.raises(JobError):create_template('mechanical',width=-1)

def test_reject_nonfinite():
    with pytest.raises(JobError):create_template('mechanical',width=float('nan'))

def test_reject_unknown_geometry():
    job=create_template('mechanical');job['geometry'][0]['type']='shell'
    with pytest.raises(JobError):validate_job(job)

def test_reject_duplicate_ids():
    job=create_template('mechanical');job['geometry'][1]['id']=job['geometry'][0]['id']
    with pytest.raises(JobError):validate_job(job)

def test_reject_missing_block():
    job=create_template('mechanical');job['geometry'].append({'id':'xx','type':'insert','block':'BAD','position':[0,0]})
    with pytest.raises(JobError):validate_job(job)

def test_block_insert_supported():
    job=create_template('mechanical')
    job['blocks']=[{'name':'TAG','base':[0,0],'entities':[{'id':'c','type':'circle','radius':2,'center':[0,0],'layer':'0'}]}]
    job['geometry'].append({'id':'tag1','layer':'M-TAG','type':'insert','block':'TAG','position':[10,10],'scale':1})
    assert validate_job(job)['geometry'][-1]['block']=='TAG'

def test_unsupported_purpose():
    job=create_template('mechanical');job['purpose']='fully_TCVN_certified'
    with pytest.raises(JobError):validate_job(job)

def test_bool_rejected_for_float():
    job=create_template('mechanical');job['geometry'][1]['radius']=True
    with pytest.raises(JobError):validate_job(job)
