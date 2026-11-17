/** CU-05, CU-06 y CU-07: captura diaria de gastos (D) y comidas fuera del hogar (D1), y control del día. */
import { useEffect, useState } from 'react';
import { api, fecha, fechaHora, nombre, pesos, type Comida, type ComidaEntrada, type Gasto, type GastoEntrada, type Jornada } from '../api';
import { Aviso, Campo, Cargando, Lista, opcional, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

const DIA_SEMANA = (f: string) => new Date(f + 'T00:00').toLocaleDateString('es-CO', { weekday: 'short' });

export default function Dias({ ctx }: { ctx: Contexto }) {
  const { jornadas } = ctx.avance;
  const hoy = jornadas.filter((j) => !j.futura).at(-1)?.dia_encuesta ?? 1;
  const [dia, setDia] = useState<number>(hoy);
  if (jornadas.length === 0) {
    return <p className="vacio">La captura no ha iniciado. El encuestador debe iniciarla para abrir las 14 jornadas.</p>;
  }
  const { avance } = ctx.avance;
  const pendientes = [
    ...jornadas.filter((j) => !j.futura && !j.completa).map((j) => `Día ${j.dia_encuesta}: falta declarar o cuadrar el total de renglones`),
    ...(avance.grupos_capitulo_c < 25 ? [`Capítulo C: ${25 - avance.grupos_capitulo_c} grupos sin registrar`] : []),
    ...(avance.hallazgos_abiertos ? [`Crítica: ${avance.hallazgos_abiertos} hallazgo(s) ABIERTO por corregir`] : []),
  ];
  return (
    <>
      {['EN_CAPTURA', 'DEVUELTO'].includes(ctx.ficha.hogar.estado) && (
        <div className={pendientes.length ? 'nota' : 'aviso aviso-ok'}>
          {pendientes.length ? <><b>Pendientes ({pendientes.length})</b><ul>{pendientes.map((p) => <li key={p}>{p}</li>)}</ul></> : 'Sin pendientes: el encuestador puede cerrar el cuadernillo.'}
        </div>
      )}
      <div className="calendario">
        {jornadas.map((j) => (
          <button key={j.dia_encuesta} className={`dia ${j.dia_encuesta === dia ? 'activo' : ''} ${j.completa ? 'completo' : ''} ${j.futura ? 'futuro' : ''}`}
            onClick={() => setDia(j.dia_encuesta)} title={j.completa ? 'Día completo' : j.futura ? 'Día futuro' : 'Pendiente de cierre'}>
            <b>{j.dia_encuesta}</b><small>{DIA_SEMANA(j.fecha)} {j.fecha.slice(8)}</small>
            <small>{j.renglones_d + j.renglones_d1} reng.</small>
          </button>
        ))}
      </div>
      <p className="leyenda"><i className="completo" /> Día completo (total declarado coincide) <i className="pendiente" /> Pendiente <i className="futuro" /> Futuro</p>
      <Dia key={dia} ctx={ctx} dia={dia} />
    </>
  );
}

type DatosDia = { jornada: Jornada; gastos: Gasto[]; comidas: Comida[] };

function Dia({ ctx, dia }: { ctx: Contexto; dia: number }) {
  const { usuario, catalogos: cat } = useSesion();
  const id = ctx.ficha.hogar.id_hogar;
  const { datos, error, recargar } = useDatos(() => api<DatosDia>(`/hogares/${id}/dias/${dia}`), [id, dia]);
  const [edicion, setEdicion] = useState<{ tipo: 'gasto' | 'comida'; orden: number | null } | null>(null);
  const cierre = useAccion();
  const [total, setTotal] = useState('');
  const [obs, setObs] = useState('');
  useEffect(() => {
    if (datos) { setTotal(String(datos.jornada.total_renglones ?? datos.gastos.length + datos.comidas.length)); setObs(datos.jornada.observaciones ?? ''); }
  }, [datos]);

  if (!datos) return <Cargando error={error} />;
  const { jornada, gastos, comidas } = datos;
  const abierta = ['EN_CAPTURA', 'DEVUELTO'].includes(ctx.ficha.hogar.estado) && !jornada.futura;
  const registra = abierta && ['INFORMANTE', 'ENCUESTADOR'].includes(usuario.rol);
  const corrige = abierta && usuario.rol === 'ENCUESTADOR';
  const listo = () => { setEdicion(null); recargar(); ctx.recargar(); };
  const autor = (r: { id_usuario_registro: number; fecha_registro: string }) =>
    `${ctx.ficha.asignaciones.find((a) => a.usuario.id_usuario === r.id_usuario_registro)?.usuario.nombre_completo ?? 'Usuario ' + r.id_usuario_registro} · ${fechaHora(r.fecha_registro)}`;

  const eliminar = (tipo: 'gastos' | 'comidas', orden: number) => {
    if (!confirm(`¿Eliminar el renglón ${orden}?`)) return;
    cierre.ejecutar(() => api(`/hogares/${id}/dias/${dia}/${tipo}/${orden}`, 'DELETE'), 'Renglón eliminado.').then((ok) => ok && listo());
  };

  return (
    <section className="panel">
      <div className="panel-cabeza">
        <div>
          <h2>Día {dia} · {fecha(jornada.fecha)}</h2>
          <p className="tenue">{jornada.completa ? `Completo: ${jornada.total_renglones} renglones declarados y registrados.` : jornada.futura ? 'Día futuro: aún no admite registros.' : 'Pendiente: falta declarar el total de renglones del día.'}</p>
        </div>
        <strong>{pesos(jornada.valor_total)}</strong>
      </div>
      {dia > 7 && <p className="nota">Desde el día 8 no se registran gastos personales del responsable del cuadernillo (tipo de gasto 2).</p>}
      <Aviso mensaje={cierre.mensaje} />

      <div className="seccion-cabeza">
        <h3>Capítulo D · Gastos diarios</h3>
        {registra && !edicion && <button onClick={() => setEdicion({ tipo: 'gasto', orden: null })}>Agregar gasto</button>}
      </div>
      {edicion?.tipo === 'gasto' && (
        <FormGasto id={id} dia={dia} orden={edicion.orden} inicial={gastos.find((g) => g.numero_orden === edicion.orden)} cancelar={() => setEdicion(null)} listo={listo} />
      )}
      <div className="tabla">
        <table>
          <thead><tr><th>N.º</th><th>Artículo o servicio</th><th>Cantidad</th><th>Forma</th><th>Lugar</th><th>Frecuencia</th><th>Tipo</th><th className="num">Valor</th>{corrige && <th />}</tr></thead>
          <tbody>
            {gastos.length === 0 && <tr><td colSpan={9} className="vacio">Sin gastos registrados este día.</td></tr>}
            {gastos.map((g) => (
              <tr key={g.numero_orden}>
                <td>{g.numero_orden}</td>
                <td>{g.descripcion}<small>{g.tipo_item === 'SERVICIO' ? 'Servicio' : 'Bien'} · {autor(g)}</small></td>
                <td>{Number(g.cantidad)} {g.tipo_item === 'BIEN' ? (g.cod_unidad === '8' ? g.otra_unidad : nombre(cat.unidad_medida, g.cod_unidad)) : ''}{g.equivalencia_g_cc ? <small>{Number(g.equivalencia_g_cc)} g/cc</small> : null}</td>
                <td>{g.cod_forma === '7' ? g.otra_forma : nombre(cat.forma_adquisicion, g.cod_forma)}</td>
                <td>{nombre(cat.lugar_compra, g.cod_lugar)}</td>
                <td>{nombre(cat.frecuencia_compra, g.cod_frecuencia)}</td>
                <td>{{ '1': 'Hogar', '2': 'Personal', NA: 'No aplica' }[g.tipo_gasto]}</td>
                <td className="num">{pesos(g.valor_pagado)}</td>
                {corrige && <td className="acciones"><button className="enlace" onClick={() => setEdicion({ tipo: 'gasto', orden: g.numero_orden })}>Corregir</button><button className="enlace peligro" onClick={() => eliminar('gastos', g.numero_orden)}>Eliminar</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="seccion-cabeza">
        <h3>Apartado D1 · Comidas preparadas fuera del hogar</h3>
        {registra && !edicion && <button onClick={() => setEdicion({ tipo: 'comida', orden: null })}>Agregar comida</button>}
      </div>
      {edicion?.tipo === 'comida' && (
        <FormComida id={id} dia={dia} orden={edicion.orden} inicial={comidas.find((c) => c.numero_orden === edicion.orden)} cancelar={() => setEdicion(null)} listo={listo} />
      )}
      <div className="tabla">
        <table>
          <thead><tr><th>N.º</th><th>Comida</th><th>Tipo de comida</th><th>Cantidad</th><th>Lugar</th><th>Domicilio</th><th>Tipo</th><th className="num">Valor</th>{corrige && <th />}</tr></thead>
          <tbody>
            {comidas.length === 0 && <tr><td colSpan={9} className="vacio">Sin comidas fuera del hogar este día.</td></tr>}
            {comidas.map((c) => (
              <tr key={c.numero_orden}>
                <td>{c.numero_orden}</td><td>{c.descripcion}<small>{autor(c)}</small></td><td>{nombre(cat.tipo_comida, c.cod_tipo_comida)}</td>
                <td>{Number(c.cantidad)}</td><td>{nombre(cat.lugar_compra, c.cod_lugar)}</td><td>{c.a_domicilio ? 'Sí' : 'No'}</td>
                <td>{c.tipo_gasto === '1' ? 'Hogar' : 'Personal'}</td><td className="num">{pesos(c.valor_pagado)}</td>
                {corrige && <td className="acciones"><button className="enlace" onClick={() => setEdicion({ tipo: 'comida', orden: c.numero_orden })}>Corregir</button><button className="enlace peligro" onClick={() => eliminar('comidas', c.numero_orden)}>Eliminar</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {registra && (
        <form className="cierre-dia" onSubmit={(e) => { e.preventDefault(); cierre.ejecutar(() => api(`/hogares/${id}/dias/${dia}/cierre`, 'POST', { total_renglones: Number(total), observaciones: opcional(obs) }), `Día ${dia} cerrado.`).then((ok) => ok && listo()); }}>
          <h3>Control del día</h3>
          <p className="tenue">Declare el total de renglones con información (D + D1). Debe coincidir con lo registrado: {gastos.length + comidas.length}.</p>
          <div className="campos">
            <Campo etiqueta="Total de renglones del día"><input type="number" min={0} value={total} onChange={(e) => setTotal(e.target.value)} required /></Campo>
            <Campo etiqueta="Observaciones"><input value={obs} maxLength={500} onChange={(e) => setObs(e.target.value)} /></Campo>
          </div>
          <button disabled={cierre.ocupado}>Cerrar día {dia}</button>
        </form>
      )}
    </section>
  );
}

const GASTO_VACIO: GastoEntrada = {
  descripcion: '', tipo_item: 'BIEN', cantidad: '', cod_unidad: null, otra_unidad: null, equivalencia_g_cc: null, cod_forma: '1',
  otra_forma: null, cod_lugar: null, valor_pagado: '', cod_frecuencia: null, tipo_gasto: '1',
};

function FormGasto({ id, dia, orden, inicial, cancelar, listo }: { id: number; dia: number; orden: number | null; inicial?: Gasto; cancelar: () => void; listo: () => void }) {
  const { catalogos: cat } = useSesion();
  const [f, setF] = useState<GastoEntrada>(inicial ? { ...GASTO_VACIO, ...pick(inicial, GASTO_VACIO) } : GASTO_VACIO);
  const { ejecutar, ocupado, mensaje } = useAccion();
  const set = <K extends keyof GastoEntrada>(k: K, v: GastoEntrada[K]) => setF((x) => ({ ...x, [k]: v }));
  const bien = f.tipo_item === 'BIEN', otraUnidad = bien && f.cod_unidad === '8', compra = f.cod_forma === '1';

  const enviar = (e: React.FormEvent) => {
    e.preventDefault();
    // Limpia los campos que la regla del cuadernillo no admite en esta combinación.
    const datos: GastoEntrada = {
      ...f, cod_unidad: bien ? f.cod_unidad : null, otra_unidad: otraUnidad ? f.otra_unidad : null,
      equivalencia_g_cc: otraUnidad ? f.equivalencia_g_cc : null, otra_forma: f.cod_forma === '7' ? f.otra_forma : null,
      cod_lugar: compra ? f.cod_lugar : null, cod_frecuencia: compra ? f.cod_frecuencia : null,
    };
    const ruta = `/hogares/${id}/dias/${dia}/gastos${orden ? '/' + orden : ''}`;
    ejecutar(() => api(ruta, orden ? 'PUT' : 'POST', datos)).then((ok) => ok && listo());
  };

  return (
    <form className="formulario" onSubmit={enviar}>
      <h4>{orden ? `Corregir renglón ${orden}` : 'Nuevo gasto del día ' + dia}</h4>
      <div className="campos">
        <Campo etiqueta="D4. Artículo o servicio" ancho><input value={f.descripcion} maxLength={180} onChange={(e) => set('descripcion', e.target.value)} required /></Campo>
        <Campo etiqueta="Clase">
          <select value={f.tipo_item} onChange={(e) => set('tipo_item', e.target.value as GastoEntrada['tipo_item'])}><option value="BIEN">Bien</option><option value="SERVICIO">Servicio</option></select>
        </Campo>
        <Campo etiqueta="D5. Cantidad"><input type="number" step="0.01" min="0.01" value={f.cantidad} onChange={(e) => set('cantidad', e.target.value)} required /></Campo>
        {bien && <Campo etiqueta="D6. Unidad de medida"><Lista items={cat.unidad_medida} valor={f.cod_unidad} cambiar={(v) => set('cod_unidad', v)} vacio="Seleccione" /></Campo>}
        {otraUnidad && <Campo etiqueta="¿Cuál unidad?"><input value={f.otra_unidad ?? ''} maxLength={40} onChange={(e) => set('otra_unidad', opcional(e.target.value))} required /></Campo>}
        {otraUnidad && <Campo etiqueta="Equivalencia en gramos o cc" ayuda="Opcional; solo para unidades no tradicionales."><input type="number" step="0.01" min="0.01" value={f.equivalencia_g_cc ?? ''} onChange={(e) => set('equivalencia_g_cc', opcional(e.target.value))} /></Campo>}
        <Campo etiqueta="D7. Forma de adquisición"><Lista items={cat.forma_adquisicion} valor={f.cod_forma} cambiar={(v) => set('cod_forma', v ?? '1')} /></Campo>
        {f.cod_forma === '7' && <Campo etiqueta="¿Cuál forma?"><input value={f.otra_forma ?? ''} maxLength={60} onChange={(e) => set('otra_forma', opcional(e.target.value))} required /></Campo>}
        {compra && <Campo etiqueta="D8. Lugar de compra"><Lista items={cat.lugar_compra} valor={f.cod_lugar} cambiar={(v) => set('cod_lugar', v)} vacio="No registra" /></Campo>}
        {compra && <Campo etiqueta="D10. Frecuencia de compra"><Lista items={cat.frecuencia_compra.filter((x) => x.codigo !== '1')} valor={f.cod_frecuencia} cambiar={(v) => set('cod_frecuencia', v)} vacio="Seleccione" /></Campo>}
        <Campo etiqueta={compra ? 'D9. Valor pagado' : 'D9. Valor estimado'}><input type="number" step="0.01" min="0.01" value={f.valor_pagado} onChange={(e) => set('valor_pagado', e.target.value)} required /></Campo>
        <Campo etiqueta="Tipo de gasto">
          <select value={f.tipo_gasto} onChange={(e) => set('tipo_gasto', e.target.value as GastoEntrada['tipo_gasto'])}>
            <option value="1">1 · Del hogar</option>{dia <= 7 && <option value="2">2 · Personal del responsable</option>}<option value="NA">No aplica</option>
          </select>
        </Campo>
      </div>
      <Aviso mensaje={mensaje} />
      <div className="botones"><button type="button" className="secundario" onClick={cancelar}>Cancelar</button><button disabled={ocupado}>Guardar</button></div>
    </form>
  );
}

const COMIDA_VACIA: ComidaEntrada = {
  descripcion: '', cod_tipo_comida: '2', cantidad: '1', cod_forma: '1', otra_forma: null, cod_lugar: null, valor_pagado: '',
  cod_frecuencia: null, tipo_gasto: '1', a_domicilio: false,
};

function FormComida({ id, dia, orden, inicial, cancelar, listo }: { id: number; dia: number; orden: number | null; inicial?: Comida; cancelar: () => void; listo: () => void }) {
  const { catalogos: cat } = useSesion();
  const [f, setF] = useState<ComidaEntrada>(inicial ? { ...COMIDA_VACIA, ...pick(inicial, COMIDA_VACIA) } : COMIDA_VACIA);
  const { ejecutar, ocupado, mensaje } = useAccion();
  const set = <K extends keyof ComidaEntrada>(k: K, v: ComidaEntrada[K]) => setF((x) => ({ ...x, [k]: v }));
  const compra = f.cod_forma === '1';
  const enviar = (e: React.FormEvent) => {
    e.preventDefault();
    const datos = { ...f, otra_forma: f.cod_forma === '7' ? f.otra_forma : null, cod_lugar: compra ? f.cod_lugar : null, cod_frecuencia: compra ? f.cod_frecuencia : null };
    ejecutar(() => api(`/hogares/${id}/dias/${dia}/comidas${orden ? '/' + orden : ''}`, orden ? 'PUT' : 'POST', datos)).then((ok) => ok && listo());
  };
  return (
    <form className="formulario" onSubmit={enviar}>
      <h4>{orden ? `Corregir comida ${orden}` : 'Nueva comida fuera del hogar'}</h4>
      <div className="campos">
        <Campo etiqueta="Descripción" ancho><input value={f.descripcion} maxLength={180} onChange={(e) => set('descripcion', e.target.value)} required /></Campo>
        <Campo etiqueta="Tipo de comida"><Lista items={cat.tipo_comida} valor={f.cod_tipo_comida} cambiar={(v) => set('cod_tipo_comida', v ?? '2')} /></Campo>
        <Campo etiqueta="Cantidad"><input type="number" step="0.01" min="0.01" value={f.cantidad} onChange={(e) => set('cantidad', e.target.value)} required /></Campo>
        <Campo etiqueta="Forma de adquisición"><Lista items={cat.forma_adquisicion} valor={f.cod_forma} cambiar={(v) => set('cod_forma', v ?? '1')} /></Campo>
        {f.cod_forma === '7' && <Campo etiqueta="¿Cuál forma?"><input value={f.otra_forma ?? ''} onChange={(e) => set('otra_forma', opcional(e.target.value))} required /></Campo>}
        {compra && <Campo etiqueta="Lugar de compra"><Lista items={cat.lugar_compra} valor={f.cod_lugar} cambiar={(v) => set('cod_lugar', v)} vacio="No registra" /></Campo>}
        {compra && <Campo etiqueta="Frecuencia"><Lista items={cat.frecuencia_compra.filter((x) => x.codigo !== '1')} valor={f.cod_frecuencia} cambiar={(v) => set('cod_frecuencia', v)} vacio="Seleccione" /></Campo>}
        <Campo etiqueta={compra ? 'Valor pagado' : 'Valor estimado'}><input type="number" step="0.01" min="0.01" value={f.valor_pagado} onChange={(e) => set('valor_pagado', e.target.value)} required /></Campo>
        <Campo etiqueta="Tipo de gasto">
          <select value={f.tipo_gasto} onChange={(e) => set('tipo_gasto', e.target.value as ComidaEntrada['tipo_gasto'])}><option value="1">1 · Del hogar</option>{dia <= 7 && <option value="2">2 · Personal del responsable</option>}</select>
        </Campo>
        <label className="casilla"><input type="checkbox" checked={f.a_domicilio} onChange={(e) => set('a_domicilio', e.target.checked)} /> Adquirida a domicilio</label>
      </div>
      <Aviso mensaje={mensaje} />
      <div className="botones"><button type="button" className="secundario" onClick={cancelar}>Cancelar</button><button disabled={ocupado}>Guardar</button></div>
    </form>
  );
}

/** Copia solo los campos de entrada (sin número de orden ni auditoría). */
function pick<T extends object>(origen: object, plantilla: T): Partial<T> {
  const r: Partial<T> = {};
  for (const k of Object.keys(plantilla) as (keyof T)[]) {
    const v = (origen as T)[k];
    r[k] = (typeof v === 'number' ? String(v) : v) as T[keyof T];
  }
  return r;
}
