import json
from pathlib import Path

def test_registry_has_unique_ids_no_verified_clauses():
    root=Path(__file__).parents[1]
    registry=json.loads((root/'standards'/'registry.json').read_text(encoding='utf-8'))
    ids=[e['id'] for e in registry['standards']]
    assert len(ids)==len(set(ids))
    assert all(e.get('rule_status')!='CLAUSE_VERIFIED' for e in registry['standards'])

def test_requires_mcp_stdio_config():
    root=Path(__file__).parents[1]
    content=(root/'install'/'dsh-mcp-client.example.yml').read_text(encoding='utf-8')
    assert '@deepseek-ai/dsh-mcp-client' in content
    assert 'transport: stdio' in content
