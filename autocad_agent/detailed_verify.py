"""Read-only native DXF/PDF checks after AutoCAD publication."""
import math
import ezdxf
from pypdf import PdfReader
from .reference_profiles import native_model_viewports

def verify_sheet(dxf,pdf,code,views):
    doc=ezdxf.readfile(dxf);ports=native_model_viewports(doc.layouts.get(code))
    if len(ports)!=len(views):raise ValueError('Native viewport count mismatch')
    measured=[]
    for port,view in zip(ports,views):
        scale=port.dxf.view_height/port.dxf.height
        if not math.isclose(scale,view['scale'],rel_tol=1e-6):raise ValueError('Native viewport scale changed')
        if not math.isclose(port.dxf.width,view['rect'][2],abs_tol=.001):raise ValueError('Native viewport width changed')
        measured.append(scale)
    pages=PdfReader(pdf).pages
    if len(pages)!=1:raise ValueError('Native sheet PDF must have one page')
    size=[float(pages[0].mediabox.width)*25.4/72,float(pages[0].mediabox.height)*25.4/72]
    if abs(size[0]-420)>1 or abs(size[1]-297)>1:raise ValueError('Native PDF page is not landscape A3')
    return {'viewport_scales':measured,'paper_mm':size,'audit_errors':len(doc.audit().errors)}
