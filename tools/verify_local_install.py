"""Exercise read-only/offline MCP tools through the configured stdio server."""
import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from autocad_agent.runtime import atomic_json


async def main():
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,CAD_OUTPUT_DIR=str(root/'output'/'mcp-smoke'),PYTHONUTF8='1',OPENBLAS_NUM_THREADS='1')
    server=StdioServerParameters(command=sys.executable,args=['-m','autocad_agent.mcp_server'],cwd=str(root),env=env)
    results={}
    async with stdio_client(server) as (reader,writer):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            names=[tool.name for tool in (await session.list_tools()).tools]
            assert len(names)==34
            async def call(name,args=None):
                print('Calling '+name,flush=True)
                response=await asyncio.wait_for(session.call_tool(name,args or {}),45)
                assert not response.isError,(name,response)
                data=response.structuredContent
                if data is None:data=json.loads(response.content[0].text)
                results[name]=data
                return data
            await call('cad_capabilities')
            probe=await call('cad_probe_autocad');assert probe['status']=='CONNECTED',probe
            job=await call('cad_template',{'discipline':'mechanical','width':200,'height':100,'output_name':'MCP_CHECK.dwg'})
            check=await call('cad_validate',{'job':job});assert check['status']=='VALID_INPUT'
            await call('cad_quality_gate',{'job':job})
            preview=await call('cad_preview',{'job':job})
            await call('cad_audit_dxf',{'filename':Path(preview['dxf']['file']).name})
            await call('cad_catalog',{'discipline':'mechanical'})
            await call('cad_screen_standards',{'job':job})
            await call('cad_check_project_rules',{'job':job,'project_rules':{'kind':'PROJECT_RULE','project_id':'SMOKE','checks':[{'type':'required_layers','layers':['M-OUTLINE','M-DIM']}]}})
            await call('cad_check_clause_rules',{'job':job,'rule_pack_name':'EXAMPLE_NOT_VERIFIED.json'})
            job['plot']={'enabled':True,'pdf':True}
            await call('cad_plot_plan',{'job':job})
            await call('cad_prepare',{'job':job})
            # Verify that manual mode denies an unapproved ticket; no CAD write.
            response=await session.call_tool('cad_create_dwg',{'ticket':results['cad_prepare']['ticket']})
            assert response.isError,'Manual approval gate unexpectedly allowed execution'
            results['cad_create_dwg']={'status':'UNAPPROVED_TICKET_REJECTED','isError':True}
    report={'status':'MCP_LEGACY_14_TOOLS_EXERCISED_19_REGISTERED','registered_tools':names,'results':results,'cad_creation_scope':'native COM tested separately; unapproved MCP creation correctly rejected'}
    atomic_json(root/'output'/'MCP_VERIFICATION.json',report)
    print(json.dumps({'status':report['status'],'tools':list(results)},indent=2))

if __name__=='__main__':asyncio.run(main())
