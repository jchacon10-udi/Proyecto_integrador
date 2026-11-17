/** CU-02. Identificación del hogar (capítulo A) y asignación de usuarios (RF-03). */
import { useState } from 'react';
import { api, ROLES, type HogarActualizacion, type HogarNuevo, type Usuario } from '../api';
import { Aviso, Campo, opcional, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

const CAMPOS_TEXTO: [keyof HogarActualizacion, string, number][] = [
  ['sector', 'A5. Sector', 8], ['seccion', 'A6. Sección', 8], ['manzana', 'A7. Manzana', 8], ['segmento', 'A8. Segmento', 8],
  ['ciclo', 'A9. Ciclo', 5], ['edificacion_numero', 'A10. N.º de edificación', 8], ['vivienda_numero', 'A11. N.º de vivienda', 8],
  ['barrio_vereda', 'A15. Barrio o vereda', 120], ['telefono', 'A17. Teléfono', 30], ['responsable_nombre', 'A19. Responsable del cuadernillo', 100],
];

export function FormHogar<T extends HogarActualizacion>({ inicial, nuevo, editable, guardar }: {
  inicial: T; nuevo?: boolean; editable: boolean; guardar: (datos: T) => Promise<unknown>;
}) {
  const [f, setF] = useState<T>(inicial);
  const { ejecutar, ocupado, mensaje } = useAccion();
  const set = (k: string, v: unknown) => setF((x) => ({ ...x, [k]: v }));
  const texto = (k: string, etiqueta: string, max: number, requerido = false) => (
    <Campo key={k} etiqueta={etiqueta}>
      <input value={(f as Record<string, unknown>)[k] as string ?? ''} maxLength={max} disabled={!editable} required={requerido}
        onChange={(e) => set(k, requerido ? e.target.value : opcional(e.target.value))} />
    </Campo>
  );
  const numero = (k: string, etiqueta: string, requerido = true) => (
    <Campo key={k} etiqueta={etiqueta}>
      <input type="number" min={1} value={(f as Record<string, unknown>)[k] as number ?? ''} disabled={!editable} required={requerido}
        onChange={(e) => set(k, e.target.value === '' ? null : Number(e.target.value))} />
    </Campo>
  );
  return (
    <form className="formulario" onSubmit={(e) => { e.preventDefault(); ejecutar(() => guardar(f), nuevo ? undefined : 'Identificación actualizada.'); }}>
      <div className="campos">
        {nuevo && <>
          {texto('codigo_operativo', 'Código operativo', 30, true)}
          {texto('region', 'A1. Región', 5, true)}{texto('departamento', 'A2. Departamento (DIVIPOLA)', 5, true)}
          {texto('municipio', 'A3. Municipio (DIVIPOLA)', 8, true)}{texto('clase', 'A4. Clase', 5, true)}
          <Campo etiqueta="A21. Fecha de inicio del período" ayuda="El día 14 es esta fecha + 13 días.">
            <input type="date" value={(f as unknown as HogarNuevo).fecha_inicio} onChange={(e) => set('fecha_inicio', e.target.value)} required />
          </Campo>
        </>}
        {CAMPOS_TEXTO.slice(0, 7).map(([k, e, m]) => texto(k, e, m))}
        {numero('total_hogares_vivienda', 'A12. Total de hogares en la vivienda')}
        {numero('hogar_numero', 'A13. N.º de hogar')}
        {numero('total_personas', 'A14. Total de personas del hogar')}
        {texto('direccion', 'A16. Dirección', 180, true)}
        {CAMPOS_TEXTO.slice(7).map(([k, e, m]) => texto(k, e, m))}
        {numero('responsable_orden', 'A20. N.º de orden del responsable', false)}
      </div>
      <Aviso mensaje={mensaje} />
      {editable && <div className="botones"><button disabled={ocupado}>{nuevo ? 'Registrar hogar' : 'Guardar cambios'}</button></div>}
    </form>
  );
}

export default function Identificacion({ ctx }: { ctx: Contexto }) {
  const { usuario } = useSesion();
  const { hogar, asignaciones } = ctx.ficha;
  const editable = usuario.rol === 'ENCUESTADOR' && !['CERRADO', 'APROBADO'].includes(hogar.estado);
  const campos = Object.fromEntries(
    ['sector', 'seccion', 'manzana', 'segmento', 'ciclo', 'edificacion_numero', 'vivienda_numero', 'total_hogares_vivienda',
      'hogar_numero', 'total_personas', 'barrio_vereda', 'direccion', 'telefono', 'responsable_nombre', 'responsable_orden']
      .map((k) => [k, hogar[k as keyof HogarActualizacion]])) as HogarActualizacion;
  return (
    <section className="panel">
      <h2>Capítulo A · Identificación</h2>
      <p className="tenue">Región {hogar.region} · Departamento {hogar.departamento} · Municipio {hogar.municipio} · Clase {hogar.clase}{hogar.cod_resultado ? ` · Resultado del cuadernillo: ${hogar.cod_resultado}` : ''}</p>
      <FormHogar key={hogar.id_hogar + hogar.estado} inicial={campos} editable={editable}
        guardar={(d) => api(`/hogares/${hogar.id_hogar}`, 'PUT', d).then(ctx.recargar)} />
      <h3>Usuarios asignados</h3>
      <ul className="asignados">
        {asignaciones.map(({ usuario: a, estado }) => (
          <li key={a.id_usuario}><b>{a.nombre_completo}</b> · {ROLES[a.rol]}{estado !== 'VIGENTE' ? ' (retirada)' : ''}</li>
        ))}
      </ul>
      {usuario.rol === 'SUPERVISOR' && <Asignar idHogar={hogar.id_hogar} asignados={asignaciones.map((a) => a.usuario.id_usuario)} listo={ctx.recargar} />}
    </section>
  );
}

function Asignar({ idHogar, asignados, listo }: { idHogar: number; asignados: number[]; listo: () => void }) {
  const { datos } = useDatos(() => api<Usuario[]>('/usuarios'), []);
  const [id, setId] = useState('');
  const { ejecutar, ocupado, mensaje } = useAccion();
  const libres = (datos ?? []).filter((u) => !asignados.includes(u.id_usuario));
  return (
    <form className="en-linea" onSubmit={(e) => { e.preventDefault(); ejecutar(() => api(`/hogares/${idHogar}/asignaciones`, 'POST', { id_usuario: Number(id) }), 'Usuario asignado.').then((ok) => ok && (setId(''), listo())); }}>
      <select value={id} onChange={(e) => setId(e.target.value)} required>
        <option value="">Asignar un usuario…</option>
        {libres.map((u) => <option key={u.id_usuario} value={u.id_usuario}>{u.nombre_completo} · {ROLES[u.rol]}</option>)}
      </select>
      <button disabled={ocupado || !id}>Asignar</button>
      <Aviso mensaje={mensaje} />
    </form>
  );
}
