/** CU-03. Control de visitas (capítulo B). */
import { useState } from 'react';
import { api, fechaHora, nombre, type Visita, type VisitaEntrada } from '../api';
import { Aviso, Campo, Cargando, Lista, opcional, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

const VACIA: VisitaEntrada = { fecha_hora_inicio: '', fecha_hora_fin: null, cod_resultado: 'EI', pendientes: null, proxima_visita: null };
const local = (v: string | null) => (v ? v.slice(0, 16) : '');
/** Duración derivada de la visita (inicio y fin). */
const duracion = (v: Visita) => {
  if (!v.fecha_hora_fin) return '—';
  const min = Math.round((new Date(v.fecha_hora_fin).getTime() - new Date(v.fecha_hora_inicio).getTime()) / 60000);
  return min >= 60 ? `${Math.floor(min / 60)} h ${min % 60} min` : `${min} min`;
};

export default function Visitas({ ctx }: { ctx: Contexto }) {
  const { usuario, catalogos: cat } = useSesion();
  const id = ctx.ficha.hogar.id_hogar;
  const { datos, error, recargar } = useDatos(() => api<Visita[]>(`/hogares/${id}/visitas`), [id]);
  const [edicion, setEdicion] = useState<number | 'nueva' | null>(null);
  if (!datos) return <Cargando error={error} />;
  const editable = usuario.rol === 'ENCUESTADOR' && ctx.ficha.hogar.estado !== 'APROBADO';
  const actual = typeof edicion === 'number' ? datos.find((v) => v.numero_visita === edicion) : undefined;
  return (
    <section className="panel">
      <div className="seccion-cabeza"><h2>Capítulo B · Control de visitas</h2>{editable && !edicion && <button onClick={() => setEdicion('nueva')}>Registrar visita</button>}</div>
      {edicion && <FormVisita id={id} numero={actual?.numero_visita} inicial={actual ?? VACIA} cancelar={() => setEdicion(null)} listo={() => { setEdicion(null); recargar(); }} />}
      <div className="tabla">
        <table>
          <thead><tr><th>N.º</th><th>Inicio</th><th>Fin</th><th>Duración</th><th>Resultado</th><th>Pendientes</th><th>Próxima visita</th>{editable && <th />}</tr></thead>
          <tbody>
            {datos.length === 0 && <tr><td colSpan={8} className="vacio">Sin visitas registradas.</td></tr>}
            {datos.map((v) => (
              <tr key={v.numero_visita}>
                <td>{v.numero_visita}</td><td>{fechaHora(v.fecha_hora_inicio)}</td><td>{fechaHora(v.fecha_hora_fin)}</td><td>{duracion(v)}</td>
                <td>{nombre(cat.resultado_entrevista, v.cod_resultado)}</td><td>{v.pendientes ?? '—'}</td><td>{fechaHora(v.proxima_visita)}</td>
                {editable && <td className="acciones"><button className="enlace" onClick={() => setEdicion(v.numero_visita)}>Editar</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FormVisita({ id, numero, inicial, cancelar, listo }: { id: number; numero?: number; inicial: VisitaEntrada; cancelar: () => void; listo: () => void }) {
  const { catalogos: cat } = useSesion();
  const [f, setF] = useState<VisitaEntrada>({ ...inicial, fecha_hora_inicio: local(inicial.fecha_hora_inicio), fecha_hora_fin: local(inicial.fecha_hora_fin) || null, proxima_visita: local(inicial.proxima_visita) || null, pendientes: inicial.pendientes });
  const { ejecutar, ocupado, mensaje } = useAccion();
  const set = <K extends keyof VisitaEntrada>(k: K, v: VisitaEntrada[K]) => setF((x) => ({ ...x, [k]: v }));
  return (
    <form className="formulario" onSubmit={(e) => { e.preventDefault(); ejecutar(() => api(`/hogares/${id}/visitas${numero ? '/' + numero : ''}`, numero ? 'PUT' : 'POST', f)).then((ok) => ok && listo()); }}>
      <h4>{numero ? `Visita ${numero}` : 'Nueva visita'}</h4>
      <div className="campos">
        <Campo etiqueta="Fecha y hora de inicio"><input type="datetime-local" value={f.fecha_hora_inicio} onChange={(e) => set('fecha_hora_inicio', e.target.value)} required /></Campo>
        <Campo etiqueta="Fecha y hora de fin"><input type="datetime-local" value={f.fecha_hora_fin ?? ''} onChange={(e) => set('fecha_hora_fin', opcional(e.target.value))} /></Campo>
        <Campo etiqueta="Resultado"><Lista items={cat.resultado_entrevista} valor={f.cod_resultado} cambiar={(v) => set('cod_resultado', v ?? 'EI')} /></Campo>
        <Campo etiqueta="Próxima visita"><input type="datetime-local" value={f.proxima_visita ?? ''} onChange={(e) => set('proxima_visita', opcional(e.target.value))} /></Campo>
        <Campo etiqueta="Pendientes" ancho><input value={f.pendientes ?? ''} maxLength={300} onChange={(e) => set('pendientes', opcional(e.target.value))} /></Campo>
      </div>
      <Aviso mensaje={mensaje} />
      <div className="botones"><button type="button" className="secundario" onClick={cancelar}>Cancelar</button><button disabled={ocupado}>Guardar</button></div>
    </form>
  );
}
