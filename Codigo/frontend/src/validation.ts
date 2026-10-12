export type CaptureForm = {numero_orden:string;descripcion:string;cantidad:string;tipo_item:string;unidad_id:string;equivalencia_g_cc?:string;forma_id:string;lugar_id?:string;frecuencia_id?:string;valor:string;tipo_gasto:string};
/** Validación auxiliar de interfaz; el servidor repite todas las reglas. */
export function validateCapture(f: CaptureForm): Record<string,string> {
  const e:Record<string,string>={};
  if(!['1','2','NA'].includes(f.tipo_gasto))e.tipo_gasto='Selecciona 1, 2 o NA expresamente.';
  if(!['BIEN','SERVICIO'].includes(f.tipo_item))e.tipo_item='Indica bien o servicio.';
  if(f.tipo_item==='BIEN'&&!f.unidad_id)e.unidad_id='Los bienes necesitan una unidad aplicable.';
  if(!f.descripcion.trim())e.descripcion='Escribe el artículo o servicio.';
  if(f.descripcion.length>180)e.descripcion='Máximo 180 caracteres.';
  if(!/^\d+(\.\d{1,2})?$/.test(f.cantidad)||Number(f.cantidad)<=0)e.cantidad='Cantidad positiva, hasta dos decimales.';
  if(!/^\d+(\.\d{1,2})?$/.test(f.valor))e.valor='Valor no negativo, hasta dos decimales.';
  if(!/^\d+$/.test(f.numero_orden)||Number(f.numero_orden)<1||Number(f.numero_orden)>99999)e.numero_orden='Número de orden entero entre 1 y 99999.';
  if(!f.forma_id)e.forma_id='Selecciona la forma de adquisición.';
  return e;
}
