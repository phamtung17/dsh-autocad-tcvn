from pathlib import Path
import json,time
import ezdxf
import pytest
from autocad_agent.live_drawing import batches,LiveProgress,make_empty_model_template,progress_status
from autocad_agent.fitout_design import demo_spec
from autocad_agent.design_dispatch import build_project
from autocad_agent.single_drawing import compose_project


def test_batches_keep_order_and_layer_and_limit():
 d=ezdxf.new();m=d.modelspace()
 for i in range(29):m.add_line((i,0),(i,1),dxfattribs={'layer':'WALL' if i<25 else 'DOOR'})
 groups=list(batches(m));assert [len(g) for _,g in groups]==[12,12,1,4]
 assert [e for _,g in groups for e in g]==list(m)
 assert all(all(e.dxf.layer==layer for e in group) for layer,group in groups)


def test_empty_template_keeps_layout_resources(tmp_path):
 d=ezdxf.new();d.layers.new('A-WALL');d.blocks.new('DOOR').add_line((0,0),(0,1));d.layouts.new('AR-101').add_text('Title');d.modelspace().add_blockref('DOOR',(0,0))
 source=tmp_path/'source.dxf';empty=tmp_path/'empty.dxf';d.saveas(source)
 make_empty_model_template(source,empty);result=ezdxf.readfile(empty)
 assert not list(result.modelspace());assert 'DOOR' in result.blocks
 assert len(result.layouts.get('AR-101'))==1
 assert len(ezdxf.readfile(source).modelspace())==1


def test_progress_separates_creation_from_completion(tmp_path,monkeypatch):
 monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path));root=tmp_path/'generated_projects'/'test-live';root.mkdir(parents=True)
 t=LiveProgress(root,2);t.emit(status='RUNNING',phase='DRAWING',total_entities=10,completed_entities=5)
 t.emit(completed_entities=10,phase='SAVING_DWG')
 p=progress_status('test-live');assert p['drawing_percent']==100 and p['status']=='RUNNING'
 events=[json.loads(s) for s in (root/'LIVE_EVENTS.jsonl').read_text(encoding='utf-8').splitlines()]
 assert [e['sequence'] for e in events]==[1,2,3]
 assert events[1]['completed_entities']==5
 t.emit(status='FAILED_PARTIAL',phase='FAILED',error='COM busy')
 assert progress_status('test-live')['status']=='FAILED_PARTIAL'


def test_progress_rejects_traversal_and_reports_absence(tmp_path,monkeypatch):
 monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path))
 with pytest.raises(ValueError):progress_status('../other')
 assert progress_status('not-started')['status']=='NOT_STARTED'


def test_composition_leader_links_and_sheet_handle_inventory(tmp_path):
 project=build_project(demo_spec());path=tmp_path/'project.dxf';rows=compose_project(project,{},path);doc=ezdxf.readfile(path)
 handles=[h for row in rows for h in row['model_handles']]
 assert len(handles)==len(set(handles))
 assert set(handles)=={e.dxf.handle for e in doc.modelspace() if e.dxf.layer!='_PREVIEW_TABLE'}
 for leader in doc.modelspace().query('LEADER'):
  annotation=doc.entitydb.get(leader.dxf.annotation_handle)
  assert annotation is not None and annotation.dxftype() in ('MTEXT','TEXT')
