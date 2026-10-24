import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { unlinkSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const testTs = join(__dirname, 'studentLogic.test.ts');
const bundleMjs = join(__dirname, 'studentLogic.test.bundle.mjs');

try {
  execSync(
    `node "${join(__dirname, '../../../node_modules/esbuild/bin/esbuild')}" "${testTs}" --bundle --platform=node --format=esm --packages=external --outfile="${bundleMjs}"`,
    { stdio: 'inherit' }
  );
  execSync(`node --test "${bundleMjs}"`, { stdio: 'inherit' });
} finally {
  try {
    unlinkSync(bundleMjs);
  } catch {
    // ignore
  }
}
