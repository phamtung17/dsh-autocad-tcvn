const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const core=require('../scripts/launch-core.cjs');
const pkg=require('../package.json');
const patch=fs.readFileSync(path.join(root,'cordis.patch.yml'),'utf8');
test('DSH manifest declares a real bundle patch',()=>{
  assert.equal(pkg.dsh.bundle.patch,'./cordis.patch.yml');
  assert.equal(pkg.name,'@phamtung17/dsh-autocad-tcvn');
  assert.match(patch,/^- insert:/m);
});
test('MCP server uses stdio and a bundle-relative Node launcher',()=>{
  assert.match(patch,/transport: stdio/);
  assert.match(patch,/args: !!js '\[ctx\.autocadBundle\.launcher\]'/);
  assert.match(patch,/inject: \[autocadBundle\]/);
});
test('all ten skills are discoverable under the two DSH scan roots',()=>{
  const roots=['skills','skills/disciplines'];
  let skills=[];
  for(const dir of roots)for(const entry of fs.readdirSync(path.join(root,dir),{withFileTypes:true})){
    if(entry.isDirectory()&&fs.existsSync(path.join(root,dir,entry.name,'SKILL.md')))skills.push(entry.name);
  }
  assert.equal(skills.length,10);
  assert.match(patch,/customSkillDirs:/);
});
test('launcher isolates Python setup and reserves stdout for MCP',()=>{
  assert.equal(core.PACKAGE_ROOT,root);
  assert.equal(core.expectedHash().length,64);
  assert.match(fs.readFileSync(path.join(root,'scripts/launch-mcp.cjs'),'utf8'),/stdio: \['inherit','inherit','inherit'\]/);
});
test('default mode requires manual approval',()=>{
  assert.match(patch,/CAD_APPROVAL_MODE: manual/);
});
test('bundle does not need git prepare script permission',()=>{
  assert.equal(pkg.scripts.prepare,undefined);
  assert.equal(pkg.scripts.postinstall,undefined);
});
