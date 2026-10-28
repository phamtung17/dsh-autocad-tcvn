"""Separate, signed one-use approvals for native reference publication."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from .runtime import workspace,atomic_json,_execution_secret,DIGEST_RE
from .reference_profiles import reference_plan,profile_root,digest,load_profile


def _home():
    base=workspace()/'reference_jobs'
    for name in ('pending','approvals','permits'):(base/name).mkdir(parents=True,exist_ok=True)
    return base


def _hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def _sign(value):return hmac.new(_execution_secret(),json.dumps(value,sort_keys=True,ensure_ascii=False).encode(),'sha256').hexdigest()


def prepare_reference(job):
    plan=reference_plan(job)
    if plan['status']=='BLOCKED':return plan
    payload={'kind':'REFERENCE_PUBLISH','job':plan['job'],
             'profile_sha256':digest(profile_root()/plan['job']['profile_id']/'profile.json')}
    ticket=_hash(payload)
    atomic_json(_home()/'pending'/(ticket+'.json'),payload)
    return {'status':'PREPARED_REFERENCE','ticket':ticket,'sheet_count':plan['sheet_count'],
            'approval':'REQUIRED','warnings':plan['issues'],'completeness':plan['completeness'],
            'approval_command':f'python -m autocad_agent.cli approve-reference {ticket}'}


def _read(ticket):
    if not isinstance(ticket,str) or not DIGEST_RE.fullmatch(ticket):raise ValueError('Invalid reference ticket')
    value=json.loads((_home()/'pending'/(ticket+'.json')).read_text(encoding='utf-8'))
    if _hash(value)!=ticket or value.get('kind')!='REFERENCE_PUBLISH':raise PermissionError('Reference payload changed')
    if digest(profile_root()/value['job']['profile_id']/'profile.json')!=value['profile_sha256']:
        raise PermissionError('Profile changed after preparation')
    if reference_plan(value['job'])['status']=='BLOCKED':raise PermissionError('Reference plan no longer passes preflight')
    return value


def approve_reference(ticket,interactive=True):
    value=_read(ticket)
    if not interactive:raise ValueError('Noninteractive approvals are not allowed')
    print('REFERENCE REISSUE: '+value['job']['project_id'])
    print('SHEETS: '+str(len(value['job']['sheet_ids'])))
    print('Reference design remains; font substitutions may be present. Not TCVN certification.')
    if input('Type VE to approve this NEW output package: ').strip()!='VE':return {'status':'CANCELLED'}
    payload={'kind':'REFERENCE_APPROVAL','ticket':ticket,'approved_at':int(time.time())}
    atomic_json(_home()/'approvals'/(ticket+'.json'),{'payload':payload,'signature':_sign(payload)})
    return {'status':'APPROVED_FOR_ONE_EXECUTION','ticket':ticket}


def export_reference(ticket,timeout=720):
    value=_read(ticket)
    if (workspace()/'HALTED_AFTER_REFERENCE_TIMEOUT').exists():raise RuntimeError('Inspect previous timed-out publication before retrying')
    lock=workspace()/'cad_worker.lock'
    try:
        with lock.open('x') as f:f.write(str(os.getpid()))
    except FileExistsError:return {'status':'BUSY'}
    try:
        if os.environ.get('CAD_APPROVAL_MODE','manual')!='auto_new':
            source=_home()/'approvals'/(ticket+'.json');taken=source.with_suffix('.taken')
            os.rename(source,taken)
            try:
                approval=json.loads(taken.read_text(encoding='utf-8'));p=approval['payload']
                if not hmac.compare_digest(_sign(p),approval['signature']) or p.get('ticket')!=ticket or p.get('kind')!='REFERENCE_APPROVAL':
                    raise PermissionError('Invalid reference approval')
            finally:taken.unlink(missing_ok=True)
        nonce=secrets.token_hex(24)
        permit={'kind':'REFERENCE_WORKER','permit_id':nonce,'issued_at':int(time.time()),'ticket':ticket,'payload':value}
        atomic_json(_home()/'permits'/(nonce+'.json'),{'payload':permit,'signature':_sign(permit)})
        try:
            result=subprocess.run([sys.executable,'-m','autocad_agent.reference_worker',nonce],
                                  cwd=Path(__file__).resolve().parents[1],stdin=subprocess.DEVNULL,
                                  capture_output=True,text=True,encoding='utf-8',timeout=timeout)
        except subprocess.TimeoutExpired:
            (workspace()/'HALTED_AFTER_REFERENCE_TIMEOUT').write_text('Inspect AutoCAD and partial reference package before retrying.',encoding='utf-8')
            return {'status':'TIMEOUT_NEEDS_INSPECTION'}
        try:return json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError,IndexError):return {'status':'FAIL','error':result.stderr[-1500:]}
    finally:lock.unlink(missing_ok=True)


def consume_reference_permit(nonce):
    if not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{48}',nonce):raise PermissionError('Invalid reference permit')
    path=_home()/'permits'/(nonce+'.json');taken=path.with_suffix('.taken');os.rename(path,taken)
    try:
        value=json.loads(taken.read_text(encoding='utf-8'));p=value['payload']
        if not hmac.compare_digest(_sign(p),value['signature']) or p.get('kind')!='REFERENCE_WORKER':raise PermissionError('Bad reference signature')
        if p.get('permit_id')!=nonce or not 0<=time.time()-p['issued_at']<120:raise PermissionError('Reference permit expired')
        if _read(p['ticket'])!=p['payload']:raise PermissionError('Reference permit payload mismatch')
        return p['payload']['job']
    finally:taken.unlink(missing_ok=True)
