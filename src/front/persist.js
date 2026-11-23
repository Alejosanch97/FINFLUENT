/* =====================================================================
   NO PERDER NADA AL RECARGAR
   1) usePersistentState: recuerda en qué pestaña / clase / actividad
      estaba el estudiante. Si la página se actualiza, vuelve ahí mismo.
   2) Borradores: todo lo que el estudiante escribe en una actividad se
      copia a localStorage mientras teclea y se devuelve a su casilla
      cuando la actividad se abre otra vez. Se borra cuando la actividad
      se guarda en el servidor.
   ===================================================================== */
import { useCallback, useEffect, useState } from "react";
import { getSession } from "./api";

const who = () => String(getSession()?.Student_Key || "anon");

/* ---------------- 1) Estado que sobrevive al refresh ---------------- */
const navKey = (key) => `finNav_${who()}_${key}`;

export function usePersistentState(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = sessionStorage.getItem(navKey(key));
      return raw === null ? initial : JSON.parse(raw);
    } catch { return initial; }
  });

  const set = useCallback((next) => {
    setValue((prev) => {
      const v = typeof next === "function" ? next(prev) : next;
      try {
        if (v === null || v === undefined) sessionStorage.removeItem(navKey(key));
        else sessionStorage.setItem(navKey(key), JSON.stringify(v));
      } catch { /* modo privado: no pasa nada */ }
      return v;
    });
  }, [key]);

  // La actividad abierta define a qué "cajón" van los borradores
  const isAct = key.endsWith(":act");
  useEffect(() => {
    if (!isAct) return undefined;
    setDraftContext(value ? `${key}:${value}` : null);
    return () => setDraftContext(null);
  }, [isAct, key, value]);

  return [value, set];
}

/* ---------------- 2) Borradores de lo que se escribe ---------------- */
let ctx = null;
let installed = false;
const restored = new WeakSet();

const draftKey = (c) => `finDraft_${who()}_${c}`;
const readDraft = (c) => { try { return JSON.parse(localStorage.getItem(draftKey(c)) || "{}"); } catch { return {}; } };
const writeDraft = (c, d) => {
  try {
    if (Object.keys(d).length) localStorage.setItem(draftKey(c), JSON.stringify(d));
    else localStorage.removeItem(draftKey(c));
  } catch { /* almacenamiento lleno */ }
};

export function setDraftContext(next) {
  ctx = next;
  if (ctx) scheduleRestore();
}
export function clearCurrentDrafts() {
  if (ctx) { try { localStorage.removeItem(draftKey(ctx)); } catch { /* nada */ } }
}

const TEXT_TYPES = ["text", "number", "search", "tel", "url", "email", ""];
function eligible(el) {
  if (!el || !el.closest || !el.closest(".fin-main")) return false;
  if (el.closest("[data-no-draft]")) return false;
  if (el.tagName === "TEXTAREA") return true;
  if (el.tagName !== "INPUT") return false;
  if (!TEXT_TYPES.includes((el.getAttribute("type") || "").toLowerCase())) return false;
  const max = el.maxLength;
  if (max > 0 && max <= 8) return false;          // PIN y códigos cortos nunca se guardan
  return true;
}
const fields = () => Array.from(document.querySelectorAll(".fin-main textarea, .fin-main input")).filter(eligible);

function hash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}
// Identifica una casilla por: su posición, su placeholder y el último título que tiene encima
// (el paso de la actividad). Nada de esto cambia mientras el estudiante escribe.
function fieldId(el, list) {
  let heading = "";
  const heads = document.querySelectorAll(".fin-main h1, .fin-main h2, .fin-main h3, .fin-main h4, .fin-main h5");
  for (const h of heads) {
    if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) heading = h.textContent || "";
    else break;
  }
  const scope = heading.replace(/\s+/g, " ").trim().slice(0, 80);
  return `${list.indexOf(el)}.${el.tagName === "TEXTAREA" ? "t" : "i"}.${hash((el.placeholder || "") + "|" + scope)}`;
}

function onInput(e) {
  const el = e.target;
  if (!ctx || !eligible(el)) return;
  const d = readDraft(ctx);
  const id = fieldId(el, fields());
  if (el.value) d[id] = el.value; else delete d[id];
  writeDraft(ctx, d);
}

function setNativeValue(el, value) {
  const proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value").set.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));   // React recibe el cambio como si se hubiera tecleado
}

let timer = null;
function scheduleRestore() {
  clearTimeout(timer);
  timer = setTimeout(restore, 120);
}
function restore() {
  if (!ctx) return;
  const d = readDraft(ctx);
  if (!Object.keys(d).length) return;
  const list = fields();
  list.forEach((el) => {
    if (restored.has(el)) return;
    restored.add(el);
    const saved = d[fieldId(el, list)];
    if (saved && !el.value) setNativeValue(el, saved);
  });
}

export function installDraftAutosave() {
  if (installed || typeof document === "undefined") return;
  installed = true;
  document.addEventListener("input", onInput, true);
  new MutationObserver(() => { if (ctx) scheduleRestore(); }).observe(document.body, { childList: true, subtree: true });
}
