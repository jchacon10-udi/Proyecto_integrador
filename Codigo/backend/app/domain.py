"""Contrato de captura D; decisiones explícitas y valores monetarios exactos."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

ROLES = ("Informante del hogar", "Encuestador", "Supervisor", "Crítico-digitador")

@dataclass(frozen=True)
class Session:
    usuario_id: int
    rol: str
    hogares: frozenset[int]

@dataclass(frozen=True)
class Jornada:
    id: int
    hogar_id: int
    dia: int
    fecha: date
    inicio: date

    def __post_init__(self):
        if type(self.dia) is not int or not 1 <= self.dia <= 14:
            raise ValueError("Día obligatorio entero entre 1 y 14")
        if self.fecha != self.inicio + timedelta(days=self.dia - 1):
            raise ValueError("Fecha no corresponde al día del período")

class GastoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    numero_orden: StrictInt = Field(gt=0, le=99999)
    descripcion: str = Field(min_length=1, max_length=180)
    cantidad: Decimal = Field(gt=0, max_digits=10, decimal_places=2, allow_inf_nan=False)
    tipo_item: Literal["BIEN", "SERVICIO"]
    unidad_id: StrictInt | None = None
    equivalencia_g_cc: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    forma_id: StrictInt
    lugar_id: StrictInt | None = None
    frecuencia_id: StrictInt | None = None
    valor: Decimal = Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)
    tipo_gasto: Literal["1", "2", "NA"]

    @field_validator("descripcion")
    @classmethod
    def nonblank(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Descripción obligatoria")
        return value

    @model_validator(mode="after")
    def unit_for_goods(self):
        if self.tipo_item == "BIEN" and self.unidad_id is None:
            raise ValueError("Un bien requiere unidad aplicable")
        return self

class Gasto(GastoInput):
    id: int
    hogar_id: int
    jornada_id: int

class ConflictError(ValueError):
    """Duplicado o captura cerrada: conflicto 409, no validación 422."""
