import { describe, expect, it } from 'vitest';
import { validateCapture } from './validation';

const valid = {tipo_item:'SERVICIO',unidad_id:'',tipo_gasto:'NA',forma_id:'3',descripcion:'Pasaje ficticio',cantidad:'1',valor:'3200.25',numero_orden:'1'};
describe('Selecciones de captura D', () => {
  it('NA expreso es respuesta y vacío no lo es', () => {
    expect(validateCapture(valid)).toEqual({});
    expect(validateCapture({...valid,tipo_gasto:''})).toHaveProperty('tipo_gasto');
  });
  it('regalo clasificado con 1 no se transforma en NA', () => {
    expect(validateCapture({...valid,tipo_gasto:'1'})).toEqual({});
  });
  it('BIEN sin unidad se rechaza y servicio sin unidad se admite', () => {
    expect(validateCapture({...valid,tipo_item:'BIEN'})).toHaveProperty('unidad_id');
    expect(validateCapture(valid)).toEqual({});
  });
  it('selección BIEN con unidad se admite', () => {
    expect(validateCapture({...valid,tipo_item:'BIEN',unidad_id:'3'})).toEqual({});
  });
  it.each(['NaN','Infinity','-1','0','1.001'])('rechaza cantidad %s', (cantidad) => {
    expect(validateCapture({...valid,cantidad})).toHaveProperty('cantidad');
  });
  it('rechaza tipo ausente y descripción sin contenido', () => {
    expect(validateCapture({...valid,tipo_item:'',descripcion:' '})).toHaveProperty('tipo_item');
    expect(validateCapture({...valid,descripcion:' '})).toHaveProperty('descripcion');
  });
});
