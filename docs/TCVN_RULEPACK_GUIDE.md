# Clause-linked TCVN rules: what the engine guarantees

This release adds *measurement and evidence traceability*, **not** an official
TCVN compliance certificate or copies of protected national standards.

## Authoring workflow

1. Qualified reviewer determines exact applicable regulation or national
   standard, edition, amendments and scope from official sources.
2. Obtain the lawful original document. Record SHA-256 of that source;
   never copy any copyrighted full text into a public repository.
3. Reviewer transcribes an authorized, narrow machine-measurable constraint
   into an approved local JSON rulepack with a clause identifier and method.
4. Put the pack in `standards/verified_rules/` or an approved `CAD_RULES_DIR`.
   No arbitrary rule file path is accepted through the MCP API.
5. Declare the exact catalog standard ID in the drawing's `standards` array
   and reference the local filename in `clause_rule_packs`. Run
   `cad_check_clause_rules` and `cad_quality_gate`.
6. Each rule returns `PASS`, `FAIL` or `NOT_CHECKED` with measured, expected,
   method, provenance and a disclaimer. **PASS is a measured constraint only**.
   Reviewer still must check source authenticity, interpretation,
   current validity, project applicability and design safety.

## Example shape (NOT valid as a source attestation)

```json
{
  "kind": "TCVN_CLAUSE_RULEPACK",
  "standard": {
    "id": "TCVN 7285:2003",
    "edition": "2003",
    "source_title": "REPLACE WITH EXACT VERIFIED TITLE",
    "source_sha256": "<64-character sha256 of lawful source>",
    "reviewed_by": "QUALIFIED REVIEWER NAME",
    "reviewed_at": "2026-10-28"
  },
  "rules": [
    {"id":"EXAMPLE-ONLY","clause":"VERIFY EXACT CLAUSE",
     "type":"sheet_format","expected":"A3",
     "method":"Read declared sheet format in signed drawing specification",
     "reviewed_by":"QUALIFIED REVIEWER NAME","attested":false}
  ]
}
```

The example uses placeholder values and `attested:false`: it MUST return
`NOT_CHECKED`. The chosen format is **not** asserted to be a normative
requirement of that TCVN. Approval requires comparison to the actual source.

## Guardrails

- Source verification metadata comes from a human-maintained local file, NOT
  authenticated automatically by the plugin.
- `rule_type`, `expected`, `method`, `clause` and `comparison` are separated.
- Rules without matching measurable entities return `NOT_CHECKED`.
- Mismatched standards/disciplines return `NOT_CHECKED`.
- A job that explicitly requests a rule pack which returns `FAIL` or
  `NOT_CHECKED` is blocked by the production Quality Gate.
- No arbitrary Python expressions, scripts or shells may occur in rule files.
- Legal compliance, manufacturing and construction approvals require independent
  licensed engineers and the governing legal process, not an AI flag.
