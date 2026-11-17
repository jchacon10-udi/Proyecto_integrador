/** RF-10. Consulta de los catálogos oficiales del Cuadernillo 2. */
import { useState } from 'react';
import type { Catalogos as C } from '../api';
import { useSesion } from '../componentes';

const NOMBRES: [keyof C, string][] = [
  ['unidad_medida', 'Unidades de medida'], ['forma_adquisicion', 'Formas de adquisición'], ['lugar_compra', 'Lugares de compra'],
  ['frecuencia_compra', 'Frecuencias de compra'], ['grupo_alimento', 'Grupos de alimentos (C)'], ['tipo_mercado', 'Tipos de mercado (C)'],
  ['tipo_comida', 'Tipos de comida (D1)'], ['forma_pago', 'Formas de pago (D2)'], ['resultado_entrevista', 'Resultados de entrevista (A y B)'],
  ['rol', 'Roles'],
];

export default function Catalogos() {
  const { catalogos } = useSesion();
  const [actual, setActual] = useState<keyof C>('unidad_medida');
  return (
    <>
      <div className="titulo"><h1>Catálogos</h1><p>Códigos oficiales del DANE usados en la captura.</p></div>
      <div className="pestanas">{NOMBRES.map(([k, n]) => <button key={k} className={actual === k ? 'activo' : ''} onClick={() => setActual(k)}>{n}</button>)}</div>
      <section className="panel">
        <div className="tabla">
          <table>
            <thead><tr><th>Código</th><th>Nombre</th></tr></thead>
            <tbody>{catalogos[actual].map((i) => <tr key={i.codigo}><td>{i.codigo}</td><td>{i.nombre}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </>
  );
}
