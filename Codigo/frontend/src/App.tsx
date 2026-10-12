import { useEffect, useState } from "react";
import { ApiError, request, toPayload } from "./api";
import type { Context, Gasto } from "./api";
import { validateCapture } from "./validation";
import type { CaptureForm } from "./validation";

const empty = (orden = 1): CaptureForm => ({
  numero_orden: String(orden),
  descripcion: "",
  cantidad: "",
  tipo_item: "",
  unidad_id: "",
  equivalencia_g_cc: "",
  forma_id: "",
  lugar_id: "",
  frecuencia_id: "",
  valor: "",
  tipo_gasto: "",
});
const accounts = ["informante", "encuestador", "supervisor", "critico"];

export default function App() {
  const [token, setToken] = useState(""),
    [context, setContext] = useState<Context | null>(null),
    [user, setUser] = useState("informante"),
    [password, setPassword] = useState(""),
    [jornada, setJornada] = useState(6);
  const [rows, setRows] = useState<Gasto[]>([]),
    [form, setForm] = useState<CaptureForm>(empty()),
    [editing, setEditing] = useState<number | null>(null),
    [errors, setErrors] = useState<Record<string, string>>({}),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const hogar = context?.hogares[0] ?? 1;
  const selected = context?.jornadas.find((j) => j.id === jornada);
  const dayKey = `${token}/${hogar}/${jornada}`;
  const [loadedDay, setLoadedDay] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const ready = loadedDay === dayKey;
  const report = (e: unknown) => {
    if (e instanceof ApiError) {
      setErrors(e.fields);
      setNotice(
        e.status === 401
          ? "La sesión expiró. Sal y vuelve a iniciar sesión."
          : e.message,
      );
    } else
      setNotice(
        "No hay respuesta del servidor demo. Comprueba que está iniciado.",
      );
  };
  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      const result = await request<{ token: string }>(
        "/demo/login",
        "",
        "POST",
        { usuario: user, password },
      );
      const ctx = await request<Context>("/context", result.token);
      setContext(ctx);
      setToken(result.token);
      setPassword("");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  async function load() {
    if (token) {
      const data = await request<Gasto[]>(
        `/hogares/${hogar}/jornadas/${jornada}/gastos`,
        token,
      );
      setRows(data);
      return data;
    }
    return [] as Gasto[];
  }
  useEffect(() => {
    let current = true;
    if (!token) return;
    setLoadedDay(null);
    setLoading(true);
    setRows([]);
    setEditing(null);
    setForm(empty());
    setErrors({});
    request<Gasto[]>(`/hogares/${hogar}/jornadas/${jornada}/gastos`, token)
      .then((r) => {
        if (current) {
          setRows(r);
          setEditing(null);
          setForm(
            empty(r.reduce((m, g) => Math.max(m, g.numero_orden), 0) + 1),
          );
          setErrors({});
          setLoadedDay(dayKey);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (current) {
          setLoading(false);
          report(e);
        }
      });
    return () => {
      current = false;
    };
  }, [token, hogar, jornada]);
  function change(key: keyof CaptureForm, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: "" }));
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!ready) return;
    const invalid = validateCapture(form);
    setErrors(invalid);
    if (Object.keys(invalid).length) return;
    setBusy(true);
    setNotice("");
    try {
      await request(
        editing
          ? `/gastos/${editing}`
          : `/hogares/${hogar}/jornadas/${jornada}/gastos`,
        token,
        editing ? "PUT" : "POST",
        toPayload(form),
      );
      const data = await load();
      setForm(empty(data.reduce((m, g) => Math.max(m, g.numero_orden), 0) + 1));
      setEditing(null);
      setNotice("Registro guardado en memoria demo.");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  function edit(g: Gasto) {
    if (!ready || g.jornada_id !== jornada) return;
    setEditing(g.id);
    setForm({
      ...g,
      numero_orden: String(g.numero_orden),
      unidad_id: g.unidad_id === null ? "" : String(g.unidad_id),
      forma_id: String(g.forma_id),
      lugar_id: g.lugar_id === null ? "" : String(g.lugar_id),
      frecuencia_id: g.frecuencia_id === null ? "" : String(g.frecuencia_id),
      equivalencia_g_cc: g.equivalencia_g_cc ?? "",
    });
    setErrors({});
    setNotice("");
  }
  async function remove(g: Gasto) {
    if (!ready || g.jornada_id !== jornada) return;
    if (!window.confirm("¿Eliminar sólo este registro ficticio de la demo?"))
      return;
    setBusy(true);
    try {
      await request(`/gastos/${g.id}`, token, "DELETE");
      await load();
      if (editing === g.id) {
        setEditing(null);
        setForm(empty());
      }
      setNotice("Registro ficticio eliminado.");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  const field = (
    key: keyof CaptureForm,
    label: string,
    options?: Record<string, string>,
    hint?: string,
  ) => (
    <label className={key === "descripcion" ? "wide" : ""} htmlFor={key}>
      {label}
      {options ? (
        <select
          id={key}
          value={form[key] ?? ""}
          onChange={(e) => change(key, e.target.value)}
          aria-invalid={!!errors[key]}
          aria-describedby={errors[key] ? key + "-error" : undefined}
        >
          <option value="">Selecciona…</option>
          {Object.entries(options).map(([code, title]) => (
            <option value={code} key={code}>
              {code} · {title}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={key}
          value={form[key] ?? ""}
          onChange={(e) => change(key, e.target.value)}
          inputMode={
            ["cantidad", "valor", "numero_orden", "equivalencia_g_cc"].includes(
              key,
            )
              ? "decimal"
              : "text"
          }
          maxLength={key === "descripcion" ? 180 : 30}
          aria-invalid={!!errors[key]}
          aria-describedby={errors[key] ? key + "-error" : undefined}
        />
      )}{" "}
      {hint && <small>{hint}</small>}
      {errors[key] && (
        <span id={key + "-error"} className="field-error">
          {errors[key]}
        </span>
      )}
    </label>
  );
  return (
    <>
      <header>
        <div className="brand">
          <span className="brand-mark">E</span>
          <div>
            <strong>ENPH</strong>
            <span>Cuadernillo 2 urbano</span>
          </div>
        </div>
        <span className="demo-tag">DEMO LOCAL · SIN ORACLE</span>
      </header>
      {!context ? (
        <main className="login">
          <div className="eyebrow">PRIMERA VERTICAL · CU-05</div>
          <h1>
            Gastos del hogar,
            <br />
            día a día.
          </h1>
          <p>
            Captura de bienes y servicios con las reglas conciliadas del
            cuadernillo.
          </p>
          <form onSubmit={signIn}>
            <label htmlFor="usuario">
              Cuenta ficticia
              <select
                id="usuario"
                value={user}
                onChange={(e) => setUser(e.target.value)}
              >
                {accounts.map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label htmlFor="password">
              Contraseña demo
              <input
                id="password"
                type="password"
                autoComplete="off"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <button disabled={busy}>Entrar a la demo</button>
            <small>
              Las cuatro cuentas usan <code>enph-demo</code>. El servidor asigna
              el perfil.
            </small>
          </form>
          {notice && (
            <p role="alert" className="notice">
              {notice}
            </p>
          )}
          <p className="disclaimer">
            Sólo datos ficticios. La información se pierde al reiniciar el
            servidor. No es una aplicación de producción ni CRUD Oracle.
          </p>
        </main>
      ) : (
        <div className="shell">
          <aside>
            <span className="eyebrow">PERFIL ACTIVO</span>
            <h2>{context.rol}</h2>
            <p>Hogar ficticio H001</p>
            <nav aria-label="Módulos">
              <span className="nav-active">D · Gastos diarios</span>
              <span>
                D1 · Comidas <small>Pendiente</small>
              </span>
              <span>
                Seguimiento <small>Pendiente</small>
              </span>
              <span>
                Crítica <small>Pendiente</small>
              </span>
            </nav>
            <div className="aside-bottom">
              <p>
                Modo de demostración
                <br />
                <small>Sin persistencia Oracle</small>
              </p>
              <button
                className="secondary"
                onClick={() => {
                  setToken("");
                  setContext(null);
                  setRows([]);
                  setNotice("");
                }}
              >
                Salir
              </button>
            </div>
          </aside>
          <main className="workspace">
            <div className="heading">
              <div>
                <span className="eyebrow">CAPÍTULO D</span>
                <h1>Gastos diarios</h1>
                <p>Registra lo adquirido durante el día seleccionado.</p>
              </div>
              <div className="progress">
                <strong>{rows.length}</strong>
                <span>registros del día</span>
              </div>
            </div>
            <section className="day-strip" aria-label="Día de encuesta">
              <div>
                <strong>Día {selected?.dia} de 14</strong>
                <span>{selected?.fecha} · Hogar H001</span>
              </div>
              <div className="days">
                {context.jornadas
                  .filter((j) => j.hogar_id === hogar)
                  .map((j) => (
                    <button
                      key={j.id}
                      className={j.id === jornada ? "selected" : ""}
                      aria-pressed={j.id === jornada}
                      aria-label={`Día ${j.dia}`}
                      disabled={busy}
                      onClick={() => {
                        setJornada(j.id);
                        setNotice("");
                      }}
                    >
                      {j.dia}
                    </button>
                  ))}
              </div>
            </section>
            {notice && (
              <p className="notice" role="status">
                {notice}
              </p>
            )}
            {!context.can_capture && (
              <p className="notice">
                Consulta de captura en esta vertical. Tu perfil no puede crear,
                editar ni borrar gastos D.
              </p>
            )}
            <div className="content-grid">
              <section className="records">
                <div className="section-heading">
                  <h2>Registros del día</h2>
                  <span>{rows.length} total</span>
                </div>
                {!ready ? (
                  <div className="empty" role="status">
                    <h3>{loading ? "Cargando jornada…" : "Jornada no disponible"}</h3>
                    <p>No se habilitan escrituras hasta cargar el día seleccionado.</p>
                  </div>
                ) : !rows.length ? (
                  <div className="empty">
                    <span className="empty-icon">＋</span>
                    <h3>Un día por registrar</h3>
                    <p>
                      {context.can_capture
                        ? "Añade el primer artículo o servicio en el formulario."
                        : "No hay registros ficticios en este día."}
                    </p>
                  </div>
                ) : (
                  <ul className="record-list">
                    {rows.map((g) => (
                      <li key={g.id}>
                        <div className="record-top">
                          <span className="item-badge">
                            {g.tipo_item === "BIEN" ? "Bien" : "Servicio"}
                          </span>
                          <strong>${g.valor}</strong>
                        </div>
                        <h3>{g.descripcion}</h3>
                        <p>
                          #{g.numero_orden} · Cantidad {g.cantidad} ·{" "}
                          {g.unidad_id
                            ? context.unidades[g.unidad_id]
                            : "Sin unidad"}
                        </p>
                        <p>
                          Tipo de gasto:{" "}
                          {g.tipo_gasto === "NA"
                            ? "NA expreso"
                            : g.tipo_gasto === "1"
                              ? "1 · Hogar"
                              : "2 · Personal"}
                        </p>
                        {context.can_capture && (
                          <div className="record-actions">
                            <button
                              className="text-button"
                              disabled={busy}
                              onClick={() => edit(g)}
                            >
                              Editar
                            </button>
                            <button
                              className="text-button danger"
                              disabled={busy}
                              onClick={() => remove(g)}
                            >
                              Eliminar
                            </button>
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                <p className="record-note">
                  NA es una selección expresa, no una respuesta ausente. No se
                  asigna automáticamente a los regalos.
                </p>
              </section>
              <section className="capture">
                <div className="section-heading">
                  <h2>{editing ? "Editar registro" : "Nuevo registro"}</h2>
                  <span>CU-05</span>
                </div>
                <form onSubmit={save}>
                  <fieldset disabled={busy || !context.can_capture || !ready}>
                    <div className="fields">
                      {field("descripcion", "Artículo o servicio")}
                      {field("numero_orden", "Número de orden")}
                      {field("tipo_item", "Clasificación", {
                        BIEN: "Bien",
                        SERVICIO: "Servicio",
                      })}
                      {field("cantidad", "Cantidad adquirida")}
                      {field(
                        "unidad_id",
                        "Unidad de medida",
                        context.unidades,
                        "Obligatoria para bienes; opcional para servicios.",
                      )}
                      {field(
                        "equivalencia_g_cc",
                        "Equivalencia g / cc",
                        undefined,
                        "Opcional cuando corresponde.",
                      )}
                      {field("valor", "Valor pagado o estimado ($)")}
                      {field(
                        "forma_id",
                        "Forma de adquisición",
                        context.formas,
                      )}
                      {field("tipo_gasto", "Tipo de gasto", {
                        "1": "Gasto del hogar",
                        "2": "Gasto personal",
                        NA: "No aplica, expreso",
                      })}
                      {field(
                        "lugar_id",
                        "Lugar de compra",
                        context.lugares,
                        "Opcional cuando no aplica.",
                      )}
                      {field(
                        "frecuencia_id",
                        "Frecuencia",
                        context.frecuencias,
                        "Opcional cuando no aplica.",
                      )}
                    </div>
                    <div className="form-actions">
                      {editing && (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => {
                            setEditing(null);
                            setForm(empty());
                            setErrors({});
                          }}
                        >
                          Cancelar edición
                        </button>
                      )}
                      <button type="submit">
                        {busy
                          ? "Guardando…"
                          : editing
                            ? "Guardar cambios"
                            : "Guardar registro"}
                      </button>
                    </div>
                  </fieldset>
                </form>
              </section>
            </div>
            <footer>
              Inicio del segundo avance · CU-05 en memoria · Otros CU,
              autenticación real y Oracle pendientes.
            </footer>
          </main>
        </div>
      )}
    </>
  );
}
