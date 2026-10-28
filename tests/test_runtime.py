from pathlib import Path
from unittest.mock import patch
import io,os,json,pytest
from autocad_agent.templates import create_template
from autocad_agent.runtime import prepare,read_pending,fingerprint,approve,consume,copy_exclusive
from autocad_agent.api import preview,catalog,capabilities,audit_dxf

@pytest.fixture(autouse=True)
def home(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path))

def test_prepare_and_require_human_approval():
    job=create_template('mechanical');prepared=prepare(job)
    assert prepared['status']=='PREPARED'
    with pytest.raises(PermissionError):consume(prepared['ticket'])
    with patch('builtins.input',return_value='KHONG'):
        assert approve(prepared['ticket'])['status']=='CANCELLED'
    with patch('builtins.input',return_value='VE'):
        assert approve(prepared['ticket'])['status']=='APPROVED_FOR_ONE_EXECUTION'
    assert consume(prepared['ticket'])['output_name']==job['output_name']
    with pytest.raises(PermissionError):consume(prepared['ticket'])

def test_prepare_rejects_overwrite(tmp_path):
    job=create_template('mechanical')
    (tmp_path/job['output_name']).write_bytes(b'preserve')
    assert prepare(job)['status']=='OUTPUT_EXISTS'

def test_copy_exclusive_protects_existing_file(tmp_path):
    src=tmp_path/'working.dwg';src.write_bytes(b'DWG'*200)
    dst=tmp_path/'final.dwg';dst.write_bytes(b'original')
    with pytest.raises(FileExistsError):copy_exclusive(src,dst)
    assert dst.read_bytes()==b'original'
    dst.unlink();assert copy_exclusive(src,dst)==dst

def test_preview_and_audit():
    job=create_template('mechanical');result=preview(job)
    assert result['dxf']['audit_errors']==0
    filename=Path(result['dxf']['file']).name
    assert audit_dxf(filename)['status']=='PASS_STRUCTURE'
    with pytest.raises(ValueError):audit_dxf('../../private.dxf')

def test_catalog_is_not_compliance():
    assert catalog('electrical')['tcvn_compliance']=='NOT_CHECKED'
    assert any('existing DWG editing' in item for item in capabilities()['unsupported'])


def test_user_opt_in_auto_new(tmp_path,monkeypatch):
    job=create_template('mechanical')
    ticket=prepare(job)['ticket']
    monkeypatch.setenv('CAD_APPROVAL_MODE','auto_new')
    assert consume(ticket)['output_name']==job['output_name']
    (tmp_path/job['output_name']).write_text('existing')
    with pytest.raises(FileExistsError):consume(ticket)
