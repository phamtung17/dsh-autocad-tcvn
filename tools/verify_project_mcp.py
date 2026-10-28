"""Exercise actual stdio contracts for the 14-stage tools, including preview."""
import asyncio,json,os,sys
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,CAD_OUTPUT_DIR=str(root/'output'/'mcp-v14'),CAD_APPROVAL_MODE='manual',PYTHONUTF8='1')
    async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','autocad_agent.mcp_server'],cwd=str(root),env=env)) as (r,w):
        async with ClientSession(r,w) as session:
            await session.initialize();names={t.name for t in (await session.list_tools()).tools};assert len(names)==34
            async def call(name,args=None):
                result=await asyncio.wait_for(session.call_tool(name,args or {}),120)
                assert not result.isError,(name,result)
                return result.structuredContent or json.loads(result.content[0].text)
            assert len((await call('cad_project_catalog'))['stages'])==14
            spec=(await call('cad_project_example'))['spec']
            assert len((await call('cad_project_plan',{'spec':spec}))['sheets'])==58
            assert not (await call('cad_project_check',{'spec':spec}))['issues']
            import copy
            changed=copy.deepcopy(spec);changed['prices']['floor_finish']*=2
            assert (await call('cad_project_change_impact',{'before':spec,'after':changed}))['rebuild_stages']==[13,14]
            preview=await call('cad_project_preview',{'spec':spec});assert preview['sheet_count']==58 and Path(preview['pdf']).is_file()
            ticket=(await call('cad_project_prepare',{'spec':spec}))['ticket']
            result=await session.call_tool('cad_project_export',{'ticket':ticket});assert result.isError
            print(json.dumps({'status':'PASS','tools':len(names),'stages':14,'preview_sheets':58,'unapproved_export_rejected':True}))

if __name__=='__main__':asyncio.run(main())
