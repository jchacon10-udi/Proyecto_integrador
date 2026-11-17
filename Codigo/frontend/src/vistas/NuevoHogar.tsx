/** CU-02. El encuestador registra un hogar nuevo y queda asignado a él. */
import { api, type Hogar, type HogarNuevo } from '../api';
import { FormHogar } from './Identificacion';

const VACIO: HogarNuevo = {
  codigo_operativo: '', region: '', departamento: '', municipio: '', clase: '1', fecha_inicio: new Date().toISOString().slice(0, 10),
  sector: null, seccion: null, manzana: null, segmento: null, ciclo: null, edificacion_numero: null, vivienda_numero: null,
  total_hogares_vivienda: 1, hogar_numero: 1, total_personas: 1, barrio_vereda: null, direccion: '', telefono: null,
  responsable_nombre: null, responsable_orden: null,
};

export default function NuevoHogar({ creado }: { creado: (id: number) => void }) {
  return (
    <>
      <div className="titulo"><h1>Registrar hogar</h1><p>Capítulo A del Cuadernillo 2. El hogar queda ASIGNADO a usted; el supervisor asigna al informante.</p></div>
      <section className="panel">
        <FormHogar inicial={VACIO} nuevo editable guardar={(d) => api<Hogar>('/hogares', 'POST', d).then((h) => creado(h.id_hogar))} />
      </section>
    </>
  );
}
