import React, { useEffect, useState } from "react";
import {
  Building2, Plus, RefreshCw, AlertTriangle, Check, Pencil, Users, Pause, Play, Trash2,
  Upload, KeyRound, UserPlus, X, ShieldCheck, Lock,
} from "lucide-react";
import { apiOk } from "../api";
import { GRADES } from "../courses";
import { AdminPanel } from "./AdminPanel";
import "../Styles/admin.css";
import "../Styles/platform.css";

/* =====================================================================
   SUPER ADMIN · la vista del dueño de la plataforma
   1) Crea un colegio con sus cupos por grado y su usuario admin.
   2) Ese admin entra y crea a sus estudiantes (hasta el cupo de cada grado).
   3) Los estudiantes entran y ven el curso de su grado; el diploma sale
      con el nombre, escudo y firma de SU colegio.
   ===================================================================== */

const emptyForm = () => ({
  id: null, name: "", city: "", signer_name: "", signer_role: "", logo: "", lock_periods: false,
  quotas: Object.fromEntries(GRADES.map((g) => [g, 0])),
  admin: { name: "", key: "", password: "" },
});

// Reduce el escudo a máx. 360 px y lo convierte a texto (data URL) para guardarlo en la base de datos
function fileToLogo(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const scale = Math.min(1, 360 / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/png"));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("No se pudo leer la imagen.")); };
    img.src = url;
  });
}

function SchoolForm({ initial, onCancel, onSaved }) {
  const [f, setF] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isNew = !f.id;
  const set = (patch) => setF((prev) => ({ ...prev, ...patch }));
  const totalSeats = GRADES.reduce((a, g) => a + (parseInt(f.quotas[g], 10) || 0), 0);

  const pickLogo = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try { set({ logo: await fileToLogo(file) }); } catch (err) { setError(err.message); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const body = {
        name: f.name, city: f.city, signer_name: f.signer_name, signer_role: f.signer_role,
        logo: f.logo, lock_periods: f.lock_periods,
        quotas: Object.fromEntries(GRADES.map((g) => [g, parseInt(f.quotas[g], 10) || 0])),
      };
      if (isNew) body.admin = f.admin;
      const res = await apiOk(isNew ? "/super/schools" : `/super/schools/${f.id}`, { method: isNew ? "POST" : "PUT", body });
      onSaved(res.school, isNew);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  return (
    <form className="adm-card sup-form" onSubmit={submit}>
      <div className="adm-resp-head">
        <h3><Building2 size={18} strokeWidth={2.3} /> {isNew ? "Nuevo colegio" : `Editar ${initial.name}`}</h3>
        <button type="button" className="adm-btn" onClick={onCancel}><X size={16} strokeWidth={2.4} /> Cancelar</button>
      </div>

      <div className="sup-grid">
        <label className="adm-field wide"><span>Nombre del colegio (así sale en el diploma)</span>
          <input value={f.name} onChange={(e) => set({ name: e.target.value })} placeholder="Instituto Pedagógico CREAR" required />
        </label>
        <label className="adm-field"><span>Ciudad</span>
          <input value={f.city} onChange={(e) => set({ city: e.target.value })} placeholder="Bogotá" />
        </label>
        <label className="adm-field"><span>Quién firma el diploma</span>
          <input value={f.signer_name} onChange={(e) => set({ signer_name: e.target.value })} placeholder="Nombre y apellido" />
        </label>
        <label className="adm-field"><span>Cargo de quien firma</span>
          <input value={f.signer_role} onChange={(e) => set({ signer_role: e.target.value })} placeholder="Rector(a)" />
        </label>
        <div className="adm-field sup-logo">
          <span>Escudo (opcional)</span>
          <div>
            {f.logo ? <img src={f.logo} alt="Escudo" /> : <i><Building2 size={22} strokeWidth={2} /></i>}
            <label className="adm-btn"><Upload size={15} strokeWidth={2.4} /> Subir imagen<input type="file" accept="image/*" onChange={pickLogo} hidden /></label>
            {f.logo && <button type="button" className="adm-link danger" onClick={() => set({ logo: "" })}>Quitar</button>}
          </div>
        </div>
      </div>

      <h4 className="sup-sub">Cupos por grado <em>{totalSeats} estudiantes en total</em></h4>
      <div className="sup-quotas">
        {GRADES.map((g) => (
          <label key={g}><span>{g}°</span>
            <input type="number" min="0" max="5000" inputMode="numeric" value={f.quotas[g]}
              onChange={(e) => set({ quotas: { ...f.quotas, [g]: e.target.value } })} />
          </label>
        ))}
      </div>
      <label className="sup-check">
        <input type="checkbox" checked={f.lock_periods} onChange={(e) => set({ lock_periods: e.target.checked })} />
        <span><Lock size={14} strokeWidth={2.3} /> Periodos en orden: el estudiante debe terminar un periodo para abrir el siguiente.</span>
      </label>

      {isNew && (
        <>
          <h4 className="sup-sub">Usuario admin del colegio <em>él crea a los estudiantes</em></h4>
          <div className="sup-grid three">
            <label className="adm-field"><span>Nombre</span>
              <input value={f.admin.name} onChange={(e) => set({ admin: { ...f.admin, name: e.target.value } })} placeholder="Coordinación académica" required />
            </label>
            <label className="adm-field"><span>Usuario</span>
              <input value={f.admin.key} onChange={(e) => set({ admin: { ...f.admin, key: e.target.value.trim() } })} placeholder="admin.crear" required />
            </label>
            <label className="adm-field"><span>Clave (4+ caracteres)</span>
              <input value={f.admin.password} onChange={(e) => set({ admin: { ...f.admin, password: e.target.value } })} placeholder="••••••" required minLength={4} />
            </label>
          </div>
        </>
      )}

      {error && <div className="adm-error"><AlertTriangle size={18} strokeWidth={2.4} /> {error}</div>}
      <div className="sup-submit">
        <button className="adm-btn primary" disabled={busy}>{busy ? "Guardando…" : isNew ? "Crear colegio" : "Guardar cambios"}</button>
      </div>
    </form>
  );
}

function AdminsBox({ school, onChange, setError }) {
  const [add, setAdd] = useState(null);
  const run = async (fn) => { setError(""); try { const res = await fn(); onChange(res.school); } catch (e) { setError(e.message); } };
  const resetPw = (a) => {
    const pw = window.prompt(`Clave nueva para ${a.name} (${a.key}):`);
    if (pw) run(() => apiOk(`/super/users/${a.id}`, { method: "PUT", body: { password: pw } }));
  };
  return (
    <div className="sup-admins">
      {school.admins.map((a) => (
        <div key={a.id} className="sup-admin">
          <span className="sup-admin-who"><ShieldCheck size={15} strokeWidth={2.3} /> <b>{a.name}</b> · {a.key}{!a.active && " · pausado"}</span>
          <button className="adm-link" onClick={() => resetPw(a)}><KeyRound size={13} strokeWidth={2.3} /> Cambiar clave</button>
          <button className="adm-link danger" onClick={() => window.confirm(`¿Borrar al admin ${a.key}?`) && run(() => apiOk(`/super/users/${a.id}`, { method: "DELETE" }))}>Borrar</button>
        </div>
      ))}
      {!school.admins.length && <span className="adm-muted">Este colegio no tiene admin todavía.</span>}
      {add ? (
        <div className="sup-admin-new">
          <input placeholder="Nombre" value={add.name} onChange={(e) => setAdd({ ...add, name: e.target.value })} />
          <input placeholder="Usuario" value={add.key} onChange={(e) => setAdd({ ...add, key: e.target.value.trim() })} />
          <input placeholder="Clave" value={add.password} onChange={(e) => setAdd({ ...add, password: e.target.value })} />
          <button className="adm-btn primary" onClick={() => run(() => apiOk(`/super/schools/${school.id}/admins`, { method: "POST", body: add })).then(() => setAdd(null))}>Agregar</button>
          <button className="adm-link" onClick={() => setAdd(null)}>Cancelar</button>
        </div>
      ) : (
        <button className="adm-link" onClick={() => setAdd({ name: "", key: "", password: "" })}><UserPlus size={13} strokeWidth={2.3} /> Agregar otro admin</button>
      )}
    </div>
  );
}

export const SuperAdmin = () => {
  const [schools, setSchools] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState(null);
  const [inside, setInside] = useState(null);     // colegio abierto con el panel Admin

  const load = async () => {
    setLoading(true); setError("");
    try { setSchools((await apiOk("/super/schools")).schools); }
    catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const replace = (school) => setSchools((list) => (list || []).map((s) => (s.id === school.id ? school : s)));
  const toggle = async (s) => {
    setError("");
    try { replace((await apiOk(`/super/schools/${s.id}`, { method: "PUT", body: { is_active: !s.is_active } })).school); }
    catch (e) { setError(e.message); }
  };
  const remove = async (s) => {
    if (!window.confirm(`¿Borrar el colegio ${s.name}? Solo se puede si no tiene estudiantes.`)) return;
    setError("");
    try { await apiOk(`/super/schools/${s.id}`, { method: "DELETE" }); setSchools((list) => list.filter((x) => x.id !== s.id)); }
    catch (e) { setError(e.message); }
  };

  if (inside) return <AdminPanel schoolId={inside.id} schoolName={inside.name} onExit={() => { setInside(null); load(); }} />;

  const totals = (schools || []).reduce((a, s) => {
    GRADES.forEach((g) => { a.used += s.used[g] || 0; a.seats += s.quotas[g] || 0; });
    return a;
  }, { used: 0, seats: 0 });

  return (
    <div className="adm">
      <header className="adm-head">
        <div>
          <h1>Colegios</h1>
          <p>{schools ? `${schools.length} ${schools.length === 1 ? "colegio" : "colegios"} · ${totals.used} estudiantes creados de ${totals.seats} cupos` : "Cargando…"}</p>
        </div>
        <div className="adm-actions">
          <button className="adm-btn" onClick={load} disabled={loading}><RefreshCw size={16} strokeWidth={2.4} className={loading ? "spin-icon" : ""} /> Refrescar</button>
          <button className="adm-btn primary" onClick={() => { setNotice(""); setForm(emptyForm()); }}><Plus size={16} strokeWidth={2.6} /> Nuevo colegio</button>
        </div>
      </header>

      {notice && <div className="adm-notice"><Check size={18} strokeWidth={2.6} /> {notice}</div>}
      {error && <div className="adm-error"><AlertTriangle size={18} strokeWidth={2.4} /> {error}</div>}

      {form && (
        <SchoolForm initial={form} onCancel={() => setForm(null)}
          onSaved={(school, isNew) => {
            setForm(null);
            if (isNew) { setSchools((list) => [...(list || []), school]); setNotice(`Colegio creado. Entrégale al admin su usuario "${school.admins[0]?.key}" y su clave: desde su panel crea a los estudiantes.`); }
            else { replace(school); setNotice("Cambios guardados."); }
          }} />
      )}

      {schools && !schools.length && !form && (
        <div className="adm-empty"><Building2 size={28} strokeWidth={2} /> Aún no hay colegios. Crea el primero con "Nuevo colegio".</div>
      )}

      <div className="sup-list">
        {(schools || []).map((s) => {
          const usedTotal = GRADES.reduce((a, g) => a + (s.used[g] || 0), 0);
          const seatTotal = GRADES.reduce((a, g) => a + (s.quotas[g] || 0), 0);
          return (
            <article key={s.id} className={`adm-card sup-school ${s.is_active ? "" : "off"}`}>
              <div className="sup-school-head">
                {s.logo ? <img src={s.logo} alt="" /> : <i><Building2 size={22} strokeWidth={2} /></i>}
                <div>
                  <h3>{s.name}</h3>
                  <p>{[s.city, `${usedTotal}/${seatTotal} cupos usados`, `avance promedio ${s.avg_progress}%`].filter(Boolean).join(" · ")}</p>
                </div>
                <span className={`adm-status ${s.is_active ? "finished" : "never"}`}>{s.is_active ? "Activo" : "Pausado"}</span>
              </div>

              <div className="sup-seats">
                {GRADES.map((g) => {
                  const q = s.quotas[g] || 0, u = s.used[g] || 0;
                  return (
                    <div key={g} className={!q ? "none" : ""}>
                      <b>{g}°</b>
                      <i><u style={{ width: `${q ? Math.min(100, (u / q) * 100) : 0}%` }} /></i>
                      <span>{u}/{q}</span>
                    </div>
                  );
                })}
              </div>

              <AdminsBox school={s} onChange={replace} setError={setError} />

              <div className="adm-actions">
                <button className="adm-btn primary" onClick={() => setInside(s)}><Users size={15} strokeWidth={2.4} /> Ver estudiantes y progreso</button>
                <button className="adm-btn" onClick={() => { setNotice(""); setForm({ ...emptyForm(), ...s, quotas: { ...s.quotas } }); window.scrollTo(0, 0); }}><Pencil size={15} strokeWidth={2.4} /> Editar y cupos</button>
                <button className="adm-btn" onClick={() => toggle(s)}>{s.is_active ? <><Pause size={15} strokeWidth={2.4} /> Pausar</> : <><Play size={15} strokeWidth={2.4} /> Reactivar</>}</button>
                <button className="adm-btn danger" onClick={() => remove(s)}><Trash2 size={15} strokeWidth={2.4} /> Borrar</button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
};
