"""Exercise the installed Harness launcher, not the repository Python module."""
import asyncio,json,os
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root=Path(r'C:\Users\Admin\.dsh\profiles\web\node_modules\@phamtung17\dsh-autocad-tcvn')
    env=dict(os.environ,PYTHONUTF8='1')
    async with stdio_client(StdioServerParameters(command='node',args=[str(root/'scripts/launch-mcp.cjs')],cwd=str(root),env=env)) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            async def call(name,args=None):
                result=await session.call_tool(name,args or {})
                assert not result.isError,result
                return result.structuredContent or json.loads(result.content[0].text)
            cap=await call('cad_capabilities');assert cap['version']=='1.7.0-local'
            assert cap['live_drawing']['mode']=='REAL_NATIVE_ENTITY_CREATION'
            assert len((await session.list_tools()).tools)==35
            live=await call('cad_project_progress',{'project_id':'v17-launcher-not-started'})
            assert live['status']=='NOT_STARTED'
            cat=await call('cad_project_catalog');assert cat['output_mode']=='SINGLE_DWG_MULTIPLE_LAYOUTS'
            spec=(await call('cad_project_example',{'template':'villa_18x17'}))['spec']
            check=await call('cad_project_check',{'spec':spec});assert not check['issues']
            bad=json.loads(json.dumps(spec));bad['extensions']['openings'][0]['position']=[8000,3000]
            rejected=await call('cad_project_check',{'spec':bad});assert any(i['type']=='OPENING_HOST_MISSING' for i in rejected['issues'])
            denied=await session.call_tool('cad_project_prepare',{'spec':bad});assert denied.isError
            probe=await call('cad_probe_autocad')
            report={'status':'INSTALLED_LAUNCHER_CHECKED','version':cap['version'],
                    'tools':len((await session.list_tools()).tools),'villa_sheet_count':check['sheet_count'],
                    'spatial_rules':check['spatial_rules']['ruleset'],'unhosted_opening_prepare_rejected':True,
                    'autocad':probe,'running_harness_reload_required':True}
            report['live_native_drawing']=cap['live_drawing'];report['progress_tool_checked']=True
            Path('output/HARNESS_V15_TEST_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report))


if __name__=='__main__':asyncio.run(main())
