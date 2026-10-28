"""Offline contracts for native profiles. Fixture DWGs are not real CAD files."""
from pathlib import Path
import json
import time
import types
import pytest
import ezdxf
from autocad_agent import reference_profiles as rp
from autocad_agent import reference_runtime as rr
from autocad_agent.runtime import atomic_json


@pytest.fixture
def profile(monkeypatch,tmp_path):
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path/'output'))
    monkeypatch.setenv('CAD_PROFILE_DIR',str(tmp_path/'profiles'))
    monkeypatch.setenv('CAD_APPROVAL_MODE','manual')
    monkeypatch.setattr(rp,'_font_files',lambda:{'txt','txt.shx','arial','arial.ttf'})
    inspection=tmp_path/'inspection';source=inspection/'source';source.mkdir(parents=True)
    dxf_dir=inspection/'dxf';dxf_dir.mkdir()
    assets=[];drawings=[]
    for name in ['100 WALL PLAN.dwg','101 FLOOR PLAN.dwg']:
        asset=source/name;asset.write_bytes(b'OFFLINE FIXTURE '+name.encode())
        assets.append({'name':name,'bytes':asset.stat().st_size,'sha256':rp.digest(asset)})
        doc=ezdxf.new('R2013');layout=doc.layouts.get('Layout1')
        layout.page_setup(size=(420,297),margins=(0,0,0,0))
        vp=layout.add_viewport(center=(150,150),size=(200,200),view_center_point=(1000,1000),view_height=6000)
        vp.dxf.id=-1  # common AutoCAD representation of inactive native layouts
        block=doc.blocks.new('TITLE');block.add_attdef('PROJECT',(0,0),height=2.5)
        insert=layout.add_blockref('TITLE',(350,20));insert.add_auto_attribs({'PROJECT':'OLD'})
        path=dxf_dir/(Path(name).stem+'.dxf');doc.saveas(path)
        drawings.append({'name':name,'dxf':str(path),'status':'EXPORTED_FOR_INSPECTION'})
    atomic_json(inspection/'native_inventory.json',{'source':str(source),'staged':str(source),
                'cad_version':'OFFLINE_FIXTURE','originals_unchanged':True,'assets':assets,'drawings':drawings})
    return rp.import_inspected_profile('test_profile',inspection)


def job(**changes):
    value={'profile_id':'test_profile','project_id':'new_project'};value.update(changes);return value


def test_import_preserves_inactive_viewport_and_attributes(profile):
    assert len(profile['sheets'])==2
    assert len(profile['sheets'][0]['viewports'])==1
    assert profile['sheets'][0]['title_blocks'][0]['attributes']=={'PROJECT':'OLD'}
    assert profile['sheets'][0]['viewports'][0]['custom_scale']==pytest.approx(200/6000)


def test_inactive_native_layout_primary_is_not_a_model_view():
    doc=ezdxf.new('R2013');layout=doc.layouts.get('Layout1')
    paper=layout.add_viewport(center=(200,150),size=(600,400),view_center_point=(200,150),view_height=400)
    model=layout.add_viewport(center=(200,150),size=(300,200),view_center_point=(10000,10000),view_height=6000)
    for vp in (paper,model):vp.dxf.id=0;vp.dxf.status=0
    assert rp.native_model_viewports(layout)==[model]


def test_profile_can_query_one_sheet_without_all_frozen_layer_payloads(profile):
    result=rp.profile_info('test_profile',['s001'])
    assert len(result['sheets'])==1
    assert 'frozen_layers' not in result['sheets'][0]['viewports'][0]
    assert 'frozen_layers' in rp.profile_info('test_profile',['s001'],True)['sheets'][0]['viewports'][0]


def test_native_attribute_tags_preferred_to_dxf_conversion_aliases(profile):
    inspection=Path(profile['source_directory']).parent
    inventory=json.loads((inspection/'native_inventory.json').read_text(encoding='utf-8'))
    inventory['drawings'][0]['layouts']=[{'Name':'Layout1','ModelType':False,'title_blocks':[
        {'handle':'AB','name':'TITLE','attributes':{'NATIVE_TAG':'VALUE'}}]}]
    atomic_json(inspection/'native_inventory.json',inventory)
    native=rp.import_inspected_profile('native_attribute_test',inspection)
    assert native['sheets'][0]['title_blocks'][0]['attributes']=={'NATIVE_TAG':'VALUE'}


def test_complete_set_and_explicit_subset(profile):
    assert rp.reference_plan(job())['status']=='READY_FOR_REFERENCE_REISSUE'
    partial=rp.reference_plan(job(sheet_ids=['s001']))
    assert partial['status']=='BLOCKED'
    assert any(i['kind']=='INCOMPLETE_SET' for i in partial['issues'])
    assert rp.reference_plan(job(sheet_ids=['s001'],require_complete=False))['completeness']=='SELECTED_SUBSET'


@pytest.mark.parametrize('name',['../escape','A profile','C:\\test','..','x/y',''])
def test_invalid_profile_identifier(name):
    with pytest.raises(ValueError):rp.load_profile(name)


def test_asset_tamper_is_rejected(profile):
    path=rp.profile_root()/'test_profile'/'assets'/'100 WALL PLAN.dwg'
    path.write_bytes(b'CHANGED')
    with pytest.raises(ValueError,match='modified'):rp.reference_plan(job())


def test_asset_path_traversal(tmp_path):
    for name in ('../x.dwg','C:\\x.dwg','a/b.dwg','..'):
        with pytest.raises(ValueError):rp.safe_asset(tmp_path,name)


def test_font_missing_blocks_unless_explicitly_accepted(profile):
    path=rp.profile_root()/'test_profile'/'profile.json'
    profile['issues'].append({'kind':'FONT_MISSING','level':'WARNING','font':'missing.shx'})
    atomic_json(path,profile)
    assert rp.reference_plan(job())['status']=='BLOCKED'
    assert rp.reference_plan(job(accept_font_substitution=True))['status']=='READY_FOR_REFERENCE_REISSUE'
    profile['issues'].append({'kind':'XREF_MISSING','level':'BLOCKING'})
    atomic_json(path,profile)
    assert rp.reference_plan(job(accept_font_substitution=True))['status']=='BLOCKED'


def test_plain_attribute_changes_only(profile):
    plan=rp.reference_plan(job(attributes={'s001':{'PROJECT':'Dự án mới'}}))
    assert plan['job']['attributes']['s001']['PROJECT']=='Dự án mới'
    for values in ({'UNKNOWN':'X'},{'PROJECT':'%<field>%'},{'PROJECT':'x\ny'}):
        with pytest.raises(ValueError):rp.reference_plan(job(attributes={'s001':values}))


def test_prepare_does_not_authorize_export(profile,monkeypatch):
    prepared=rr.prepare_reference(job())
    assert prepared['status']=='PREPARED_REFERENCE'
    monkeypatch.setattr(rr.subprocess,'run',lambda *a,**k:pytest.fail('Unapproved worker was launched'))
    with pytest.raises(FileNotFoundError):rr.export_reference(prepared['ticket'])
    assert not (rr.workspace()/'cad_worker.lock').exists()


def test_profile_metadata_change_invalidates_ticket(profile):
    prepared=rr.prepare_reference(job())
    profile['required_roles'].append('extra_role')
    atomic_json(rp.profile_root()/'test_profile'/'profile.json',profile)
    with pytest.raises(PermissionError,match='changed'):rr._read(prepared['ticket'])


def test_reference_worker_rejects_unsigned_or_missing_permit(profile):
    with pytest.raises(PermissionError):rr.consume_reference_permit('../escape')
    nonce='a'*48
    atomic_json(rr._home()/'permits'/(nonce+'.json'),{'payload':{'kind':'REFERENCE_WORKER'},'signature':'bad'})
    with pytest.raises(PermissionError):rr.consume_reference_permit(nonce)


def test_approval_is_one_use(profile,monkeypatch):
    prepared=rr.prepare_reference(job());ticket=prepared['ticket']
    monkeypatch.setattr('builtins.input',lambda prompt:'VE')
    rr.approve_reference(ticket)
    def fake_worker(args,**kwargs):
        approved_job=rr.consume_reference_permit(args[-1])
        assert approved_job['project_id']=='new_project'
        with pytest.raises(FileNotFoundError):rr.consume_reference_permit(args[-1])
        return types.SimpleNamespace(stdout='{"status":"MOCK_WORKER_CHECKED"}',stderr='')
    monkeypatch.setattr(rr.subprocess,'run',fake_worker)
    assert rr.export_reference(ticket)['status']=='MOCK_WORKER_CHECKED'
    with pytest.raises(FileNotFoundError):rr.export_reference(ticket)


def test_no_silent_new_design_claim(profile):
    with pytest.raises(ValueError,match='new design'):rp.reference_plan(job(mode='new_design'))


def test_portable_xrefs_never_reload():
    from autocad_agent.reference_publish import repair_xrefs
    doc=types.SimpleNamespace(Blocks=types.SimpleNamespace(Item=lambda name:pytest.fail('Valid Xref was unnecessarily reloaded')))
    repair_xrefs(doc,[{'block':'FRAME','path':'FRAME A3.dwg','asset':'FRAME A3.dwg'}])


def test_nonportable_xref_is_repaired():
    from autocad_agent.reference_publish import repair_xrefs
    calls=[]
    block=types.SimpleNamespace(Path='G:/old/frame.dwg',Reload=lambda:calls.append('reload'))
    doc=types.SimpleNamespace(Blocks=types.SimpleNamespace(Item=lambda name:block))
    repair_xrefs(doc,[{'block':'FRAME','path':'G:/old/frame.dwg','asset':'frame.dwg'}])
    assert block.Path=='frame.dwg' and calls==['reload']
