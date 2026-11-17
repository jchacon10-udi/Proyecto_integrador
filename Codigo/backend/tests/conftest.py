import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal

import oracledb
import pytest

from app import config
from app.datos_prueba import cargar
from app.modelos import CaracteristicaEntrada, CierreEntrada, CierreJornada, GastoEntrada, HogarNuevo
from app.repositorio.memoria import RepositorioMemoria
from app.repositorio.oracle import RepositorioOracle, SesionOracle, traducir
from app.servicios import Servicios

HOY = datetime(2026, 11, 16, 12, 0)


class RepositorioOraclePrueba(RepositorioOracle):
    """Una sola conexión por prueba: cada operación usa un SAVEPOINT y al final se revierte todo."""

    def __init__(self, cfg):
        super().__init__(cfg)
        self.conexion = self.pool.acquire()
        self.n = 0

    @contextmanager
    def transaccion(self):
        self.n += 1
        punto = f"T{self.n}"
        self.conexion.cursor().execute(f"SAVEPOINT {punto}")
        try:
            yield SesionOracle(self.conexion)
        except oracledb.DatabaseError as e:
            self.conexion.cursor().execute(f"ROLLBACK TO SAVEPOINT {punto}")
            raise traducir(e) from e
        except BaseException:
            self.conexion.cursor().execute(f"ROLLBACK TO SAVEPOINT {punto}")
            raise

    def deshacer(self):
        self.conexion.rollback()
        self.pool.release(self.conexion)
        self.pool.close()


@pytest.fixture
def s():
    """Repositorio en memoria; con ENPH_PRUEBAS_ORACLE=1 usa el esquema ENPH real (datos de 08_datos_prueba.sql)."""
    if os.environ.get("ENPH_PRUEBAS_ORACLE") == "1":
        repo = RepositorioOraclePrueba(config.oracle())
        yield Servicios(repo)
        repo.deshacer()
    else:
        servicios = Servicios(RepositorioMemoria(reloj=lambda: HOY))
        cargar(servicios)
        yield servicios


@pytest.fixture
def u(s):
    """Usuarios de los datos de prueba por nombre de usuario."""
    with s.repo.transaccion() as r:
        return {x.nombre_usuario: x for x in r.usuarios()}


@pytest.fixture
def h(s):
    """Ids de los hogares de prueba: 1 APROBADO, 2 EN_CAPTURA, 3 ASIGNADO."""
    with s.repo.transaccion() as r:
        return {int(x.codigo_operativo[-1]): x.id_hogar for x in r.hogares() if x.codigo_operativo.startswith("ENPH-")}


def gasto(**cambios) -> GastoEntrada:
    base = dict(descripcion="Arroz blanco", tipo_item="BIEN", cantidad=Decimal(1), cod_unidad="5", cod_forma="1",
                cod_lugar="6", valor_pagado=Decimal(2500), cod_frecuencia="3", tipo_gasto="1")
    return GastoEntrada(**{**base, **cambios})


def hogar_nuevo(codigo: str, inicio: date) -> HogarNuevo:
    return HogarNuevo(codigo_operativo=codigo, region="2", departamento="68", municipio="68001", clase="1",
                      direccion="Calle 1 # 2-3", total_hogares_vivienda=1, hogar_numero=1, total_personas=2,
                      fecha_inicio=inicio)


@pytest.fixture
def hogar_cerrado(s, u):
    """Hogar nuevo que recorre la captura completa y queda CERRADO por el encuestador."""
    enc, sup = u["ccastro"], u["mlopez"]
    id_hogar = s.crear_hogar(enc, hogar_nuevo("ENPH-PRUEBA-9001", HOY.date() - timedelta(days=20))).id_hogar
    for x in ("jgomez", "mlopez", "acritico"):
        s.asignar(sup, id_hogar, u[x].id_usuario)
    for n in range(1, 26):
        s.guardar_caracteristica(enc, id_hogar, f"{n:02d}", CaracteristicaEntrada(cod_frecuencia="3"))
    s.iniciar_captura(enc, id_hogar)
    for d in range(1, 15):
        s.registrar_gasto(u["jgomez"], id_hogar, d, gasto())
        s.cerrar_jornada(u["jgomez"], id_hogar, d, CierreJornada(total_renglones=1))
    s.cerrar_cuadernillo(enc, id_hogar, CierreEntrada(gasto_evento_especial=False, cod_forma_pago="3"))
    return id_hogar
