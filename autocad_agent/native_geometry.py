from collections import Counter

def primitive_keys(entities,native=False):
    def point(p):return (round(float(p[0]),5),round(float(p[1]),5))
    result=Counter()
    for e in entities:
        kind=e.dxftype().lower() if native else e['type'];layer=e.dxf.layer if native else e.get('layer','0')
        if kind=='line':
            ends=sorted([point(e.dxf.start),point(e.dxf.end)] if native else [point(e['start']),point(e['end'])]);key=('line',*ends)
        elif kind in ('polyline','lwpolyline'):
            points=tuple(point(p) for p in (e.get_points('xy') if native else e['points']));closed=e.closed if native else e['closed']
            if closed:points=min([points[i:]+points[:i] for i in range(len(points))]+[points[::-1][i:]+points[::-1][:i] for i in range(len(points))])
            key=('polyline',bool(closed),points)
        elif kind in ('circle','arc'):
            key=(kind,point(e.dxf.center) if native else point(e['center']),round(float(e.dxf.radius if native else e['radius']),5))
            if kind=='arc':key+=tuple(round(float(e.dxf.get(k) if native else e[k])%360,5) for k in ('start_angle','end_angle'))
        elif kind=='insert':
            key=('insert',(e.dxf.name if native else e['block']).casefold(),point(e.dxf.insert) if native else point(e['position']),
                 round(float(e.dxf.xscale if native else e['scale']),5),round(float(e.dxf.rotation if native else e['rotation'])%360,5))
        else:continue
        result[(layer.casefold(),key)]+=1
    return result
