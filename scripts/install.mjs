import { copyFileSync, existsSync } from 'node:fs';
import path from 'node:path';

import { backend, frontend, python, root, run } from './common.mjs';

// npm install invokes this lifecycle hook too. The child install must stop here.
if (process.env.CHANGEORDER_INSTALLING === '1') process.exit(0);

try {
  const npmCli = process.env.npm_execpath;
  if (!npmCli) throw new Error('Run setup with npm run install.');

  const env = { ...process.env, CHANGEORDER_INSTALLING: '1' };
  run(process.execPath, [npmCli, 'install', '--include=dev'], root, env);
  run(process.execPath, [npmCli, 'install', '--include=dev'], frontend, env);

  if (!existsSync(python)) {
    const launcher = process.platform === 'win32' ? 'py' : 'python3';
    const args = process.platform === 'win32' ? ['-3.12'] : [];
    run(launcher, [...args, '-m', 'venv', '.venv'], backend);
  }

  run(python, ['-m', 'pip', 'install', '-r', 'requirements.txt'], backend);

  // Preserve existing local settings on every subsequent install.
  for (const directory of [backend, frontend]) {
    const destination = path.join(directory, '.env');
    if (!existsSync(destination)) {
      copyFileSync(path.join(directory, '.env.example'), destination);
    }
  }

  console.log('\nSetup complete. Set your PC address in frontend/.env, then run npm run dev.');
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
