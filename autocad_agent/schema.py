"""Strict, pure-Python schema for non-destructive AutoCAD new-drawing jobs.

Never accept commands, script snippets, arbitrary local file paths or URLs from a job.
The model-space units are supplied explicitly. A validated job is not a safe design.
"""
from __future__ import annotations
import math
import re
from copy import deepcopy

DISCIPLINES = {"mechanical", "architectural", "structural", "electrical", "hvac", "plumbing", "mep", "civil", "fire_safety", "general"}
UNITS = {"mm": 4, "m": 6, "inch": 1, "feet": 2}
SHEETS = {"A4": (210, 297), "A3": (297, 420), "A2": (420, 594), "A1": (594, 841), "A0": (841, 1189)}
LAYER_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$")
IDENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,70}\.dwg$", re.I)
ALLOWED_TYPES = {"line", "polyline", "circle", "arc", "text", "mtext", "dim_aligned", "dim_rotated", "dim_radial", "dim_diametric", "insert", "hatch", "leader", "table"}
HATCH_PATTERNS={'SOLID','ANSI31','ANSI32','ANSI33','ANSI37','AR-CONC','AR-SAND','EARTH','NET','BRICK'}
MAX_ENTITIES = 3000
MAX_BLOCKS = 100
MAX_COORD = 10_000_000

class JobError(ValueError):
    pass

def finite(v, label="number", positive=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise JobError(f"{label}: finite number required")
    if abs(v) > MAX_COORD or (positive and v <= 0):
        raise JobError(f"{label}: out of range")
    return float(v)

def pt(v, label="point"):
    if not isinstance(v, list) or len(v) != 2:
        raise JobError(f"{label}: expected [x,y]")
    return [finite(v[0], label+'.x'), finite(v[1], label+'.y')]

def text(v, label="text", length=300):
    if not isinstance(v, str) or not v.strip() or len(v) > length or any(ord(c) < 32 and c not in "\n\t" for c in v):
        raise JobError(f"{label}: invalid text")
    return v

def seq(v, label, low, high):
    if not isinstance(v, list) or not low <= len(v) <= high:
        raise JobError(f"{label}: expected list of {low}..{high} items")
    return v

def validate_entity(raw, *, in_block=False):
    if not isinstance(raw, dict):
        raise JobError("entity must be object")
    e = deepcopy(raw)
    t = e.get("type")
    if t not in ALLOWED_TYPES or (in_block and t not in {"line", "polyline", "circle", "arc", "text"}):
        raise JobError(f"unsupported entity type: {t}")
    if not isinstance(e.get("id"), str) or not IDENT_RE.fullmatch(e["id"]):
        raise JobError("invalid entity id")
    if not isinstance(e.get("layer", "0"), str) or not LAYER_RE.fullmatch(e.get("layer", "0")):
        raise JobError("invalid layer")
    e.setdefault("layer", "0")
    if t == "line":
        e["start"], e["end"] = pt(e.get("start"),"start"), pt(e.get("end"),"end")
        if e["start"] == e["end"]: raise JobError("zero-length line")
    elif t == "polyline":
        e["points"] = [pt(p) for p in seq(e.get("points"),"points",2,5000)]
        e["closed"] = e.get("closed", False)
        if type(e["closed"]) is not bool: raise JobError("closed must be boolean")
        if len(set(map(tuple,e["points"]))) < (3 if e["closed"] else 2):
            raise JobError("degenerate polyline")
    elif t in ("circle", "arc"):
        e["center"] = pt(e.get("center"),"center")
        e["radius"] = finite(e.get("radius"),"radius",positive=True)
        if t == "arc":
            e["start_angle"] = finite(e.get("start_angle"),"start_angle")
            e["end_angle"] = finite(e.get("end_angle"),"end_angle")
            if e["start_angle"] == e["end_angle"]: raise JobError("zero-angle arc")
    elif t in ("text", "mtext"):
        e["position"] = pt(e.get("position"),"position")
        e["text"] = text(e.get("text"),"text",4000 if t=="mtext" else 512)
        e["height"] = finite(e.get("height"),"height",positive=True)
        if t=="text": e["rotation"] = finite(e.get("rotation",0),"rotation")
        else: e["width"] = finite(e.get("width"),"width",positive=True)
    elif t == "dim_aligned":
        e["start"] = pt(e.get("start"),"start")
        e["end"] = pt(e.get("end"),"end")
        e["position"] = pt(e.get("position"),"position")
        if e["start"]==e["end"]: raise JobError("degenerate aligned dimension")
    elif t == "dim_rotated":
        e["start"],e["end"],e["position"] = pt(e.get("start")),pt(e.get("end")),pt(e.get("position"))
        e["rotation"] = finite(e.get("rotation",0),"rotation")
        if e["start"]==e["end"]: raise JobError("degenerate rotated dimension")
    elif t in ("dim_radial", "dim_diametric"):
        e["center"] = pt(e.get("center"),"center")
        e["radius"] = finite(e.get("radius"),"radius",positive=True)
        e["angle"] = finite(e.get("angle",0),"angle")
        e["leader"] = finite(e.get("leader",5),"leader",positive=True)
    elif t == "insert":
        if not isinstance(e.get("block"),str) or not IDENT_RE.fullmatch(e["block"]): raise JobError("invalid block reference")
        e["position"] = pt(e.get("position"))
        e["rotation"] = finite(e.get("rotation",0),"rotation")
        e["scale"] = finite(e.get("scale",1),"scale",positive=True)
    elif t=='hatch':
        e['points']=[pt(p) for p in seq(e.get('points'),'hatch points',3,700)]
        e['holes']=[[pt(p) for p in seq(loop,'hatch hole',3,700)] for loop in seq(e.get('holes',[]),'holes',0,20)]
        if e.get('pattern','ANSI31') not in HATCH_PATTERNS:raise JobError('Unsupported predefined hatch pattern')
        e['pattern']=e.get('pattern','ANSI31');e['pattern_scale']=finite(e.get('pattern_scale',1),'pattern_scale',positive=True)
        e['angle']=finite(e.get('angle',0),'hatch angle')
    elif t=='leader':
        e['points']=[pt(p) for p in seq(e.get('points'),'leader points',2,20)]
        if any(a==b for a,b in zip(e['points'],e['points'][1:])):raise JobError('Zero-length leader segment')
        e['text']=text(e.get('text'),'leader text',1000)
        e['height']=finite(e.get('height'),'leader text height',positive=True)
        e['text_width']=finite(e.get('text_width',e['height']*30),'leader width',positive=True)
        e['align']=e.get('align','left')
        if e['align'] not in ('left','right'):raise JobError('leader align must be left or right')
    elif t=='table':
        e['position']=pt(e.get('position'));e['title']=text(e.get('title'),'table title',100)
        e['columns']=[text(v,'column',100) for v in seq(e.get('columns'),'columns',1,10)]
        e['widths']=[finite(v,'column width',positive=True) for v in seq(e.get('widths'),'widths',len(e['columns']),len(e['columns']))]
        e['rows']=seq(e.get('rows'),'rows',1,200)
        e['rows']=[[text(v,'cell',300) for v in seq(row,'row',len(e['columns']),len(e['columns']))] for row in e['rows']]
        e['height']=finite(e.get('height'),'table text height',positive=True)
        e['row_height']=finite(e.get('row_height',e['height']*2.8),'row height',positive=True)
        if e['row_height']<e['height']*1.5:raise JobError('Table rows too small for text')
    if t.startswith('dim_') and 'text_height' in e:e['text_height']=finite(e['text_height'],'dimension text height',positive=True)
    return e

def validate_job(raw):
    if not isinstance(raw,dict): raise JobError("job must be object")
    job = deepcopy(raw)
    if job.get("discipline") not in DISCIPLINES: raise JobError("unsupported discipline")
    if job.get("units") not in UNITS: raise JobError("unsupported units")
    name=job.get("output_name")
    if not isinstance(name,str) or not FILENAME_RE.fullmatch(name) or ".." in name:
        raise JobError("unsafe output_name, use simple .dwg filename")
    geometry=seq(job.get("geometry"),"geometry",1,MAX_ENTITIES)
    ids=set()
    job["geometry"]=[]
    for raw_e in geometry:
        e=validate_entity(raw_e)
        if e["id"] in ids: raise JobError("duplicate entity id")
        ids.add(e["id"])
        job["geometry"].append(e)
    blocks=job.get("blocks",[])
    seq(blocks,"blocks",0,MAX_BLOCKS)
    names=set()
    for block in blocks:
        if not isinstance(block,dict) or not isinstance(block.get("name"),str) or not IDENT_RE.fullmatch(block["name"]):
            raise JobError("invalid block name")
        if block["name"] in names: raise JobError("duplicate block")
        names.add(block["name"])
        block['base'] = pt(block.get("base",[0,0]))
        block['entities'] = [validate_entity(be,in_block=True) for be in seq(block.get("entities"),"block entities",1,500)]
        entity_ids = [e['id'] for e in block['entities']]
        if len(entity_ids) != len(set(entity_ids)):
            raise JobError('duplicate block entity id')
    for e in job["geometry"]:
        if e["type"]=="insert" and e["block"] not in names: raise JobError("missing block definition: "+e["block"])
    sheet=job.get("sheet",{"format":"A3","orientation":"landscape","scale_denominator":1})
    if not isinstance(sheet,dict) or sheet.get("format","A3") not in SHEETS: raise JobError("invalid sheet")
    if sheet.get("orientation","landscape") not in {"portrait","landscape"}: raise JobError("invalid sheet orientation")
    den=finite(sheet.get("scale_denominator",1),"scale_denominator",positive=True)
    if not 0.001 <= den <= 100000: raise JobError("invalid sheet scale")
    job["sheet"]={"format":sheet.get("format","A3"),"orientation":sheet.get("orientation","landscape"),"scale_denominator":den}
    titleblock=job.get('titleblock')
    if titleblock is not None:
        if not isinstance(titleblock,dict):raise JobError('titleblock must be an object')
        allowed={'title','drawing_number','revision','author','material'}
        if set(titleblock)-allowed:raise JobError('unknown titleblock field')
        if not {'title','drawing_number'}<=set(titleblock):raise JobError('titleblock requires title and drawing_number')
        for key,value in titleblock.items():
            text(value,'titleblock.'+key,40 if key=='title' else 24)
            if any(c in value for c in ('\n','\t','\\')):raise JobError('titleblock fields must be plain single-line text')
        job['titleblock']=titleblock
    sts=job.get("standards",[])
    if not isinstance(sts,list) or len(sts)>30 or not all(isinstance(s,str) and 1<=len(s)<=90 for s in sts):
        raise JobError("invalid standards list")
    job["standards"]=sts
    job["blocks"]=blocks
    # Plot configuration is restricted to a project-owned DWT name (not a path).
    plot = job.get('plot', {})
    if not isinstance(plot,dict): raise JobError('plot must be an object')
    enabled = plot.get('enabled',False)
    if type(enabled) is not bool: raise JobError('plot.enabled must be boolean')
    dwt = plot.get('dwt')
    if dwt is not None and (not isinstance(dwt,str) or
            not re.fullmatch(r'[A-Za-z0-9_-]{1,64}\.dwt',dwt,re.I)):
        raise JobError('plot.dwt must be a simple .dwt filename from CAD_DWT_DIR')
    if enabled and job['units'] not in ('mm','m','inch','feet'):
        raise JobError('unsupported plot units')
    pdf_enabled=plot.get('pdf',False)
    if type(pdf_enabled) is not bool:raise JobError('plot.pdf must be boolean')
    if pdf_enabled and not enabled:raise JobError('plot.pdf requires plot.enabled')
    job['plot']={'enabled':enabled,'dwt':dwt,'pdf':pdf_enabled,
                 'ctb':plot.get('ctb')}
    if job['plot']['ctb'] is not None and (not isinstance(job['plot']['ctb'],str) or
            not re.fullmatch(r'[A-Za-z0-9_-]{1,64}\.ctb',job['plot']['ctb'],re.I)):
        raise JobError('plot.ctb must be a simple CTB filename')
    job["purpose"] = job.get("purpose","concept_only")
    if job["purpose"] not in {"concept_only","design_review","manufacture_review","construction_review"}:
        raise JobError("invalid purpose")
    inputs=job.get('engineering_inputs',{})
    if not isinstance(inputs,dict) or len(inputs)>50:raise JobError('invalid engineering_inputs')
    for k,v in inputs.items():
        if not isinstance(k,str) or not IDENT_RE.fullmatch(k):raise JobError('invalid engineering_input key')
        if not isinstance(v,(str,int,float)) or isinstance(v,bool) or len(str(v))>500:
            raise JobError('invalid engineering_input value')
        if isinstance(v,float) and not math.isfinite(v):raise JobError('non-finite engineering input')
    job['engineering_inputs']=inputs
    # These are declarative local rule-pack filenames; the AI cannot supply
    # raw source text and claim it is a verified national standard.
    rule_packs=job.get('clause_rule_packs',[])
    if not isinstance(rule_packs,list) or len(rule_packs)>20:
        raise JobError('clause_rule_packs must be a list of <=20 filenames')
    if not all(isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\.json',x) and '..' not in x for x in rule_packs):
        raise JobError('invalid clause rule-pack filename')
    job['clause_rule_packs']=rule_packs
    project_rules=job.get('project_rules')
    if project_rules is not None:
        from .qa import validate_rules
        job['project_rules']=validate_rules(project_rules)
    return job
