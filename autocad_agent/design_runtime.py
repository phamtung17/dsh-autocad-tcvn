"""Signed one-use approvals for native export of a NEW design."""
import json,os,hmac,time,secrets,subprocess,sys,re
from pathlib import Path
from .runtime import workspace,atomic_json,DIGEST_RE
from .reference_runtime import _hash,_sign
from .design_api import frozen
from .design_dispatch import build_project

def _home():
    root=workspace()/'design_jobs'
    for name in ('pending','approvals','permits'):(root/name).mkdir(parents=True,exist_ok=True)
    return root

def prepare_design(spec,branding=None):
    value=frozen(spec,branding)
    project=build_project(value['spec'])
    if project.get('workflow',{}).get('issues'):raise ValueError('PROJECT_QUALITY_GATE_FAILED: resolve sheet or coordination issues before native export')
    if value['spec']['mode']!='demo' and not value['branding']['confirmed']:
        raise ValueError('BRANDING_CONFIRMATION_REQUIRED: ask user for final title block and logo')
    ticket=_hash(value);atomic_json(_home()/'pending'/(ticket+'.json'),value)
    return {'status':'PREPARED_NEW_DESIGN','ticket':ticket,'sheet_count':len(project['sheets']),'approval':'REQUIRED',
            'approval_command':f'python -m autocad_agent.cli approve-design {ticket}'}

def _read(ticket):
    if not isinstance(ticket,str) or not DIGEST_RE.fullmatch(ticket):raise ValueError('Invalid design ticket')
    value=json.loads((_home()/'pending'/(ticket+'.json')).read_text(encoding='utf-8'))
    if _hash(value)!=ticket or value!=frozen(value['spec'],value['branding']):raise PermissionError('Design or brand assets changed')
    return value

def approve_design(ticket,interactive=True):
    value=_read(ticket)
    if not interactive:raise ValueError('Noninteractive approvals are not allowed')
    print('NEW DESIGN: '+value['spec']['project_id']+' / '+value['branding']['company'])
    if input('Type VE to approve this NEW drawing set: ').strip()!='VE':return {'status':'CANCELLED'}
    payload={'kind':'DESIGN_APPROVAL','ticket':ticket,'approved_at':int(time.time())}
    atomic_json(_home()/'approvals'/(ticket+'.json'),{'payload':payload,'signature':_sign(payload)})
    return {'status':'APPROVED_FOR_ONE_EXECUTION','ticket':ticket}

def export_design(ticket,timeout=720):
    value=_read(ticket);lock=workspace()/'cad_worker.lock'
    if (workspace()/'HALTED_AFTER_DESIGN_TIMEOUT').exists():raise RuntimeError('Inspect previous timed-out export')
    try:
        with lock.open('x') as f:f.write(str(os.getpid()))
    except FileExistsError:return {'status':'BUSY'}
    try:
        if os.environ.get('CAD_APPROVAL_MODE','manual')!='auto_new':
            source=_home()/'approvals'/(ticket+'.json');taken=source.with_suffix('.taken');os.rename(source,taken)
            try:
                approval=json.loads(taken.read_text(encoding='utf-8'));p=approval['payload']
                if not hmac.compare_digest(_sign(p),approval['signature']) or p.get('ticket')!=ticket or p.get('kind')!='DESIGN_APPROVAL':raise PermissionError('Invalid design approval')
            finally:taken.unlink(missing_ok=True)
        nonce=secrets.token_hex(24);p={'kind':'DESIGN_WORKER','permit_id':nonce,'issued_at':int(time.time()),'ticket':ticket,'payload':value}
        atomic_json(_home()/'permits'/(nonce+'.json'),{'payload':p,'signature':_sign(p)})
        try:
            result=subprocess.run([sys.executable,'-m','autocad_agent.design_worker',nonce],cwd=Path(__file__).resolve().parents[1],stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
        except subprocess.TimeoutExpired:
            (workspace()/'HALTED_AFTER_DESIGN_TIMEOUT').write_text('Inspect AutoCAD and partial output before retry.',encoding='utf-8')
            return {'status':'TIMEOUT_NEEDS_INSPECTION'}
        try:return json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError,IndexError):return {'status':'FAIL','error':result.stderr[-1500:]}
    finally:lock.unlink(missing_ok=True)

def consume_design_permit(nonce):
    if not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{48}',nonce):raise PermissionError('Invalid design permit')
    path=_home()/'permits'/(nonce+'.json');taken=path.with_suffix('.taken');os.rename(path,taken)
    try:
        value=json.loads(taken.read_text(encoding='utf-8'));p=value['payload']
        if not hmac.compare_digest(_sign(p),value['signature']) or p.get('kind')!='DESIGN_WORKER':raise PermissionError('Bad design signature')
        if p.get('permit_id')!=nonce or not 0<=time.time()-p['issued_at']<120:raise PermissionError('Design permit expired')
        if _read(p['ticket'])!=p['payload']:raise PermissionError('Design permit payload mismatch')
        return p['payload']
    finally:taken.unlink(missing_ok=True)
