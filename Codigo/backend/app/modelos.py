"""Contratos de entrada y salida de la API, alineados con las 23 tablas del modelo.

Los nombres siguen las columnas de Oracle en minúscula. Las validaciones de tipo
y longitud viven aquí; las reglas entre campos y entre tablas viven en reglas.py
y servicios.py.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Rol = Literal["INFORMANTE", "ENCUESTADOR", "SUPERVISOR", "CRITICO_DIGITADOR"]
EstadoHogar = Literal["ASIGNADO", "EN_CAPTURA", "CERRADO", "DEVUELTO", "APROBADO"]
Capitulo = Literal["A", "B", "C", "D", "D1", "D2"]

Dinero = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
Cantidad = Field(gt=0, max_digits=10, decimal_places=2, allow_inf_nan=False)


class Entrada(BaseModel):
    """Base de las entradas: rechaza campos desconocidos y recorta los textos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def vacio_a_nulo(cls, valor):
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor


# ------------------------------------------------------------------ sesión
class Credenciales(Entrada):
    usuario: str = Field(min_length=1, max_length=30)
    clave: str = Field(min_length=1, max_length=200)


class UsuarioNuevo(Entrada):
    nombre_usuario: str = Field(min_length=3, max_length=30, pattern=r"^[a-z0-9._-]+$")
    nombre_completo: str = Field(min_length=3, max_length=100)
    correo: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    rol: Literal["INFORMANTE", "ENCUESTADOR", "SUPERVISOR", "CRITICO_DIGITADOR"]
    clave: str = Field(min_length=8, max_length=200)


class EstadoUsuario(Entrada):
    estado: Literal["ACTIVO", "INACTIVO"]


class Usuario(BaseModel):
    id_usuario: int
    nombre_usuario: str
    nombre_completo: str
    correo: str
    rol: Rol
    estado: str = "ACTIVO"


# ------------------------------------------------------------------ capítulo A
class HogarActualizacion(Entrada):
    """Campos del capítulo A que el encuestador puede corregir (privilegio por columna)."""

    sector: str | None = Field(default=None, max_length=8)
    seccion: str | None = Field(default=None, max_length=8)
    manzana: str | None = Field(default=None, max_length=8)
    segmento: str | None = Field(default=None, max_length=8)
    ciclo: str | None = Field(default=None, max_length=5)
    edificacion_numero: str | None = Field(default=None, max_length=8)
    vivienda_numero: str | None = Field(default=None, max_length=8)
    total_hogares_vivienda: int = Field(ge=1, le=999)
    hogar_numero: int = Field(ge=1, le=999)
    total_personas: int = Field(ge=1, le=999)
    barrio_vereda: str | None = Field(default=None, max_length=120)
    direccion: str = Field(min_length=1, max_length=180)
    telefono: str | None = Field(default=None, max_length=30)
    responsable_nombre: str | None = Field(default=None, max_length=100)
    responsable_orden: int | None = Field(default=None, ge=1, le=99)


class HogarNuevo(HogarActualizacion):
    codigo_operativo: str = Field(min_length=1, max_length=30)
    region: str = Field(min_length=1, max_length=5)
    departamento: str = Field(min_length=1, max_length=5)
    municipio: str = Field(min_length=1, max_length=8)
    clase: str = Field(min_length=1, max_length=5)
    fecha_inicio: date


class Hogar(HogarNuevo):
    id_hogar: int
    estado: EstadoHogar
    cod_resultado: str | None = None
    fecha_fin: date


class Asignacion(Entrada):
    id_usuario: int


# ------------------------------------------------------------------ capítulo B
class VisitaEntrada(Entrada):
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime | None = None
    cod_resultado: str = Field(min_length=1, max_length=2)
    pendientes: str | None = Field(default=None, max_length=300)
    proxima_visita: datetime | None = None


class Visita(VisitaEntrada):
    numero_visita: int


# ------------------------------------------------------------------ capítulo C
class CaracteristicaEntrada(Entrada):
    cod_frecuencia: str = Field(min_length=1, max_length=3)
    valor_ultima_compra: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    comprara_14_dias: bool | None = None


class Caracteristica(CaracteristicaEntrada):
    cod_grupo: str


class ResumenEntrada(Entrada):
    valor_total: Decimal = Dinero


class Resumen(ResumenEntrada):
    cod_mercado: str


# ------------------------------------------------------------------ capítulos D y D1
class GastoEntrada(Entrada):
    descripcion: str = Field(min_length=1, max_length=180)
    tipo_item: Literal["BIEN", "SERVICIO"]
    cantidad: Decimal = Cantidad
    cod_unidad: str | None = Field(default=None, max_length=2)
    otra_unidad: str | None = Field(default=None, max_length=40)
    equivalencia_g_cc: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    cod_forma: str = Field(min_length=1, max_length=2)
    otra_forma: str | None = Field(default=None, max_length=60)
    cod_lugar: str | None = Field(default=None, max_length=2)
    valor_pagado: Decimal = Dinero
    cod_frecuencia: str | None = Field(default=None, max_length=3)
    tipo_gasto: Literal["1", "2", "NA"]


class Gasto(GastoEntrada):
    dia_encuesta: int
    numero_orden: int
    id_usuario_registro: int
    fecha_registro: datetime


class ComidaEntrada(Entrada):
    descripcion: str = Field(min_length=1, max_length=180)
    cod_tipo_comida: str = Field(min_length=1, max_length=1)
    cantidad: Decimal = Cantidad
    cod_forma: str = Field(min_length=1, max_length=2)
    otra_forma: str | None = Field(default=None, max_length=60)
    cod_lugar: str | None = Field(default=None, max_length=2)
    valor_pagado: Decimal = Dinero
    cod_frecuencia: str | None = Field(default=None, max_length=3)
    tipo_gasto: Literal["1", "2"]
    a_domicilio: bool = False


class Comida(ComidaEntrada):
    dia_encuesta: int
    numero_orden: int
    id_usuario_registro: int
    fecha_registro: datetime


class CierreJornada(Entrada):
    total_renglones: int = Field(ge=0, le=999)
    observaciones: str | None = Field(default=None, max_length=500)


class Jornada(BaseModel):
    dia_encuesta: int
    fecha: date
    total_renglones: int | None
    observaciones: str | None
    renglones_d: int
    renglones_d1: int
    valor_total: Decimal
    completa: bool
    futura: bool


# ------------------------------------------------------------------ cierre D2 y supervisor
class CierreEntrada(Entrada):
    gasto_evento_especial: bool
    cod_forma_pago: str = Field(min_length=1, max_length=1)
    otra_forma_pago: str | None = Field(default=None, max_length=80)
    observaciones: str | None = Field(default=None, max_length=500)


class Cierre(CierreEntrada):
    id_encuestador: int
    fecha_cierre: datetime
    estado_revision: Literal["PENDIENTE", "APROBADO", "DEVUELTO"]
    id_supervisor: int | None = None
    fecha_revision: datetime | None = None
    observacion_supervisor: str | None = None


class DecisionSupervisor(Entrada):
    decision: Literal["APROBADO", "DEVUELTO"]
    observacion: str | None = Field(default=None, max_length=500)


# ------------------------------------------------------------------ crítica
class HallazgoEntrada(Entrada):
    capitulo: Capitulo
    dia_encuesta: int | None = Field(default=None, ge=1, le=14)
    descripcion: str = Field(min_length=1, max_length=1000)


class Evento(BaseModel):
    numero_evento: int
    estado: str
    fecha_evento: datetime
    id_usuario: int
    comentario: str | None


class Hallazgo(HallazgoEntrada):
    numero_hallazgo: int
    estado: Literal["ABIERTO", "CORREGIDO", "VERIFICADO"]
    fecha_registro: datetime
    id_responsable: int | None = None
    fecha_correccion: datetime | None = None
    respuesta_correccion: str | None = None
    fecha_verificacion: datetime | None = None
    eventos: list[Evento] = []


class Revision(BaseModel):
    numero_revision: int
    id_critico: int
    fecha_revision: datetime
    estado: Literal["EN_REVISION", "OBSERVADA", "CONFORME"]
    resultado: str | None
    hallazgos: list[Hallazgo] = []


class Conclusion(Entrada):
    resultado: str | None = Field(default=None, max_length=500)


class Correccion(Entrada):
    respuesta: str = Field(min_length=1, max_length=1000)


class Verificacion(Entrada):
    aceptada: bool
    comentario: str | None = Field(default=None, max_length=1000)


# ------------------------------------------------------------------ avance (CU-10)
class Avance(BaseModel):
    id_hogar: int
    codigo_operativo: str
    direccion: str
    estado: EstadoHogar
    fecha_inicio: date
    fecha_fin: date
    dias_completos: int
    renglones_d: int
    renglones_d1: int
    grupos_capitulo_c: int
    valor_total: Decimal
    hallazgos_abiertos: int
