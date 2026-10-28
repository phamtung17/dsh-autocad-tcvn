"""Run offline tests and write truthful machine-readable report with git commit if available."""
from __future__ import annotations
import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def git_revision():
    if os.getenv('GITHUB_SHA'):return os.environ['GITHUB_SHA']
    p=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    return p.stdout.strip() if p.returncode==0 else 'UNAVAILABLE_UNCOMMITTED'

def report(output):
    cmd=[sys.executable,'-m','pytest','tests','-q','-m','not autocad_real and not mcp_live',
         '--disable-warnings']
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    summary={'version':'1.1.0','generated_utc':datetime.now(timezone.utc).isoformat(),
             'commit_sha':git_revision(),'os':platform.platform(),'python':platform.python_version(),
             'offline_test_command':' '.join(cmd),'returncode':p.returncode,
             'offline_test_status':'PASS' if p.returncode==0 else 'FAIL',
             'pytest_tail':(p.stdout+p.stderr)[-5000:],
             'mcp_stdio_live':'NOT_RUN_BY_OFFLINE_REPORT',
             'dsh_web_live':'NOT_EXECUTED','autocad_2025_real':'NOT_EXECUTED',
             'autocad_pdf_plot_real':'NOT_EXECUTED',
             'tcvn_clause_source_authenticity':'NOT_INDEPENDENTLY_VERIFIED',
             'tcvn_compliance':'NOT_CERTIFIED'}
    Path(output).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return p.returncode

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='TEST_REPORT.json')
    sys.exit(report(ap.parse_args().output))
