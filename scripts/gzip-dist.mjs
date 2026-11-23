// Después de "vite build": deja una copia .gz de cada archivo de texto en dist/.
// Flask las entrega comprimidas (ver _send en src/app.py) y la plataforma carga
// mucho más rápido con el wifi del colegio.
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const dist = join(dirname(fileURLToPath(import.meta.url)), "..", "dist");
let n = 0, before = 0, after = 0;
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) { walk(full); continue; }
    if (!/\.(js|css|html|svg|json)$/.test(name)) continue;
    const raw = readFileSync(full);
    if (raw.length < 1024) continue;
    const gz = gzipSync(raw, { level: 9 });
    writeFileSync(`${full}.gz`, gz);
    n++; before += raw.length; after += gz.length;
  }
};
walk(dist);
console.log(`gzip: ${n} archivos, ${(before / 1e6).toFixed(1)} MB -> ${(after / 1e6).toFixed(1)} MB`);
