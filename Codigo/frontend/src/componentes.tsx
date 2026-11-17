/** Piezas compartidas: contexto de sesión, carga de datos, acciones y campos de formulario. */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { ApiError, ESTADOS, type Catalogos, type EstadoHogar, type Item, type Usuario } from './api';

export type Sesion = { usuario: Usuario; catalogos: Catalogos };
export const SesionContexto = createContext<Sesion | null>(null);
export function useSesion(): Sesion {
  const s = useContext(SesionContexto);
  if (!s) throw new Error('Sin sesión');
  return s;
}

/** Carga datos de la API y permite recargarlos después de una acción. */
export function useDatos<T>(cargar: () => Promise<T>, deps: unknown[]) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let vigente = true;
    setError('');
    cargar().then((d) => vigente && setDatos(d)).catch((e: Error) => vigente && setError(e.message));
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version]);
  const recargar = useCallback(() => setVersion((v) => v + 1), []);
  return { datos, error, recargar };
}

/** Ejecuta una operación de escritura y guarda el mensaje de éxito o de error. */
export function useAccion() {
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState<{ tipo: 'ok' | 'error'; texto: string } | null>(null);
  const ejecutar = useCallback(async (operacion: () => Promise<unknown>, exito?: string) => {
    setOcupado(true);
    setMensaje(null);
    try {
      await operacion();
      if (exito) setMensaje({ tipo: 'ok', texto: exito });
      return true;
    } catch (e) {
      const err = e as ApiError;
      setMensaje({ tipo: 'error', texto: err.codigo && err.codigo !== 'VALIDACION' ? `${err.message} [${err.codigo}]` : err.message });
      return false;
    } finally {
      setOcupado(false);
    }
  }, []);
  return { ejecutar, ocupado, mensaje, limpiar: () => setMensaje(null) };
}

export function Aviso({ mensaje }: { mensaje: { tipo: 'ok' | 'error'; texto: string } | null | string }) {
  if (!mensaje) return null;
  const m = typeof mensaje === 'string' ? { tipo: 'error' as const, texto: mensaje } : mensaje;
  return <p className={`aviso aviso-${m.tipo}`} role={m.tipo === 'error' ? 'alert' : 'status'}>{m.texto}</p>;
}

export function Cargando({ error }: { error?: string }) {
  return error ? <Aviso mensaje={error} /> : <p className="cargando">Cargando…</p>;
}

export function Estado({ estado }: { estado: EstadoHogar | string }) {
  return <span className={`estado estado-${estado.toLowerCase()}`}>{ESTADOS[estado as EstadoHogar] ?? estado.replace('_', ' ')}</span>;
}

export function Campo({ etiqueta, ayuda, ancho, children }: { etiqueta: string; ayuda?: string; ancho?: boolean; children: ReactNode }) {
  return (
    <label className={ancho ? 'campo ancho' : 'campo'}>
      <span>{etiqueta}</span>
      {children}
      {ayuda && <small>{ayuda}</small>}
    </label>
  );
}

export function Lista({ items, valor, cambiar, vacio, deshabilitado }: {
  items: Item[]; valor: string | null; cambiar: (v: string | null) => void; vacio?: string; deshabilitado?: boolean;
}) {
  return (
    <select value={valor ?? ''} onChange={(e) => cambiar(e.target.value || null)} disabled={deshabilitado}>
      {vacio !== undefined && <option value="">{vacio}</option>}
      {items.map((i) => <option key={i.codigo} value={i.codigo}>{i.codigo} · {i.nombre}</option>)}
    </select>
  );
}

/** Convierte texto vacío en null para los campos opcionales. */
export const opcional = (v: string) => (v.trim() === '' ? null : v);
