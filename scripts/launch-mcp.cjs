#!/usr/bin/env node
'use strict';
// stdout is reserved exclusively for MCP JSON-RPC. All diagnostics go to stderr.
const cp = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { PACKAGE_ROOT, ensurePython } = require('./launch-core.cjs');

try {
  const python = ensurePython((line) => process.stderr.write(`${line}\n`));
  if (process.argv.includes('--check')) {
    process.stderr.write(`[AutoCAD-TCVN] Ready: ${python}\n`);
    process.exit(0);
  }
  const output = process.env.CAD_OUTPUT_DIR || path.join(require('node:os').homedir(), 'Documents', 'CAD_AGENT_OUTPUT');
  const dwt = process.env.CAD_DWT_DIR || path.join(require('node:os').homedir(), 'Documents', 'CAD_DWT_Templates');
  fs.mkdirSync(output, {recursive:true});
  fs.mkdirSync(dwt, {recursive:true});
  const env = {...process.env,
    PYTHONUTF8: '1',
    CAD_OUTPUT_DIR: output,
    CAD_DWT_DIR: dwt,
    CAD_RULES_DIR: process.env.CAD_RULES_DIR || path.join(PACKAGE_ROOT, 'standards', 'verified_rules'),
    CAD_APPROVAL_MODE: process.env.CAD_APPROVAL_MODE || 'manual'
  };
  const child = cp.spawn(python, ['-m', 'autocad_agent.mcp_server'], {
    cwd: PACKAGE_ROOT,
    env,
    stdio: ['inherit','inherit','inherit'],
    windowsHide: true
  });
  child.on('error', (err) => { process.stderr.write(`[AutoCAD-TCVN] MCP launch failed: ${err.message}\n`); process.exitCode = 1; });
  child.on('exit', (code, signal) => { process.exitCode = code ?? (signal ? 1 : 0); });
  for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => { if (!child.killed) child.kill(signal); });
} catch (err) {
  process.stderr.write(`[AutoCAD-TCVN] ${err.stack || err.message}\n`);
  process.exitCode = 1;
}
