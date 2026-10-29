import json
from pathlib import Path
import pytest
from autocad_agent.design_api import preview
from autocad_agent.design_runtime import prepare_design,_read
from autocad_agent.fitout_design import demo_spec
from autocad_agent.project_delivery import seal_delivery,verify_delivery


def test_preview_has_one_combined_dxf_and_never_calls_pdf(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path))
    def forbidden(*args,**kwargs):raise AssertionError('PDF was not requested')
    monkeypatch.setattr('autocad_agent.detailed_sheets.render_sheet_pdf',forbidden)
    r=preview(demo_spec())
    folder=Path(r['dxf']).parent
    assert r['pdf'] is None and r['pdf_exported'] is False
    assert [p.name for p in folder.rglob('*.dxf')]==['PROJECT.dxf']
    assert not list(folder.rglob('*.pdf'))
    import ezdxf
    doc=ezdxf.readfile(r['dxf']);assert doc.header['$TILEMODE']==1
    assert len(doc.layouts)==12


def test_pdf_permission_is_frozen_and_cannot_be_added_to_approved_ticket(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path))
    default=prepare_design(demo_spec());requested=prepare_design(demo_spec(),export_pdf=True)
    assert default['pdf_exported'] is False and requested['pdf_exported'] is True
    assert default['ticket']!=requested['ticket']
    assert not _read(default['ticket'])['output_options']['export_pdf']
    path=tmp_path/'design_jobs/pending'/(default['ticket']+'.json')
    value=json.loads(path.read_text(encoding='utf-8'));value['output_options']['export_pdf']=True
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(PermissionError):_read(default['ticket'])


def test_single_dwg_handover_does_not_require_unrequested_pdf_or_dxf(tmp_path,monkeypatch):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));root=tmp_path/'generated_projects/one';root.mkdir(parents=True)
    (root/'PROJECT.dwg').write_bytes(b'AC1032-test-only')
    report={'output_mode':'SINGLE_DWG_MULTIPLE_LAYOUTS','pdf_exported':False,'native_dxf_delivery':False,
            'dwg_relative_path':'PROJECT.dwg','sheets':[{'code':'A-1'}]}
    (root/'GENERATION_REPORT.json').write_text(json.dumps(report),encoding='utf-8')
    seal_delivery(root)
    assert verify_delivery('one')['status']=='INTEGRITY_CHECKED'


def test_per_sheet_drawing_output_is_disabled():
    from autocad_agent.detailed_publish import publish_new_design
    with pytest.raises(ValueError,match='SEPARATE_SHEET_EXPORT_DISABLED'):
        publish_new_design(demo_spec(),sheet_codes=['A-101'])
