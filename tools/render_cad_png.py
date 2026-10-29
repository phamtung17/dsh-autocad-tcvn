"""PNG-only CAD visual QA. Does not write or publish a PDF."""
from pathlib import Path
import argparse
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext,layout
from ezdxf.addons.drawing.config import Configuration,ColorPolicy,BackgroundPolicy,HatchPolicy
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
from ezdxf.math import BoundingBox2d


def render(source,code,target,box=None):
    doc=ezdxf.readfile(source);paper=doc.layouts.get(code)
    for vp in list(paper.query('VIEWPORT')):
        if vp.dxf.id==1:paper.delete_entity(vp)
        elif vp.dxf.status==0 and not vp.dxf.flags&131072:
            # Activate the selected in-memory layout for the offline renderer.
            # Do not write these renderer-only stack IDs back to the CAD file.
            vp.dxf.status=2
    backend=PyMuPdfBackend();config=Configuration(color_policy=ColorPolicy.BLACK,background_policy=BackgroundPolicy.WHITE,hatch_policy=HatchPolicy.SHOW_OUTLINE)
    Frontend(RenderContext(doc),backend,config=config).draw_layout(paper,finalize=True)
    W=paper.dxf.get('paper_width',420);H=paper.dxf.get('paper_height',297)
    if box:W,H=box[2]-box[0],box[3]-box[1]
    else:box=[0,0,W,H]
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    data=backend.get_pixmap_bytes(layout.Page(W,H,layout.Units.mm),fmt='png',dpi=110,render_box=BoundingBox2d([(box[0],box[1]),(box[2],box[3])]))
    target.write_bytes(data);return target


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('layout');p.add_argument('output');p.add_argument('--box',nargs=4,type=float);a=p.parse_args()
    print(render(a.source,a.layout,a.output,a.box))
