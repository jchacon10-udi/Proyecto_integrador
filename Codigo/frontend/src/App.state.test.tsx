// @vitest-environment jsdom
import React from 'react';
import {it,expect,afterEach,vi} from 'vitest';
import {render,screen,cleanup,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('un cambio de día que falla no permite escribir un registro del día anterior',async()=>{
 let requested7=false;
 const old={id:42,hogar_id:1,jornada_id:6,numero_orden:1,descripcion:'Gasto del día seis',cantidad:'1',tipo_item:'SERVICIO',unidad_id:null,equivalencia_g_cc:null,forma_id:3,lugar_id:null,frecuencia_id:null,valor:'100',tipo_gasto:'NA'};
 const context={mode:'demo',rol:'Informante del hogar',hogares:[1],can_capture:true,jornadas:[{id:6,dia:6,hogar_id:1,fecha:'2026-09-06'},{id:7,dia:7,hogar_id:1,fecha:'2026-09-07'}],unidades:{3:'Gramos'},formas:{3:'Regalo'},lugares:{},frecuencias:{}};
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
  if(url.endsWith('/demo/login'))return {ok:true,status:200,json:async()=>({token:'test'})};
  if(url.endsWith('/context'))return {ok:true,status:200,json:async()=>context};
  if(url.includes('/jornadas/7/')){requested7=true;return {ok:false,status:503,json:async()=>({detail:'Jornada no disponible'})};}
  return {ok:true,status:200,json:async()=>[old]};
 }));
 const user=userEvent.setup();render(<App/>);
 await user.type(screen.getByLabelText('Contraseña demo'),'enph-demo');
 await user.click(screen.getByRole('button',{name:'Entrar a la demo'}));
 await screen.findByRole('heading',{name:'Gasto del día seis'});
 await user.click(screen.getByRole('button',{name:'Editar'}));
 await user.click(screen.getByRole('button',{name:'Día 7'}));
 await waitFor(()=>expect(requested7).toBe(true));
 expect(screen.queryByRole('heading',{name:'Gasto del día seis'})).toBeNull();
 expect(screen.queryByRole('button',{name:'Editar'})).toBeNull();
 expect(screen.getByRole('button',{name:'Guardar registro'}).closest('fieldset')).toHaveProperty('disabled',true);
});
