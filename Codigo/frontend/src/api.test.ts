import {it,expect} from 'vitest';
import {toPayload} from './api';
it('editar un registro no envía IDs internos ni cambia hogar por payload',()=>{
 const form={numero_orden:'1',descripcion:'Servicio ficticio',cantidad:'1',tipo_item:'SERVICIO',unidad_id:'',forma_id:'3',valor:'5000.10',tipo_gasto:'NA',id:42,hogar_id:2,jornada_id:99};
 const payload=toPayload(form);
 expect(payload).not.toHaveProperty('id');
 expect(payload).not.toHaveProperty('hogar_id');
 expect(payload).not.toHaveProperty('jornada_id');
 expect(payload.valor).toBe('5000.10');
});
