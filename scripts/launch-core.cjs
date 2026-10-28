'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const cp = require('node:child_process');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const WINDOWS = process.platform === 'win32';
const DATA_ROOT = process.env.CAD_RUNTIME_HOME || path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), '.local', 'share'), 'DSH-AutoCAD-TCVN');
const VENV_ROOT = path.join(DATA_ROOT, 'python-venv');
const VENV_PYTHON = path.join(VENV_ROOT, WINDOWS ? 'Scripts/python.exe' : 'bin/python');
const REQ_FILES = ['requirements.txt', 'requirements-windows.txt'];
const MARKER = path.join(DATA_ROOT, 'installed-requirements.json');
const LOCK = path.join(DATA_ROOT, 'install.lock');
const PY_CHECK = 'import sys, ezdxf, reportlab, pypdf, pymupdf; from mcp.server.fastmcp import FastMCP; assert sys.version_info >= (3, 10)' + (WINDOWS ? '; import win32com.client' : '');
const SLEEP = new Int32Array(new SharedArrayBuffer(4));

function run(exe, args, timeout=300000) {
  return cp.spawnSync(exe, args, {cwd: PACKAGE_ROOT, encoding: 'utf8', timeout, maxBuffer: 10 * 1024 * 1024, windowsHide: true});
}
function fail(message) { throw new Error(message); }
function pythonCandidates() {
  const result = [];
  if (process.env.CAD_PYTHON) result.push([process.env.CAD_PYTHON, []]);
  if (WINDOWS) result.push(['py', ['-3']], ['python', []]);
  else result.push(['python3', []], ['python', []]);
  return result;
}
function findPython() {
  for (const [exe, prefix] of pythonCandidates()) {
    const result = run(exe, [...prefix, '-c', 'import sys; assert sys.version_info >= (3, 10); print(sys.executable)'], 15000);
    if (!result.error && result.status === 0) return {exe, prefix};
  }
  fail('Python >= 3.10 not found. Install Python for Windows (enable PATH), or set CAD_PYTHON to the full python.exe path.');
}
function expectedHash() {
  const h = crypto.createHash('sha256');
  for (const f of REQ_FILES) h.update(f).update(fs.readFileSync(path.join(PACKAGE_ROOT, f)));
  return h.digest('hex');
}
function markerValid(hash) {
  try {
    const obj = JSON.parse(fs.readFileSync(MARKER, 'utf8'));
    if (obj.hash !== hash || !fs.existsSync(VENV_PYTHON)) return false;
    const result = run(VENV_PYTHON, ['-c', PY_CHECK], 30000);
    return !result.error && result.status === 0;
  } catch { return false; }
}
function withLock(fn) {
  fs.mkdirSync(DATA_ROOT, {recursive: true});
  const deadline = Date.now() + 300000;
  while (true) {
    try {
      const fd = fs.openSync(LOCK, 'wx', 0o600);
      fs.writeFileSync(fd, `${process.pid}\n${Date.now()}\n`);
      try { return fn(); }
      finally { fs.closeSync(fd); try { fs.unlinkSync(LOCK); } catch {} }
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      try {
        const st = fs.statSync(LOCK);
        if (Date.now() - st.mtimeMs > 10 * 60 * 1000) { fs.unlinkSync(LOCK); continue; }
      } catch (e) { if (e.code === 'ENOENT') continue; }
      if (Date.now() > deadline) fail(`Timed out waiting for Python setup lock: ${LOCK}`);
      Atomics.wait(SLEEP, 0, 0, 300);
    }
  }
}
function ensurePython(log=console.error) {
  const hash = expectedHash();
  if (markerValid(hash)) return VENV_PYTHON;
  if (process.env.CAD_AUTO_SETUP === '0') {
    fail(`Python dependencies not set up. Run: node "${path.join(PACKAGE_ROOT,'scripts','launch-mcp.cjs')}" --check`);
  }
  withLock(() => {
    if (markerValid(hash)) return;
    const base = findPython();
    log(`[AutoCAD-TCVN] Preparing isolated Python environment at ${VENV_ROOT}`);
    if (!fs.existsSync(VENV_PYTHON)) {
      const v = run(base.exe, [...base.prefix, '-m', 'venv', VENV_ROOT]);
      if (v.error || v.status !== 0) fail(`Could not create Python venv: ${v.stderr || v.error?.message || v.status}`);
    }
    const req = path.join(PACKAGE_ROOT, WINDOWS ? 'requirements-windows.txt' : 'requirements.txt');
    const install = run(VENV_PYTHON, ['-m','pip','install','--disable-pip-version-check','-r',req], 300000);
    if (install.error || install.status !== 0) fail(`pip install failed. ${install.stderr || install.stdout || install.error?.message || install.status}`);
    const check = run(VENV_PYTHON, ['-c', PY_CHECK], 30000);
    if (check.error || check.status !== 0) fail(`Python dependency check failed: ${check.stderr || check.error?.message || check.status}`);
    const temp = `${MARKER}.${process.pid}.tmp`;
    fs.writeFileSync(temp, JSON.stringify({hash, python: VENV_PYTHON, installedAt: new Date().toISOString()}));
    fs.renameSync(temp, MARKER);
    log('[AutoCAD-TCVN] Python dependencies ready.');
  });
  return VENV_PYTHON;
}
module.exports = {PACKAGE_ROOT, DATA_ROOT, VENV_ROOT, VENV_PYTHON, MARKER, LOCK, REQ_FILES, expectedHash, markerValid, pythonCandidates, ensurePython};
