"""Native profile publication on owned copies; original and profile assets immutable."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import csv
import json
import shutil
from .reference_profiles import reference_plan,load_profile,profile_root,safe_asset,digest,basename
from .runtime import workspace,atomic_json
from .cad_com import retry_com


def retry(fn,timeout=45):
    # Rich fit-out drawings load nested Xrefs and OLE objects asynchronously;
    # a ten-second busy retry suitable for small parts is insufficient here.
    return retry_com(fn,timeout=timeout)


def repair_xrefs(doc,references):
    """Only repair nonportable stored paths; valid relative references stay cached."""
    for ref in references:
        if ref['path'].casefold()==ref['asset'].casefold():continue
        block=retry(lambda ref=ref:doc.Blocks.Item(ref['block']))
        current=retry(lambda block=block:str(block.Path))
        if current!=ref['asset']:
            retry(lambda block=block,ref=ref:setattr(block,'Path',ref['asset']))
            retry(lambda block=block:block.Reload(),timeout=30)


def publish_reference(job,progress=None):
    import pythoncom
    import win32com.client as win32
    from pypdf import PdfReader,PdfWriter
    plan=reference_plan(job)
    if plan['status']=='BLOCKED':raise ValueError('Reference preflight blocked: '+json.dumps(plan['issues']))
    profile=load_profile(job['profile_id']);profile_dir=profile_root()/profile['id']
    target=workspace()/'projects'/plan['job']['project_id']
    target.parent.mkdir(parents=True,exist_ok=True);target.mkdir() # exclusive, never overwrite
    cad=target/'DWG';cad.mkdir();pdf_dir=target/'PDF';pdf_dir.mkdir()
    styles=target/'PlotStyles';styles.mkdir()
    report={'status':'IN_PROGRESS','mode':'reference_reissue','profile_id':profile['id'],
            'project_directory':str(target),'sheets':[],'warnings':plan['issues'],
            'completeness':plan['completeness'],'missing_roles':plan['missing_roles'],
            'font_substitution_accepted':plan['job']['accept_font_substitution'],
            'tcvn_compliance':'NOT_CHECKED'}
    for asset in profile['assets']:
        source=safe_asset(profile_dir/'assets',asset['name']);shutil.copy2(source,cad/source.name)
        if source.suffix.lower()=='.ctb':shutil.copy2(source,styles/('PROFILE_'+source.name))
    by_file=defaultdict(list)
    for sheet in plan['sheets']:by_file[sheet['drawing']].append(sheet)
    drawings={d['name']:d for d in profile['drawings']}
    pythoncom.CoInitialize();app=None;settings=None;old_style_path=None
    try:
        app=win32.gencache.EnsureDispatch(win32.GetActiveObject('AutoCAD.Application'))
        retry(lambda:setattr(app,'Visible',True))
        retry(lambda:setattr(app,'WindowState',win32.constants.acMax))
        report['cad_version']=retry(lambda:str(app.Version))
        settings=retry(lambda:app.Preferences.Files)
        old_style_path=retry(lambda:settings.PrinterStyleSheetPath)
        retry(lambda:setattr(settings,'PrinterStyleSheetPath',str(styles)+';'+old_style_path))
        for drawing,sheets in by_file.items():
            doc=None
            try:
                doc=retry(lambda:app.Documents.Open(str(cad/drawing)),timeout=30)
                retry(lambda:doc.SetVariable('BACKGROUNDPLOT',0))
                # Keep cached text/field values. Do not relink sheet-set fields to
                # the original author's unavailable workstation or DST database.
                retry(lambda:doc.SetVariable('FIELDEVAL',0))
                repair_xrefs(doc,drawings[drawing]['xrefs'])
                for sheet in sheets:
                    layout=retry(lambda:doc.Layouts.Item(sheet['layout']))
                    retry(lambda:setattr(doc,'ActiveLayout',layout))
                    retry(lambda:setattr(doc,'ActiveSpace',win32.constants.acPaperSpace))
                    overrides=plan['job']['attributes'].get(sheet['id'],{});changed=[]
                    for definition in sheet['title_blocks']:
                        if not overrides:break
                        insert=retry(lambda definition=definition:doc.HandleToObject(definition['handle']))
                        insert=win32.CastTo(insert,'IAcadBlockReference')
                        for attribute in retry(lambda:insert.GetAttributes()):
                            tag=retry(lambda:str(attribute.TagString))
                            if tag in overrides:
                                retry(lambda attribute=attribute,tag=tag:setattr(attribute,'TextString',overrides[tag]))
                                changed.append(tag)
                    if set(changed)!=set(overrides):raise RuntimeError('Not all requested title attributes were updated')
                    # Preserve native window, orientation, custom paper scaling,
                    # viewport targets, clip boundaries and layer overrides.
                    retry(lambda:setattr(layout,'ConfigName','DWG To PDF.pc3'))
                    retry(lambda:layout.RefreshPlotDeviceInfo())
                    media=sheet['plot']['paper_size']
                    names=retry(lambda:list(layout.GetCanonicalMediaNames()))
                    if media not in names:raise RuntimeError('Reference paper media not installed: '+media)
                    retry(lambda:setattr(layout,'CanonicalMediaName',media))
                    retry(lambda:setattr(layout,'PlotRotation',sheet['plot']['plot_rotation']))
                    ctb=sheet['plot']['current_style_sheet']
                    if ctb:
                        name='PROFILE_'+basename(ctb)
                        installed=retry(lambda:list(layout.GetPlotStyleTableNames()))
                        if name not in installed:raise RuntimeError('Profile CTB unavailable: '+name)
                        retry(lambda:setattr(layout,'StyleSheet',name))
                        retry(lambda:setattr(layout,'PlotWithPlotStyles',True))
                    retry(lambda:doc.Regen(win32.constants.acAllViewports))
                    retry(lambda:doc.Save())
                    filename=sheet['id']+'.pdf';path=pdf_dir/filename
                    if path.exists():raise FileExistsError(path)
                    ok=retry(lambda:doc.Plot.PlotToFile(str(path)),timeout=45)
                    if not ok or not path.is_file() or path.stat().st_size<100:raise RuntimeError('Native PDF missing or empty')
                    reader=PdfReader(path)
                    if len(reader.pages)!=1:raise RuntimeError('Expected exactly one PDF page per layout')
                    page=reader.pages[0];width=float(page.mediabox.width)*25.4/72;height=float(page.mediabox.height)*25.4/72
                    want=(sheet['plot']['paper_width'],sheet['plot']['paper_height'])
                    if min(abs(width-want[0])+abs(height-want[1]),abs(width-want[1])+abs(height-want[0]))>2:
                        raise RuntimeError('Native PDF page size differs from reference')
                    result={'id':sheet['id'],'drawing':drawing,'layout':sheet['layout'],'role':sheet['role'],
                            'pdf':str(path),'page_mm':[round(width,2),round(height,2)],
                            'attributes_updated':changed,'viewport_count':len(sheet['viewports']),
                            'native_components_preserved':True}
                    report['sheets'].append(result);atomic_json(target/'PUBLISH_REPORT.json',report)
                    if progress:progress(result)
                retry(lambda:doc.Save())
            finally:
                # This function owns this opened copy only; other user documents
                # remain open. Partial files are retained for error inspection.
                if doc is not None:
                    try:retry(lambda:doc.Close(False))
                    except Exception:pass
        ordered={row['id']:row for row in report['sheets']}
        writer=PdfWriter()
        for sheet in plan['sheets']:writer.append(ordered[sheet['id']]['pdf'],outline_item=sheet['layout'])
        merged=target/'DRAWING_SET.pdf'
        with merged.open('xb') as stream:writer.write(stream)
        with (target/'SHEET_INDEX.csv').open('x',encoding='utf-8-sig',newline='') as f:
            csvwriter=csv.writer(f);csvwriter.writerow(['Page','Sheet ID','Drawing','Layout','Role','PDF'])
            for i,s in enumerate(plan['sheets'],1):csvwriter.writerow([i,s['id'],s['drawing'],s['layout'],s['role'],'PDF/'+s['id']+'.pdf'])
        report.update({'status':'PUBLISHED_REFERENCE_REQUIRES_VISUAL_REVIEW','combined_pdf':str(merged),
                       'page_count':len(PdfReader(merged).pages),'sheet_index':str(target/'SHEET_INDEX.csv')})
        # Check profile hashes again after native operations.
        load_profile(profile['id']);report['profile_assets_unchanged']=True
        atomic_json(target/'PUBLISH_REPORT.json',report)
        return report
    except BaseException as exc:
        report['status']='FAILED_PARTIAL_OUTPUT';report['error']=str(exc)
        atomic_json(target/'PUBLISH_REPORT.json',report)
        raise
    finally:
        if settings is not None and old_style_path is not None:
            try:
                retry(lambda:setattr(settings,'PrinterStyleSheetPath',old_style_path))
                report['plot_style_search_path_restored']=retry(lambda:settings.PrinterStyleSheetPath)==old_style_path
            except Exception as exc:
                report['plot_style_search_path_restored']=False
                report['warnings'].append({'level':'WARNING','kind':'PLOT_PATH_RESTORE_FAILED','detail':str(exc)})
            atomic_json(target/'PUBLISH_REPORT.json',report)
        pythoncom.CoUninitialize()
