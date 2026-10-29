"""Native one-DWG publication. A DXF is never reported as a DWG."""
from pathlib import Path
import os
from collections import Counter
from .runtime import workspace, atomic_json
from .design_dispatch import build_project, project_quantities
from .branding import normalize_brand
from .single_drawing import compose_project
from .autocad_session import connect, wait_idle, configure_pdf, initialize_sheet_viewports
from .cad_com import retry_com


def publish_single_design(spec, branding=None, progress=None, *, export_pdf=False):
    if type(export_pdf) is not bool:raise ValueError('export_pdf must be boolean')
    import pythoncom, win32com.client as win32, ezdxf
    from pypdf import PdfReader, PdfWriter
    project = build_project(spec)
    brand = normalize_brand(branding)
    if project.get('workflow', {}).get('issues'):
        raise ValueError('PROJECT_QUALITY_GATE_FAILED: resolve modeled issues')
    if project['spec']['mode'] != 'demo' and not brand['confirmed']:
        raise ValueError('BRANDING_CONFIRMATION_REQUIRED')
    target = workspace() / 'generated_projects' / project['spec']['project_id']
    target.mkdir(parents=True, exist_ok=False)
    cache=workspace()/'cad_work'/project['spec']['project_id'];cache.mkdir(parents=True,exist_ok=False)
    dxf = cache / 'PROJECT.dxf'
    dwg = target / 'PROJECT.dwg'
    native_dxf = dxf.with_name('PROJECT_native.dxf')
    report = dict(status='IN_PROGRESS', output_mode='SINGLE_DWG_MULTIPLE_LAYOUTS',
                  pdf_exported=export_pdf,native_dxf_delivery=False,dwg_relative_path='PROJECT.dwg',
                  generation_mode='NEW_PARAMETRIC_GEOMETRY', reference_geometry_read=False,
                  spec=project['spec'], branding=brand, sheets=[], workflow=project.get('workflow'),
                  quantities=project_quantities(project), engineering_status=project['engineering_status'],
                  tcvn_compliance='NOT_CHECKED', construction_release=False)
    atomic_json(target / 'DESIGN_INPUT.json', dict(spec=project['spec'], branding=brand))
    doc = None
    from .live_drawing import LiveProgress,draw_incrementally
    live=LiveProgress(target,len(project['sheets']))
    report.update(drawing_execution='LIVE_NATIVE_BATCHES',progress_file=str(target/'LIVE_PROGRESS.json'),
                  progress_events=str(target/'LIVE_EVENTS.jsonl'))
    pythoncom.CoInitialize()
    retry = lambda fn: retry_com(fn, 40)
    pt = lambda p: win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(p[0]), float(p[1]), 0.])
    try:
        app = connect()
        retry(lambda: setattr(app,'WindowState',win32.constants.acMax))
        report['cad_version'] = retry(lambda: str(app.Version))
        live.emit(status='RUNNING',phase='PLANNING_GEOMETRY')
        rows = compose_project(project, brand, dxf)
        doc=draw_incrementally(app,dxf,cache/'LIVE_EMPTY_MODEL.dxf',project,rows,live,win32,pythoncom,retry,pt)
        for style, name in [('Standard', 'arial.ttf'), ('BRAND_BOLD', 'arialbd.ttf')]:
            retry(lambda style=style, name=name: setattr(doc.TextStyles.Item(style), 'fontFile',
                  str(Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts' / name)))
        if export_pdf:retry(lambda: doc.SetVariable('BACKGROUNDPLOT', 0))
        space = retry(lambda: doc.ModelSpace)
        remove = []
        for i in range(retry(lambda: space.Count)):
            obj = retry(lambda i=i: space.Item(i))
            if retry(lambda: str(obj.Layer)) == '_PREVIEW_TABLE': remove.append(obj)
        for obj in remove: retry(lambda obj=obj: obj.Delete())
        writer = PdfWriter() if export_pdf else None
        if export_pdf:(target/'PDF').mkdir()
        for layout_index,(sheet,row) in enumerate(zip(project['sheets'],rows),1):
            live.emit(phase='INITIALIZING_LAYOUTS',sheet=sheet['code'],sheet_index=layout_index,
                      stage=sheet.get('stage'),title=sheet['title'],detail_layer='P-VPORT')
            # Initialize native viewports even when plotting is not requested.
            # Otherwise AutoCAD can serialize imported layouts with id/status 0.
            layout=initialize_sheet_viewports(doc,sheet,win32,retry)
            pdf=None
            if export_pdf:
                layout = retry(lambda: doc.Layouts.Item(sheet['code']))
                configure_pdf(doc, layout, win32.constants, retry)
                retry(lambda: doc.Regen(win32.constants.acAllViewports))
                pdf = target / 'PDF' / (sheet['code'] + '.pdf')
                if not retry(lambda: doc.Plot.PlotToFile(str(pdf))): raise RuntimeError('NATIVE_PDF_PLOT_FAILED')
                pages = PdfReader(pdf).pages
                if len(pages) != 1: raise RuntimeError('Unexpected PDF page count')
                width, height = float(pages[0].mediabox.width)*25.4/72, float(pages[0].mediabox.height)*25.4/72
                if abs(width-420)>.2 or abs(height-297)>.2: raise RuntimeError('Native PDF paper size mismatch')
            result = {k: sheet.get(k) for k in ('code', 'title', 'stage', 'role', 'floor')}
            result.update(dwg=str(dwg), pdf=str(pdf) if pdf else None, layout=sheet['code'], model_offset=row['offset'], views=sheet['views'],native_viewports_on=True)
            report['sheets'].append(result)
            if writer:writer.append(pdf, outline_item=sheet['code']+' '+sheet['title'])
            atomic_json(target/'GENERATION_REPORT.json', report)
            if progress: progress(result)
        live.emit(phase='SAVING_DWG')
        retry(lambda: doc.SetVariable('TILEMODE',1))
        retry(lambda: setattr(doc,'ActiveSpace',win32.constants.acModelSpace))
        retry(lambda: doc.Activate());retry(lambda: app.ZoomExtents())
        retry(lambda: doc.Regen(win32.constants.acAllViewports))
        retry(lambda: doc.SaveAs(str(dwg), win32.constants.ac2018_dwg))
        if not dwg.is_file() or dwg.read_bytes()[:6] != b'AC1032':
            raise RuntimeError('NATIVE_DWG_NOT_SAVED_AS_AUTOCAD_2018_PLUS')
        retry(lambda: doc.SaveAs(str(native_dxf), win32.constants.ac2013_dxf))
        live.emit(phase='VERIFYING_NATIVE')
        native = ezdxf.readfile(native_dxf)
        if native.audit().errors: raise RuntimeError('Native DXF audit failed')
        expected = {s['code'] for s in project['sheets']}
        if expected != {l.name for l in native.layouts if l.name != 'Model'}:
            raise RuntimeError('Native layout inventory mismatch')
        counts = Counter(e.dxftype() for e in native.modelspace())
        if counts['ACAD_TABLE'] != sum(len(r['tables']) for r in rows): raise RuntimeError('Native table count mismatch')
        expected_dims = sum(e['type'].startswith('dim_') for s in project['sheets'] for e in s['job']['geometry'])
        if counts['DIMENSION'] != expected_dims: raise RuntimeError('Native dimension count mismatch')
        from .single_verify import verify_combined
        report['native_checks']=verify_combined(dxf,native_dxf,project,rows)
        atomic_json(target/'NATIVE_VERIFICATION.json',report['native_checks'])
        combined = None
        if writer:
            combined=target/'NEW_DESIGN_DRAWING_SET.pdf'
            with combined.open('xb') as stream: writer.write(stream)
        # Return the generated native DWG to the visible session and leave it open.
        retry(lambda: doc.Close(False)); doc = None
        doc = retry(lambda: app.Documents.Open(str(dwg)))
        wait_idle(app)
        report.update(status='SINGLE_DWG_NATIVE_CHECKED_NEEDS_VISUAL_REVIEW', dwg=str(dwg),
                      combined_pdf=str(combined) if combined else None, sheet_count=len(rows), output_directory=str(target),active_space='Model',
                      native_entity_types=dict(counts), autocad_left_open=True)
        if 'workflow' in project:
            from .project_delivery import write_delivery_index
            report['delivery'] = write_delivery_index(target, report, project)
        atomic_json(target/'GENERATION_REPORT.json', report)
        live.emit(status='COMPLETED_NEEDS_REVIEW',phase='COMPLETED',dwg=str(dwg))
        from .project_delivery import seal_delivery
        seal_delivery(target)
        return report
    except BaseException as exc:
        live.emit(status='FAILED_PARTIAL',phase='FAILED',error=str(exc))
        report.update(status='FAILED_PARTIAL_OUTPUT', error=str(exc))
        atomic_json(target/'GENERATION_REPORT.json', report)
        raise
    finally:
        # Preserve the user's visible document, including partial work for inspection.
        pythoncom.CoUninitialize()
