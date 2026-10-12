import pytest
from decimal import Decimal
from app.domain import GastoInput, Session
from app.repository import MemoryRepository
from app.services import CapturaService

@pytest.mark.parametrize('action',['create','update','delete'])
def test_failed_audit_restores_complete_demo_state(monkeypatch,action):
    repo=MemoryRepository();service=CapturaService(repo)
    session=Session(1,'Informante del hogar',frozenset({1}))
    dto=GastoInput(numero_orden=1,descripcion='Servicio ficticio',cantidad='1',tipo_item='SERVICIO',forma_id=3,valor='100.10',tipo_gasto='NA')
    original=service.create(session,1,6,dto)
    before=dict(repo.gastos);audit=list(repo.audit);counter=repo.next_id
    def fail(*args):raise RuntimeError('Fallo simulado de auditoría')
    monkeypatch.setattr(service,'_audit',fail)
    with pytest.raises(RuntimeError):
        if action=='create':service.create(session,1,6,dto.model_copy(update={'numero_orden':2}))
        elif action=='update':service.update(session,original.id,dto.model_copy(update={'valor':Decimal('200.20')}))
        else:service.delete(session,original.id)
    assert repo.gastos==before
    assert repo.audit==audit
    assert repo.next_id==counter
