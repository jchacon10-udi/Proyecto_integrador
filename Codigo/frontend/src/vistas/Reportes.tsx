/** Reportes del SGBDR (vistas V_*): supervisor y crítico-digitador. */
import { useState } from 'react';
import { api, fechaHora, pesos } from '../api';
import { Cargando, useDatos, useSesion } from '../componentes';

const REPORTES: { id: string; titulo: string; roles: string[] }[] = [
  { id: 'gasto_por_forma', titulo: 'Gasto por forma de adquisición', roles: ['SUPERVISOR'] },
  { id: 'gasto_por_lugar', titulo: 'Gasto por lugar de compra', roles: ['SUPERVISOR'] },
  { id: 'comidas_por_tipo', titulo: 'Comidas fuera del hogar por tipo', roles: ['SUPERVISOR'] },
  { id: 'carga_encuestador', titulo: 'Carga por encuestador', roles: ['SUPERVISOR'] },
  { id: 'hallazgos', titulo: 'Hallazgos de crítica', roles: ['SUPERVISOR', 'CRITICO_DIGITADOR'] },
];
const MONEDA = ['valor_total'];
const FECHAS = ['fecha_registro', 'fecha_correccion', 'fecha_verificacion'];

export default function Reportes() {
  const { usuario } = useSesion();
  const visibles = REPORTES.filter((r) => r.roles.includes(usuario.rol));
  const [actual, setActual] = useState(visibles[0].id);
  return (
    <>
      <div className="titulo"><h1>Reportes</h1><p>Consultas sobre las vistas de reporte de la base de datos.</p></div>
      <div className="pestanas">{visibles.map((r) => <button key={r.id} className={actual === r.id ? 'activo' : ''} onClick={() => setActual(r.id)}>{r.titulo}</button>)}</div>
      <Tabla key={actual} id={actual} />
    </>
  );
}

function Tabla({ id }: { id: string }) {
  const { datos, error } = useDatos(() => api<Record<string, unknown>[]>(`/reportes/${id}`), [id]);
  if (!datos) return <Cargando error={error} />;
  if (datos.length === 0) return <p className="vacio">Sin datos.</p>;
  const columnas = Object.keys(datos[0]);
  const celda = (c: string, v: unknown) => (v == null ? '—' : MONEDA.includes(c) ? pesos(String(v)) : FECHAS.includes(c) ? fechaHora(String(v)) : String(v));
  return (
    <section className="panel">
      <div className="tabla">
        <table>
          <thead><tr>{columnas.map((c) => <th key={c}>{c.replaceAll('_', ' ')}</th>)}</tr></thead>
          <tbody>{datos.map((f, i) => <tr key={i}>{columnas.map((c) => <td key={c} className={MONEDA.includes(c) ? 'num' : ''}>{celda(c, f[c])}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
