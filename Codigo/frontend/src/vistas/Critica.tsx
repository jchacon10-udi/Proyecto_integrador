/** CU-12 a CU-14 (crítico-digitador) y CU-07 (corrección por el responsable). */
import { useState } from 'react';
import { api, fechaHora, type Hallazgo, type Revision } from '../api';
import { Aviso, Campo, Cargando, Estado, opcional, useAccion, useDatos, useSesion } from '../componentes';
import type { Contexto } from './HogarVista';

export default function Critica({ ctx }: { ctx: Contexto }) {
  const { usuario } = useSesion();
  const { hogar, asignaciones } = ctx.ficha;
  const id = hogar.id_hogar;
  const { datos, error, recargar } = useDatos(() => api<Revision[]>(`/hogares/${id}/revisiones`), [id, hogar.estado]);
  const accion = useAccion();
  if (!datos) return <Cargando error={error} />;
  const quien = (u: number | null) => asignaciones.find((a) => a.usuario.id_usuario === u)?.usuario.nombre_completo ?? (u ? `Usuario ${u}` : '—');
  const listo = () => { recargar(); ctx.recargar(); };
  const critico = usuario.rol === 'CRITICO_DIGITADOR';
  const enCurso = datos.some((r) => r.estado === 'EN_REVISION');
  return (
    <section className="panel">
      <div className="seccion-cabeza">
        <h2>Crítica y cotejo</h2>
        {critico && hogar.estado === 'CERRADO' && !enCurso && (
          <button disabled={accion.ocupado} onClick={() => accion.ejecutar(() => api(`/hogares/${id}/revisiones`, 'POST'), 'Revisión iniciada.').then((ok) => ok && listo())}>Iniciar revisión</button>
        )}
      </div>
      <p className="tenue">La crítica se hace sobre el cuadernillo cerrado. Los hallazgos pasan de ABIERTO a CORREGIDO (el responsable) y a VERIFICADO (el crítico); cada paso queda en el historial.</p>
      <Aviso mensaje={accion.mensaje} />
      {datos.length === 0 && <p className="vacio">Sin revisiones de crítica.</p>}
      {datos.slice().reverse().map((r) => (
        <article key={r.numero_revision} className="revision">
          <div className="seccion-cabeza">
            <h3>Revisión {r.numero_revision} · {quien(r.id_critico)} · {fechaHora(r.fecha_revision)}</h3>
            <Estado estado={r.estado} />
          </div>
          {r.resultado && <p>Resultado: {r.resultado}</p>}
          {r.hallazgos.map((h) => <HallazgoFicha key={h.numero_hallazgo} id={id} revision={r.numero_revision} h={h} quien={quien} listo={listo} />)}
          {r.hallazgos.length === 0 && <p className="tenue">Sin hallazgos registrados.</p>}
          {critico && r.estado === 'EN_REVISION' && r.id_critico === usuario.id_usuario && <AccionesRevision id={id} revision={r} listo={listo} />}
        </article>
      ))}
    </section>
  );
}

function HallazgoFicha({ id, revision, h, quien, listo }: { id: number; revision: number; h: Hallazgo; quien: (u: number | null) => string; listo: () => void }) {
  const { usuario } = useSesion();
  const [texto, setTexto] = useState('');
  const { ejecutar, ocupado, mensaje } = useAccion();
  const base = `/hogares/${id}/revisiones/${revision}/hallazgos/${h.numero_hallazgo}`;
  const corrige = ['ENCUESTADOR', 'INFORMANTE'].includes(usuario.rol) && h.estado === 'ABIERTO';
  const verifica = usuario.rol === 'CRITICO_DIGITADOR' && h.estado === 'CORREGIDO';
  return (
    <div className={`hallazgo hallazgo-${h.estado.toLowerCase()}`}>
      <div className="seccion-cabeza">
        <b>Hallazgo {h.numero_hallazgo} · Capítulo {h.capitulo}{h.dia_encuesta ? `, día ${h.dia_encuesta}` : ''}</b>
        <Estado estado={h.estado} />
      </div>
      <p>{h.descripcion}</p>
      {h.respuesta_correccion && <p className="tenue">Corrección de {quien(h.id_responsable)}: {h.respuesta_correccion}</p>}
      <ol className="historial">
        {h.eventos.map((e) => <li key={e.numero_evento}><b>{e.estado}</b> · {fechaHora(e.fecha_evento)} · {quien(e.id_usuario)}{e.comentario ? ` — ${e.comentario}` : ''}</li>)}
      </ol>
      {(corrige || verifica) && (
        <div className="en-linea">
          <input placeholder={corrige ? 'Describa la corrección realizada' : 'Comentario (opcional al aceptar)'} value={texto} maxLength={1000} onChange={(e) => setTexto(e.target.value)} />
          {corrige && <button disabled={ocupado || !texto.trim()} onClick={() => ejecutar(() => api(`${base}/correccion`, 'POST', { respuesta: texto })).then((ok) => ok && listo())}>Declarar corrección</button>}
          {verifica && <>
            <button disabled={ocupado} onClick={() => ejecutar(() => api(`${base}/verificacion`, 'POST', { aceptada: true, comentario: opcional(texto) })).then((ok) => ok && listo())}>Verificar</button>
            <button className="secundario" disabled={ocupado || !texto.trim()} onClick={() => ejecutar(() => api(`${base}/verificacion`, 'POST', { aceptada: false, comentario: texto })).then((ok) => ok && listo())}>Rechazar</button>
          </>}
        </div>
      )}
      {corrige && <p className="tenue">Si el dato está en D o D1, corríjalo primero en la pestaña de días (el hogar debe estar DEVUELTO).</p>}
      <Aviso mensaje={mensaje} />
    </div>
  );
}

function AccionesRevision({ id, revision, listo }: { id: number; revision: Revision; listo: () => void }) {
  const [capitulo, setCapitulo] = useState('D');
  const [dia, setDia] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [resultado, setResultado] = useState('');
  const { ejecutar, ocupado, mensaje } = useAccion();
  const diario = capitulo === 'D' || capitulo === 'D1';
  const base = `/hogares/${id}/revisiones/${revision.numero_revision}`;
  return (
    <div className="formulario">
      <h4>Registrar hallazgo</h4>
      <form onSubmit={(e) => { e.preventDefault(); ejecutar(() => api(`${base}/hallazgos`, 'POST', { capitulo, dia_encuesta: diario ? Number(dia) : null, descripcion }), 'Hallazgo registrado.').then((ok) => ok && (setDescripcion(''), listo())); }}>
        <div className="campos">
          <Campo etiqueta="Capítulo"><select value={capitulo} onChange={(e) => setCapitulo(e.target.value)}>{['A', 'B', 'C', 'D', 'D1', 'D2'].map((c) => <option key={c}>{c}</option>)}</select></Campo>
          {diario && <Campo etiqueta="Día"><input type="number" min={1} max={14} value={dia} onChange={(e) => setDia(e.target.value)} required /></Campo>}
          <Campo etiqueta="Descripción de la discrepancia" ancho><input value={descripcion} maxLength={1000} onChange={(e) => setDescripcion(e.target.value)} required /></Campo>
        </div>
        <div className="botones"><button disabled={ocupado}>Registrar hallazgo</button></div>
      </form>
      <h4>Concluir revisión</h4>
      <p className="tenue">Queda OBSERVADA si tiene hallazgos o CONFORME si no. Una revisión concluida no se modifica.</p>
      <div className="en-linea">
        <input placeholder={revision.hallazgos.length ? 'Resumen del resultado' : 'Sin hallazgos'} value={resultado} maxLength={500} onChange={(e) => setResultado(e.target.value)} />
        <button disabled={ocupado} onClick={() => ejecutar(() => api(`${base}/conclusion`, 'POST', { resultado: opcional(resultado) }), 'Revisión concluida.').then((ok) => ok && listo())}>Concluir</button>
      </div>
      <Aviso mensaje={mensaje} />
    </div>
  );
}
