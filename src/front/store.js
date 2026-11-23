import { mergeRows } from "./progressSync";

export const initialStore = () => {
  return {
    message: null,
    semanas: {},   // { [Semana]: fila_de_progreso }
    sync: {},      // { [Semana]: "saving" | "saved" | "offline" }
  };
};

export default function storeReducer(store, action = {}) {
  switch (action.type) {
    // MERGE: una fila nueva NUNCA borra lo que ya estaba (checklist, respuestas, puntos)
    case 'save_progreso': {
      const sem = action.payload.Semana;
      return {
        ...store,
        semanas: { ...store.semanas, [sem]: mergeRows(store.semanas[sem], action.payload) },
      };
    }

    // Lo usan todavía los Periodos
    case 'rollback_progreso': {
      const next = { ...store.semanas };
      if (action.payload.prev) next[action.payload.Semana] = action.payload.prev;
      else delete next[action.payload.Semana];
      return { ...store, semanas: next };
    }

    // Antes REEMPLAZABA todo con filas "light" (sin JSON) → ahora une
    case 'set_semanas': {
      const next = { ...store.semanas };
      Object.entries(action.payload || {}).forEach(([sem, row]) => {
        next[sem] = mergeRows(row, next[sem]);
      });
      return { ...store, semanas: next };
    }

    // Llegó la verdad del servidor: se une con lo local, y lo que ya no existe allá
    // (p. ej. el profe reinició un periodo) se quita, salvo que esté pendiente por subir.
    case 'sync_server': {
      const { rows = {}, keep = [] } = action.payload || {};
      const next = {};
      Object.entries(rows).forEach(([sem, row]) => { next[sem] = mergeRows(row, store.semanas[sem]); });
      keep.forEach((sem) => { if (!next[sem] && store.semanas[sem]) next[sem] = store.semanas[sem]; });
      return { ...store, semanas: next };
    }

    case 'reset_store':
      return { ...store, semanas: {}, sync: {} };

    case 'sync_status':
      return { ...store, sync: { ...store.sync, [action.payload.semana]: action.payload.status } };

    default:
      return store;
  }
}