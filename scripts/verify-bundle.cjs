'use strict';
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));
const patch=fs.readFileSync(path.join(root,'cordis.patch.yml'),'utf8');
function check(v,m){if(!v)throw new Error(m)}
check(pkg.dsh?.bundle?.patch==='./cordis.patch.yml','Missing dsh.bundle.patch');
check(pkg.name==='@phamtung17/dsh-autocad-tcvn','Wrong package name');
check(/^- insert:/m.test(patch),'Bundle patch must use insert: operation');
for(const token of ['autocad-tcvn-bundle-paths','@deepseek-ai/dsh-mcp-client','@deepseek-ai/dsh-skill-filesystem','autocadBundle','CAD_APPROVAL_MODE: manual'])check(patch.includes(token),'Missing '+token);
for(const p of ['index.js','scripts/launch-mcp.cjs','autocad_agent/mcp_server.py','skills/cad-automation/SKILL.md','skills/disciplines/mechanical/SKILL.md'])check(fs.existsSync(path.join(root,p)),'Missing '+p);
console.log(`OK: Git-installable DSH bundle ${pkg.name}@${pkg.version}`);
