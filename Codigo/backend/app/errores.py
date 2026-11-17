"""Errores de negocio independientes de HTTP y de la base de datos.

Cada error lleva el código ORA- que la base de datos lanza para la misma regla,
así la aplicación responde igual con el repositorio en memoria o con Oracle.
"""


class ErrorNegocio(Exception):
    """Regla de negocio incumplida (HTTP 422)."""

    estado_http = 422

    def __init__(self, mensaje: str, codigo: str = ""):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class Conflicto(ErrorNegocio):
    """El estado actual del caso no permite la operación (HTTP 409)."""

    estado_http = 409


class NoAutorizado(ErrorNegocio):
    """El usuario no tiene el rol o la asignación vigente al hogar (HTTP 403)."""

    estado_http = 403


class NoEncontrado(ErrorNegocio):
    """El registro solicitado no existe (HTTP 404)."""

    estado_http = 404


class CredencialesInvalidas(ErrorNegocio):
    """Usuario o contraseña incorrectos, o sesión vencida (HTTP 401)."""

    estado_http = 401
