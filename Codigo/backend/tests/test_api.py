"""Capa HTTP: sesión, códigos de estado y formato de los errores."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def api(s):
    return TestClient(create_app("memoria", servicios=s))


def entrar(api, usuario):
    r = api.post("/api/sesion", json={"usuario": usuario, "clave": "enph-demo"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_sesion(api):
    assert api.get("/api/hogares").status_code == 401
    assert api.post("/api/sesion", json={"usuario": "pruiz", "clave": "x"}).status_code == 401
    cab = entrar(api, "pruiz")
    assert api.get("/api/sesion", headers=cab).json()["usuario"]["rol"] == "INFORMANTE"
    assert api.delete("/api/sesion", headers=cab).status_code == 204
    assert api.get("/api/sesion", headers=cab).status_code == 401


def test_flujo_http_de_captura(api, h):
    cab = entrar(api, "jgomez")
    gasto = {"descripcion": "Arroz", "tipo_item": "BIEN", "cantidad": "1", "cod_unidad": "5", "cod_forma": "1",
             "cod_lugar": "6", "valor_pagado": "2500", "cod_frecuencia": "3", "tipo_gasto": "1"}
    r = api.post(f"/api/hogares/{h[2]}/dias/5/gastos", json=gasto, headers=cab)
    assert r.status_code == 201 and r.json()["numero_orden"] == 3
    dia = api.get(f"/api/hogares/{h[2]}/dias/5", headers=cab).json()
    assert len(dia["gastos"]) == 3 and dia["jornada"]["fecha"] == "2026-10-31"

    r = api.post(f"/api/hogares/{h[2]}/dias/8/gastos", json={**gasto, "tipo_gasto": "2"}, headers=cab)
    assert r.status_code == 422 and r.json()["codigo"] == "ORA-02290" and "CK_GD_PERSONAL_7" in r.json()["detail"]
    r = api.post(f"/api/hogares/{h[2]}/dias/5/gastos", json={**gasto, "cantidad": "-1"}, headers=cab)
    assert r.status_code == 422 and r.json()["codigo"] == "VALIDACION"
    r = api.put(f"/api/hogares/{h[2]}/dias/5/gastos/1", json=gasto, headers=cab)
    assert r.status_code == 403


def test_conflicto_y_no_encontrado(api, h):
    cab = entrar(api, "pruiz")
    gasto = {"descripcion": "Pan", "tipo_item": "BIEN", "cantidad": "1", "cod_unidad": "5", "cod_forma": "1",
             "valor_pagado": "1000", "cod_frecuencia": "2", "tipo_gasto": "1"}
    r = api.post(f"/api/hogares/{h[1]}/dias/6/gastos", json=gasto, headers=cab)
    assert r.status_code == 409 and r.json()["codigo"] == "ORA-20010"
    assert api.get("/api/hogares/999999/avance", headers=cab).status_code == 404


def test_supervisor_y_reportes(api, h):
    cab = entrar(api, "mlopez")
    assert len(api.get("/api/hogares", headers=cab).json()) == 3
    caso = api.get(f"/api/hogares/{h[2]}/revision-caso", headers=cab).json()
    assert not caso["puede_aprobar"]
    assert api.get("/api/reportes/carga_encuestador", headers=cab).json()[0]["hogares"] == 3
    assert api.get("/api/catalogos", headers=cab).json()["grupo_alimento"][0]["codigo"] == "01"
