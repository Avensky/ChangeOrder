// Serve the static export with extensionless Expo routes, on loopback only.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
const root = path.resolve('.e2e-dist');
const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    let file = path.resolve(root, '.' + pathname);
    if (file !== root && !file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    if (pathname.endsWith('/')) file = path.join(file, 'index.html');
    try { await stat(file); } catch { file += '.html'; }
    const bytes = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] ?? 'application/octet-stream' });
    res.end(bytes);
  } catch {
    try { res.writeHead(404, { 'Content-Type': 'text/html' }).end(await readFile(path.join(root, '+not-found.html'))); }
    catch { res.end('Not found'); }
  }
}).listen(8123, '127.0.0.1');
