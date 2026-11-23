/* =====================================================================
   PUENTE: las actividades fueron escritas para Apps Script y llaman

       fetch(API_URL, { method: "POST", body: JSON.stringify({ action, ... }) })

   finFetch recibe EXACTAMENTE esa llamada y la manda a la ruta real del
   backend nuevo, así los juegos y periodos no cambian su lógica:

       save_progreso            -> cola segura  POST /api/progress
       trade_* shop_* fair_*    -> POST /api/games/<familia>/<accion>
       global_* team_* qb_* bs_* lb_*
   ===================================================================== */
import { rawFetch } from "./api";
import { queueSave } from "./progressSync";
import { clearCurrentDrafts } from "./persist";

const GAME_FAMILIES = ["trade", "shop", "fair", "global", "team", "qb", "bs", "lb"];
const fake = (data) => ({ ok: true, status: 200, json: async () => data });

export async function finFetch(_url, options = {}) {
  let payload = {};
  try { payload = options.body ? JSON.parse(options.body) : {}; } catch { payload = {}; }
  const action = String(payload.action || "");

  // Guardar progreso: nunca falla. Queda en este equipo y se sube con reintentos.
  if (action === "save_progreso") {
    queueSave(null, payload.data);
    clearCurrentDrafts();                 // la actividad ya se guardó: sus borradores sobran
    return fake({ status: "success", queued: true });
  }

  const cut = action.indexOf("_");
  const family = cut > 0 ? action.slice(0, cut) : "";
  if (GAME_FAMILIES.includes(family)) {
    const { action: _a, user_key: _k, ...body } = payload;   // el usuario sale del token
    return rawFetch(`/games/${family}/${action.slice(cut + 1)}`, { method: "POST", body });
  }

  return fake({ status: "error", message: `Unknown action: ${action}` });
}
