"""Subprocess boundary for COM calls (stdio result only on final line)."""
from __future__ import annotations
import json,sys
from .cad_com import create_dwg
from .runtime import consume_worker_permit, workspace

def main():
    permit_id=sys.argv[1]
    try:
        job=consume_worker_permit(permit_id)
        result=create_dwg(job,workspace())
        print(json.dumps(result,ensure_ascii=False),flush=True)
    except Exception as exc:
        print(json.dumps({'status':'FAIL','error':f'{type(exc).__name__}: {exc}',
                          'tcvn_compliance':'NOT_CHECKED'},ensure_ascii=False),flush=True)
        sys.exit(2)

if __name__=='__main__':main()
