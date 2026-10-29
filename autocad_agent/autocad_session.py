"""Visible AutoCAD connection with bounded busy checks; never sends commands."""
import time
from .cad_com import retry_com


def connect(timeout=45):
    import win32com.client as win32
    import pywintypes
    try:
        app = retry_com(lambda: win32.GetActiveObject('AutoCAD.Application'), timeout)
    except pywintypes.com_error as exc:
        if exc.hresult != -2147221021:
            raise
        app = retry_com(lambda: win32.Dispatch('AutoCAD.Application'), timeout)
    # EnsureDispatch masks a busy GetTypeInfo HRESULT as TypeError; obtain the
    # type info with bounded retries before invoking makepy.
    retry_com(lambda: app._oleobj_.GetTypeInfo(), timeout)
    app = retry_com(lambda: win32.gencache.EnsureDispatch(app), timeout)
    retry_com(lambda: setattr(app, 'Visible', True), timeout)
    wait_idle(app, timeout)
    return app


def wait_idle(app, timeout=45):
    import pythoncom
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if retry_com(lambda: app.GetAcadState().IsQuiescent, min(5, timeout)):
            return
        pythoncom.PumpWaitingMessages()
        time.sleep(.2)
    raise RuntimeError('AUTOCAD_BUSY_OR_MODAL: close the pending AutoCAD prompt, then retry; no commands were sent')


def configure_pdf(doc, layout, constants, retry):
    retry(lambda: setattr(doc, 'ActiveLayout', layout))
    retry(lambda: setattr(doc, 'ActiveSpace', constants.acPaperSpace))
    retry(lambda: setattr(layout, 'ConfigName', 'DWG To PDF.pc3'))
    retry(lambda: layout.RefreshPlotDeviceInfo())
    media = 'ISO_full_bleed_A3_(420.00_x_297.00_MM)'
    if media not in retry(lambda: list(layout.GetCanonicalMediaNames())):
        raise RuntimeError('Full bleed A3 media not installed')
    for key, value in dict(CanonicalMediaName=media, PaperUnits=constants.acMillimeters,
                           PlotRotation=constants.ac0degrees, PlotType=constants.acLayout,
                           UseStandardScale=True, StandardScale=constants.ac1_1,
                           StyleSheet='monochrome.ctb', PlotWithPlotStyles=True).items():
        retry(lambda key=key, value=value: setattr(layout, key, value))


def initialize_sheet_viewports(doc,sheet,win32,retry):
    layout=retry(lambda:doc.Layouts.Item(sheet['code']))
    retry(lambda:setattr(doc,'ActiveLayout',layout));retry(lambda:setattr(doc,'ActiveSpace',win32.constants.acPaperSpace))
    block=retry(lambda:layout.Block);ports=[]
    for i in range(retry(lambda:block.Count)):
        obj=retry(lambda i=i:block.Item(i))
        if retry(lambda:str(obj.ObjectName))=='AcDbViewport':ports.append(retry(lambda obj=obj:win32.CastTo(obj,'IAcadPViewport')))
    for view in sheet['views']:
        x,y,w,h=view['rect'];matches=[]
        for vp in ports:
            width,height=retry(lambda vp=vp:(float(vp.Width),float(vp.Height)))
            center=retry(lambda vp=vp:vp.Center)
            if abs(width-w)<.001 and abs(height-h)<.001 and abs(center[0]-(x+w/2))<.001 and abs(center[1]-(y+h/2))<.001:matches.append(vp)
        if len(matches)!=1:raise RuntimeError('Cannot identify native viewport for '+sheet['code'])
        vp=matches[0];retry(lambda:vp.Display(True));retry(lambda:setattr(vp,'DisplayLocked',True))
        if not retry(lambda:bool(vp.ViewportOn)):raise RuntimeError('Native viewport did not turn on')
    retry(lambda:doc.Regen(win32.constants.acAllViewports))
    return layout
