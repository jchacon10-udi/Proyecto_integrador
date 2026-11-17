/** Cliente de la API y tipos de datos (espejo de backend/app/modelos.py). */

export type Rol = 'INFORMANTE' | 'ENCUESTADOR' | 'SUPERVISOR' | 'CRITICO_DIGITADOR';
export type EstadoHogar = 'ASIGNADO' | 'EN_CAPTURA' | 'CERRADO' | 'DEVUELTO' | 'APROBADO';
export type Item = { codigo: string; nombre: string };
export type Catalogos = Record<
  'rol' | 'resultado_entrevista' | 'grupo_alimento' | 'frecuencia_compra' | 'tipo_mercado' | 'unidad_medida'
  | 'forma_adquisicion' | 'lugar_compra' | 'tipo_comida' | 'forma_pago', Item[]>;

export type Usuario = { id_usuario: number; nombre_usuario: string; nombre_completo: string; correo: string; rol: Rol; estado: string };

export type HogarActualizacion = {
  sector: string | null; seccion: string | null; manzana: string | null; segmento: string | null; ciclo: string | null;
  edificacion_numero: string | null; vivienda_numero: string | null; total_hogares_vivienda: number; hogar_numero: number;
  total_personas: number; barrio_vereda: string | null; direccion: string; telefono: string | null;
  responsable_nombre: string | null; responsable_orden: number | null;
};
export type HogarNuevo = HogarActualizacion & {
  codigo_operativo: string; region: string; departamento: string; municipio: string; clase: string; fecha_inicio: string;
};
export type Hogar = HogarNuevo & { id_hogar: number; estado: EstadoHogar; cod_resultado: string | null; fecha_fin: string };

export type Avance = {
  id_hogar: number; codigo_operativo: string; direccion: string; estado: EstadoHogar; fecha_inicio: string; fecha_fin: string;
  dias_completos: number; renglones_d: number; renglones_d1: number; grupos_capitulo_c: number; valor_total: string;
  hallazgos_abiertos: number;
};
export type Jornada = {
  dia_encuesta: number; fecha: string; total_renglones: number | null; observaciones: string | null; renglones_d: number;
  renglones_d1: number; valor_total: string; completa: boolean; futura: boolean;
};

export type VisitaEntrada = {
  fecha_hora_inicio: string; fecha_hora_fin: string | null; cod_resultado: string; pendientes: string | null;
  proxima_visita: string | null;
};
export type Visita = VisitaEntrada & { numero_visita: number };

export type CaracteristicaEntrada = { cod_frecuencia: string; valor_ultima_compra: string | null; comprara_14_dias: boolean | null };
export type GrupoC = { cod_grupo: string; grupo: string; registro: (CaracteristicaEntrada & { cod_grupo: string }) | null };
export type Resumen = { cod_mercado: string; valor_total: string };

export type GastoEntrada = {
  descripcion: string; tipo_item: 'BIEN' | 'SERVICIO'; cantidad: string; cod_unidad: string | null; otra_unidad: string | null;
  equivalencia_g_cc: string | null; cod_forma: string; otra_forma: string | null; cod_lugar: string | null; valor_pagado: string;
  cod_frecuencia: string | null; tipo_gasto: '1' | '2' | 'NA';
};
export type ComidaEntrada = {
  descripcion: string; cod_tipo_comida: string; cantidad: string; cod_forma: string; otra_forma: string | null;
  cod_lugar: string | null; valor_pagado: string; cod_frecuencia: string | null; tipo_gasto: '1' | '2'; a_domicilio: boolean;
};
type Renglon = { dia_encuesta: number; numero_orden: number; id_usuario_registro: number; fecha_registro: string };
export type Gasto = GastoEntrada & Renglon;
export type Comida = ComidaEntrada & Renglon;

export type CierreEntrada = {
  gasto_evento_especial: boolean; cod_forma_pago: string; otra_forma_pago: string | null; observaciones: string | null;
};
export type Cierre = CierreEntrada & {
  id_encuestador: number; fecha_cierre: string; estado_revision: 'PENDIENTE' | 'APROBADO' | 'DEVUELTO';
  id_supervisor: number | null; fecha_revision: string | null; observacion_supervisor: string | null;
};

export type Evento = { numero_evento: number; estado: string; fecha_evento: string; id_usuario: number; comentario: string | null };
export type Hallazgo = {
  numero_hallazgo: number; capitulo: string; dia_encuesta: number | null; descripcion: string;
  estado: 'ABIERTO' | 'CORREGIDO' | 'VERIFICADO'; fecha_registro: string; id_responsable: number | null;
  fecha_correccion: string | null; respuesta_correccion: string | null; fecha_verificacion: string | null; eventos: Evento[];
};
export type Revision = {
  numero_revision: number; id_critico: number; fecha_revision: string; estado: 'EN_REVISION' | 'OBSERVADA' | 'CONFORME';
  resultado: string | null; hallazgos: Hallazgo[];
};
export type RevisionCaso = {
  hogar: Hogar; avance: Avance; cierre: Cierre | null; revisiones: Revision[];
  verificaciones: { control: string; cumple: boolean }[]; puede_aprobar: boolean;
};

export class ApiError extends Error {
  constructor(message: string, public status = 0, public codigo = '') { super(message); }
}

let token = '';
let alExpirar: () => void = () => {};
export function configurarSesion(t: string, expirar?: () => void) {
  token = t;
  if (expirar) alExpirar = expirar;
}

export async function api<T>(ruta: string, metodo = 'GET', cuerpo?: unknown): Promise<T> {
  const r = await fetch('/api' + ruta, {
    method: metodo,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(cuerpo !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    ...(cuerpo !== undefined ? { body: JSON.stringify(cuerpo) } : {}),
  });
  if (r.status === 204) return undefined as T;
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && token) alExpirar();
    throw new ApiError(typeof datos.detail === 'string' ? datos.detail : 'No se pudo completar la operación.', r.status, datos.codigo ?? '');
  }
  return datos as T;
}

export const ROLES: Record<Rol, string> = {
  INFORMANTE: 'Informante del hogar', ENCUESTADOR: 'Encuestador', SUPERVISOR: 'Supervisor', CRITICO_DIGITADOR: 'Crítico-digitador',
};
export const ESTADOS: Record<EstadoHogar, string> = {
  ASIGNADO: 'Asignado', EN_CAPTURA: 'En captura', CERRADO: 'Cerrado', DEVUELTO: 'Devuelto', APROBADO: 'Aprobado',
};
export const pesos = (v: string | number) => '$' + Number(v).toLocaleString('es-CO', { maximumFractionDigits: 2 });
export const fecha = (v: string | null) => (v ? new Date(v.length === 10 ? v + 'T00:00' : v).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '—');
export const fechaHora = (v: string | null) => (v ? new Date(v).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' }) : '—');
export const nombre = (lista: Item[] | undefined, codigo: string | null) => (codigo ? lista?.find((i) => i.codigo === codigo)?.nombre ?? codigo : '—');
