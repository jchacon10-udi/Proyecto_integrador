"""Contrato de persistencia. Lo implementan el repositorio en memoria y el de Oracle.

Las lecturas devuelven modelos de app.modelos; las escrituras corresponden una a
una con los procedimientos almacenados de 05_procedimientos.sql. Los servicios
validan las reglas antes de escribir; Oracle las vuelve a validar.
"""
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from datetime import date

from ..modelos import (Caracteristica, CaracteristicaEntrada, Cierre, CierreEntrada, Comida, ComidaEntrada, Gasto,
                       GastoEntrada, Hallazgo, HallazgoEntrada, Hogar, HogarActualizacion, HogarNuevo, Resumen, Revision,
                       Usuario, Visita, VisitaEntrada)


class Repositorio(ABC):
    # ------------------------------------------------------------ transacción
    @abstractmethod
    def transaccion(self) -> AbstractContextManager["Repositorio"]:
        """Unidad de trabajo: confirma al salir sin error y revierte si hay excepción."""

    # ------------------------------------------------------------ usuarios y catálogos
    @abstractmethod
    def usuario_por_nombre(self, nombre_usuario: str) -> tuple[Usuario, str] | None:
        """Usuario y su CLAVE_HASH."""

    @abstractmethod
    def usuario(self, id_usuario: int) -> Usuario | None: ...

    @abstractmethod
    def usuarios(self) -> list[Usuario]: ...

    @abstractmethod
    def crear_usuario(self, id_rol: int, nombre_usuario: str, nombre_completo: str, correo: str, clave_hash: str) -> int:
        """INSERT en USUARIO; el ID lo asigna SEQ_USUARIO."""

    @abstractmethod
    def cambiar_estado_usuario(self, id_usuario: int, estado: str): ...

    @abstractmethod
    def catalogos(self) -> dict[str, list[dict]]:
        """{'unidad_medida': [{'codigo': '1', 'nombre': ...}], ...}"""

    # ------------------------------------------------------------ hogar y asignación
    @abstractmethod
    def hogares(self, ids: set[int] | None = None) -> list[Hogar]: ...

    @abstractmethod
    def hogar(self, id_hogar: int) -> Hogar | None: ...

    @abstractmethod
    def crear_hogar(self, dto: HogarNuevo) -> int: ...

    @abstractmethod
    def actualizar_hogar(self, id_hogar: int, dto: HogarActualizacion): ...

    @abstractmethod
    def asignaciones(self, id_hogar: int) -> list[tuple[Usuario, str]]:
        """Usuarios asignados al hogar con el estado de la asignación."""

    @abstractmethod
    def hogares_asignados(self, id_usuario: int) -> set[int]:
        """Hogares con asignación VIGENTE del usuario."""

    @abstractmethod
    def asignar(self, id_usuario: int, id_hogar: int):
        """PR_ASIGNAR_USUARIO."""

    @abstractmethod
    def iniciar_captura(self, id_hogar: int, id_encuestador: int):
        """PR_INICIAR_CAPTURA: crea las 14 jornadas y pasa a EN_CAPTURA."""

    # ------------------------------------------------------------ capítulo B
    @abstractmethod
    def visitas(self, id_hogar: int) -> list[Visita]: ...

    @abstractmethod
    def crear_visita(self, id_hogar: int, numero: int, dto: VisitaEntrada): ...

    @abstractmethod
    def actualizar_visita(self, id_hogar: int, numero: int, dto: VisitaEntrada): ...

    # ------------------------------------------------------------ capítulo C
    @abstractmethod
    def caracteristicas(self, id_hogar: int) -> list[Caracteristica]: ...

    @abstractmethod
    def guardar_caracteristica(self, id_hogar: int, cod_grupo: str, dto: CaracteristicaEntrada): ...

    @abstractmethod
    def eliminar_caracteristica(self, id_hogar: int, cod_grupo: str): ...

    @abstractmethod
    def resumen_mercado(self, id_hogar: int) -> list[Resumen]: ...

    @abstractmethod
    def guardar_resumen(self, id_hogar: int, cod_mercado: str, valor_total): ...

    @abstractmethod
    def eliminar_resumen(self, id_hogar: int, cod_mercado: str): ...

    # ------------------------------------------------------------ jornadas, D y D1
    @abstractmethod
    def jornadas(self, id_hogar: int) -> dict[int, tuple[int | None, str | None]]:
        """{día: (TOTAL_RENGLONES declarado, OBSERVACIONES)} de las jornadas creadas."""

    @abstractmethod
    def cerrar_jornada(self, id_hogar: int, dia: int, id_usuario: int, total: int, observaciones: str | None):
        """PR_CERRAR_JORNADA."""

    @abstractmethod
    def gastos(self, id_hogar: int, dia: int | None = None) -> list[Gasto]: ...

    @abstractmethod
    def registrar_gasto(self, id_hogar: int, dia: int, id_usuario: int, dto: GastoEntrada) -> int:
        """PR_REGISTRAR_GASTO; devuelve el número de orden."""

    @abstractmethod
    def actualizar_gasto(self, id_hogar: int, dia: int, orden: int, id_usuario: int, dto: GastoEntrada): ...

    @abstractmethod
    def eliminar_gasto(self, id_hogar: int, dia: int, orden: int): ...

    @abstractmethod
    def comidas(self, id_hogar: int, dia: int | None = None) -> list[Comida]: ...

    @abstractmethod
    def registrar_comida(self, id_hogar: int, dia: int, id_usuario: int, dto: ComidaEntrada) -> int:
        """PR_REGISTRAR_COMIDA; devuelve el número de orden."""

    @abstractmethod
    def actualizar_comida(self, id_hogar: int, dia: int, orden: int, id_usuario: int, dto: ComidaEntrada): ...

    @abstractmethod
    def eliminar_comida(self, id_hogar: int, dia: int, orden: int): ...

    # ------------------------------------------------------------ cierre y supervisor
    @abstractmethod
    def cierre(self, id_hogar: int) -> Cierre | None: ...

    @abstractmethod
    def cerrar_cuadernillo(self, id_hogar: int, id_encuestador: int, dto: CierreEntrada):
        """PR_CERRAR_CUADERNILLO."""

    @abstractmethod
    def revisar_supervisor(self, id_hogar: int, id_supervisor: int, decision: str, observacion: str | None):
        """PR_REVISAR_SUPERVISOR."""

    # ------------------------------------------------------------ crítica
    @abstractmethod
    def revisiones(self, id_hogar: int) -> list[Revision]:
        """Revisiones con sus hallazgos y el historial de eventos de cada uno."""

    @abstractmethod
    def iniciar_revision(self, id_hogar: int, id_critico: int) -> int:
        """PR_INICIAR_REVISION; devuelve el número de revisión."""

    @abstractmethod
    def registrar_hallazgo(self, id_hogar: int, revision: int, id_critico: int, dto: HallazgoEntrada) -> int:
        """PR_REGISTRAR_HALLAZGO; devuelve el número de hallazgo."""

    @abstractmethod
    def concluir_revision(self, id_hogar: int, revision: int, id_critico: int, resultado: str | None): ...

    @abstractmethod
    def corregir_hallazgo(self, id_hogar: int, revision: int, hallazgo: int, id_responsable: int, respuesta: str): ...

    @abstractmethod
    def verificar_hallazgo(self, id_hogar: int, revision: int, hallazgo: int, id_critico: int, aceptada: bool,
                           comentario: str | None): ...

    # ------------------------------------------------------------ reportes
    @abstractmethod
    def reporte(self, nombre: str) -> list[dict]:
        """Filas de una vista V_* de 06_vistas_reportes.sql."""

    @abstractmethod
    def hoy(self) -> date:
        """Fecha actual según el servidor de datos (SYSDATE en Oracle)."""


def buscar_hallazgo(revisiones: list[Revision], revision: int, hallazgo: int) -> tuple[Revision, Hallazgo] | None:
    for r in revisiones:
        if r.numero_revision == revision:
            for h in r.hallazgos:
                if h.numero_hallazgo == hallazgo:
                    return r, h
    return None
