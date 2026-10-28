/**
 * DSH bundle path service. This is the actual Cordis plugin loaded by DSH.
 * No TypeScript compilation, postinstall or prepare hook is required for Git installs.
 * The MCP client and skill provider are mounted by cordis.patch.yml.
 */
import { Service } from '@deepseek-ai/cordis';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';

export const name = 'dsh-autocad-tcvn-bundle-paths';

export default class AutoCADBundlePaths extends Service {
  constructor(ctx) {
    super(ctx, 'autocadBundle');
    this.root = path.dirname(fileURLToPath(import.meta.url));
    this.launcher = path.join(this.root, 'scripts', 'launch-mcp.cjs');
    this.skillsRoot = path.join(this.root, 'skills');
    this.disciplinesRoot = path.join(this.skillsRoot, 'disciplines');
    this.rulesDir = path.join(this.root, 'standards', 'verified_rules');
    this.outputDir = path.join(os.homedir(), 'Documents', 'CAD_AGENT_OUTPUT');
    this.dwtDir = path.join(os.homedir(), 'Documents', 'CAD_DWT_Templates');
  }
}
