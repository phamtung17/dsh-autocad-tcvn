"""Actual incremental native deep-cloning into an initially empty Model space.
Resources and paper layouts are preloaded; model entities are CREATED per batch,
never hidden/revealed to simulate drawing. Only owned staging documents are closed.
"""
from pathlib import Path
import json,time
from .runtime import atomic_json


class LiveProgress:
    def __init__(self,target,total_sheets):
        self.target=Path(target);self.started=time.time();self.sequence=0
        self.value=dict(status='PREPARING',phase='PREPARING',completed_entities=0,
                        total_entities=None,completed_sheets=0,total_sheets=total_sheets,
                        construction_release=False)
        self.emit()

    def emit(self,**update):
        self.sequence+=1;self.value.update(update)
        self.value.update(sequence=self.sequence,updated_at=time.time(),elapsed_seconds=round(time.time()-self.started,2))
        total=self.value['total_entities']
        self.value['drawing_percent']=round(100*self.value['completed_entities']/total,1) if total else 0
        self.value['heartbeat_note']='Drawing percentage is entity creation only; saving and verification finish afterward.'
        atomic_json(self.target/'LIVE_PROGRESS.json',self.value)
        with (self.target/'LIVE_EVENTS.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(self.value,ensure_ascii=False)+'\n')
        return dict(self.value)


def batches(entities,size=12):
    """Preserve generator order; flush on layer change so a batch has one detail role."""
    group=[];layer=None
    for entity in entities:
        current=entity.dxf.layer
        if group and (len(group)>=size or current!=layer):
            yield layer,group;group=[]
        layer=current;group.append(entity)
    if group:yield layer,group


def make_empty_model_template(source,path):
    import ezdxf
    document=ezdxf.readfile(source)
    for entity in list(document.modelspace()):document.modelspace().delete_entity(entity)
    document.header['$TILEMODE']=1
    document.saveas(path)
    if len(ezdxf.readfile(path).modelspace()):raise RuntimeError('LIVE_TEMPLATE_MODEL_NOT_EMPTY')


def draw_incrementally(app,source_path,template_path,project,rows,tracker,win32,pythoncom,retry,pt):
    import ezdxf
    from .autocad_session import wait_idle
    from .native_entities import add_native_table
    source_data=ezdxf.readfile(source_path)
    total=sum(len(row['model_handles'])+len(row['tables']) for row in rows)
    tracker.emit(status='RUNNING',phase='OPENING_AUTOCAD',total_entities=total)
    make_empty_model_template(source_path,template_path)
    source_doc=None;doc=None
    try:
        source_doc=retry(lambda:app.Documents.Open(str(source_path)))
        wait_idle(app)
        doc=retry(lambda:app.Documents.Open(str(template_path)))
        wait_idle(app)
        retry(lambda:doc.Activate());retry(lambda:doc.SetVariable('TILEMODE',1))
        retry(lambda:setattr(doc,'ActiveSpace',win32.constants.acModelSpace))
        if retry(lambda:doc.ModelSpace.Count)!=0:raise RuntimeError('LIVE_MODEL_MUST_START_EMPTY')
        tracker.emit(phase='DRAWING',native_initial_model_count=0)
        space=retry(lambda:doc.ModelSpace)
        done=0
        for index,(sheet,row) in enumerate(zip(project['sheets'],rows),1):
            retry(lambda:doc.Activate())
            view=sheet['views'][0];x,y=view['target'];w=view['rect'][2]*view['scale'];h=view['rect'][3]*view['scale'];ox,oy=row['offset']
            retry(lambda:app.ZoomWindow(pt((x+ox-w*.6,y+oy-h*.6)),pt((x+ox+w*.6,y+oy+h*.6))))
            entities=[source_data.entitydb[handle] for handle in row['model_handles']]
            for layer,group in batches(entities):
                # Get all source objects before CopyObjects; never mutate while enumerating COM.
                objects=[retry(lambda e=e:source_doc.HandleToObject(e.dxf.handle)) for e in group]
                tracker.emit(phase='DRAWING',sheet=sheet['code'],sheet_index=index,stage=sheet.get('stage'),
                             title=sheet['title'],detail_layer=layer,pending_entities=len(group))
                try:
                    retry(lambda:source_doc.CopyObjects(win32.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,objects),space))
                except Exception as exc:
                    raise RuntimeError('LIVE_COPY_BATCH_FAILED '+str([(e.dxf.handle,e.dxftype()) for e in group])+': '+str(exc)) from exc
                done+=len(group)
                retry(lambda:doc.Regen(win32.constants.acAllViewports))
                retry(lambda:doc.Utility.Prompt(f"\n[DSH LIVE] {index}/{len(rows)} {sheet['code']} | {layer} | {done}/{total}\n"))
                pythoncom.PumpWaitingMessages()
                # A short UI yield makes the actual creation observable without
                # replacing it with a hide/reveal animation.
                time.sleep(.08)
                tracker.emit(completed_entities=done,pending_entities=0)
            for table in row['tables']:
                add_native_table(space,table,pt,retry);done+=1
                retry(lambda:doc.Regen(win32.constants.acAllViewports))
                tracker.emit(detail_layer=table['layer'],completed_entities=done)
            tracker.emit(completed_sheets=index)
        tracker.emit(phase='INITIALIZING_LAYOUTS',native_model_count=retry(lambda:space.Count))
        return doc
    except BaseException as exc:
        tracker.emit(status='FAILED_PARTIAL',phase='FAILED',error=str(exc))
        raise
    finally:
        if source_doc is not None:
            retry(lambda:source_doc.Close(False))
        if doc is not None:retry(lambda:doc.Activate())


def progress_status(project_id):
    from .runtime import workspace
    from .reference_profiles import checked_id
    checked_id(project_id)
    path=workspace()/'generated_projects'/project_id/'LIVE_PROGRESS.json'
    if not path.is_file():return {'status':'NOT_STARTED','project_id':project_id}
    value=json.loads(path.read_text(encoding='utf-8'))
    value.update(project_id=project_id,progress_file=str(path),heartbeat_age_seconds=round(time.time()-value['updated_at'],2))
    value['possibly_stalled']=value['status']=='RUNNING' and value['heartbeat_age_seconds']>60
    return value
