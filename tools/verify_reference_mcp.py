"""Exercise 19-tool registration and five reference tool contracts over stdio."""
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from autocad_agent.runtime import atomic_json


async def main():
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,CAD_OUTPUT_DIR=str(root/'output/cad'),CAD_PROFILE_DIR=str(root/'output/profiles'),
             CAD_APPROVAL_MODE='manual',PYTHONUTF8='1',OPENBLAS_NUM_THREADS='1')
    server=StdioServerParameters(command=sys.executable,args=['-m','autocad_agent.mcp_server'],cwd=str(root),env=env)
    result={}
    async with stdio_client(server) as (reader,writer):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            names=[t.name for t in (await session.list_tools()).tools];assert len(names)==34
            async def call(name,args=None):
                output=await asyncio.wait_for(session.call_tool(name,args or {}),45)
                assert not output.isError,(name,output)
                value=output.structuredContent
                if value is None:value=json.loads(output.content[0].text)
                result[name]=value;return value
            await call('cad_reference_profiles')
            profile=await call('cad_reference_profile',{'profile_id':'stu4_fitout_v12'})
            assert len(profile['sheets'])==35
            job={'profile_id':profile['id'],'project_id':'mcp_reference_contract','accept_font_substitution':True}
            plan=await call('cad_reference_plan',{'job':job});assert plan['status']=='READY_FOR_REFERENCE_REISSUE'
            prepared=await call('cad_reference_prepare',{'job':job})
            blocked=await session.call_tool('cad_reference_export',{'ticket':prepared['ticket']})
            assert blocked.isError,'Unapproved publication unexpectedly succeeded'
            result['cad_reference_export']={'unapproved_ticket':'REJECTED'}
    atomic_json(root/'output/REFERENCE_MCP_VERIFICATION.json',{'status':'REFERENCE_5_TOOL_CONTRACTS_CHECKED',
                'registered_tools':names,'results':result,'native_creation':'tested by trusted publication CLI separately'})
    print('34 tools registered; 5 reference contracts checked; 35 sheets discovered; unapproved export rejected')

if __name__=='__main__':asyncio.run(main())
