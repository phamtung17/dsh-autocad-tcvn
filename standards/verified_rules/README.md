# Clause rulepack — safety boundary

This directory intentionally contains **NO** pre-verified TCVN rule.
`EXAMPLE_NOT_VERIFIED.json` demonstrates the schema and MUST return NOT_CHECKED.
Never set `attested: true` or fabricate a source hash based on model memory.
A qualified reviewer must lawfully obtain the exact applicable source, hash it,
verify title/edition/clauses/values, identify reviewer and review date, and
approve each specific machine-checkable rule. PASS only means the project
measurement met an attested declarative constraint, **not** that the building
or product is certified compliant. Manual approvals remain required.

Supported types: sheet_format (equals string), sheet_scale_denominator (le),
max_entity_count (le), min_line_length (ge), min_circle_diameter (ge),
required_layers (subset), all_polylines_closed (equals boolean).
Each rule must include clause, type, expected, method, reviewed_by,
attested=true and comparison for numeric rules. Source metadata includes exact
catalog id, edition, title, SHA256 of lawful standard PDF/file, reviewer and
ISO review date. No validation of authenticity of these local assertions occurs.
