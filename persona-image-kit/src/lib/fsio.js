import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.join(__dirname, '../../public/img');

export function ensureDirs() {
  if (!fs.existsSync(path.join(__dirname, '../../public'))) fs.mkdirSync(path.join(__dirname, '../../public'));
  if (!fs.existsSync(ROOT)) fs.mkdirSync(ROOT);
}
ensureDirs();

export function filePathFor(id) {
  return path.join(ROOT, `${id}.png`);
}

export function toDataUrl(buf) {
  const base64 = buf.toString('base64');
  return `data:image/png;base64,${base64}`;
}