"""Reglas y autorización independientes de FastAPI y React."""
from datetime import datetime, timezone
from contextlib import contextmanager
from .domain import GastoInput, Gasto, Session, ROLES, ConflictError
from .repository import MemoryRepository

class AutorizacionService:
    def exigir(self, session: Session, hogar_id: int, write: bool = False):
        if session.rol not in ROLES or hogar_id not in session.hogares:
            raise PermissionError("Hogar no autorizado")
        # CU-05 sólo corresponde al Informante. CU-07 del Encuestador es otra
        # vertical; este CRUD no concede capturas nuevas al Encuestador.
        if write and session.rol != "Informante del hogar":
            raise PermissionError("Perfil sin permiso de captura D")

class CapturaService:
    def __init__(self, repository: MemoryRepository):
        self.repository = repository
        self.authorization = AutorizacionService()

    def _validate(self, session: Session, hogar_id: int, jornada_id: int, dto: GastoInput, exclude: int | None = None):
        self.authorization.exigir(session, hogar_id, write=True)
        jornada = self.repository.jornadas.get(jornada_id)
        if jornada is None or jornada.hogar_id != hogar_id:
            raise ValueError("Jornada inválida para el hogar")
        if hogar_id in self.repository.closed_homes:
            raise ConflictError("Captura cerrada")
        if dto.tipo_gasto == "2" and jornada.dia > 7:
            raise ValueError("El gasto personal del responsable sólo se registra en los primeros siete días")
        for value, catalog in [(dto.unidad_id,self.repository.unidades),(dto.forma_id,self.repository.formas),(dto.lugar_id,self.repository.lugares),(dto.frecuencia_id,self.repository.frecuencias)]:
            if value is not None and value not in catalog:
                raise ValueError("Código de catálogo inexistente en demo")
        if any(g.id!=exclude and g.jornada_id==jornada_id and g.numero_orden==dto.numero_orden for g in self.repository.gastos.values()):
            raise ConflictError("Número de orden duplicado")

    def _audit(self, action: str, session: Session, gasto: Gasto):
        self.repository.audit.append(dict(action=action,actor=session.usuario_id,gasto_id=gasto.id,at=datetime.now(timezone.utc).isoformat()))

    @contextmanager
    def _mutation(self):
        """Atomicidad sólo del estado demo de un proceso, no transacción Oracle."""
        with self.repository.lock:
            gastos=dict(self.repository.gastos)
            audit=list(self.repository.audit)
            counter=self.repository.next_id
            try:
                yield
            except Exception:
                self.repository.gastos.clear()
                self.repository.gastos.update(gastos)
                self.repository.audit[:]=audit
                self.repository.next_id=counter
                raise

    def create(self, session: Session, hogar_id: int, jornada_id: int, dto: GastoInput) -> Gasto:
        with self._mutation():
            self._validate(session,hogar_id,jornada_id,dto)
            result = Gasto(**dto.model_dump(),id=self.repository.next_id,hogar_id=hogar_id,jornada_id=jornada_id)
            self.repository.gastos[result.id] = result
            self.repository.next_id += 1
            self._audit("create",session,result)
            return result

    def list(self, session: Session, hogar_id: int, jornada_id: int) -> list[Gasto]:
        self.authorization.exigir(session,hogar_id)
        with self.repository.lock:
            j = self.repository.jornadas.get(jornada_id)
            if not j or j.hogar_id!=hogar_id:
                raise ValueError("Jornada inválida para el hogar")
            return sorted((g for g in self.repository.gastos.values() if g.hogar_id==hogar_id and g.jornada_id==jornada_id),key=lambda g:g.numero_orden)

    def update(self, session: Session, gasto_id: int, dto: GastoInput) -> Gasto:
        with self._mutation():
            old = self.repository.gastos[gasto_id]
            self._validate(session,old.hogar_id,old.jornada_id,dto,exclude=gasto_id)
            result=Gasto(**dto.model_dump(),id=old.id,hogar_id=old.hogar_id,jornada_id=old.jornada_id)
            self.repository.gastos[gasto_id]=result
            self._audit("update",session,result)
            return result

    def delete(self, session: Session, gasto_id: int):
        with self._mutation():
            old=self.repository.gastos[gasto_id]
            self.authorization.exigir(session,old.hogar_id,write=True)
            if old.hogar_id in self.repository.closed_homes:
                raise ConflictError("Captura cerrada")
            del self.repository.gastos[gasto_id]
            self._audit("delete",session,old)
