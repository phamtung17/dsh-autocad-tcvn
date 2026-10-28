"""Windows terminal commands for a human to approve a prepared drawing."""
from __future__ import annotations
import sys,json
from .runtime import approve,workspace

def main():
    if len(sys.argv)==3 and sys.argv[1]=='approve-design':
        from .design_runtime import approve_design
        print(json.dumps(approve_design(sys.argv[2]),ensure_ascii=True,indent=2));return
    if len(sys.argv)==3 and sys.argv[1]=='approve-reference':
        from .reference_runtime import approve_reference
        print(json.dumps(approve_reference(sys.argv[2]),ensure_ascii=True,indent=2));return
    if len(sys.argv)==3 and sys.argv[1]=='approve':
        print(json.dumps(approve(sys.argv[2]),ensure_ascii=False,indent=2));return
    if len(sys.argv)==2 and sys.argv[1]=='where':
        print(workspace());return
    print('Usage: python -m autocad_agent.cli approve <ticket> OR approve-reference <ticket> OR where')
    sys.exit(2)

if __name__=='__main__':main()
