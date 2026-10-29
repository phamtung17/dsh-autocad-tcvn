"""Deterministic room labels constrained to their local wall-bounded cell."""
from functools import lru_cache
from pathlib import Path
import os
from .spatial_rules import overlap,resolve_openings,cut_walls,fixture_rect,furniture_rect,RULES


@lru_cache(maxsize=1)
def _font():
    from PIL import ImageFont
    path=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts/arial.ttf'
    try:return ImageFont.truetype(str(path),1000)
    except OSError:return None


def text_width(value,height):
    font=_font()
    if font:
        box=font.getbbox('H');cap=box[3]-box[1]
        return font.getlength(value)*height/cap
    return len(value)*height*.7


def room_zone(s,point,solid):
    b=s['building'];t=b['wall'];x,y=point;lo=t;hi=b['width']-t;bot=t;top=b['depth']-t
    for X,Y,W,H in solid:
        if Y<y<Y+H:
            if X+W<=x:lo=max(lo,X+W)
            if X>=x:hi=min(hi,X)
        if X<x<X+W:
            if Y+H<=y:bot=max(bot,Y+H)
            if Y>=y:top=min(top,Y)
    return (lo,bot,hi-lo,top-bot)


def place_room_labels(p,s,floor,labels):
    walls,ops,_=resolve_openings(s,floor);solid=cut_walls(walls,ops);ext=s.get('extensions',{});b=s['building']
    occupied=solid+[fixture_rect(v) for v in ext.get('fixtures',[]) if v['floor']==floor]+[furniture_rect(v) for v in ext.get('furniture',[]) if v['floor']==floor]
    sx,sy=b['stair_origin'];occupied.append((sx,sy,2*b['stair_width']+150,(b['stair_risers']/2-1)*b['stair_run']+b['stair_width']))
    lift=ext.get('elevator')
    if lift:occupied.append((*lift['origin'],lift['width'],lift['depth']))
    if 'partitions' not in ext:
        W,D=b['width'],b['depth'];occupied += [(W-1000,2150,360,630),(W-1500,2200,500,400),(W-1400,350,900,900)]
        occupied += [(500,D-2600,1600,2000),(W/2-850,D-2400,600,1800)]
        occupied += [(500,600,800,2000),(1700,2800,1100,600)] if floor==1 else [(500,600,1600,2000),(W/2+b['wall'],600,1600,2000)]
    labels=list(labels)
    for item in labels:
        name=item['name'];x,y=item['position'];height=RULES['room_label_paper_height_mm']*p.scale;w=text_width(name,height)+height*.3;h=height*1.65
        zone=item.get('label_zone') or item.get('boundary') or room_zone(s,(x,y),solid);X,Y,W,H=zone;pad=RULES['room_label_paper_gap_mm']*p.scale;chosen=None
        shifts=[(0,0)]+[(dx*height*2,dy*height*2) for dy in range(-4,5) for dx in range(-4,5) if (dx,dy)!=(0,0)]
        shifts.sort(key=lambda v:abs(v[0])+abs(v[1]))
        for dx,dy in shifts:
            r=(x+dx,y+dy-h,w,h)
            if r[0]<X+pad or r[1]<Y+pad or r[0]+w>X+W-pad or r[1]+h>Y+H-pad:continue
            if any(overlap((r[0]-pad,r[1]-pad,w+2*pad,h+2*pad),o,0) for o in occupied):continue
            chosen=r;break
        if chosen is None:
            if not hasattr(p.b,'spatial_label_issues'):p.b.spatial_label_issues=[]
            p.b.spatial_label_issues.append(dict(type='ROOM_LABEL_HAS_NO_CLEAR_POSITION_IN_ZONE',stage=11,floor=floor,room=item.get('id',name)))
            chosen=(x,y-h,w,h)
        occupied.append(chosen);p.mtext(name,chosen[0],chosen[1]+h,w,RULES['room_label_paper_height_mm'])
