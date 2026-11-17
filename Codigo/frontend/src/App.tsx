/** Aplicación ENPH Cuadernillo 2 urbano: inicio de sesión (CU-01) y navegación por rol. */
import { useEffect, useState } from 'react';
import { api, configurarSesion, ROLES, type Catalogos, type Usuario } from './api';
import { Aviso, SesionContexto, useAccion, type Sesion } from './componentes';
import Hogares from './vistas/Hogares';
import HogarVista from './vistas/HogarVista';
import NuevoHogar from './vistas/NuevoHogar';
import Reportes from './vistas/Reportes';
import VistaCatalogos from './vistas/Catalogos';
import Usuarios from './vistas/Usuarios';

type Pantalla = { tipo: 'hogares' } | { tipo: 'hogar'; id: number } | { tipo: 'nuevo' } | { tipo: 'reportes' } | { tipo: 'usuarios' } | { tipo: 'catalogos' };
const CLAVE_TOKEN = 'enph-token';

function leerToken() {
  try { return sessionStorage.getItem(CLAVE_TOKEN) ?? ''; } catch { return ''; }
}
function guardarToken(t: string) {
  try { if (t) sessionStorage.setItem(CLAVE_TOKEN, t); else sessionStorage.removeItem(CLAVE_TOKEN); } catch { /* sin almacenamiento */ }
}

export default function App() {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [pantalla, setPantalla] = useState<Pantalla>({ tipo: 'hogares' });
  const [iniciando, setIniciando] = useState(Boolean(leerToken()));

  const salir = () => {
    api('/sesion', 'DELETE').catch(() => {});
    configurarSesion('');
    guardarToken('');
    setSesion(null);
    setPantalla({ tipo: 'hogares' });
  };

  const abrir = async (token: string) => {
    configurarSesion(token, () => { guardarToken(''); setSesion(null); });
    const [{ usuario }, catalogos] = await Promise.all([api<{ usuario: Usuario }>('/sesion'), api<Catalogos>('/catalogos')]);
    guardarToken(token);
    setSesion({ usuario, catalogos });
  };

  useEffect(() => {
    const t = leerToken();
    if (t) abrir(t).catch(() => guardarToken('')).finally(() => setIniciando(false));
  }, []);

  if (iniciando) return <p className="cargando">Cargando…</p>;
  if (!sesion) return <Login alEntrar={abrir} />;

  const rol = sesion.usuario.rol;
  const menu: [Pantalla['tipo'], string][] = [['hogares', 'Hogares']];
  if (rol === 'ENCUESTADOR') menu.push(['nuevo', 'Registrar hogar']);
  if (rol === 'SUPERVISOR' || rol === 'CRITICO_DIGITADOR') menu.push(['reportes', 'Reportes']);
  if (rol === 'SUPERVISOR') menu.push(['usuarios', 'Usuarios y roles']);
  menu.push(['catalogos', 'Catálogos']);

  return (
    <SesionContexto.Provider value={sesion}>
      <header>
        <div className="marca"><b>ENPH</b><span>Cuadernillo 2 · Gastos diarios urbanos</span></div>
        <div className="usuario">
          <span>{sesion.usuario.nombre_completo}<small>{ROLES[rol]}</small></span>
          <button className="secundario" onClick={salir}>Salir</button>
        </div>
      </header>
      <div className="marco">
        <nav>
          {menu.map(([tipo, texto]) => (
            <button key={tipo} className={pantalla.tipo === tipo || (tipo === 'hogares' && pantalla.tipo === 'hogar') ? 'activo' : ''}
              onClick={() => setPantalla({ tipo } as Pantalla)}>{texto}</button>
          ))}
        </nav>
        <main>
          {pantalla.tipo === 'hogares' && <Hogares abrir={(id) => setPantalla({ tipo: 'hogar', id })} />}
          {pantalla.tipo === 'hogar' && <HogarVista id={pantalla.id} volver={() => setPantalla({ tipo: 'hogares' })} />}
          {pantalla.tipo === 'nuevo' && <NuevoHogar creado={(id) => setPantalla({ tipo: 'hogar', id })} />}
          {pantalla.tipo === 'reportes' && <Reportes />}
          {pantalla.tipo === 'usuarios' && <Usuarios />}
          {pantalla.tipo === 'catalogos' && <VistaCatalogos />}
        </main>
      </div>
    </SesionContexto.Provider>
  );
}

function Login({ alEntrar }: { alEntrar: (token: string) => Promise<void> }) {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const { ejecutar, ocupado, mensaje } = useAccion();
  const entrar = (e: React.FormEvent) => {
    e.preventDefault();
    ejecutar(async () => {
      const r = await api<{ token: string }>('/sesion', 'POST', { usuario, clave });
      await alEntrar(r.token);
    });
  };
  return (
    <div className="login">
      <p className="sobre">DANE · Encuesta Nacional de Presupuestos de los Hogares</p>
      <h1>Cuadernillo 2 urbano</h1>
      <p>Registro de gastos diarios del hogar durante los 14 días de recolección.</p>
      <form onSubmit={entrar}>
        <label>Usuario<input autoComplete="username" value={usuario} onChange={(e) => setUsuario(e.target.value)} required /></label>
        <label>Contraseña<input type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required /></label>
        <Aviso mensaje={mensaje} />
        <button disabled={ocupado}>{ocupado ? 'Ingresando…' : 'Ingresar'}</button>
      </form>
    </div>
  );
}
