/** CU-10. Hogares visibles para el usuario con el avance del período de 14 días. */
import { api, fecha, pesos, ROLES, type Avance } from '../api';
import { Cargando, Estado, useDatos, useSesion } from '../componentes';

export default function Hogares({ abrir }: { abrir: (id: number) => void }) {
  const { usuario } = useSesion();
  const { datos, error } = useDatos(() => api<Avance[]>('/hogares'), []);
  if (!datos) return <Cargando error={error} />;
  return (
    <>
      <div className="titulo">
        <h1>Hogares</h1>
        <p>{usuario.rol === 'SUPERVISOR' ? 'Todos los hogares del operativo.' : `Hogares asignados a usted como ${ROLES[usuario.rol].toLowerCase()}.`}</p>
      </div>
      {datos.length === 0 && <p className="vacio">No tiene hogares asignados.</p>}
      <div className="tarjetas">
        {datos.map((h) => (
          <button key={h.id_hogar} className="tarjeta" onClick={() => abrir(h.id_hogar)}>
            <div className="tarjeta-cabeza"><strong>{h.codigo_operativo}</strong><Estado estado={h.estado} /></div>
            <p>{h.direccion}</p>
            <p className="tenue">{fecha(h.fecha_inicio)} – {fecha(h.fecha_fin)}</p>
            <div className="barra" aria-label={`${h.dias_completos} de 14 días completos`}>
              <span style={{ width: `${(h.dias_completos / 14) * 100}%` }} />
            </div>
            <dl>
              <div><dt>Días completos</dt><dd>{h.dias_completos}/14</dd></div>
              <div><dt>Renglones D / D1</dt><dd>{h.renglones_d} / {h.renglones_d1}</dd></div>
              <div><dt>Capítulo C</dt><dd>{h.grupos_capitulo_c}/25</dd></div>
              <div><dt>Valor registrado</dt><dd>{pesos(h.valor_total)}</dd></div>
              {h.hallazgos_abiertos > 0 && <div className="alerta"><dt>Hallazgos abiertos</dt><dd>{h.hallazgos_abiertos}</dd></div>}
            </dl>
          </button>
        ))}
      </div>
    </>
  );
}
