/* =====================================================================
   FINFLUENT · CLIENTE DE LA API
   Un solo lugar para hablar con el backend (Flask). Agrega el token,
   devuelve JSON y, si la sesión venció, manda al login sin perder lo
   que estaba pendiente por subir (queda en localStorage).
   ===================================================================== */

// Vacío = mismo dominio (Render) o proxy de Vite en local. Solo se llena si el back vive en otra URL.
const BASE = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/+$/, "");
export const API_URL = `${BASE}/api`;

const SESSION_KEY = "userFIN";

export const getSession = () => {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "null"); } catch { return null; }
};
export const setSession = (data) => localStorage.setItem(SESSION_KEY, JSON.stringify(data));
export const clearSession = () => {
  localStorage.removeItem(SESSION_KEY);
  try { Object.keys(sessionStorage).filter((k) => k.startsWith("finNav_")).forEach((k) => sessionStorage.removeItem(k)); } catch { /* nada */ }
};

let expiredOnce = false;
function sessionExpired() {
  if (expiredOnce) return;
  expiredOnce = true;
  clearSession();
  window.location.assign("/?expired=1");
}

/** fetch con token. Devuelve la Response original (para código que hace res.json()). */
export async function rawFetch(path, { method = "GET", body, signal } = {}) {
  const token = getSession()?.token;
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, {
    method, headers, signal,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && token && !path.startsWith("/auth/login")) sessionExpired();
  return res;
}

/** Igual que rawFetch pero devuelve el JSON ya leído. Lanza error si la respuesta no es JSON. */
export async function api(path, options) {
  const res = await rawFetch(path, options);
  let data = null;
  try { data = await res.json(); } catch { /* respuesta vacía o HTML */ }
  if (data === null) throw new Error(`Server error (${res.status})`);
  return data;
}

/** Como api(), pero lanza Error con el mensaje del servidor cuando status === "error". */
export async function apiOk(path, options) {
  const data = await api(path, options);
  if (data && data.status === "error") {
    const err = new Error(data.message || "Error");
    err.details = data.errors || [];
    throw err;
  }
  return data;
}

/** Reintenta (útil para el login: la instancia gratis de Render tarda en despertar). */
export async function apiRetry(path, options, { tries = 3, timeoutMs = 25000 } = {}) {
  let last;
  for (let i = 0; i < tries; i++) {
    const ctrl = new AbortController();
    const id = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const data = await api(path, { ...options, signal: ctrl.signal });
      clearTimeout(id);
      return data;
    } catch (e) {
      clearTimeout(id);
      last = e;
      if (i < tries - 1) await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
    }
  }
  throw last;
}
