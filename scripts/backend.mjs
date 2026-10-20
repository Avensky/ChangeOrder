import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

import { backend, python } from './common.mjs';

if (!existsSync(python)) {
  console.error('Backend environment missing. Run npm run install first.');
  process.exit(1);
}

const args = [
  '-m', 'uvicorn', 'main:app', '--reload',
  '--reload-dir', backend, '--host', '0.0.0.0', '--port', '8000',
];
const envFile = path.join(backend, '.env');
if (existsSync(envFile)) args.push('--env-file', envFile);

const server = spawn(python, args, { cwd: backend, stdio: 'inherit' });
server.on('error', (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
server.on('exit', (code, signal) => {
  process.exit(code ?? (signal === 'SIGINT' ? 0 : 1));
});

process.on('SIGINT', () => server.kill('SIGINT'));
process.on('SIGTERM', () => server.kill('SIGTERM'));
