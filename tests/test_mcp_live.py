"""Actual MCP stdio handshake when the `mcp` Python SDK is installed.

This is NOT a DSH plugin activation test (requires running DeepSeek Harness).
"""
from pathlib import Path
import sys
import pytest

@pytest.fixture
def anyio_backend(): return 'asyncio'

@pytest.mark.mcp_live
@pytest.mark.anyio
async def test_stdio_mcp_tools_listed(tmp_path):
    pytest.importorskip('mcp')
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    root=Path(__file__).resolve().parents[1]
    server=StdioServerParameters(command=sys.executable,args=['-m','autocad_agent.mcp_server'],
                                 cwd=str(root),env={'CAD_OUTPUT_DIR':str(tmp_path)})
    with anyio.fail_after(35):
        async with stdio_client(server) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                available=await session.list_tools()
                names={t.name for t in available.tools}
                assert len(names)==34
                assert {'cad_probe_autocad','cad_check_clause_rules','cad_plot_plan','cad_quality_gate'}.issubset(names)
