"""Repositorio en memoria: mismo contrato que Oracle, para pruebas y desarrollo local.

Guarda las filas de las 23 tablas en diccionarios. Cada transacción toma un
bloqueo y una copia del estado; si la operación falla, el estado se restaura,
como hace ROLLBACK. Los datos se pierden al reiniciar el proceso.
"""
import copy
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from threading import RLock

from ..errores import ErrorNegocio, NoEncontrado
from ..modelos import (Caracteristica, Cierre, Comida, Evento, Gasto, Hallazgo, Hogar, Resumen, Revision, Usuario,
                       Visita)
from ..reglas import DIAS, fecha_dia
from .base import Repositorio, buscar_hallazgo
from .catalogos import CATALOGOS

ROLES = {c["codigo"]: c["nombre"] for c in CATALOGOS["rol"]}


class RepositorioMemoria(Repositorio):
    def __init__(self, reloj=datetime.now):
        self._reloj = reloj
        self._bloqueo = RLock()
        self._d = {
            "usuarios": {},          # id -> (Usuario, clave_hash)
            "hogares": {},           # id -> Hogar
            "asignaciones": {},      # (id_usuario, id_hogar) -> estado
            "visitas": defaultdict(dict),            # hogar -> numero -> Visita
            "caracteristicas": defaultdict(dict),    # hogar -> grupo -> Caracteristica
            "resumen": defaultdict(dict),            # hogar -> mercado -> Resumen
            "jornadas": defaultdict(dict),           # hogar -> dia -> [total, observaciones]
            "gastos": defaultdict(dict),             # hogar -> (dia, orden) -> Gasto
            "comidas": defaultdict(dict),            # hogar -> (dia, orden) -> Comida
            "cierres": {},                           # hogar -> Cierre
            "revisiones": defaultdict(dict),         # hogar -> numero -> Revision
            "secuencias": {"usuario": 100, "hogar": 1000},
        }

    # ------------------------------------------------------------ transacción
    @contextmanager
    def transaccion(self):
        with self._bloqueo:
            copia = copy.deepcopy(self._d)
            try:
                yield self
            except BaseException:
                self._d = copia
                raise

    def ahora(self) -> datetime:
        return self._reloj().replace(microsecond=0)

    def hoy(self) -> date:
        return self._reloj().date()

    # ------------------------------------------------------------ usuarios y catálogos
    def crear_usuario(self, id_rol: int, nombre_usuario: str, nombre_completo: str, correo: str, clave_hash: str) -> int:
        """INSERT en USUARIO con SEQ_USUARIO (lo usan los datos de prueba)."""
        if any(u.nombre_usuario == nombre_usuario or u.correo == correo for u, _ in self._d["usuarios"].values()):
            raise ErrorNegocio("Nombre de usuario o correo repetido (UQ_USUARIO_NOMBRE/UQ_USUARIO_CORREO)", "ORA-00001")
        nuevo = self._d["secuencias"]["usuario"]
        self._d["secuencias"]["usuario"] += 1
        u = Usuario(id_usuario=nuevo, nombre_usuario=nombre_usuario, nombre_completo=nombre_completo, correo=correo,
                    rol=ROLES[str(id_rol)])
        self._d["usuarios"][nuevo] = (u, clave_hash)
        return nuevo

    def cambiar_estado_usuario(self, id_usuario, estado):
        u, h = self._d["usuarios"][id_usuario]
        self._d["usuarios"][id_usuario] = (u.model_copy(update={"estado": estado}), h)

    def usuario_por_nombre(self, nombre_usuario):
        return next(((u, h) for u, h in self._d["usuarios"].values() if u.nombre_usuario == nombre_usuario), None)

    def usuario(self, id_usuario):
        fila = self._d["usuarios"].get(id_usuario)
        return fila[0] if fila else None

    def usuarios(self):
        return sorted((u for u, _ in self._d["usuarios"].values()), key=lambda u: u.nombre_completo)

    def catalogos(self):
        return copy.deepcopy(CATALOGOS)

    # ------------------------------------------------------------ hogar y asignación
    def hogares(self, ids=None):
        return [h for i, h in sorted(self._d["hogares"].items()) if ids is None or i in ids]

    def hogar(self, id_hogar):
        return self._d["hogares"].get(id_hogar)

    def crear_hogar(self, dto):
        if any(h.codigo_operativo == dto.codigo_operativo for h in self._d["hogares"].values()):
            raise ErrorNegocio("Ya existe un hogar con ese código operativo (UQ_HOGAR_CODIGO)", "ORA-00001")
        nuevo = self._d["secuencias"]["hogar"]
        self._d["secuencias"]["hogar"] += 1
        self._d["hogares"][nuevo] = Hogar(**dto.model_dump(), id_hogar=nuevo, estado="ASIGNADO",
                                         fecha_fin=fecha_dia(dto.fecha_inicio, DIAS))
        return nuevo

    def actualizar_hogar(self, id_hogar, dto):
        h = self._d["hogares"][id_hogar]
        self._d["hogares"][id_hogar] = h.model_copy(update=dto.model_dump())

    def _estado_hogar(self, id_hogar, estado, **otros):
        h = self._d["hogares"][id_hogar]
        self._d["hogares"][id_hogar] = h.model_copy(update={"estado": estado, **otros})

    def asignaciones(self, id_hogar):
        return [(self.usuario(u), e) for (u, h), e in self._d["asignaciones"].items() if h == id_hogar]

    def hogares_asignados(self, id_usuario):
        return {h for (u, h), e in self._d["asignaciones"].items() if u == id_usuario and e == "VIGENTE"}

    def asignar(self, id_usuario, id_hogar):
        self._d["asignaciones"][(id_usuario, id_hogar)] = "VIGENTE"

    def iniciar_captura(self, id_hogar, id_encuestador):
        for d in range(1, DIAS + 1):
            self._d["jornadas"][id_hogar][d] = [None, None]
        self._estado_hogar(id_hogar, "EN_CAPTURA")

    # ------------------------------------------------------------ capítulo B
    def visitas(self, id_hogar):
        return [v for _, v in sorted(self._d["visitas"][id_hogar].items())]

    def crear_visita(self, id_hogar, numero, dto):
        if numero in self._d["visitas"][id_hogar]:
            raise ErrorNegocio("Número de visita repetido (PK_VISITA)", "ORA-00001")
        self._d["visitas"][id_hogar][numero] = Visita(**dto.model_dump(), numero_visita=numero)

    def actualizar_visita(self, id_hogar, numero, dto):
        if numero not in self._d["visitas"][id_hogar]:
            raise NoEncontrado(f"No existe la visita {numero}")
        self._d["visitas"][id_hogar][numero] = Visita(**dto.model_dump(), numero_visita=numero)

    # ------------------------------------------------------------ capítulo C
    def caracteristicas(self, id_hogar):
        return [c for _, c in sorted(self._d["caracteristicas"][id_hogar].items())]

    def guardar_caracteristica(self, id_hogar, cod_grupo, dto):
        self._d["caracteristicas"][id_hogar][cod_grupo] = Caracteristica(**dto.model_dump(), cod_grupo=cod_grupo)

    def eliminar_caracteristica(self, id_hogar, cod_grupo):
        self._d["caracteristicas"][id_hogar].pop(cod_grupo, None)

    def resumen_mercado(self, id_hogar):
        return [r for _, r in sorted(self._d["resumen"][id_hogar].items())]

    def guardar_resumen(self, id_hogar, cod_mercado, valor_total):
        self._d["resumen"][id_hogar][cod_mercado] = Resumen(cod_mercado=cod_mercado, valor_total=valor_total)

    def eliminar_resumen(self, id_hogar, cod_mercado):
        self._d["resumen"][id_hogar].pop(cod_mercado, None)

    # ------------------------------------------------------------ jornadas, D y D1
    def jornadas(self, id_hogar):
        return {d: tuple(v) for d, v in sorted(self._d["jornadas"][id_hogar].items())}

    def _exigir_jornada(self, id_hogar, dia):
        if dia not in self._d["jornadas"][id_hogar]:
            raise ErrorNegocio(f"La jornada {dia} no existe: inicie la captura del hogar", "ORA-20064")

    def cerrar_jornada(self, id_hogar, dia, id_usuario, total, observaciones):
        self._exigir_jornada(id_hogar, dia)
        self._d["jornadas"][id_hogar][dia] = [total, observaciones]

    def _renglones(self, tabla, id_hogar, dia):
        return [r for (d, _), r in sorted(self._d[tabla][id_hogar].items()) if dia is None or d == dia]

    def _siguiente(self, tabla, id_hogar, dia):
        return max((o for d, o in self._d[tabla][id_hogar] if d == dia), default=0) + 1

    def gastos(self, id_hogar, dia=None):
        return self._renglones("gastos", id_hogar, dia)

    def registrar_gasto(self, id_hogar, dia, id_usuario, dto):
        self._exigir_jornada(id_hogar, dia)
        orden = self._siguiente("gastos", id_hogar, dia)
        self._d["gastos"][id_hogar][(dia, orden)] = Gasto(**dto.model_dump(), dia_encuesta=dia, numero_orden=orden,
                                                          id_usuario_registro=id_usuario, fecha_registro=self.ahora())
        return orden

    def actualizar_gasto(self, id_hogar, dia, orden, id_usuario, dto):
        if (dia, orden) not in self._d["gastos"][id_hogar]:
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")
        self._d["gastos"][id_hogar][(dia, orden)] = Gasto(**dto.model_dump(), dia_encuesta=dia, numero_orden=orden,
                                                          id_usuario_registro=id_usuario, fecha_registro=self.ahora())

    def eliminar_gasto(self, id_hogar, dia, orden):
        if self._d["gastos"][id_hogar].pop((dia, orden), None) is None:
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")

    def comidas(self, id_hogar, dia=None):
        return self._renglones("comidas", id_hogar, dia)

    def registrar_comida(self, id_hogar, dia, id_usuario, dto):
        self._exigir_jornada(id_hogar, dia)
        orden = self._siguiente("comidas", id_hogar, dia)
        self._d["comidas"][id_hogar][(dia, orden)] = Comida(**dto.model_dump(), dia_encuesta=dia, numero_orden=orden,
                                                            id_usuario_registro=id_usuario, fecha_registro=self.ahora())
        return orden

    def actualizar_comida(self, id_hogar, dia, orden, id_usuario, dto):
        if (dia, orden) not in self._d["comidas"][id_hogar]:
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")
        self._d["comidas"][id_hogar][(dia, orden)] = Comida(**dto.model_dump(), dia_encuesta=dia, numero_orden=orden,
                                                            id_usuario_registro=id_usuario, fecha_registro=self.ahora())

    def eliminar_comida(self, id_hogar, dia, orden):
        if self._d["comidas"][id_hogar].pop((dia, orden), None) is None:
            raise NoEncontrado(f"No existe el renglón {orden} del día {dia}")

    # ------------------------------------------------------------ cierre y supervisor
    def cierre(self, id_hogar):
        return self._d["cierres"].get(id_hogar)

    def cerrar_cuadernillo(self, id_hogar, id_encuestador, dto):
        self._d["cierres"][id_hogar] = Cierre(**dto.model_dump(), id_encuestador=id_encuestador,
                                              fecha_cierre=self.ahora(), estado_revision="PENDIENTE")
        self._estado_hogar(id_hogar, "CERRADO", cod_resultado="EC")

    def revisar_supervisor(self, id_hogar, id_supervisor, decision, observacion):
        c = self._d["cierres"][id_hogar]
        self._d["cierres"][id_hogar] = c.model_copy(update=dict(
            estado_revision=decision, id_supervisor=id_supervisor, fecha_revision=self.ahora(),
            observacion_supervisor=observacion))
        self._estado_hogar(id_hogar, decision)

    # ------------------------------------------------------------ crítica
    def revisiones(self, id_hogar):
        return copy.deepcopy([r for _, r in sorted(self._d["revisiones"][id_hogar].items())])

    def _revision(self, id_hogar, numero) -> Revision:
        r = self._d["revisiones"][id_hogar].get(numero)
        if r is None:
            raise ErrorNegocio(f"No existe la revisión {numero} del hogar {id_hogar}", "ORA-20076")
        return r

    def iniciar_revision(self, id_hogar, id_critico):
        numero = max(self._d["revisiones"][id_hogar], default=0) + 1
        self._d["revisiones"][id_hogar][numero] = Revision(numero_revision=numero, id_critico=id_critico,
                                                           fecha_revision=self.ahora(), estado="EN_REVISION",
                                                           resultado=None)
        return numero

    def _evento(self, h: Hallazgo, estado, id_usuario, comentario):
        h.eventos.append(Evento(numero_evento=len(h.eventos) + 1, estado=estado, fecha_evento=self.ahora(),
                                id_usuario=id_usuario, comentario=comentario))

    def registrar_hallazgo(self, id_hogar, revision, id_critico, dto):
        r = self._revision(id_hogar, revision)
        numero = len(r.hallazgos) + 1
        h = Hallazgo(**dto.model_dump(), numero_hallazgo=numero, estado="ABIERTO", fecha_registro=self.ahora())
        self._evento(h, "ABIERTO", id_critico, dto.descripcion)
        r.hallazgos.append(h)
        return numero

    def concluir_revision(self, id_hogar, revision, id_critico, resultado):
        r = self._revision(id_hogar, revision)
        r.estado = "OBSERVADA" if r.hallazgos else "CONFORME"
        r.resultado = resultado or "Sin hallazgos"

    def _hallazgo(self, id_hogar, revision, hallazgo) -> Hallazgo:
        encontrado = buscar_hallazgo(list(self._d["revisiones"][id_hogar].values()), revision, hallazgo)
        if encontrado is None:
            raise ErrorNegocio("No existe el hallazgo indicado", "ORA-20077")
        return encontrado[1]

    def corregir_hallazgo(self, id_hogar, revision, hallazgo, id_responsable, respuesta):
        h = self._hallazgo(id_hogar, revision, hallazgo)
        h.estado, h.id_responsable, h.fecha_correccion, h.respuesta_correccion = (
            "CORREGIDO", id_responsable, self.ahora(), respuesta)
        self._evento(h, "CORREGIDO", id_responsable, respuesta)

    def verificar_hallazgo(self, id_hogar, revision, hallazgo, id_critico, aceptada, comentario):
        h = self._hallazgo(id_hogar, revision, hallazgo)
        if aceptada:
            h.estado, h.fecha_verificacion = "VERIFICADO", self.ahora()
        else:
            h.estado = "ABIERTO"
        self._evento(h, h.estado, id_critico, comentario)

    # ------------------------------------------------------------ reportes (mismas columnas que las vistas V_*)
    def reporte(self, nombre):
        cat = {k: {c["codigo"]: c["nombre"] for c in v} for k, v in CATALOGOS.items()}
        renglones = ([g for h in self._d["gastos"].values() for g in h.values()]
                     + [c for h in self._d["comidas"].values() for c in h.values()])
        comidas = [c for h in self._d["comidas"].values() for c in h.values()]
        suma = lambda filas: sum((x.valor_pagado for x in filas), Decimal(0))
        if nombre == "gasto_por_forma":
            return [{"cod_forma": c, "forma_adquisicion": n, "renglones": len(x), "valor_total": suma(x)}
                    for c, n in cat["forma_adquisicion"].items() for x in [[g for g in renglones if g.cod_forma == c]]]
        if nombre == "gasto_por_lugar":
            return [{"cod_lugar": c, "lugar_compra": n, "renglones": len(x), "valor_total": suma(x)}
                    for c, n in cat["lugar_compra"].items() for x in [[g for g in renglones if g.cod_lugar == c]]]
        if nombre == "comidas_por_tipo":
            return [{"cod_tipo_comida": c, "tipo_comida": n, "renglones": len(x),
                     "a_domicilio": sum(1 for y in x if y.a_domicilio), "valor_total": suma(x)}
                    for c, n in cat["tipo_comida"].items() for x in [[y for y in comidas if y.cod_tipo_comida == c]]]
        if nombre == "carga_encuestador":
            filas = []
            for u, _ in self._d["usuarios"].values():
                if u.rol == "ENCUESTADOR":
                    hs = [self._d["hogares"][h] for h in self.hogares_asignados(u.id_usuario)]
                    cuenta = lambda e: sum(1 for h in hs if h.estado == e)
                    filas.append({"id_usuario": u.id_usuario, "encuestador": u.nombre_completo, "hogares": len(hs),
                                  "en_captura": cuenta("EN_CAPTURA"), "cerrados": cuenta("CERRADO"),
                                  "devueltos": cuenta("DEVUELTO"), "aprobados": cuenta("APROBADO")})
            return filas
        if nombre == "hallazgos":
            nombre_de = lambda i: self.usuario(i).nombre_usuario if i else None
            return [{"id_hogar": id_hogar, "codigo_operativo": self._d["hogares"][id_hogar].codigo_operativo,
                     "numero_revision": r.numero_revision, "numero_hallazgo": x.numero_hallazgo,
                     "capitulo": x.capitulo, "dia_encuesta": x.dia_encuesta, "descripcion": x.descripcion,
                     "estado": x.estado, "critico": nombre_de(r.id_critico), "fecha_registro": x.fecha_registro,
                     "responsable": nombre_de(x.id_responsable), "fecha_correccion": x.fecha_correccion,
                     "fecha_verificacion": x.fecha_verificacion, "eventos": len(x.eventos)}
                    for id_hogar, revs in self._d["revisiones"].items() for r in revs.values() for x in r.hallazgos]
        raise NoEncontrado(f"No existe el reporte {nombre}")
