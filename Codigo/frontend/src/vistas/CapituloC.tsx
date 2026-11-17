/** CU-04. Características del gasto en alimentos (capítulo C) y resumen de mercado. */
import { useState } from 'react';
import { api, nombre, pesos, type CaracteristicaEntrada, type GrupoC, type Resumen } from '../api';
import { Aviso, Cargando, Lista, opcional, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

const MAYORES_A_BISEMANA = ['5', '6', '7', '9'];
type Datos = { grupos: GrupoC[]; resumen_mercado: Resumen[] };

export default function CapituloC({ ctx }: { ctx: Contexto }) {
  const { usuario, catalogos: cat } = useSesion();
  const id = ctx.ficha.hogar.id_hogar;
  const { datos, error, recargar } = useDatos(() => api<Datos>(`/hogares/${id}/caracteristicas`), [id]);
  const accion = useAccion();
  if (!datos) return <Cargando error={error} />;
  const editable = usuario.rol === 'ENCUESTADOR' && !['CERRADO', 'APROBADO'].includes(ctx.ficha.hogar.estado);
  const listos = datos.grupos.filter((g) => g.registro).length;
  const listo = () => { recargar(); ctx.recargar(); };
  return (
    <section className="panel">
      <div className="seccion-cabeza"><h2>Capítulo C · Características del gasto</h2><span className="contador">{listos}/25 grupos</span></div>
      <p className="tenue">C2. Frecuencia habitual de compra de cada grupo. C3.1 (valor de la última compra) y C3.2 (¿comprará en los 14 días?) solo aplican a compras mensuales, bimestrales, trimestrales o esporádicas.</p>
      <Aviso mensaje={accion.mensaje} />
      <div className="tabla">
        <table>
          <thead><tr><th>Grupo de alimentos</th><th>C2. Frecuencia</th><th>C3.1 Valor última compra</th><th>C3.2 Comprará en 14 días</th>{editable && <th />}</tr></thead>
          <tbody>
            {datos.grupos.map((g) => editable
              ? <FilaC key={g.cod_grupo} id={id} grupo={g} accion={accion} listo={listo} />
              : (
                <tr key={g.cod_grupo}>
                  <td>{g.cod_grupo} · {g.grupo}</td><td>{nombre(cat.frecuencia_compra, g.registro?.cod_frecuencia ?? null)}</td>
                  <td>{g.registro?.valor_ultima_compra ? pesos(g.registro.valor_ultima_compra) : '—'}</td>
                  <td>{g.registro?.comprara_14_dias == null ? '—' : g.registro.comprara_14_dias ? 'Sí' : 'No'}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      <h3>Resumen de mercado (códigos 95 a 98)</h3>
      <p className="tenue">Solo cuando el hogar no puede desagregar el gasto del mercado.</p>
      <div className="tabla">
        <table>
          <tbody>
            {cat.tipo_mercado.map((m) => (
              <FilaMercado key={m.codigo} id={id} codigo={m.codigo} nombreMercado={m.nombre} editable={editable}
                actual={datos.resumen_mercado.find((r) => r.cod_mercado === m.codigo)} accion={accion} listo={listo} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FilaC({ id, grupo, accion, listo }: { id: number; grupo: GrupoC; accion: ReturnType<typeof useAccion>; listo: () => void }) {
  const { catalogos: cat } = useSesion();
  const r = grupo.registro;
  const [f, setF] = useState<CaracteristicaEntrada>({ cod_frecuencia: r?.cod_frecuencia ?? '', valor_ultima_compra: r?.valor_ultima_compra ?? null, comprara_14_dias: r?.comprara_14_dias ?? null });
  const aplica = MAYORES_A_BISEMANA.includes(f.cod_frecuencia);
  const guardar = () => accion.ejecutar(() => api(`/hogares/${id}/caracteristicas/${grupo.cod_grupo}`, 'PUT', {
    cod_frecuencia: f.cod_frecuencia, valor_ultima_compra: aplica ? f.valor_ultima_compra : null, comprara_14_dias: aplica ? f.comprara_14_dias : null,
  }), `Grupo ${grupo.cod_grupo} guardado.`).then((ok) => ok && listo());
  const cambiado = !r || r.cod_frecuencia !== f.cod_frecuencia || r.valor_ultima_compra !== f.valor_ultima_compra || r.comprara_14_dias !== f.comprara_14_dias;
  return (
    <tr className={r ? '' : 'pendiente'}>
      <td>{grupo.cod_grupo} · {grupo.grupo}</td>
      <td><Lista items={cat.frecuencia_compra} valor={f.cod_frecuencia || null} cambiar={(v) => setF({ ...f, cod_frecuencia: v ?? '' })} vacio="Seleccione" /></td>
      <td><input type="number" min={0} step="0.01" disabled={!aplica} value={aplica ? f.valor_ultima_compra ?? '' : ''} onChange={(e) => setF({ ...f, valor_ultima_compra: opcional(e.target.value) })} /></td>
      <td>
        <select disabled={!aplica} value={!aplica || f.comprara_14_dias == null ? '' : f.comprara_14_dias ? 'S' : 'N'} onChange={(e) => setF({ ...f, comprara_14_dias: e.target.value === '' ? null : e.target.value === 'S' })}>
          <option value="">—</option><option value="S">Sí</option><option value="N">No</option>
        </select>
      </td>
      <td className="acciones"><button className="enlace" disabled={!f.cod_frecuencia || !cambiado || accion.ocupado} onClick={guardar}>Guardar</button></td>
    </tr>
  );
}

function FilaMercado({ id, codigo, nombreMercado, editable, actual, accion, listo }: {
  id: number; codigo: string; nombreMercado: string; editable: boolean; actual?: Resumen; accion: ReturnType<typeof useAccion>; listo: () => void;
}) {
  const [valor, setValor] = useState(actual?.valor_total ?? '');
  const ruta = `/hogares/${id}/resumen-mercado/${codigo}`;
  if (!editable) return <tr><td>{codigo} · {nombreMercado}</td><td className="num">{actual ? pesos(actual.valor_total) : '—'}</td></tr>;
  return (
    <tr>
      <td>{codigo} · {nombreMercado}</td>
      <td><input type="number" min="0.01" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Valor total" /></td>
      <td className="acciones">
        <button className="enlace" disabled={!valor || valor === actual?.valor_total} onClick={() => accion.ejecutar(() => api(ruta, 'PUT', { valor_total: valor }), 'Resumen guardado.').then((ok) => ok && listo())}>Guardar</button>
        {actual && <button className="enlace peligro" onClick={() => accion.ejecutar(() => api(ruta, 'DELETE'), 'Resumen eliminado.').then((ok) => ok && (setValor(''), listo()))}>Quitar</button>}
      </td>
    </tr>
  );
}
