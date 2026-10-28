"""Rich native AutoCAD entities shared by direct and generated-sheet routes."""
from __future__ import annotations


def add_native_table(space,e,pt,retry):
    import win32com.client as win32
    table=retry(lambda:space.AddTable(pt(e['position']),len(e['rows'])+2,len(e['columns']),e['row_height'],e['widths'][0]))
    retry(lambda:setattr(table,'RegenerateTableSuppressed',True))
    try:
        retry(lambda:setattr(table,'TitleSuppressed',False));retry(lambda:setattr(table,'HeaderSuppressed',False))
        mask=win32.constants.acTitleRow|win32.constants.acHeaderRow|win32.constants.acDataRow
        retry(lambda:table.SetTextHeight(mask,e['height']))
        retry(lambda:table.SetTextStyle(mask,'Standard'))
        retry(lambda:setattr(table,'VertCellMargin',.5))
        retry(lambda:setattr(table,'HorzCellMargin',1.))
        for i,width in enumerate(e['widths']):retry(lambda i=i,width=width:table.SetColumnWidth(i,width))
        retry(lambda:table.SetText(0,0,e['title']))
        for r,row in enumerate([e['columns']]+e['rows'],1):
            for c,value in enumerate(row):
                retry(lambda r=r,c=c,value=value:table.SetText(r,c,value))
                alignment=win32.constants.acMiddleCenter if r==1 else win32.constants.acMiddleLeft
                retry(lambda r=r,c=c,alignment=alignment:table.SetCellAlignment(r,c,alignment))
                retry(lambda r=r,c=c:table.SetCellTextHeight(r,c,e['height']))
        for r in range(len(e['rows'])+2):
            retry(lambda r=r:table.SetRowHeight(r,e['row_height']))
        retry(lambda:setattr(table,'Layer',e['layer']))
    finally:retry(lambda:setattr(table,'RegenerateTableSuppressed',False))
    retry(lambda:table.RecomputeTableBlock(True))
    return table


def add_native_hatch(space,e,pt,coords,retry,ensure_layer):
    import pythoncom,win32com.client as win32
    boundary_layer='_HATCH_BOUNDARY'
    ensure_layer(boundary_layer)
    def boundary(points):
        obj=retry(lambda:space.AddLightWeightPolyline(coords(points)))
        retry(lambda:setattr(obj,'Closed',True));retry(lambda:setattr(obj,'Layer',boundary_layer));return obj
    outer=boundary(e['points'])
    inners=[boundary(points) for points in e['holes']]
    hatch=retry(lambda:space.AddHatch(win32.constants.acHatchPatternTypePreDefined,e['pattern'],True))
    retry(lambda:hatch.AppendOuterLoop(win32.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[outer])))
    for inner in inners:
        retry(lambda inner=inner:hatch.AppendInnerLoop(win32.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[inner])))
    if e['pattern']!='SOLID':
        import math
        retry(lambda:setattr(hatch,'PatternScale',e['pattern_scale']))
        retry(lambda:setattr(hatch,'PatternAngle',math.radians(e['angle'])))
    retry(lambda:hatch.Evaluate());return hatch


def add_native_leader(space,e,pt,retry):
    import pythoncom,win32com.client as win32
    annotation=retry(lambda:space.AddMText(pt(e['points'][-1]),e['text_width'],e['text']))
    retry(lambda:setattr(annotation,'Height',e['height']))
    if e.get('align')=='right':retry(lambda:setattr(annotation,'AttachmentPoint',win32.constants.acAttachmentPointTopRight))
    retry(lambda:setattr(annotation,'Layer',e['layer']))
    coordinates=win32.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,[value for point in e['points'] for value in (*point,0.)])
    leader=retry(lambda:space.AddLeader(coordinates,annotation,win32.constants.acLineWithArrow))
    retry(lambda:setattr(leader,'ArrowheadSize',e['height']*.8));return leader
