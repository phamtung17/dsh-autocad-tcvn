"""Verify wiring of MCP tools using a mock SDK (not a protocol negotiation test)."""
import importlib,sys,types
from unittest.mock import patch

def test_tool_registration():
    tools=[]
    class FakeMCP:
        def __init__(self,*args,**kwargs):pass
        def tool(self):
            def register(fn):tools.append(fn.__name__);return fn
            return register
    fake=types.ModuleType('mcp');server=types.ModuleType('mcp.server');fast=types.ModuleType('mcp.server.fastmcp')
    fast.FastMCP=FakeMCP
    with patch.dict(sys.modules,{'mcp':fake,'mcp.server':server,'mcp.server.fastmcp':fast}):
        sys.modules.pop('autocad_agent.mcp_server',None)
        module=importlib.import_module('autocad_agent.mcp_server')
        assert 'cad_template' in tools and 'cad_create_dwg' in tools
        assert 'cad_screen_standards' in tools
        assert len(tools)==35
        assert {'cad_reference_profiles','cad_reference_profile','cad_reference_plan','cad_reference_prepare','cad_reference_export'}<=set(tools)
        assert module.cad_capabilities()['tcvn_compliance']=='NOT_CHECKED'
