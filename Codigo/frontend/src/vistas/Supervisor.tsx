/** CU-11 (revisar caso) y CU-09 (aprobar o devolver) del supervisor. */
import { useState } from 'react';
import { api, pesos, type RevisionCaso } from '../api';
import { Aviso, Cargando, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

export default function Supervisor({ ctx }: { ctx: Contexto }) {
  const { usuario } = useSesion();
  const id = ctx.ficha.hogar.id_hogar;
  const { datos, error, recargar } = useDatos(() => api<RevisionCaso>(`/hogares/${id}/revision-caso`), [id, ctx.ficha.hogar.estado]);
  const [observacion, setObservacion] = useState('');
  const { ejecutar, ocupado, mensaje } = useAccion();
  if (!datos) return <Cargando error={error} />;
  const { avance } = datos;
  const decidir = (decision: 'APROBADO' | 'DEVUELTO') =>
    ejecutar(() => api(`/hogares/${id}/decision`, 'POST', { decision, observacion: observacion.trim() || null }),
      decision === 'APROBADO' ? 'Caso aprobado.' : 'Caso devuelto al encuestador.').then((ok) => ok && (recargar(), ctx.recargar()));
  const asignado = ctx.ficha.asignaciones.some((a) => a.usuario.id_usuario === usuario.id_usuario && a.estado === 'VIGENTE');
  return (
    <section className="panel">
      <h2>Revisión del caso</h2>
      <dl className="ficha">
        <div><dt>Días completos</dt><dd>{avance.dias_completos}/14</dd></div>
        <div><dt>Renglones D / D1</dt><dd>{avance.renglones_d} / {avance.renglones_d1}</dd></div>
        <div><dt>Grupos del capítulo C</dt><dd>{avance.grupos_capitulo_c}/25</dd></div>
        <div><dt>Valor total registrado</dt><dd>{pesos(avance.valor_total)}</dd></div>
        <div><dt>Revisiones de crítica</dt><dd>{datos.revisiones.length}</dd></div>
      </dl>
      <h3>Controles para aprobar</h3>
      <ul className="controles">{datos.verificaciones.map((v) => <li key={v.control} className={v.cumple ? 'cumple' : 'falta'}>{v.control}</li>)}</ul>
      {ctx.ficha.hogar.estado === 'CERRADO' ? (
        <div className="formulario">
          <p className="tenue">Aprobar exige cero hallazgos ABIERTO y ninguna crítica en curso. Devolver exige el motivo y reabre la captura para el encuestador.</p>
          <input placeholder="Observación (obligatoria para devolver)" value={observacion} maxLength={500} onChange={(e) => setObservacion(e.target.value)} />
          <div className="botones">
            <button className="secundario" disabled={ocupado || !observacion.trim()} onClick={() => decidir('DEVUELTO')}>Devolver</button>
            <button disabled={ocupado || !datos.puede_aprobar} onClick={() => decidir('APROBADO')}>Aprobar</button>
          </div>
          {!asignado && <p className="tenue">Para decidir debe estar asignado al hogar (pestaña Identificación).</p>}
        </div>
      ) : <p className="vacio">El caso está {ctx.ficha.hogar.estado.replace('_', ' ').toLowerCase()}: solo se decide sobre un caso cerrado.</p>}
      <Aviso mensaje={mensaje} />
    </section>
  );
}
