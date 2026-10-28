"""Local workspace + approval gate. Nothing remotely reachable; no arbitrary shell endpoints."""
from __future__ import annotations
import hashlib
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from .schema import validate_job
from .qa import geometry_report
from .gates import assess

DIGEST_RE=re.compile(r'^[0-9a-f]{64}$')

def workspace():
    p=Path(os.environ.get('CAD_OUTPUT_DIR',str(Path.home()/'Documents'/'CAD_AGENT_OUTPUT'))).expanduser().resolve()
    for child in ('pending','approvals','working','reports','previews'):(p/child).mkdir(parents=True,exist_ok=True)
    return p

def fingerprint(job):
    normalized=validate_job(job)
    return hashlib.sha256(json.dumps(normalized,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(exist_ok=True,parents=True)
    temp=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
    try:
        with temp.open('x',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2)
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

def prepare(job):
    job=validate_job(job)
    gate=assess(job)
    if gate['status']=='BLOCKED':
        return {'status':'REJECTED_QUALITY_GATE','gate':gate}
    report=gate['geometry']
    home=workspace();digest=fingerprint(job)
    destination=home/job['output_name']
    if destination.exists():return {'status':'OUTPUT_EXISTS','file':str(destination)}
    atomic_json(home/'pending'/(digest+'.json'),{'job':job,'digest':digest,'created_at':int(time.time()),'qa':report})
    return {'status':'PREPARED','ticket':digest,'output':str(destination),'geometry':report,'gate_status':gate['status'],
            'approval':'REQUIRED','approval_command':f'python -m autocad_agent.cli approve {digest}',
            'note':'Run approval command manually after reviewing preview. Tool cannot self-approve.'}

def read_pending(ticket):
    if not DIGEST_RE.fullmatch(ticket):raise ValueError('invalid ticket')
    path=workspace()/'pending'/(ticket+'.json')
    if not path.exists():raise FileNotFoundError('pending job not found')
    payload=json.loads(path.read_text(encoding='utf-8'))
    if fingerprint(payload['job'])!=ticket:raise ValueError('job changed after preparation')
    return payload

def approve(ticket,interactive=True):
    pending=read_pending(ticket);job=pending['job']
    print(f"PROJECT: {job['discipline']} / {job['purpose']}")
    print(f"DWG: {workspace()/job['output_name']}")
    print(f"ENTITIES: {len(job['geometry'])} | UNITS: {job['units']}")
    print('WARNING: No TCVN compliance certificate; drawing will be reviewed in AutoCAD.')
    if interactive:
        answer=input('Type VE to approve creation of this NEW DWG: ').strip()
        if answer!='VE':return {'status':'CANCELLED'}
    else:raise ValueError('noninteractive approvals disallowed')
    token=secrets.token_hex(24)
    atomic_json(workspace()/'approvals'/(ticket+'.json'),{'ticket':ticket,'secret':token,'approved_at':int(time.time())})
    return {'status':'APPROVED_FOR_ONE_EXECUTION','ticket':ticket}

def consume(ticket):
    data=read_pending(ticket)
    if os.environ.get('CAD_APPROVAL_MODE', 'manual') == 'auto_new' and data['job']['purpose']=='concept_only':
        # Opt-in in the trusted local DSH configuration, NEVER selected by model job data.
        if (workspace()/data['job']['output_name']).exists():
            raise FileExistsError('output DWG exists; refuse overwrite')
        return data['job']
    path=workspace()/'approvals'/(ticket+'.json')
    if not path.exists():raise PermissionError('human approval not found; use CLI approve command')
    approval=json.loads(path.read_text(encoding='utf-8'))
    if approval.get('ticket')!=ticket or time.time()-approval.get('approved_at',0)>900:
        raise PermissionError('approval expired or invalid')
    # Atomic rename prevents repeated concurrent consumption on same volume.
    consumed=path.with_suffix('.consumed')
    os.rename(path,consumed)
    consumed.unlink(missing_ok=True)
    if (workspace()/data['job']['output_name']).exists():raise FileExistsError('output DWG exists; refuse overwrite')
    return data['job']

def copy_exclusive(src,dst):
    """Create a completed DWG without overwriting, even with concurrent processes."""
    src=Path(src);dst=Path(dst)
    with src.open('rb') as r:
        with dst.open('xb') as w:
            try:
                while True:
                    chunk=r.read(1024*1024)
                    if not chunk:break
                    w.write(chunk)
            except BaseException:
                w.close();dst.unlink(missing_ok=True)
                raise
    if dst.stat().st_size<100:dst.unlink(missing_ok=True);raise RuntimeError('DWG unreasonably small')
    return dst


def _execution_secret():
    """User-local key; only protects accidental/internal worker bypass, not arbitrary same-user code execution."""
    import os
    path=workspace()/'.worker_key'
    try:
        with path.open('xb') as f:
            if os.name=='posix': os.chmod(path,0o600)
            f.write(secrets.token_bytes(32))
    except FileExistsError: pass
    return path.read_bytes()

def issue_worker_permit(ticket,job):
    """Issue single-use signed permit only AFTER API has consumed an approval."""
    import hmac
    job=validate_job(job)
    if fingerprint(job)!=ticket:raise ValueError('ticket does not match job')
    permit_id=secrets.token_hex(24)
    stamp=int(time.time())
    payload={'ticket':ticket,'job':job,'permit_id':permit_id,'issued_at':stamp}
    signature=hmac.new(_execution_secret(),json.dumps(payload,sort_keys=True).encode('utf-8'),'sha256').hexdigest()
    atomic_json(workspace()/'working'/(permit_id+'.permit.json'),{'payload':payload,'signature':signature})
    return permit_id

def consume_worker_permit(permit_id):
    """Authenticate invocation; worker must never read a pending job directly."""
    import hmac
    if not re.fullmatch(r'[0-9a-f]{48}',permit_id):raise PermissionError('invalid worker permit id')
    base=workspace()/'working'
    source=base/(permit_id+'.permit.json')
    taken=base/(permit_id+'.taken')
    # Exclusive move before reading so concurrent worker calls cannot reuse the permit.
    os.rename(source,taken)
    try:
        obj=json.loads(taken.read_text(encoding='utf-8'))
        payload=obj['payload']
        expected=hmac.new(_execution_secret(),json.dumps(payload,sort_keys=True).encode('utf-8'),'sha256').hexdigest()
        if not hmac.compare_digest(expected,obj['signature']):raise PermissionError('worker permit signature invalid')
        if payload['permit_id']!=permit_id or time.time()-payload['issued_at']>120:
            raise PermissionError('worker permit expired or id mismatch')
        if fingerprint(payload['job'])!=payload['ticket']:
            raise PermissionError('worker payload changed')
        if assess(payload['job'])['status']=='BLOCKED':
            raise PermissionError('worker quality gate rejected job')
        return payload['job']
    finally: taken.unlink(missing_ok=True)
