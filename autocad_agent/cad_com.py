"""AutoCAD 2025 English COM adapter; import only inside Windows worker process.

Creates a NEW document only. No AutoLISP, SendCommand, shutdown, purge or arbitrary script.
Zero claims of verified plot/TCVN. Leave incomplete AutoCAD documents open for inspection.
"""
from __future__ import annotations
import math
import os
import time
from pathlib import Path
from .schema import validate_job,UNITS
from .runtime import copy_exclusive
from .plotting import dwt_path,configure_layout_and_pdf

RETRYABLE_HRESULT={-2147418111,-2147417846,-2147417848}

def retry_com(fn,timeout=10):
    import pythoncom,pywintypes
    deadline=time.monotonic()+timeout;delay=.15
    while True:
        try:return fn()
        except pywintypes.com_error as e:
            if e.hresult not in RETRYABLE_HRESULT or time.monotonic()>deadline:raise
            pythoncom.PumpWaitingMessages();time.sleep(delay);delay=min(.7,delay*1.5)

def create_dwg(job,home):
    job=validate_job(job);home=Path(home)
    import pythoncom
    import win32com.client
    from win32com.client import VARIANT
    def pt(p):return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,[float(p[0]),float(p[1]),0.0])
    def coords(points):return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,[float(x) for p in points for x in p])
    def retry(fn):return retry_com(fn)
    pythoncom.CoInitialize()
    doc=None
    try:
        from .autocad_session import connect
        app=connect()
        # Generate type-library wrappers: late-bound Documents.Add can otherwise
        # return a generic object without SetVariable on real AutoCAD 2025.
        app=retry(lambda:win32com.client.gencache.EnsureDispatch(app))
        version=retry(lambda: str(app.Version))
        if not version.startswith('25.'):
            raise RuntimeError(f'AutoCAD 2025 expected (25.x), found {version}. Override only after testing.')
        retry(lambda:setattr(app,'Visible',True))
        template=dwt_path(job)
        doc=retry(lambda:app.Documents.Add(template) if template else app.Documents.Add())
        retry(lambda:doc.SetVariable('INSUNITS',UNITS[job['units']]))
        from .presentation import layer_style,annotation_height
        height=annotation_height(job)
        for key,value in {'DIMTXT':height,'DIMASZ':height,'DIMEXO':height*.4,
                          'DIMEXE':height*.6,'DIMGAP':height*.3,'DIMTAD':1,
                          'DIMDEC':2,'DIMZIN':8,'DIMLUNIT':2,'DIMLFAC':1.,'DIMSCALE':1.,
                          'MEASUREMENT':1 if job['units'] in ('mm','m') else 0}.items():
            retry(lambda key=key,value=value:doc.SetVariable(key,value))
        font=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/'arial.ttf'
        if not font.is_file():raise RuntimeError('Arial TrueType font is required for Unicode drafting')
        retry(lambda:setattr(doc.TextStyles.Item('Standard'),'fontFile',str(font)))
        # Keep enumeration inside retries; pywin32 can mask a busy COM error
        # from _NewEnum as TypeError, so use the collection's indexed API.
        collection=retry(lambda:doc.Layers)
        layers={retry(lambda i=i:collection.Item(i).Name).upper()
                for i in range(retry(lambda:collection.Count))}
        def ensure_layer(name):
            if name.upper() not in layers:
                layer=retry(lambda:doc.Layers.Add(name));layers.add(name.upper())
                color,weight,linetype=layer_style(name)
                retry(lambda:setattr(layer,'color',color))
                retry(lambda:setattr(layer,'Lineweight',weight))
                if name=='_HATCH_BOUNDARY':retry(lambda:setattr(layer,'Plottable',False))
                if linetype!='Continuous':
                    try:retry(lambda:doc.Linetypes.Item(linetype))
                    except Exception:
                        retry(lambda:doc.Linetypes.Load(linetype,'acadiso.lin'))
                    retry(lambda:setattr(layer,'Linetype',linetype))
        def add_e(space,e):
            t=e['type']
            if t=='line':obj=retry(lambda:space.AddLine(pt(e['start']),pt(e['end'])))
            elif t=='polyline':
                obj=retry(lambda:space.AddLightWeightPolyline(coords(e['points'])))
                retry(lambda:setattr(obj,'Closed',e['closed']))
            elif t=='circle':obj=retry(lambda:space.AddCircle(pt(e['center']),e['radius']))
            elif t=='arc':obj=retry(lambda:space.AddArc(pt(e['center']),e['radius'],math.radians(e['start_angle']),math.radians(e['end_angle'])))
            elif t=='text':
                obj=retry(lambda:space.AddText(e['text'],pt(e['position']),e['height']))
                retry(lambda:setattr(obj,'Rotation',math.radians(e['rotation'])))
            elif t=='mtext':
                obj=retry(lambda:space.AddMText(pt(e['position']),e['width'],e['text']))
                retry(lambda:setattr(obj,'Height',e['height']))
            elif t=='dim_aligned':obj=retry(lambda:space.AddDimAligned(pt(e['start']),pt(e['end']),pt(e['position'])))
            elif t=='dim_rotated':obj=retry(lambda:space.AddDimRotated(pt(e['start']),pt(e['end']),pt(e['position']),math.radians(e['rotation'])))
            elif t in ('dim_radial','dim_diametric'):
                ang=math.radians(e['angle']);c=e['center'];r=e['radius']
                near=[c[0]+r*math.cos(ang),c[1]+r*math.sin(ang)]
                if t=='dim_radial':obj=retry(lambda:space.AddDimRadial(pt(c),pt(near),e['leader']))
                else:
                    far=[c[0]-r*math.cos(ang),c[1]-r*math.sin(ang)]
                    obj=retry(lambda:space.AddDimDiametric(pt(near),pt(far),e['leader']))
            elif t=='insert':obj=retry(lambda:space.InsertBlock(pt(e['position']),e['block'],e['scale'],e['scale'],e['scale'],math.radians(e['rotation'])))
            elif t=='hatch':
                from .native_entities import add_native_hatch
                obj=add_native_hatch(space,e,pt,coords,retry,ensure_layer)
            elif t=='leader':
                from .native_entities import add_native_leader
                obj=add_native_leader(space,e,pt,retry)
            elif t=='table':
                from .native_entities import add_native_table
                obj=add_native_table(space,e,pt,retry)
            else:raise RuntimeError('unsupported COM entity')
            retry(lambda:setattr(obj,'Layer',e['layer']))
            if 'HIDDEN' in e['layer'].upper():retry(lambda:setattr(obj,'LinetypeScale',.2))
            if t.startswith('dim_'):
                dim_height=e.get('text_height',height)
                for key,value in {'TextHeight':dim_height,'ArrowheadSize':dim_height,'ScaleFactor':1.,
                                  'PrimaryUnitsPrecision':2,'SuppressTrailingZeros':True}.items():
                    retry(lambda key=key,value=value:setattr(obj,key,value))
            return obj
        for b in job['blocks']:
            for e in b['entities']:ensure_layer(e.get('layer','0'))
            base=pt(b.get('base',[0,0]))
            block=retry(lambda:doc.Blocks.Add(base,b['name']))
            for e in b['entities']:add_e(block,e)
        for e in job['geometry']:
            ensure_layer(e['layer']);add_e(doc.ModelSpace,e)
        working=home/'working'/(job['output_name'][:-4]+'.'+str(int(time.time()*1000))+'.working.dwg')
        pdf_working=working.with_suffix('.pdf')
        saved_before_plot=[False]
        def staged_save():
            retry(lambda:doc.SaveAs(str(working)))
            saved_before_plot[0]=True
        plot_result=configure_layout_and_pdf(doc,job,pdf_working,pt,retry,staged_save) if job['plot']['enabled'] else None
        if not saved_before_plot[0]:staged_save()
        if not working.is_file() or working.stat().st_size<100:raise RuntimeError('AutoCAD SaveAs did not produce plausible DWG')
        dest=home/job['output_name']
        if plot_result and job['plot']['pdf']:
            # PDF must already have passed page-size verification before DWG promotion.
            if not pdf_working.is_file():raise RuntimeError('PDF required but missing')
        copy_exclusive(working,dest)
        pdf_delivered=None
        if plot_result and job['plot']['pdf']:
            pdf_delivered=copy_exclusive(pdf_working,home/(job['output_name'][:-4]+'.pdf'))
        return {'status':'DWG_CREATED_NEEDS_VISUAL_REVIEW','output':str(dest),
                'working_dwg':str(working),'plot_result':plot_result,'pdf_output':str(pdf_delivered) if pdf_delivered else None,'cad_version':version,'entities_requested':len(job['geometry']),
                'tcvn_compliance':'NOT_CHECKED',
                'note':'Not reopened or visually inspected. Original new AutoCAD document may remain open as working DWG.'}
    finally:
        # NEVER quit AutoCAD / close arbitrary document. An incomplete new doc may remain open.
        pythoncom.CoUninitialize()
