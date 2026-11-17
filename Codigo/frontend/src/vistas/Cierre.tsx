/** CU-08. Cierre del cuadernillo (preguntas D2) por el encuestador. */
import { useState } from 'react';
import { api, fechaHora, nombre, type Cierre as CierreT, type CierreEntrada } from '../api';
import { Aviso, Campo, Cargando, Lista, opcional, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

export default function Cierre({ ctx }: { ctx: Contexto }) {
  const { usuario, catalogos: cat } = useSesion();
  const { hogar } = ctx.ficha;
  const { avance } = ctx.avance;
  const { datos: cierre, error, recargar } = useDatos(() => api<CierreT | null>(`/hogares/${hogar.id_hogar}/cierre`), [hogar.id_hogar, hogar.estado]);
  if (cierre === null && error) return <Cargando error={error} />;
  const puedeCerrar = usuario.rol === 'ENCUESTADOR' && ['EN_CAPTURA', 'DEVUELTO'].includes(hogar.estado);
  const requisitos = [
    { texto: `14 jornadas completas (${avance.dias_completos}/14)`, ok: avance.dias_completos === 14 },
    { texto: `25 grupos del capítulo C (${avance.grupos_capitulo_c}/25)`, ok: avance.grupos_capitulo_c === 25 },
  ];
  return (
    <section className="panel">
      <h2>Cierre del cuadernillo (D2)</h2>
      {cierre && (
        <dl className="ficha">
          <div><dt>Cerrado</dt><dd>{fechaHora(cierre.fecha_cierre)}</dd></div>
          <div><dt>D2-1. Gastos por evento especial</dt><dd>{cierre.gasto_evento_especial ? 'Sí' : 'No'}</dd></div>
          <div><dt>D2-2. Principal forma de pago</dt><dd>{cierre.cod_forma_pago === '6' ? cierre.otra_forma_pago : nombre(cat.forma_pago, cierre.cod_forma_pago)}</dd></div>
          <div><dt>Observaciones</dt><dd>{cierre.observaciones ?? '—'}</dd></div>
          <div><dt>Revisión del supervisor</dt><dd>{cierre.estado_revision}{cierre.fecha_revision ? ` · ${fechaHora(cierre.fecha_revision)}` : ''}</dd></div>
          {cierre.observacion_supervisor && <div><dt>Motivo de la devolución</dt><dd>{cierre.observacion_supervisor}</dd></div>}
        </dl>
      )}
      {!cierre && !puedeCerrar && <p className="vacio">El cuadernillo aún no se ha cerrado.</p>}
      {puedeCerrar && (
        <>
          <h3>Requisitos para cerrar</h3>
          <ul className="controles">{requisitos.map((r) => <li key={r.texto} className={r.ok ? 'cumple' : 'falta'}>{r.texto}</li>)}</ul>
          <FormCierre id={hogar.id_hogar} inicial={cierre} listo={() => { recargar(); ctx.recargar(); }} />
        </>
      )}
    </section>
  );
}

function FormCierre({ id, inicial, listo }: { id: number; inicial: CierreT | null; listo: () => void }) {
  const { catalogos: cat } = useSesion();
  const [f, setF] = useState<CierreEntrada>({
    gasto_evento_especial: inicial?.gasto_evento_especial ?? false, cod_forma_pago: inicial?.cod_forma_pago ?? '3',
    otra_forma_pago: inicial?.otra_forma_pago ?? null, observaciones: null,
  });
  const { ejecutar, ocupado, mensaje } = useAccion();
  return (
    <form className="formulario" onSubmit={(e) => { e.preventDefault(); ejecutar(() => api(`/hogares/${id}/cierre`, 'POST', { ...f, otra_forma_pago: f.cod_forma_pago === '6' ? f.otra_forma_pago : null }), 'Cuadernillo cerrado: queda disponible para crítica y revisión del supervisor.').then((ok) => ok && listo()); }}>
      <div className="campos">
        <Campo etiqueta="D2-1. ¿Hubo gastos por fiestas, reuniones u otro evento especial?">
          <select value={f.gasto_evento_especial ? 'S' : 'N'} onChange={(e) => setF({ ...f, gasto_evento_especial: e.target.value === 'S' })}><option value="N">No</option><option value="S">Sí</option></select>
        </Campo>
        <Campo etiqueta="D2-2. Principal forma de pago"><Lista items={cat.forma_pago} valor={f.cod_forma_pago} cambiar={(v) => setF({ ...f, cod_forma_pago: v ?? '3' })} /></Campo>
        {f.cod_forma_pago === '6' && <Campo etiqueta="¿Cuál forma de pago?"><input value={f.otra_forma_pago ?? ''} maxLength={80} onChange={(e) => setF({ ...f, otra_forma_pago: opcional(e.target.value) })} required /></Campo>}
        <Campo etiqueta="Observaciones" ancho><input value={f.observaciones ?? ''} maxLength={500} onChange={(e) => setF({ ...f, observaciones: opcional(e.target.value) })} /></Campo>
      </div>
      <Aviso mensaje={mensaje} />
      <div className="botones"><button disabled={ocupado}>Cerrar cuadernillo</button></div>
    </form>
  );
}
