import pytest
from fastapi.testclient import TestClient

def client():
    from app.main import create_app
    return TestClient(create_app())

def login(c, user="informante"):
    r=c.post("/api/demo/login",json={"usuario":user,"password":"enph-demo"})
    assert r.status_code==200
    return {"Authorization":"Bearer "+r.json()["token"]}

def data(**changes):
    return dict(numero_orden=1,descripcion="Servicio ficticio",cantidad="1",tipo_item="SERVICIO",unidad_id=None,forma_id=3,valor="3200.25",tipo_gasto="NA") | changes

def test_no_session_or_wrong_credentials():
    c=client()
    assert c.get("/api/context").status_code==401
    assert c.post("/api/demo/login",json={"usuario":"informante","password":"wrong"}).status_code==401
    assert c.get("/api/context",headers={"Authorization":"Bearer forged"}).status_code==401

@pytest.mark.parametrize("user,role", [("informante","Informante del hogar"),("encuestador","Encuestador"),("supervisor","Supervisor"),("critico","Crítico-digitador")])
def test_four_roles_are_derived_from_session(user,role):
    c=client();h=login(c,user);r=c.get("/api/context",headers=h)
    assert r.status_code==200 and r.json()["rol"]==role and r.json()["mode"]=="demo"

def test_complete_crud_over_http():
    c=client();h=login(c);url="/api/hogares/1/jornadas/6/gastos"
    r=c.post(url,headers=h,json=data());assert r.status_code==201
    g=r.json();assert g["valor"]=="3200.25" and g["tipo_gasto"]=="NA" and g["unidad_id"] is None
    assert c.get(url,headers=h).json()==[g]
    r=c.put(f"/api/gastos/{g['id']}",headers=h,json=data(valor="5000.10"));assert r.status_code==200 and r.json()["valor"]=="5000.10"
    assert c.delete(f"/api/gastos/{g['id']}",headers=h).status_code==204
    assert c.get(url,headers=h).json()==[]

@pytest.mark.parametrize("user", ["encuestador","supervisor","critico"])
def test_other_roles_are_read_only_in_this_vertical(user):
    c=client();h=login(c,user);url="/api/hogares/1/jornadas/6/gastos"
    assert c.get(url,headers=h).status_code==200
    assert c.post(url,headers=h,json=data()).status_code==403

def test_foreign_household_denied():
    c=client();h=login(c)
    assert c.post("/api/hogares/2/jornadas/26/gastos",headers=h,json=data()).status_code==403
    assert c.get("/api/hogares/2/jornadas/26/gastos",headers=h).status_code==403

@pytest.mark.parametrize("changes",[{"rol":"Supervisor"},{"hogar_id":2},{"tipo_gasto":""},{"tipo_item":"BIEN"},{"cantidad":"NaN"},{"numero_orden":True},{"cantidad":"1.001"}])
def test_bad_payload_422_and_no_write(changes):
    c=client();h=login(c);url="/api/hogares/1/jornadas/6/gastos"
    assert c.post(url,headers=h,json=data(**changes)).status_code==422
    assert c.get(url,headers=h).json()==[]

def test_duplicate_returns409_and_missing_record404():
    c=client();h=login(c);url="/api/hogares/1/jornadas/6/gastos"
    assert c.post(url,headers=h,json=data()).status_code==201
    assert c.post(url,headers=h,json=data(valor="999")).status_code==409
    assert len(c.get(url,headers=h).json())==1
    assert c.delete("/api/gastos/999",headers=h).status_code==404

def test_oracle_mode_fails_closed():
    from app.main import create_app
    with pytest.raises(RuntimeError,match="Oracle"):create_app(mode="oracle")

def test_expired_session_cannot_access():
    from app.auth import AuthService
    now=[0.0];a=AuthService(clock=lambda:now[0]);token=a.login("informante","enph-demo")
    now[0]=1201
    with pytest.raises(PermissionError):a.resolve(token)

def test_each_app_has_independent_fixtures():
    c=client();h=login(c);url="/api/hogares/1/jornadas/6/gastos"
    assert c.post(url,headers=h,json=data()).status_code==201
    fresh=client();assert fresh.get(url,headers=login(fresh)).json()==[]
