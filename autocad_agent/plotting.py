"""AutoCAD 2025 ActiveX paper-space plot pipeline (Windows integration required).

Fail closed: missing media/device/CTB, wrong sheet or clipped view are errors;
no silent scale-to-fit. Requires actual AutoCAD on the operator's PC.
"""
from __future__ import annotations
import math
import os
from pathlib import Path
from .qa import geometry_report
from .schema import SHEETS

MM_PER_UNIT={'mm':1.,'m':1000.,'inch':25.4,'feet':304.8}


def dwt_path(job):
    name=job['plot']['dwt']
    if not name:return None
    raw=os.environ.get('CAD_DWT_DIR')
    if not raw:raise ValueError('plot.dwt specified but CAD_DWT_DIR is missing')
    root=Path(raw).expanduser().resolve(strict=True)
    template=(root/name).resolve(strict=True)
    if root not in template.parents or template.suffix.lower()!='.dwt':
        raise ValueError('DWT must be inside CAD_DWT_DIR')
    return str(template)


def sheet_size_mm(job):
    short,long=SHEETS[job['sheet']['format']]
    return (long,short) if job['sheet']['orientation']=='landscape' else (short,long)


def viewport_plan(job,margin_x=18,margin_bottom=22,margin_top=18):
    """Pure plan, validates physical model fit at the ACTUAL intended print scale."""
    sw,sh=sheet_size_mm(job)
    if job.get('titleblock'):margin_bottom=max(margin_bottom,60)
    vp_w=sw-2*margin_x;vp_h=sh-margin_top-margin_bottom
    if vp_w<=0 or vp_h<=0:raise ValueError('page too small for project margins')
    den=job['sheet']['scale_denominator']
    factor=MM_PER_UNIT[job['units']]/den
    bounds=geometry_report(job)['bounds']
    if bounds is None:raise ValueError('drawing has no geometry bounds')
    model_width=(bounds[2]-bounds[0])*factor
    model_height=(bounds[3]-bounds[1])*factor
    if model_width>vp_w-2 or model_height>vp_h-2:
        raise ValueError(f'drawing clipped at requested 1:{den:g} scale: need {model_width:.2f}x{model_height:.2f}mm, available {vp_w-2:.2f}x{vp_h-2:.2f}mm')
    return {'sheet_mm':(sw,sh),'viewport_center_mm':(sw/2,margin_bottom+vp_h/2),
            'viewport_mm':(vp_w,vp_h),'target_center':((bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2),
            'custom_scale':factor,'model_extents_mm':(model_width,model_height),
            'scale_denominator':den,'scope':'project sheet template; not a TCVN clause'}


def _constant(name):
    """Require an actual AutoCAD type library, never guess enum values."""
    from win32com.client import constants
    try:return getattr(constants,name)
    except AttributeError as exc:
        raise RuntimeError(f'Missing AutoCAD type-library constant {name}. Verify COM registration and generated win32com support.') from exc


def choose_media(layout, wanted, sheet):
    """Select canonical media by measured physical dimensions, fail on ambiguous/missing."""
    candidates=[]
    for medium in list(layout.GetCanonicalMediaNames()):
        if medium in ('None','UserDefinedMetric') or not isinstance(medium,str):continue
        try:
            layout.CanonicalMediaName=medium
            w,h=map(float,layout.GetPaperSize())
        except Exception:continue
        target_w,target_h=wanted
        if min(abs(w-target_w)+abs(h-target_h),abs(w-target_h)+abs(h-target_w))<=1.2:
            lower,upper=layout.GetPaperMargins()
            candidates.append((medium,w,h,tuple(lower),tuple(upper)))
    if not candidates:
        raise RuntimeError(f'No installed PDF canonical media matches {sheet} {wanted}; configure printer in AutoCAD')
    # Prefer media whose orientation already matches the target, avoiding layout rotation ambiguity.
    candidates.sort(key=lambda x:(sum(x[3])+sum(x[4]),abs(x[1]-wanted[0])+abs(x[2]-wanted[1]),0 if sheet.lower() in x[0].lower() else 1,len(x[0])))
    name,w,h,lower,upper=candidates[0]
    if max(*lower,*upper)>9:
        raise RuntimeError('PDF media margins exceed project 10mm frame; install full-bleed ISO media')
    layout.CanonicalMediaName=name
    # For the official sheet orientation, rotate if native media orientation is opposite.
    layout.PlotRotation=_constant('ac0degrees' if abs(w-wanted[0])+abs(h-wanted[1])<=1.2 else 'ac90degrees')
    return {'canonical_name':name,'native_size_mm':(w,h),'margins_mm':[lower,upper]}


def configure_layout_and_pdf(doc,job,pdf_path,pt,retry,save_before_plot=None):
    """Create named layout, locked viewport and (if requested) real AutoCAD PDF.

    Must be called within STA COM worker before final deliverable promotion.
    Errors are intentionally fatal; caller must preserve working DWG for inspection.
    """
    if not job['plot']['enabled']:return None
    plan=viewport_plan(job)
    layout_names={x.Name.lower() for x in retry(lambda:doc.Layouts)}
    name='CAD_AGENT_SHEET'
    if name.lower() in layout_names:
        raise RuntimeError('DWT already contains CAD_AGENT_SHEET; remove/rename it in the approved DWT before use')
    layout=retry(lambda:doc.Layouts.Add(name))
    retry(lambda:setattr(doc,'ActiveLayout',layout))
    retry(lambda:setattr(doc,'ActiveSpace',_constant('acPaperSpace')))
    # Preserve the layout's primary paper viewport (DXF id=1). Deleting it
    # promotes the next viewport and corrupts the paper/model view distinction.
    generated_viewports=[]
    for i in range(retry(lambda:doc.PaperSpace.Count)):
        entity=retry(lambda i=i:doc.PaperSpace.Item(i))
        if retry(lambda:entity.ObjectName)=='AcDbViewport':generated_viewports.append(entity)
    # In this newly created layout AutoCAD enumerates the primary viewport
    # first, followed by its optional automatic model viewport(s).
    for entity in generated_viewports[1:]:retry(lambda entity=entity:entity.Delete())
    if job.get('titleblock'):
        from .titleblock import apply_project_titleblock
        apply_project_titleblock(doc,job,pt,retry)
    sw,sh=plan['sheet_mm']
    cx,cy=plan['viewport_center_mm'];w,h=plan['viewport_mm']
    viewport=retry(lambda:doc.PaperSpace.AddPViewport(pt((cx,cy)),w,h))
    viewport_layer=retry(lambda:doc.Layers.Add('CAD_AGENT_VIEWPORT'))
    retry(lambda:setattr(viewport_layer,'Plottable',False))
    retry(lambda:setattr(viewport,'Layer','CAD_AGENT_VIEWPORT'))
    retry(lambda:viewport.Display(True))
    # Target alone leaves AutoCAD's inherited DCS view center offset intact.
    # Activate the viewport and explicitly center the model before locking.
    retry(lambda:setattr(doc,'MSpace',True))
    retry(lambda:setattr(doc,'ActivePViewport',viewport))
    retry(lambda:doc.Application.ZoomCenter(pt(plan['target_center']),h/plan['custom_scale']))
    retry(lambda:setattr(viewport,'StandardScale',_constant('acVpCustomScale')))
    retry(lambda:setattr(viewport,'CustomScale',plan['custom_scale']))
    retry(lambda:setattr(viewport,'DisplayLocked',True))
    retry(lambda:setattr(doc,'MSpace',False))
    # Request printer only if PDF is needed. Paper size cannot be guessed.
    if not job['plot']['pdf']:
        return {'status':'LAYOUT_CONFIGURED_NEEDS_VISUAL_REVIEW','viewport':plan,'pdf_requested':False}
    pdf_path=Path(pdf_path)
    if pdf_path.exists():raise FileExistsError('PDF staging file already exists')
    retry(lambda:setattr(layout,'ConfigName','DWG To PDF.pc3'))
    retry(lambda:layout.RefreshPlotDeviceInfo())
    media=choose_media(layout,plan['sheet_mm'],job['sheet']['format'])
    retry(lambda:setattr(layout,'PaperUnits',_constant('acMillimeters')))
    retry(lambda:setattr(layout,'PlotType',_constant('acLayout')))
    retry(lambda:setattr(layout,'UseStandardScale',True))
    retry(lambda:setattr(layout,'StandardScale',_constant('ac1_1')))
    # CenterPlot is invalid for acLayout on real AutoCAD; use layout origin.
    if job['plot']['ctb']:
        styles=set(retry(lambda:list(layout.GetPlotStyleTableNames())))
        if job['plot']['ctb'] not in styles:raise RuntimeError('Requested CTB not installed')
        retry(lambda:setattr(layout,'StyleSheet',job['plot']['ctb']))
        retry(lambda:setattr(layout,'PlotWithPlotStyles',True))
    # AutoCAD plotting is more reliable when the drawing is already saved.
    if save_before_plot is not None:save_before_plot()
    old_bg=retry(lambda:doc.GetVariable('BACKGROUNDPLOT'))
    try:
        retry(lambda:doc.SetVariable('BACKGROUNDPLOT',0))
        retry(lambda:doc.Regen(_constant('acAllViewports')))
        # PlotToFile targets ActiveLayout only; avoid plot multi-layout names and prompts.
        ok=retry(lambda:doc.Plot.PlotToFile(str(pdf_path)))
        if not ok:raise RuntimeError('AutoCAD PlotToFile returned False')
    finally:
        retry(lambda:doc.SetVariable('BACKGROUNDPLOT',old_bg))
    if not pdf_path.is_file() or pdf_path.stat().st_size<100:
        raise RuntimeError('AutoCAD PDF missing or empty after plotting')
    from pypdf import PdfReader
    reader=PdfReader(str(pdf_path))
    if len(reader.pages)!=1:raise RuntimeError('expected one PDF page')
    page=reader.pages[0]
    pw=float(page.mediabox.width)*25.4/72
    ph=float(page.mediabox.height)*25.4/72
    if min(abs(pw-sw)+abs(ph-sh),abs(pw-sh)+abs(ph-sw))>2.0:
        raise RuntimeError(f'PDF page {pw:.2f}x{ph:.2f}mm not requested sheet {sw}x{sh}mm')
    return {'status':'AUTOCAD_PDF_PAGE_SIZE_CHECKED_NEEDS_VISUAL_REVIEW',
            'pdf_file':str(pdf_path),'pdf_size_mm':[round(pw,2),round(ph,2)],
            'viewport':plan,'media':media,'tcvn_compliance':'NOT_CHECKED'}
