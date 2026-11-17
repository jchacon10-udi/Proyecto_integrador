"""Repositorio Oracle: lee tablas y vistas del esquema ENPH y escribe con sus procedimientos.

Usa python-oracledb. Con ORACLE_CLIENTE apunta a un Oracle Instant Client y activa el
modo thick, obligatorio para Oracle 10g (el modo thin solo conecta a 12.1 o superior).
Cada transacción toma una conexión del pool, fija CURRENT_SCHEMA al dueño de los
objetos y termina con COMMIT o ROLLBACK; los procedimientos no confirman por sí solos.
"""
import re
from contextlib import contextmanager
from decimal import Decimal

import oracledb

from ..config import ConfigOracle
from ..errores import Conflicto, ErrorNegocio, NoAutorizado, NoEncontrado
from ..modelos import (Caracteristica, Cierre, Comida, Evento, Gasto, Hallazgo, Hogar, Resumen, Revision, Usuario,
                       Visita)
from ..reglas import DIAS, fecha_dia
from .base import Repositorio

oracledb.defaults.fetch_decimals = True

CATALOGOS = {  # tabla: columna del código
    "rol": "ID_ROL", "resultado_entrevista": "COD_RESULTADO", "grupo_alimento": "COD_GRUPO",
    "frecuencia_compra": "COD_FRECUENCIA", "tipo_mercado": "COD_MERCADO", "unidad_medida": "COD_UNIDAD",
    "forma_adquisicion": "COD_FORMA", "lugar_compra": "COD_LUGAR", "tipo_comida": "COD_TIPO_COMIDA",
    "forma_pago": "COD_FORMA_PAGO",
}
REPORTES = {"gasto_por_forma", "gasto_por_lugar", "comidas_por_tipo", "carga_encuestador", "hallazgos"}

# Códigos de RAISE_APPLICATION_ERROR (02_secuencias_triggers.sql y 05_procedimientos.sql) por tipo de error.
CONFLICTOS = {20010, 20031, 20032, 20033, 20040, 20041, 20042, 20043, 20044, 20045, 20050, 20061, 20066, 20069,
              20071, 20072, 20073, 20074, 20078}
NO_AUTORIZADOS = {20020, 20021, 20030, 20060, 20075}
NO_ENCONTRADOS = {20002, 20076, 20077}


def traducir(error: oracledb.DatabaseError) -> ErrorNegocio:
    """Convierte un ORA- en el error de negocio equivalente, con el mensaje sin la pila PL/SQL."""
    e = error.args[0]
    codigo = getattr(e, "code", 0)
    texto = str(getattr(e, "message", e)).split("\n")[0]
    texto = re.sub(r"^ORA-\d+:\s*", "", texto)
    etiqueta = f"ORA-{codigo:05d}"
    if 20000 <= codigo <= 20999:
        clase = (Conflicto if codigo in CONFLICTOS else NoAutorizado if codigo in NO_AUTORIZADOS
                 else NoEncontrado if codigo in NO_ENCONTRADOS else ErrorNegocio)
        return clase(texto, etiqueta)
    if codigo in (1, 2290, 2291, 2292):
        restriccion = re.search(r"\(([^)]+)\)", texto)
        detalle = {1: "Registro repetido", 2290: "Regla de validación incumplida",
                   2291: "Código inexistente en el catálogo", 2292: "El registro está en uso"}[codigo]
        return ErrorNegocio(f"{detalle} ({restriccion.group(1) if restriccion else texto})", etiqueta)
    return ErrorNegocio(f"Error de base de datos: {texto}", etiqueta)


def _sn(valor: bool | None) -> str | None:
    return None if valor is None else ("S" if valor else "N")


def _bool(valor: str | None) -> bool | None:
    return None if valor is None else valor == "S"


class RepositorioOracle:
    """Pool de conexiones; cada transaccion() entrega una SesionOracle con el contrato Repositorio."""

    def __init__(self, cfg: ConfigOracle):
        if cfg.cliente:
            oracledb.init_oracle_client(lib_dir=cfg.cliente)
        esquema = cfg.esquema.upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_$#]{0,29}", esquema):
            raise ValueError("ORACLE_ESQUEMA inválido")

        def al_conectar(conexion, _etiqueta):
            conexion.cursor().execute(f"ALTER SESSION SET CURRENT_SCHEMA = {esquema}")

        self.pool = oracledb.create_pool(user=cfg.usuario, password=cfg.clave, dsn=cfg.dsn, min=1, max=4, increment=1,
                                         session_callback=al_conectar)

    @contextmanager
    def transaccion(self):
        conexion = self.pool.acquire()
        try:
            yield SesionOracle(conexion)
            conexion.commit()
        except oracledb.DatabaseError as e:
            conexion.rollback()
            raise traducir(e) from e
        except BaseException:
            conexion.rollback()
            raise
        finally:
            self.pool.release(conexion)

    def cerrar(self):
        self.pool.close()


class SesionOracle(Repositorio):
    def __init__(self, conexion):
        self.c = conexion

    def transaccion(self):
        raise RuntimeError("La transacción la abre RepositorioOracle")

    # ------------------------------------------------------------ utilidades
    def _filas(self, sql: str, **p) -> list[dict]:
        cur = self.c.cursor()
        cur.execute(sql, p)
        columnas = [d[0].lower() for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur]

    def _uno(self, sql: str, **p) -> dict | None:
        filas = self._filas(sql, **p)
        return filas[0] if filas else None

    def _ejecutar(self, sql: str, **p) -> int:
        cur = self.c.cursor()
        cur.execute(sql, p)
        return cur.rowcount

    def _proc(self, nombre: str, *args, salida: bool = False):
        cur = self.c.cursor()
        if salida:
            var = cur.var(oracledb.NUMBER)
            cur.callproc(nombre, [*args, var])
            return int(var.getvalue())
        cur.callproc(nombre, list(args))

    def hoy(self):
        return self._uno("SELECT TRUNC(SYSDATE) HOY FROM DUAL")["hoy"].date()

    # ------------------------------------------------------------ usuarios y catálogos
    _USUARIO = """SELECT U.ID_USUARIO, U.NOMBRE_USUARIO, U.NOMBRE_COMPLETO, U.CORREO, U.ESTADO, U.CLAVE_HASH,
                         R.NOMBRE ROL FROM USUARIO U JOIN ROL R ON R.ID_ROL = U.ID_ROL"""

    @staticmethod
    def _usuario(f: dict) -> Usuario:
        return Usuario(**{k: v for k, v in f.items() if k != "clave_hash"})

    def usuario_por_nombre(self, nombre_usuario):
        f = self._uno(self._USUARIO + " WHERE U.NOMBRE_USUARIO = :n", n=nombre_usuario)
        return (self._usuario(f), f["clave_hash"]) if f else None

    def usuario(self, id_usuario):
        f = self._uno(self._USUARIO + " WHERE U.ID_USUARIO = :i", i=id_usuario)
        return self._usuario(f) if f else None

    def usuarios(self):
        return [self._usuario(f) for f in self._filas(self._USUARIO + " ORDER BY U.NOMBRE_COMPLETO")]

    def crear_usuario(self, id_rol, nombre_usuario, nombre_completo, correo, clave_hash):
        cur = self.c.cursor()
        nuevo = cur.var(oracledb.NUMBER)
        cur.execute("""INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
                       VALUES (:r, :n, :c, :e, :h) RETURNING ID_USUARIO INTO :nuevo""",
                    r=id_rol, n=nombre_usuario, c=nombre_completo, e=correo, h=clave_hash, nuevo=nuevo)
        return int(nuevo.getvalue()[0])

    def cambiar_estado_usuario(self, id_usuario, estado):
        if not self._ejecutar("UPDATE USUARIO SET ESTADO = :e WHERE ID_USUARIO = :i", e=estado, i=id_usuario):
            raise NoEncontrado(f"No existe el usuario {id_usuario}")

    _cache_catalogos: dict | None = None

    def catalogos(self):
        """Los catálogos oficiales no cambian en operación: se leen una vez por proceso."""
        if SesionOracle._cache_catalogos is None:
            SesionOracle._cache_catalogos = {
                t: [{"codigo": str(f["codigo"]), "nombre": f["nombre"]}
                    for f in self._filas(f"SELECT {col} CODIGO, NOMBRE FROM {t.upper()} ORDER BY {col}")]
                for t, col in CATALOGOS.items()}
        return SesionOracle._cache_catalogos

    # ------------------------------------------------------------ hogar y asignación
    @staticmethod
    def _hogar(f: dict) -> Hogar:
        f["fecha_inicio"] = f["fecha_inicio"].date()
        return Hogar(**f, fecha_fin=fecha_dia(f["fecha_inicio"], DIAS))

    def hogares(self, ids=None):
        filas = self._filas("SELECT * FROM HOGAR ORDER BY ID_HOGAR")
        return [self._hogar(f) for f in filas if ids is None or f["id_hogar"] in ids]

    def hogar(self, id_hogar):
        f = self._uno("SELECT * FROM HOGAR WHERE ID_HOGAR = :h", h=id_hogar)
        return self._hogar(f) if f else None

    def crear_hogar(self, dto):
        datos = dto.model_dump()
        columnas = ", ".join(k.upper() for k in datos)
        valores = ", ".join(f":{k}" for k in datos)
        cur = self.c.cursor()
        nuevo = cur.var(oracledb.NUMBER)
        cur.execute(f"INSERT INTO HOGAR ({columnas}) VALUES ({valores}) RETURNING ID_HOGAR INTO :nuevo",
                    {**datos, "nuevo": nuevo})
        return int(nuevo.getvalue()[0])

    def actualizar_hogar(self, id_hogar, dto):
        datos = dto.model_dump()
        asignaciones = ", ".join(f"{k.upper()} = :{k}" for k in datos)
        self._ejecutar(f"UPDATE HOGAR SET {asignaciones} WHERE ID_HOGAR = :id_hogar", **datos, id_hogar=id_hogar)

    def asignaciones(self, id_hogar):
        filas = self._filas(self._USUARIO.replace("SELECT", "SELECT A.ESTADO ESTADO_ASIGNACION,", 1)
                            + " JOIN ASIGNACION_HOGAR A ON A.ID_USUARIO = U.ID_USUARIO WHERE A.ID_HOGAR = :h", h=id_hogar)
        return [(self._usuario({k: v for k, v in f.items() if k != "estado_asignacion"}), f["estado_asignacion"])
                for f in filas]

    def hogares_asignados(self, id_usuario):
        return {int(f["id_hogar"]) for f in self._filas(
            "SELECT ID_HOGAR FROM ASIGNACION_HOGAR WHERE ID_USUARIO = :u AND ESTADO = 'VIGENTE'", u=id_usuario)}

    def asignar(self, id_usuario, id_hogar):
        self._proc("PR_ASIGNAR_USUARIO", id_usuario, id_hogar)

    def iniciar_captura(self, id_hogar, id_encuestador):
        self._proc("PR_INICIAR_CAPTURA", id_hogar, id_encuestador)

    # ------------------------------------------------------------ capítulo B
    def visitas(self, id_hogar):
        return [Visita(**{k: v for k, v in f.items() if k != "id_hogar"})
                for f in self._filas("SELECT * FROM VISITA WHERE ID_HOGAR = :h ORDER BY NUMERO_VISITA", h=id_hogar)]

    def crear_visita(self, id_hogar, numero, dto):
        self._ejecutar("""INSERT INTO VISITA (ID_HOGAR, NUMERO_VISITA, FECHA_HORA_INICIO, FECHA_HORA_FIN, COD_RESULTADO,
                          PENDIENTES, PROXIMA_VISITA) VALUES (:h, :n, :fecha_hora_inicio, :fecha_hora_fin, :cod_resultado,
                          :pendientes, :proxima_visita)""", h=id_hogar, n=numero, **dto.model_dump())

    def actualizar_visita(self, id_hogar, numero, dto):
        if not self._ejecutar("""UPDATE VISITA SET FECHA_HORA_INICIO = :fecha_hora_inicio, FECHA_HORA_FIN = :fecha_hora_fin,
                                 COD_RESULTADO = :cod_resultado, PENDIENTES = :pendientes, PROXIMA_VISITA = :proxima_visita
                                 WHERE ID_HOGAR = :h AND NUMERO_VISITA = :n""", h=id_hogar, n=numero, **dto.model_dump()):
            raise NoEncontrado(f"No existe la visita {numero}")

    # ------------------------------------------------------------ capítulo C
    def caracteristicas(self, id_hogar):
        return [Caracteristica(cod_grupo=f["cod_grupo"], cod_frecuencia=f["cod_frecuencia"],
                               valor_ultima_compra=f["valor_ultima_compra"], comprara_14_dias=_bool(f["comprara_14_dias"]))
                for f in self._filas("SELECT * FROM CARACTERISTICA_GASTO WHERE ID_HOGAR = :h ORDER BY COD_GRUPO", h=id_hogar)]

    def guardar_caracteristica(self, id_hogar, cod_grupo, dto):
        self._ejecutar("""MERGE INTO CARACTERISTICA_GASTO D
                          USING (SELECT :h ID_HOGAR, :g COD_GRUPO FROM DUAL) S
                             ON (D.ID_HOGAR = S.ID_HOGAR AND D.COD_GRUPO = S.COD_GRUPO)
                          WHEN MATCHED THEN UPDATE SET COD_FRECUENCIA = :f, VALOR_ULTIMA_COMPRA = :v, COMPRARA_14_DIAS = :c
                          WHEN NOT MATCHED THEN INSERT (ID_HOGAR, COD_GRUPO, COD_FRECUENCIA, VALOR_ULTIMA_COMPRA,
                               COMPRARA_14_DIAS) VALUES (:h, :g, :f, :v, :c)""",
                       h=id_hogar, g=cod_grupo, f=dto.cod_frecuencia, v=dto.valor_ultima_compra, c=_sn(dto.comprara_14_dias))

    def eliminar_caracteristica(self, id_hogar, cod_grupo):
        self._ejecutar("DELETE FROM CARACTERISTICA_GASTO WHERE ID_HOGAR = :h AND COD_GRUPO = :g", h=id_hogar, g=cod_grupo)

    def resumen_mercado(self, id_hogar):
        return [Resumen(cod_mercado=f["cod_mercado"], valor_total=f["valor_total"])
                for f in self._filas("SELECT * FROM RESUMEN_MERCADO WHERE ID_HOGAR = :h ORDER BY COD_MERCADO", h=id_hogar)]

    def guardar_resumen(self, id_hogar, cod_mercado, valor_total):
        self._ejecutar("""MERGE INTO RESUMEN_MERCADO D
                          USING (SELECT :h ID_HOGAR, :m COD_MERCADO FROM DUAL) S
                             ON (D.ID_HOGAR = S.ID_HOGAR AND D.COD_MERCADO = S.COD_MERCADO)
                          WHEN MATCHED THEN UPDATE SET VALOR_TOTAL = :v
                          WHEN NOT MATCHED THEN INSERT (ID_HOGAR, COD_MERCADO, VALOR_TOTAL) VALUES (:h, :m, :v)""",
                       h=id_hogar, m=cod_mercado, v=valor_total)

    def eliminar_resumen(self, id_hogar, cod_mercado):
        self._ejecutar("DELETE FROM RESUMEN_MERCADO WHERE ID_HOGAR = :h AND COD_MERCADO = :m", h=id_hogar, m=cod_mercado)

    # ------------------------------------------------------------ jornadas, D y D1
    def jornadas(self, id_hogar):
        entero = lambda v: None if v is None else int(v)
        return {int(f["dia_encuesta"]): (entero(f["total_renglones"]), f["observaciones"]) for f in self._filas(
            "SELECT DIA_ENCUESTA, TOTAL_RENGLONES, OBSERVACIONES FROM JORNADA_DIARIA WHERE ID_HOGAR = :h "
            "ORDER BY DIA_ENCUESTA", h=id_hogar)}

    def cerrar_jornada(self, id_hogar, dia, id_usuario, total, observaciones):
        self._proc("PR_CERRAR_JORNADA", id_hogar, dia, id_usuario, total, observaciones)

    def _renglones(self, tabla, id_hogar, dia):
        sql = f"SELECT * FROM {tabla} WHERE ID_HOGAR = :h" + (" AND DIA_ENCUESTA = :d" if dia else "")
        return self._filas(sql + " ORDER BY DIA_ENCUESTA, NUMERO_ORDEN", h=id_hogar, **({"d": dia} if dia else {}))

    def gastos(self, id_hogar, dia=None):
        return [Gasto(**{k: v for k, v in f.items() if k != "id_hogar"}) for f in self._renglones("GASTO_DIARIO", id_hogar, dia)]

    def registrar_gasto(self, id_hogar, dia, id_usuario, dto):
        g = dto
        return self._proc("PR_REGISTRAR_GASTO", id_hogar, dia, id_usuario, g.descripcion, g.tipo_item, g.cantidad,
                          g.cod_unidad, g.otra_unidad, g.equivalencia_g_cc, g.cod_forma, g.otra_forma, g.cod_lugar,
                          g.valor_pagado, g.cod_frecuencia, g.tipo_gasto, salida=True)

    def actualizar_gasto(self, id_hogar, dia, orden, id_usuario, dto):
        datos = dto.model_dump()
        asignaciones = ", ".join(f"{k.upper()} = :{k}" for k in datos)
        if not self._ejecutar(f"""UPDATE GASTO_DIARIO SET {asignaciones}, ID_USUARIO_REGISTRO = :u
                                  WHERE ID_HOGAR = :h AND DIA_ENCUESTA = :d AND NUMERO_ORDEN = :o""",
                              **datos, u=id_usuario, h=id_hogar, d=dia, o=orden):
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")

    def eliminar_gasto(self, id_hogar, dia, orden):
        if not self._ejecutar("DELETE FROM GASTO_DIARIO WHERE ID_HOGAR = :h AND DIA_ENCUESTA = :d AND NUMERO_ORDEN = :o",
                              h=id_hogar, d=dia, o=orden):
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")

    def comidas(self, id_hogar, dia=None):
        return [Comida(**{**{k: v for k, v in f.items() if k != "id_hogar"}, "a_domicilio": f["a_domicilio"] == "S"})
                for f in self._renglones("COMIDA_FUERA", id_hogar, dia)]

    def registrar_comida(self, id_hogar, dia, id_usuario, dto):
        c = dto
        return self._proc("PR_REGISTRAR_COMIDA", id_hogar, dia, id_usuario, c.descripcion, c.cod_tipo_comida, c.cantidad,
                          c.cod_forma, c.otra_forma, c.cod_lugar, c.valor_pagado, c.cod_frecuencia, c.tipo_gasto,
                          _sn(c.a_domicilio), salida=True)

    def actualizar_comida(self, id_hogar, dia, orden, id_usuario, dto):
        datos = {**dto.model_dump(), "a_domicilio": _sn(dto.a_domicilio)}
        asignaciones = ", ".join(f"{k.upper()} = :{k}" for k in datos)
        if not self._ejecutar(f"""UPDATE COMIDA_FUERA SET {asignaciones}, ID_USUARIO_REGISTRO = :u
                                  WHERE ID_HOGAR = :h AND DIA_ENCUESTA = :d AND NUMERO_ORDEN = :o""",
                              **datos, u=id_usuario, h=id_hogar, d=dia, o=orden):
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")

    def eliminar_comida(self, id_hogar, dia, orden):
        if not self._ejecutar("DELETE FROM COMIDA_FUERA WHERE ID_HOGAR = :h AND DIA_ENCUESTA = :d AND NUMERO_ORDEN = :o",
                              h=id_hogar, d=dia, o=orden):
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")

    # ------------------------------------------------------------ cierre y supervisor
    def cierre(self, id_hogar):
        f = self._uno("SELECT * FROM CIERRE_CUADERNILLO WHERE ID_HOGAR = :h", h=id_hogar)
        if f is None:
            return None
        f.pop("id_hogar")
        return Cierre(**{**f, "gasto_evento_especial": f["gasto_evento_especial"] == "S"})

    def cerrar_cuadernillo(self, id_hogar, id_encuestador, dto):
        self._proc("PR_CERRAR_CUADERNILLO", id_hogar, id_encuestador, _sn(dto.gasto_evento_especial), dto.cod_forma_pago,
                   dto.otra_forma_pago, dto.observaciones)

    def revisar_supervisor(self, id_hogar, id_supervisor, decision, observacion):
        self._proc("PR_REVISAR_SUPERVISOR", id_hogar, id_supervisor, decision, observacion)

    # ------------------------------------------------------------ crítica
    def revisiones(self, id_hogar):
        eventos: dict[tuple, list[Evento]] = {}
        for f in self._filas("SELECT * FROM EVENTO_HALLAZGO WHERE ID_HOGAR = :h ORDER BY NUMERO_EVENTO", h=id_hogar):
            clave = (f.pop("numero_revision"), f.pop("numero_hallazgo"))
            f.pop("id_hogar")
            eventos.setdefault(clave, []).append(Evento(**f))
        hallazgos: dict[int, list[Hallazgo]] = {}
        for f in self._filas("SELECT * FROM HALLAZGO_CRITICA WHERE ID_HOGAR = :h ORDER BY NUMERO_HALLAZGO", h=id_hogar):
            rev = f.pop("numero_revision")
            f.pop("id_hogar")
            hallazgos.setdefault(rev, []).append(Hallazgo(**f, eventos=eventos.get((rev, f["numero_hallazgo"]), [])))
        return [Revision(**{k: v for k, v in f.items() if k != "id_hogar"}, hallazgos=hallazgos.get(f["numero_revision"], []))
                for f in self._filas("SELECT * FROM REVISION_CRITICA WHERE ID_HOGAR = :h ORDER BY NUMERO_REVISION", h=id_hogar)]

    def iniciar_revision(self, id_hogar, id_critico):
        return self._proc("PR_INICIAR_REVISION", id_hogar, id_critico, salida=True)

    def registrar_hallazgo(self, id_hogar, revision, id_critico, dto):
        return self._proc("PR_REGISTRAR_HALLAZGO", id_hogar, revision, id_critico, dto.capitulo, dto.dia_encuesta,
                          dto.descripcion, salida=True)

    def concluir_revision(self, id_hogar, revision, id_critico, resultado):
        self._proc("PR_CONCLUIR_REVISION", id_hogar, revision, id_critico, resultado)

    def corregir_hallazgo(self, id_hogar, revision, hallazgo, id_responsable, respuesta):
        self._proc("PR_CORREGIR_HALLAZGO", id_hogar, revision, hallazgo, id_responsable, respuesta)

    def verificar_hallazgo(self, id_hogar, revision, hallazgo, id_critico, aceptada, comentario):
        self._proc("PR_VERIFICAR_HALLAZGO", id_hogar, revision, hallazgo, id_critico, _sn(aceptada), comentario)

    # ------------------------------------------------------------ reportes
    def reporte(self, nombre):
        if nombre not in REPORTES:
            raise NoEncontrado(f"No existe el reporte {nombre}")
        filas = self._filas(f"SELECT * FROM V_{nombre.upper()} ORDER BY 1")
        return [{k: (int(v) if isinstance(v, Decimal) and v == v.to_integral() and k != "valor_total" else v)
                 for k, v in f.items()} for f in filas]
