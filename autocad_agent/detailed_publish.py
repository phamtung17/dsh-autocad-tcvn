"""Publish newly generated geometry, never cloned reference design geometry."""
from __future__ import annotations
from pathlib import Path
import json
import os
from collections import Counter
from .design_dispatch import build_project,project_quantities
from .branding import normalize_brand
from .detailed_sheets import make_sheet_dxf
from .native_entities import add_native_table
from .runtime import workspace,atomic_json
from .cad_com import retry_com


def publish_new_design(spec,branding=None,progress=None,*,sheet_codes=None,export_pdf=False):
    if sheet_codes is None:
        from .single_publish import publish_single_design
        return publish_single_design(spec, branding, progress,export_pdf=export_pdf)
    raise ValueError('SEPARATE_SHEET_EXPORT_DISABLED: export one complete DWG; sheet selections must not create separate drawing files')


def publish_separate_sheets(spec,branding=None,progress=None,*,sheet_codes=None):
    import pythoncom,win32com.client as win32
    from pypdf import PdfReader,PdfWriter
    project=build_project(spec);brand=normalize_brand(branding)
    if sheet_codes is not None:
        sheet_codes=set(sheet_codes)
        if not sheet_codes or not sheet_codes<={s['code'] for s in project['sheets']}:raise ValueError('Unknown or empty sheet selection')
    if project.get('workflow',{}).get('issues'):raise ValueError('PROJECT_QUALITY_GATE_FAILED: resolve modeled content or coordination issues')
    if project['spec']['mode']!='demo' and not brand['confirmed']:
        raise ValueError('BRANDING_CONFIRMATION_REQUIRED: ask the user for the final title block and logo before real export')
    target=workspace()/'generated_projects'/project['spec']['project_id'];target.parent.mkdir(parents=True,exist_ok=True);target.mkdir()
    dxf_dir=target/'DWG';dxf_dir.mkdir();pdf_dir=target/'PDF';pdf_dir.mkdir()
    report={'status':'IN_PROGRESS','generation_mode':'NEW_PARAMETRIC_GEOMETRY','reference_geometry_read':False,
            'spec':project['spec'],'branding':brand,'sheets':[],'quantities':project_quantities(project),'workflow':project.get('workflow'),
            'tcvn_compliance':'NOT_CHECKED','engineering_status':project['engineering_status']}
    atomic_json(target/'DESIGN_INPUT.json',{'spec':project['spec'],'branding':brand})
    def retry(fn,timeout=40):return retry_com(fn,timeout)
    def pt(point):return win32.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,[float(point[0]),float(point[1]),0.])
    pythoncom.CoInitialize()
    try:
        import pywintypes
        try:app=win32.gencache.EnsureDispatch(win32.GetActiveObject('AutoCAD.Application'))
        except pywintypes.com_error as exc:
            if exc.hresult!=-2147221021:raise
            app=win32.gencache.EnsureDispatch('AutoCAD.Application')
        retry(lambda:setattr(app,'Visible',True));retry(lambda:setattr(app,'WindowState',win32.constants.acMax))
        report['cad_version']=retry(lambda:str(app.Version))
        for index,sheet in enumerate(project['sheets'],1):
            if sheet_codes is not None and sheet['code'] not in sheet_codes:continue
            dxf=dxf_dir/(sheet['code']+'.dxf');dwg=dxf.with_suffix('.dwg');pdf=pdf_dir/(sheet['code']+'.pdf')
            composed=make_sheet_dxf(sheet,project['spec'],brand,dxf,index,len(project['sheets']));doc=None
            try:
                doc=retry(lambda:app.Documents.Open(str(dxf)))
                for style,font_name in [('Standard','arial.ttf'),('BRAND_BOLD','arialbd.ttf')]:
                    font=str(Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/font_name)
                    retry(lambda style=style,font=font:setattr(doc.TextStyles.Item(style),'fontFile',font))
                retry(lambda:doc.SetVariable('BACKGROUNDPLOT',0));retry(lambda:doc.SetVariable('IMAGEFRAME',win32.VARIANT(pythoncom.VT_I2,0)))
                # Tables in offline previews are explicitly tagged. Only these
                # generated preview entities are removed and replaced by native
                # editable ACAD_TABLE objects; no user objects are selected.
                space=retry(lambda:doc.ModelSpace);remove=[]
                for i in range(retry(lambda:space.Count)):
                    obj=retry(lambda i=i:space.Item(i))
                    if retry(lambda:str(obj.Layer))=='_PREVIEW_TABLE':remove.append(obj)
                for obj in remove:retry(lambda obj=obj:obj.Delete())
                tables=[e for e in sheet['job']['geometry'] if e['type']=='table']
                for e in tables:add_native_table(space,e,pt,retry)
                layout=retry(lambda:doc.Layouts.Item(sheet['code']))
                retry(lambda:setattr(doc,'ActiveLayout',layout));retry(lambda:setattr(doc,'ActiveSpace',win32.constants.acPaperSpace))
                retry(lambda:setattr(layout,'ConfigName','DWG To PDF.pc3'));retry(lambda:layout.RefreshPlotDeviceInfo())
                medium='ISO_full_bleed_A3_(420.00_x_297.00_MM)'
                if medium not in retry(lambda:list(layout.GetCanonicalMediaNames())):raise RuntimeError('Full bleed A3 media not installed')
                retry(lambda:setattr(layout,'CanonicalMediaName',medium));retry(lambda:setattr(layout,'PaperUnits',win32.constants.acMillimeters))
                retry(lambda:setattr(layout,'PlotRotation',win32.constants.ac0degrees));retry(lambda:setattr(layout,'PlotType',win32.constants.acLayout))
                retry(lambda:setattr(layout,'UseStandardScale',True));retry(lambda:setattr(layout,'StandardScale',win32.constants.ac1_1))
                if 'monochrome.ctb' not in retry(lambda:list(layout.GetPlotStyleTableNames())):raise RuntimeError('monochrome.ctb is missing')
                retry(lambda:setattr(layout,'StyleSheet','monochrome.ctb'));retry(lambda:setattr(layout,'PlotWithPlotStyles',True))
                retry(lambda:doc.Regen(win32.constants.acAllViewports));retry(lambda:doc.SaveAs(str(dwg),win32.constants.ac2018_dwg))
                if not retry(lambda:doc.Plot.PlotToFile(str(pdf)),timeout=60):raise RuntimeError('AutoCAD PDF plot failed')
                native_dxf=dxf_dir/(sheet['code']+'_native.dxf')
                retry(lambda:doc.SaveAs(str(native_dxf),win32.constants.ac2013_dxf))
                import ezdxf
                native=ezdxf.readfile(native_dxf);audit=native.audit()
                if audit.errors:raise RuntimeError('Native DXF structural audit failed')
                counts=dict(Counter(e.dxftype() for e in native.modelspace()))
                if counts.get('ACAD_TABLE',0)!=len(tables):raise RuntimeError('Expected native tables not found after save/reopen')
                if any(e.dxf.layer=='_PREVIEW_TABLE' for e in native.modelspace()):raise RuntimeError('Preview table geometry remained in native deliverable')
                expected_hatches=sum(e['type']=='hatch' for e in sheet['job']['geometry'])
                if counts.get('HATCH',0)!=expected_hatches:raise RuntimeError('Native hatch count mismatch')
                expected_dims=sum(e['type'].startswith('dim_') for e in sheet['job']['geometry'])
                if counts.get('DIMENSION',0)!=expected_dims:raise RuntimeError('Native dimension count mismatch')
                measured=[]
                for entity in native.modelspace().query('DIMENSION'):
                    value=entity.get_measurement()
                    if isinstance(value,(int,float)):measured.append(round(float(value),6))
                pages=PdfReader(pdf).pages
                if len(pages)!=1:raise RuntimeError('Expected one native page')
                from .detailed_verify import verify_sheet
                native_checks=verify_sheet(native_dxf,pdf,sheet['code'],sheet['views'])
                result={'code':sheet['code'],'title':sheet['title'],'stage':sheet.get('stage'),'role':sheet.get('role'),'floor':sheet.get('floor'),'dwg':str(dwg),'dxf':str(native_dxf),'pdf':str(pdf),
                        'native_entity_types':counts,'native_dimension_measurements':measured,
                        'viewports':len(sheet['views']),'views':sheet['views'],'native_tables':len(tables),
                        'new_geometry_entities':len(sheet['job']['geometry']),'dxf_audit_errors':len(audit.errors),'native_checks':native_checks,
                        'paper_mm':[round(float(pages[0].mediabox.width)*25.4/72,2),round(float(pages[0].mediabox.height)*25.4/72,2)]}
                report['sheets'].append(result);atomic_json(target/'GENERATION_REPORT.json',report)
                if progress:progress(result)
            finally:
                if doc is not None:
                    try:retry(lambda:doc.Close(False))
                    except Exception:pass
        writer=PdfWriter()
        for row in report['sheets']:writer.append(row['pdf'],outline_item=row['code']+' '+row['title'])
        output=target/'NEW_DESIGN_DRAWING_SET.pdf'
        with output.open('xb') as f:writer.write(f)
        report.update({'status':'NEW_DESIGN_NATIVE_VERIFIED_NEEDS_VISUAL_REVIEW','combined_pdf':str(output),
                       'output_directory':str(target),'sheet_count':len(report['sheets'])})
        if sheet_codes is not None:
            report.update(status='PARTIAL_NATIVE_REGEN_NOT_A_FULL_DELIVERY',source_sheet_count=len(project['sheets']))
        if 'workflow' in project and sheet_codes is None:
            from .project_delivery import write_delivery_index
            report['delivery']=write_delivery_index(target,report,project)
        atomic_json(target/'GENERATION_REPORT.json',report)
        if 'workflow' in project and sheet_codes is None:
            from .project_delivery import seal_delivery
            seal_delivery(target)
        return report
    except BaseException as exc:
        report['status']='FAILED_PARTIAL_OUTPUT';report['error']=str(exc);atomic_json(target/'GENERATION_REPORT.json',report);raise
    finally:pythoncom.CoUninitialize()
