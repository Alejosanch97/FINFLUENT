// Lee los archivos PeriodoX.jsx y arma src/front/activityCatalog.js:
// el nombre de cada clase y de cada actividad, para que el panel Admin
// muestre "Reading check" en vez de "w1_check". Se ejecuta solo en cada build.
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pagesDir = join(root, "src/front/pages");
const WEEK = /\{\s*n:\s*(\d+),(?:\s*g:\s*"?([^",]*)"?,)?\s*title:\s*"((?:[^"\\]|\\.)*)".*acts:\s*\[/;
const ACT = /(?:\bA\d*\(\s*|\{\s*key:\s*)"([A-Za-z0-9_]+)",\s*(?:title:\s*)?"((?:[^"\\]|\\.)*)"/g;
const BUCKET = /"(comportamiento|quizzes|aprendi)"/;

const catalog = {};
for (const file of readdirSync(pagesDir).filter((f) => /^Periodo\d.*\.jsx$/.test(f)).sort()) {
  const src = readFileSync(join(pagesDir, file), "utf8");
  const key = (src.match(/const PERIOD_KEY = "([^"]+)"/) || src.match(/KEY:\s*"([^"]+)"/) || [])[1];
  if (!key) continue;
  const title = (src.match(/KEY:\s*"[^"]+",\s*title:\s*"((?:[^"\\]|\\.)*)"/) || [])[1]
    || (src.match(/GRADE \{GRADE\} · PERIOD \d<\/span>\s*<h1>([^<]+)<\/h1>/) || [])[1] || key;
  const weeks = [];
  let current = null;
  for (const line of src.split("\n")) {
    const w = line.match(WEEK);
    if (w) { current = { n: Number(w[1]), label: w[2] || w[1], title: JSON.parse(`"${w[3]}"`), acts: [] }; weeks.push(current); }
    if (!current) continue;
    for (const m of line.matchAll(ACT)) {
      if (!/coins|,\s*\d+,\s*"/.test(line)) continue;
      current.acts.push({ key: m[1], title: JSON.parse(`"${m[2]}"`), bucket: (line.slice(m.index).match(BUCKET) || [])[1] || "" });
    }
    if (/^\];/.test(line)) current = null;
  }
  catalog[key] = { title: title.trim(), weeks: weeks.filter((w) => w.acts.length) };
}

const out = `// ARCHIVO GENERADO por scripts/build-catalog.mjs — no lo edites a mano.\nexport const CATALOG = ${JSON.stringify(catalog, null, 1)};\n`;
writeFileSync(join(root, "src/front/activityCatalog.js"), out);
console.log("activityCatalog.js:", Object.entries(catalog).map(([k, v]) => `${k}=${v.weeks.reduce((a, w) => a + w.acts.length, 0)}`).join(" "));
