// @vitest-environment jsdom
// Integración React→proxy Vite→API real local; sólo fixtures ficticios.
import React from 'react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {cleanup,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe.runIf(process.env.ENPH_LIVE_API==='1')('Captura integrada con API demo local',()=>{
 it('crea, consulta, edita y elimina un servicio con NA expreso',async()=>{
  const nativeFetch=globalThis.fetch.bind(globalThis);
  vi.stubGlobal('fetch',(url:string,options?:RequestInit)=>nativeFetch(new URL(url,'http://127.0.0.1:5173').toString(),options));
  vi.stubGlobal('confirm',()=>true);
  const user=userEvent.setup();render(<App/>);
  await user.type(screen.getByLabelText('Contraseña demo'),'enph-demo');
  await user.click(screen.getByRole('button',{name:'Entrar a la demo'}));
  await screen.findByRole('heading',{name:'Gastos diarios'});
  await user.click(screen.getByRole('button',{name:'Día 14'}));
  await waitFor(()=>expect(screen.getByLabelText('Número de orden')).toHaveProperty('value','1'));
  await user.type(screen.getByLabelText('Artículo o servicio'),'Pasaje ficticio de integración');
  await user.selectOptions(screen.getByLabelText('Clasificación'),'SERVICIO');
  await user.type(screen.getByLabelText('Cantidad adquirida'),'1');
  await user.type(screen.getByLabelText('Valor pagado o estimado ($)'),'3200.25');
  await user.selectOptions(screen.getByLabelText('Forma de adquisición'),'3');
  await user.selectOptions(screen.getByLabelText('Tipo de gasto'),'NA');
  await user.click(screen.getByRole('button',{name:'Guardar registro'}));
  await screen.findByRole('heading',{name:'Pasaje ficticio de integración'});
  expect(screen.getByText('Tipo de gasto: NA expreso')).toBeTruthy();
  await user.click(screen.getByRole('button',{name:'Editar'}));
  const value=screen.getByLabelText('Valor pagado o estimado ($)');
  await user.clear(value);await user.type(value,'5000.10');
  await user.click(screen.getByRole('button',{name:'Guardar cambios'}));
  await screen.findByText('$5000.10');
  await user.click(screen.getByRole('button',{name:'Eliminar'}));
  await waitFor(()=>expect(screen.queryByRole('heading',{name:'Pasaje ficticio de integración'})).toBeNull());
  expect(screen.getByRole('heading',{name:'Un día por registrar'})).toBeTruthy();
 },15000);
});
