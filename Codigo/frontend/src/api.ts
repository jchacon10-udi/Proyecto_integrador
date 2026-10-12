import type { CaptureForm } from './validation';
export type Gasto = Omit<CaptureForm,'unidad_id'|'forma_id'|'lugar_id'|'frecuencia_id'|'numero_orden'|'equivalencia_g_cc'> & {id:number;hogar_id:number;jornada_id:number;unidad_id:number|null;forma_id:number;lugar_id:number|null;frecuencia_id:number|null;numero_orden:number;equivalencia_g_cc:string|null};
export type Context = {mode:'demo';rol:string;hogares:number[];can_capture:boolean;jornadas:{id:number;dia:number;hogar_id:number;fecha:string}[];unidades:Record<string,string>;formas:Record<string,string>;lugares:Record<string,string>;frecuencias:Record<string,string>};
export class ApiError extends Error { constructor(message:string, public fields:Record<string,string>={}, public status=0){super(message);} }
export async function request<T>(path:string, token:string, method='GET', body?:unknown):Promise<T> {
 const r=await fetch('/api'+path,{method,headers:{...(token?{Authorization:`Bearer ${token}`} : {}),...(body!==undefined?{'Content-Type':'application/json'}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 if(r.status===204)return undefined as T;
 const data=await r.json();
 if(!r.ok){
  const fields:Record<string,string>={};
  if(Array.isArray(data.detail))for(const e of data.detail){if(e.loc?.[0]==='body')fields[String(e.loc[1])]='Revisa este valor: '+e.msg;}
  throw new ApiError(typeof data.detail==='string'?data.detail:'No se pudo completar la operación.',fields,r.status);
 }
 return data as T;
}
/** Lista blanca: el objeto editado puede tener IDs de respuesta, nunca se reenvían. */
export function toPayload(f:CaptureForm){return {
 numero_orden:Number(f.numero_orden),descripcion:f.descripcion,cantidad:f.cantidad,
 tipo_item:f.tipo_item,tipo_gasto:f.tipo_gasto,valor:f.valor,
 unidad_id:f.unidad_id?Number(f.unidad_id):null,forma_id:Number(f.forma_id),
 lugar_id:f.lugar_id?Number(f.lugar_id):null,frecuencia_id:f.frecuencia_id?Number(f.frecuencia_id):null,
 equivalencia_g_cc:f.equivalencia_g_cc||null,
};}
