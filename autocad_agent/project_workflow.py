"""Fourteen-stage completeness, revision impact and bounded coordination checks."""
from .building_model import normalize,digest,takeoff,service_routes
from .qa import geometry_report

STAGES=[
 (1,'Khảo sát hiện trạng',[],['survey','survey_section']),
 (2,'Tổng mặt bằng',[1],['site','setting_out']),
 (3,'Mặt bằng kiến trúc',[2],['architecture']),
 (4,'Mặt đứng và mặt cắt',[3],['elevation_front','elevation_rear','elevation_left','elevation_right','section']),
 (5,'Mặt bằng mái',[4],['roof']),
 (6,'Chi tiết kiến trúc',[5],['stair','openings','wet_detail','eaves']),
 (7,'Thiết kế kết cấu',[3],['foundations','framing','footing_detail','reinforcement','slab_detail','stair_reinforcement']),
 (8,'Cấp thoát nước',[3],['water','waste','riser','plumbing_detail']),
 (9,'Điện',[3],['lighting','sockets','single_line','earthing']),
 (10,'Điện nhẹ và kỹ thuật',[3],['low_voltage','hvac','hvac_detail']),
 (11,'Nội thất',[6],['interior','joinery','bathroom','finishes','ceiling']),
 (12,'Sân vườn và hạ tầng',[2],['landscape','grading','chamber']),
 (13,'Thống kê và dự toán',[7,8,9,10,11,12],['takeoff','estimate']),
 (14,'Kiểm tra và phát hành',[13],['coordination','drawing_index'])]

INPUTS={1:['site','source'],2:['site','building'],3:['building','finishes'],4:['building','structure'],5:['building','finishes'],
        6:['building','finishes','structure'],7:['structure','building'],8:['systems','building'],9:['systems','building'],
        10:['systems','building'],11:['building','finishes'],12:['site','systems','building'],13:['building','structure','systems','finishes','prices','estimate_scope'],14:['source','reviews','issues','revision','site','building','structure','systems','finishes','prices','estimate_scope']}
for fields in INPUTS.values(): fields.append('extensions')

def stage_hash(s,stage):return digest({'revision':s['revision'],**{k:s.get(k,{}) for k in INPUTS[stage] if k!='reviews'}})

def clash_check(s):
    """AABB swept route versus columns, beams and slabs. Not a full 3D clash solver."""
    b,st=s['building'],s['structure'];boxes=[];findings=[]
    for floor,z in enumerate(b['levels'][:-1]):
        top=b['levels'][floor+1]
        for x in b['grids_x']:
            for y in b['grids_y']:boxes.append((f'C{floor}-{x:g}-{y:g}',[x-st['column_width']/2,y-st['column_depth']/2,z,x+st['column_width']/2,y+st['column_depth']/2,top]))
        for x in b['grids_x']:boxes.append((f'BY{floor}-{x:g}',[x-st['beam_width']/2,0,top-st['beam_depth'],x+st['beam_width']/2,b['depth'],top]))
        for y in b['grids_y']:boxes.append((f'BX{floor}-{y:g}',[0,y-st['beam_width']/2,top-st['beam_depth'],b['width'],y+st['beam_width']/2,top]))
        sx,sy=b['stair_origin'];sw=2*b['stair_width']+150;sd=(b['stair_risers']/2-1)*b['stair_run']+b['stair_width']
        for name,xy in [('L',[0,0,sx,b['depth']]),('R',[sx+sw,0,b['width'],b['depth']]),('F',[sx,0,sx+sw,sy]),('B',[sx,sy+sd,sx+sw,b['depth']])]:
            if xy[2]>xy[0] and xy[3]>xy[1]:boxes.append((f'SLAB{floor}-{name}',[xy[0],xy[1],top-st['slab_thickness'],xy[2],xy[3],top]))
        for route in service_routes(s,floor+1):
            r=route['diameter']/2
            for a,c in zip(route['points'],route['points'][1:]):
                lo=[min(a[i],c[i])+(z if i==2 else 0)-r for i in range(3)]
                hi=[max(a[i],c[i])+(z if i==2 else 0)+r for i in range(3)]
                for name,box in boxes:
                    if all(min(hi[i],box[i+3])-max(lo[i],box[i])>1e-6 for i in range(3)):
                        finding={'severity':'ERROR','type':'ROUTE_STRUCTURE_INTERSECTION','route':route['id'],'floor':floor+1,'element':name}
                        if finding not in findings:findings.append(finding)
            if route['system']=='waste':
                for a,c in zip(route['points'],route['points'][1:]):
                    length=((a[0]-c[0])**2+(a[1]-c[1])**2)**.5
                    if length and (a[2]-c[2])/length+1e-9<s['systems']['drain_slope']:
                        findings.append({'severity':'ERROR','type':'DRAIN_SLOPE_OR_DIRECTION','route':route['id'],'floor':floor+1})
    return {'status':'CONFLICTS_FOUND' if findings else 'NO_CONFLICT_IN_CHECKED_SCOPE','scope':'2.5D conservative route AABBs versus modeled columns/beams/slabs; sleeves and unmodeled systems not checked','findings':findings}

def change_impact(before,after):
    a,b=normalize(before),normalize(after);changed=[k for k in a if a[k]!=b[k]]
    direct={i for i in INPUTS if 'revision' in changed or any(k in changed for k in INPUTS[i])};impacted=set(direct)
    while True:
        old=set(impacted)
        for i,title,deps,roles in STAGES:
            if set(deps)&impacted:impacted.add(i)
        if old==impacted:break
    return {'changed_inputs':changed,'direct_stages':sorted(direct),'rebuild_stages':sorted(impacted),
            'invalidate_reviews':sorted(impacted),'requires_qa_again':bool(impacted),'before_hash':digest(a),'after_hash':digest(b)}

def check_project(project):
    s=project['spec'];sheets=project['sheets'];issues=[];stages=[];ids=[x['code'] for x in sheets]
    if len(ids)!=len(set(ids)):issues.append({'severity':'ERROR','type':'DUPLICATE_SHEET_CODE'})
    for stage,title,deps,roles in STAGES:
        actual=[x for x in sheets if x['stage']==stage];present={x['role'] for x in actual};missing=sorted(set(roles)-present)
        if missing:issues.append({'severity':'ERROR','type':'MISSING_SHEETS','stage':stage,'roles':missing})
        # Floor-dependent systems must cover every modeled floor.
        for role in set(roles)&{'architecture','framing','water','waste','lighting','sockets','low_voltage','hvac','interior','finishes','ceiling'}:
            floors={x.get('floor') for x in actual if x['role']==role}
            expected=set(range(1,len(s['building']['levels'])))
            if floors!=expected:issues.append({'severity':'ERROR','type':'FLOOR_COVERAGE','stage':stage,'role':role,'missing':sorted(expected-floors)})
        review=s['reviews'].get(str(stage),{})
        reviewed=review.get('input_hash')==stage_hash(s,stage) and bool(review.get('reviewer')) and bool(review.get('reference'))
        stages.append({'id':stage,'title':title,'dependencies':deps,'sheet_count':len(actual),'missing_roles':missing,
                       'input_hash':stage_hash(s,stage),'review':'USER_ATTESTED' if reviewed else 'REVIEW_REQUIRED'})
    for sheet in sheets:
        for finding in sheet.get('spatial_label_issues',[]):issues.append(dict(severity='ERROR',sheet=sheet['code'],**finding))
        counts={k:sum(e['type']==k for e in sheet['job']['geometry']) for k in ('dim_aligned','leader','table','insert','hatch')}
        required=sheet.get('required_features',[])
        for feature in required:
            if not counts.get(feature):issues.append({'severity':'ERROR','type':'MISSING_DETAIL_CONTENT','sheet':sheet['code'],'feature':feature})
        main_ids=set(sheet.get('main_entity_ids',[]));main=[e for e in sheet['job']['geometry'] if e['id'] in main_ids]
        requirements={
            'survey':('dim_aligned','circle','text'),'site':('dim_aligned','circle','text'),
            'setting_out':('table',),'architecture':('dim_aligned','hatch','insert'),
            'foundations':('dim_aligned','hatch','insert'),'framing':('dim_aligned','insert'),
            'roof':('dim_aligned','hatch','insert'),'water':('dim_aligned','leader','polyline'),
            'waste':('dim_aligned','leader','polyline'),'lighting':('dim_aligned','circle','line'),
            'sockets':('dim_aligned','polyline','line'),'low_voltage':('dim_aligned','leader','circle'),
            'hvac':('dim_aligned','leader','polyline'),'interior':('dim_aligned','insert'),
            'finishes':('dim_aligned','hatch','insert'),'ceiling':('dim_aligned','leader','insert'),
            'reinforcement':('dim_aligned','circle','hatch','leader'),
            'takeoff':('table',),'estimate':('table',),'drawing_index':('table',),
            'landscape':('dim_aligned','hatch','circle'),'grading':('dim_aligned','polyline'),
        }.get(sheet['role'],('dim_aligned','leader'))
        for feature in requirements:
            if not any(e['type']==feature for e in main):issues.append({'severity':'ERROR','type':'MISSING_MAIN_CONTENT','sheet':sheet['code'],'feature':feature})
        if len(sheet['views'])<2:issues.append({'severity':'ERROR','type':'MISSING_DETAIL_VIEW','sheet':sheet['code']})
        for ref in sheet.get('references',[]):
            if ref not in ids:issues.append({'severity':'ERROR','type':'BROKEN_SHEET_REFERENCE','sheet':sheet['code'],'target':ref})
        if sheet.get('input_hash')!=stage_hash(s,sheet['stage']):issues.append({'severity':'ERROR','type':'STALE_SHEET','sheet':sheet['code']})
        geo=geometry_report(sheet['job'])
        if geo['status']!='GEOMETRY_CHECKED':issues.append({'severity':'ERROR','type':'GEOMETRY_FAILED','sheet':sheet['code'],'findings':geo['findings']})
    from .spatial_rules import check_spatial
    spatial=check_spatial(s);issues.extend(spatial['findings'])
    clashes=clash_check(s);issues.extend(clashes['findings'])
    for item in s['issues']:
        if not isinstance(item,dict) or item.get('status')!='resolved':issues.append({'severity':'ERROR','type':'OPEN_PROJECT_ISSUE','stage':item.get('stage') if isinstance(item,dict) else 14,'issue':item})
    blockers=list(issues)
    zone=s.get('extensions',{}).get('ceiling_service_zone',0)
    if zone and s['finishes']['ceiling_drop']<s['structure']['beam_depth']+zone:
        issues.append({'severity':'ERROR','type':'CEILING_SERVICE_CLEARANCE','stage':10,
                       'required_drop_mm':s['structure']['beam_depth']+zone,'actual_drop_mm':s['finishes']['ceiling_drop']})
        blockers.append(issues[-1])
    if s['mode']=='demo':blockers.append({'type':'DEMO_NOT_FOR_CONSTRUCTION'})
    for st in stages:
        if st['review']!='USER_ATTESTED':blockers.append({'type':'ENGINEERING_REVIEW_REQUIRED','stage':st['id']})
    for key,value in s['source'].items():
        if 'DEMO' in value.upper():blockers.append({'type':'DEMO_SOURCE','source':key})
    # Cost rows cover modeled scope only. Never label a partial takeoff a full tender estimate.
    if not s['estimate_scope']['scope_confirmed']:
        blockers.append({'type':'ESTIMATE_SCOPE_REVIEW_REQUIRED','scope':s['estimate_scope']})
    repairs=[];sheet_stage={x['code']:x['stage'] for x in sheets}
    for finding in issues:
        stage=finding.get('stage') or sheet_stage.get(finding.get('sheet'))
        if stage is None and finding.get('route'):
            route=next(r for r in service_routes(s,finding.get('floor',1)) if r['id']==finding['route'])
            stage={'water':8,'waste':8,'power':9,'data':10,'hvac':10}[route['system']]
        if stage:
            action={'stage':stage,'reason':finding['type'],'action':'FIX_INPUT_OR_DRAWING_THEN_REBUILD','recheck_stage':14}
            if action not in repairs:repairs.append(action)
    from .building_extensions import engineering_summary
    return {'status':'ERRORS_FOUND' if issues else 'MODELED_CONTENT_CHECKED','stages':stages,'issues':issues,'engineering':engineering_summary(s),
            'coordination':clashes,'spatial_rules':spatial,'sheet_count':len(sheets),'release_status':'BLOCKED' if blockers else 'READY_FOR_HUMAN_RELEASE',
            'repair_queue':repairs,'release_blockers':blockers,'tcvn_compliance':'NOT_CHECKED'}
