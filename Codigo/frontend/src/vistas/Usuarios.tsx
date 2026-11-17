/** Usuarios y roles (RF-01): el supervisor da de alta usuarios y los activa o desactiva. */
import { useState } from 'react';
import { api, ROLES, type Rol, type Usuario } from '../api';
import { Aviso, Campo, Cargando, Estado, useAccion, useDatos, useSesion } from '../componentes';

const VACIO = { nombre_usuario: '', nombre_completo: '', correo: '', rol: 'INFORMANTE' as Rol, clave: '' };

export default function Usuarios() {
  const { usuario: yo } = useSesion();
  const { datos, error, recargar } = useDatos(() => api<Usuario[]>('/usuarios'), []);
  const [f, setF] = useState(VACIO);
  const alta = useAccion();
  const estado = useAccion();
  if (!datos) return <Cargando error={error} />;
  return (
    <>
      <div className="titulo"><h1>Usuarios y roles</h1><p>Cada usuario tiene un único rol. Las contraseñas se guardan como hash PBKDF2.</p></div>
      <section className="panel">
        <h2>Nuevo usuario</h2>
        <form className="formulario" onSubmit={(e) => { e.preventDefault(); alta.ejecutar(() => api('/usuarios', 'POST', f), 'Usuario creado.').then((ok) => ok && (setF(VACIO), recargar())); }}>
          <div className="campos">
            <Campo etiqueta="Usuario" ayuda="Minúsculas, números, punto o guion."><input value={f.nombre_usuario} onChange={(e) => setF({ ...f, nombre_usuario: e.target.value.toLowerCase() })} required minLength={3} maxLength={30} /></Campo>
            <Campo etiqueta="Nombre completo"><input value={f.nombre_completo} onChange={(e) => setF({ ...f, nombre_completo: e.target.value })} required maxLength={100} /></Campo>
            <Campo etiqueta="Correo"><input type="email" value={f.correo} onChange={(e) => setF({ ...f, correo: e.target.value })} required maxLength={120} /></Campo>
            <Campo etiqueta="Rol">
              <select value={f.rol} onChange={(e) => setF({ ...f, rol: e.target.value as Rol })}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
            </Campo>
            <Campo etiqueta="Contraseña inicial" ayuda="Mínimo 8 caracteres."><input type="password" autoComplete="new-password" value={f.clave} onChange={(e) => setF({ ...f, clave: e.target.value })} required minLength={8} /></Campo>
          </div>
          <Aviso mensaje={alta.mensaje} />
          <div className="botones"><button disabled={alta.ocupado}>Crear usuario</button></div>
        </form>
      </section>
      <section className="panel">
        <Aviso mensaje={estado.mensaje} />
        <div className="tabla">
          <table>
            <thead><tr><th>Usuario</th><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th /></tr></thead>
            <tbody>
              {datos.map((u) => (
                <tr key={u.id_usuario}>
                  <td>{u.nombre_usuario}</td><td>{u.nombre_completo}</td><td>{u.correo}</td><td>{ROLES[u.rol]}</td><td><Estado estado={u.estado} /></td>
                  <td className="acciones">
                    {u.id_usuario !== yo.id_usuario && (
                      <button className="enlace" disabled={estado.ocupado} onClick={() => estado.ejecutar(() => api(`/usuarios/${u.id_usuario}/estado`, 'PUT', { estado: u.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO' })).then((ok) => ok && recargar())}>
                        {u.estado === 'ACTIVO' ? 'Desactivar' : 'Activar'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
