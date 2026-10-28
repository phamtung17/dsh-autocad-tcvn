"""Register this checkout's isolated MCP runtime without changing other servers."""
from pathlib import Path
from datetime import datetime
import json
import sys
import tomllib


def main():
    root=Path(__file__).resolve().parents[1]
    config=Path.home()/'.codex'/'config.toml'
    current=config.read_text(encoding='utf-8') if config.exists() else ''
    parsed=tomllib.loads(current)
    python=root/'.venv'/'Scripts'/'python.exe'
    if not python.is_file():raise RuntimeError('Install the repository .venv first')
    if 'dsh_autocad_tcvn' in parsed.get('mcp_servers',{}):
        existing=parsed['mcp_servers']['dsh_autocad_tcvn']
        if Path(existing['command'])!=python:raise RuntimeError('Existing server uses another checkout; inspect configuration manually')
        updated=current
        marker='[mcp_servers.dsh_autocad_tcvn.env]'
        if 'CAD_PROFILE_DIR' not in existing.get('env',{}):
            value=json.dumps(str(root/'output'/'profiles').replace('\\','/'))
            if marker in updated:updated=updated.replace(marker,marker+'\nCAD_PROFILE_DIR = '+value,1)
            else:updated+='\n'+marker+'\nCAD_PROFILE_DIR = '+value+'\n'
        # Upgrade the old installer default; preserve other custom timeouts.
        if existing.get('tool_timeout_sec')==180:
            begin=updated.index('[mcp_servers.dsh_autocad_tcvn]')
            end=updated.find('\n[',begin+1)
            if end<0:end=len(updated)
            updated=updated[:begin]+updated[begin:end].replace('tool_timeout_sec = 180','tool_timeout_sec = 900')+updated[end:]
        if updated!=current:
            tomllib.loads(updated)
            backup=config.with_name('config.toml.before-reference-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
            backup.write_bytes(config.read_bytes());config.write_text(updated,encoding='utf-8')
            print('Existing server upgraded; backup: '+str(backup))
        else:print('Server already registered with reference profile settings')
        return
    q=lambda value:json.dumps(str(value).replace('\\','/'))
    addition=f'''

# Local upgrade of phamtung17/dsh-autocad-TCVN
[mcp_servers.dsh_autocad_tcvn]
command = {q(python)}
args = ["-m", "autocad_agent.mcp_server"]
cwd = {q(root)}
startup_timeout_sec = 60
tool_timeout_sec = 900

[mcp_servers.dsh_autocad_tcvn.env]
CAD_PROFILE_DIR = {q(root/'output'/'profiles')}
CAD_OUTPUT_DIR = {q(root/'output'/'cad')}
CAD_DWT_DIR = {q(root/'output'/'templates')}
CAD_RULES_DIR = {q(root/'standards'/'verified_rules')}
CAD_APPROVAL_MODE = "manual"
PYTHONUTF8 = "1"
'''
    tomllib.loads(current+addition)
    backup=config.with_name('config.toml.before-dsh-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
    if config.exists():backup.write_bytes(config.read_bytes())
    config.parent.mkdir(parents=True,exist_ok=True)
    config.write_text(current+addition,encoding='utf-8')
    print('Registered: '+str(config))
    print('Backup: '+str(backup))

if __name__=='__main__':main()
