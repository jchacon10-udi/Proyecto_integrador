/** Ficha del hogar: pestañas por capítulo según el rol del usuario. */
import { useState } from 'react';
import { api, fecha, type Avance, type Hogar, type Jornada, type Usuario } from '../api';
import { Aviso, Cargando, Estado, useAccion, useDatos, useSesion } from '../componentes';
import CapituloC from './CapituloC';
import Cierre from './Cierre';
import Critica from './Critica';
import Dias from './Dias';
import Identificacion from './Identificacion';
import Supervisor from './Supervisor';
import Visitas from './Visitas';

export type FichaHogar = { hogar: Hogar; asignaciones: { usuario: Usuario; estado: string }[] };
export type Contexto = { ficha: FichaHogar; avance: { avance: Avance; jornadas: Jornada[] }; recargar: () => void };

const PESTANAS = [
  ['dias', 'Días 1 a 14 (D y D1)'], ['a', 'Identificación (A)'], ['b', 'Visitas (B)'], ['c', 'Características (C)'],
  ['cierre', 'Cierre (D2)'], ['critica', 'Crítica'], ['supervisor', 'Revisión del caso'],
] as const;
type Pestana = (typeof PESTANAS)[number][0];

export default function HogarVista({ id, volver }: { id: number; volver: () => void }) {
  const { usuario } = useSesion();
  const [pestana, setPestana] = useState<Pestana>('dias');
  const ficha = useDatos(() => api<FichaHogar>(`/hogares/${id}`), [id]);
  const avance = useDatos(() => api<Contexto['avance']>(`/hogares/${id}/avance`), [id]);
  const { ejecutar, ocupado, mensaje } = useAccion();

  if (!ficha.datos || !avance.datos) return <Cargando error={ficha.error || avance.error} />;
  const recargar = () => { ficha.recargar(); avance.recargar(); };
  const ctx: Contexto = { ficha: ficha.datos, avance: avance.datos, recargar };
  const h = ficha.datos.hogar;
  const visibles = PESTANAS.filter(([p]) => p !== 'supervisor' || usuario.rol === 'SUPERVISOR');

  return (
    <>
      <button className="enlace" onClick={volver}>← Hogares</button>
      <div className="titulo fila">
        <div>
          <h1>{h.codigo_operativo} <Estado estado={h.estado} /></h1>
          <p>{h.direccion}{h.barrio_vereda ? ` · ${h.barrio_vereda}` : ''} · Período {fecha(h.fecha_inicio)} – {fecha(h.fecha_fin)}</p>
        </div>
        {usuario.rol === 'ENCUESTADOR' && h.estado === 'ASIGNADO' && (
          <button disabled={ocupado} onClick={() => ejecutar(() => api(`/hogares/${id}/iniciar-captura`, 'POST'), 'Captura iniciada: se abrieron las 14 jornadas.').then((ok) => ok && recargar())}>
            Iniciar captura (14 días)
          </button>
        )}
      </div>
      <Aviso mensaje={mensaje} />
      <div className="pestanas" role="tablist">
        {visibles.map(([p, texto]) => (
          <button key={p} role="tab" aria-selected={pestana === p} className={pestana === p ? 'activo' : ''} onClick={() => setPestana(p)}>{texto}</button>
        ))}
      </div>
      {pestana === 'dias' && <Dias ctx={ctx} />}
      {pestana === 'a' && <Identificacion ctx={ctx} />}
      {pestana === 'b' && <Visitas ctx={ctx} />}
      {pestana === 'c' && <CapituloC ctx={ctx} />}
      {pestana === 'cierre' && <Cierre ctx={ctx} />}
      {pestana === 'critica' && <Critica ctx={ctx} />}
      {pestana === 'supervisor' && <Supervisor ctx={ctx} />}
    </>
  );
}
