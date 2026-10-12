"""Reglas de D y autorización: pruebas sobre servicio/repositorio reales de demo."""
from datetime import date
from decimal import Decimal
import pytest

def service():
    from app.repository import MemoryRepository
    from app.services import CapturaService
    return CapturaService(MemoryRepository())

def session(role="Informante del hogar", homes=frozenset({1})):
    from app.domain import Session
    return Session(1, role, homes)

def payload(**changes):
    from app.domain import GastoInput
    data=dict(numero_orden=1, descripcion="Arroz ficticio", cantidad="500", tipo_item="BIEN",
              unidad_id=3, equivalencia_g_cc=None, forma_id=1, lugar_id=6,
              frecuencia_id=3, valor="2500.10", tipo_gasto="1")
    return GastoInput(**(data | changes))

@pytest.mark.parametrize("code", ["1", "2", "NA"])
def test_explicit_type_preserved_even_for_gift(code):
    s=service(); g=s.create(session(),1,6,payload(tipo_gasto=code,forma_id=3))
    assert g.tipo_gasto==code
    assert g.valor==Decimal("2500.10")

def test_service_without_unit_and_full_crud():
    s=service(); g=s.create(session(),1,6,payload(tipo_item="SERVICIO",unidad_id=None))
    assert s.list(session(),1,6)==[g]
    updated=s.update(session(),g.id,payload(tipo_item="SERVICIO",unidad_id=None,valor="3200.25"))
    assert updated.id==g.id and updated.valor==Decimal("3200.25")
    s.delete(session(),g.id)
    assert s.list(session(),1,6)==[]

@pytest.mark.parametrize("changes", [{"unidad_id":None},{"unidad_id":99},{"forma_id":99},{"tipo_gasto":""},{"tipo_gasto":" "},{"tipo_gasto":None},{"cantidad":"NaN"},{"valor":"Infinity"},{"descripcion":" "},{"numero_orden":True}])
def test_invalid_capture_does_not_write(changes):
    s=service()
    with pytest.raises(ValueError):s.create(session(),1,6,payload(**changes))
    assert s.list(session(),1,6)==[]

@pytest.mark.parametrize("role", ["Supervisor","Crítico-digitador"])
def test_wrong_role_cannot_capture(role):
    s=service()
    with pytest.raises(PermissionError):s.create(session(role),1,6,payload())
    assert s.list(session(),1,6)==[]

def test_foreign_household_cannot_read_or_write():
    s=service()
    with pytest.raises(PermissionError):s.create(session(homes=frozenset({2})),1,6,payload())
    with pytest.raises(PermissionError):s.list(session(homes=frozenset({2})),1,6)

def test_duplicate_fails_without_overwriting():
    s=service();g=s.create(session(),1,6,payload())
    with pytest.raises(ValueError,match="duplicado"):s.create(session(),1,6,payload(valor="999"))
    assert s.list(session(),1,6)==[g]

def test_closed_capture_denies_update_and_delete():
    s=service();g=s.create(session(),1,6,payload());s.repository.closed_homes.add(1)
    with pytest.raises(ValueError,match="cerrad"):s.update(session(),g.id,payload())
    with pytest.raises(ValueError,match="cerrad"):s.delete(session(),g.id)
    assert s.repository.gastos[g.id]==g

@pytest.mark.parametrize("day", [None,0,15,True,1.5])
def test_invalid_day_rejected(day):
    from app.domain import Jornada
    with pytest.raises(ValueError):Jornada(6,1,day,date(2026,9,6),date(2026,9,1))

def test_date_must_equal_period_start_plus_day_minus_one():
    from app.domain import Jornada
    with pytest.raises(ValueError):Jornada(6,1,6,date(2026,9,7),date(2026,9,1))

def test_duplicate_jornada_by_home_day_rejected():
    from app.domain import Jornada
    s=service()
    with pytest.raises(ValueError):s.repository.add_jornada(Jornada(99,1,6,date(2026,9,6),date(2026,9,1)))

def test_personal_expense_only_first_seven_days():
    s=service()
    with pytest.raises(ValueError):s.create(session(),1,8,payload(tipo_gasto="2"))
    assert s.list(session(),1,8)==[]
    assert s.create(session(),1,7,payload(tipo_gasto="2")).tipo_gasto=="2"
