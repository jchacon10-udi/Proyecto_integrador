"""Prueba la conexión con Oracle usando las variables de .env (ORACLE_*).

Uso, desde Codigo/backend:
    .venv/bin/python probar_conexion.py            (Windows: .venv\\Scripts\\python probar_conexion.py)

Muestra el modo (thin o thick), la versión del cliente y del servidor, y cuántos objetos
del esquema ENPH están válidos. Sale con código 1 si la conexión falla.
"""
import sys

import oracledb

from app import config


def main() -> int:
    cfg = config.oracle()
    if cfg.cliente:
        try:
            oracledb.init_oracle_client(lib_dir=cfg.cliente)
        except oracledb.Error as e:
            print(f"No se pudo cargar Oracle Instant Client desde {cfg.cliente}:\n  {e}")
            print("Revise ORACLE_CLIENTE y que la arquitectura de Python coincida con la del cliente (64 bits / x86_64).")
            return 1
        print(f"Modo thick · Instant Client {'.'.join(map(str, oracledb.clientversion()))} en {cfg.cliente}")
    else:
        print("Modo thin (sin Instant Client): solo conecta a Oracle 12.1 o superior")
    try:
        with oracledb.connect(user=cfg.usuario, password=cfg.clave, dsn=cfg.dsn) as con:
            cur = con.cursor()
            print(f"Conectado como {cfg.usuario} · servidor Oracle {con.version}")
            cur.execute("SELECT status, COUNT(*) FROM all_objects WHERE owner = :o GROUP BY status", o=cfg.esquema.upper())
            estados = dict(cur.fetchall())
            print(f"Objetos del esquema {cfg.esquema}: {estados.get('VALID', 0)} válidos, {estados.get('INVALID', 0)} inválidos")
            if not estados:
                print(f"  El usuario {cfg.usuario} no ve objetos de {cfg.esquema}: instale el esquema o revise los privilegios.")
    except oracledb.Error as e:
        print(f"Error de conexión: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
