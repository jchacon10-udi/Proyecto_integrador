"""Casos de uso y reglas de negocio. Equivalen a las pruebas C, N y F de 09_pruebas.sql."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.errores import Conflicto, CredencialesInvalidas, ErrorNegocio, NoAutorizado
from app.modelos import (CaracteristicaEntrada, CierreEntrada, CierreJornada, ComidaEntrada, Conclusion, Correccion,
                         DecisionSupervisor, HallazgoEntrada, HogarActualizacion, ResumenEntrada, Verificacion,
                         VisitaEntrada)
from conftest import HOY, gasto, hogar_nuevo


@contextmanager
def falla(tipo=ErrorNegocio, codigo: str | None = None):
    with pytest.raises(tipo) as e:
        yield
    if codigo:
        assert e.value.codigo == codigo, e.value.mensaje


def comida(**cambios):
    base = dict(descripcion="Almuerzo corriente", cod_tipo_comida="2", cantidad=Decimal(1), cod_forma="1",
                cod_lugar="18", valor_pagado=Decimal(12000), cod_frecuencia="3", tipo_gasto="1")
    return ComidaEntrada(**{**base, **cambios})


# ====================================================================== CU-01
def test_inicio_de_sesion_con_pbkdf2(s):
    token, usuario = s.iniciar_sesion("pruiz", "enph-demo")
    assert usuario.rol == "INFORMANTE"
    assert s.usuario_de_token(token).nombre_usuario == "pruiz"
    with falla(CredencialesInvalidas):
        s.iniciar_sesion("pruiz", "otra")
    with falla(CredencialesInvalidas):
        s.usuario_de_token("token-falso")


def test_cada_usuario_ve_solo_sus_hogares(s, u, h):
    assert {a.id_hogar for a in s.hogares(u["pruiz"])} == {h[1]}
    assert {a.id_hogar for a in s.hogares(u["mlopez"])} == {h[1], h[2], h[3]}  # el supervisor ve todos
    with falla(NoAutorizado, "ORA-20060"):
        s.avance(u["pruiz"], h[2])


# ====================================================================== C: CRUD de tablas básicas
def test_c01_crud_gasto_diario(s, u, h):
    g = s.registrar_gasto(u["jgomez"], h[2], 5, gasto())
    assert g.numero_orden == 3 and g.id_usuario_registro == u["jgomez"].id_usuario
    assert [x.descripcion for x in s.dia(u["jgomez"], h[2], 5)["gastos"]][-1] == "Arroz blanco"
    g = s.actualizar_gasto(u["ccastro"], h[2], 5, 3, gasto(valor_pagado=Decimal(2700)))
    assert g.valor_pagado == 2700 and g.id_usuario_registro == u["ccastro"].id_usuario
    s.eliminar_gasto(u["ccastro"], h[2], 5, 3)
    assert len(s.dia(u["jgomez"], h[2], 5)["gastos"]) == 2


def test_c02_crud_comida_fuera(s, u, h):
    c = s.registrar_comida(u["jgomez"], h[2], 3, comida(a_domicilio=True))
    assert c.numero_orden == 1 and c.a_domicilio
    s.actualizar_comida(u["ccastro"], h[2], 3, 1, comida(valor_pagado=Decimal(15000)))
    assert s.dia(u["jgomez"], h[2], 3)["comidas"][0].valor_pagado == 15000
    s.eliminar_comida(u["ccastro"], h[2], 3, 1)
    assert s.dia(u["jgomez"], h[2], 3)["comidas"] == []


def test_c03_hogar_y_asignacion(s, u):
    nuevo = s.crear_hogar(u["ccastro"], hogar_nuevo("ENPH-PRUEBA-0100", HOY.date()))
    assert nuevo.estado == "ASIGNADO" and nuevo.fecha_fin == HOY.date() + timedelta(days=13)
    datos = HogarActualizacion(**{**nuevo.model_dump(include=set(HogarActualizacion.model_fields)), "total_personas": 5})
    assert s.actualizar_hogar(u["ccastro"], nuevo.id_hogar, datos).total_personas == 5
    s.asignar(u["mlopez"], nuevo.id_hogar, u["jgomez"].id_usuario)
    assert {a["usuario"].nombre_usuario for a in s.hogar(u["mlopez"], nuevo.id_hogar)["asignaciones"]} == {
        "ccastro", "jgomez"}
    with falla(ErrorNegocio, "ORA-00001"):
        s.crear_hogar(u["ccastro"], hogar_nuevo("ENPH-PRUEBA-0100", HOY.date()))


def test_c04_visitas(s, u, h):
    v = s.registrar_visita(u["ccastro"], h[2], VisitaEntrada(
        fecha_hora_inicio=datetime(2026, 11, 1, 17, 0), fecha_hora_fin=datetime(2026, 11, 1, 17, 45),
        cod_resultado="EI", pendientes="Días 6 a 14", proxima_visita=datetime(2026, 11, 4, 17, 0)))
    assert v.numero_visita == 2
    v = s.actualizar_visita(u["ccastro"], h[2], 2, VisitaEntrada(**{**v.model_dump(exclude={"numero_visita"}),
                                                                   "cod_resultado": "AT"}))
    assert v.cod_resultado == "AT"
    with falla(ErrorNegocio, "ORA-02290"):
        s.registrar_visita(u["ccastro"], h[2], VisitaEntrada(fecha_hora_inicio=datetime(2026, 11, 2, 9),
                                                             fecha_hora_fin=datetime(2026, 11, 2, 8),
                                                             cod_resultado="EI"))


def test_c05_capitulo_c_y_resumen(s, u, h):
    s.guardar_caracteristica(u["ccastro"], h[2], "01", CaracteristicaEntrada(cod_frecuencia="2"))
    s.guardar_caracteristica(u["ccastro"], h[2], "05", CaracteristicaEntrada(
        cod_frecuencia="5", valor_ultima_compra=Decimal(30000), comprara_14_dias=False))
    s.guardar_resumen(u["ccastro"], h[2], "96", ResumenEntrada(valor_total=Decimal(80000)))
    datos = s.caracteristicas(u["ccastro"], h[2])
    assert sum(1 for g in datos["grupos"] if g["registro"]) == 2 and len(datos["grupos"]) == 25
    assert datos["resumen_mercado"][0].cod_mercado == "96"


def test_c06_avance_y_dia_6_del_ejemplo(s, u, h):
    datos = s.avance(u["pruiz"], h[1])
    assert datos["avance"].dias_completos == 14 and datos["avance"].valor_total == 224800
    dia6 = s.dia(u["pruiz"], h[1], 6)
    assert dia6["jornada"].fecha.isoformat() == "2026-10-08"
    assert len(dia6["gastos"]) == 9 and len(dia6["comidas"]) == 3
    assert dia6["gastos"][1].valor_pagado == 4200  # corregido tras la crítica


def test_c07_historial_del_hallazgo(s, u, h):
    hallazgo = s.revisiones(u["acritico"], h[1])[0].hallazgos[0]
    assert hallazgo.estado == "VERIFICADO"
    assert [e.estado for e in hallazgo.eventos] == ["ABIERTO", "CORREGIDO", "VERIFICADO"]


def test_c08_reportes(s, u):
    formas = {f["cod_forma"]: f for f in s.reporte(u["mlopez"], "gasto_por_forma")}
    assert formas["1"]["renglones"] == 46 and formas["1"]["valor_total"] == 257300  # mismo R03 de Oracle
    assert formas["3"]["valor_total"] == 5500
    assert s.reporte(u["acritico"], "hallazgos")[0]["eventos"] == 3
    with falla(NoAutorizado):
        s.reporte(u["pruiz"], "gasto_por_forma")


# ====================================================================== N: reglas declarativas (CHECK, FK, UNIQUE)
@pytest.mark.parametrize("cambios, restriccion", [
    (dict(tipo_gasto="2"), "CK_GD_PERSONAL_7"),                                          # N01 personal en el día 8
    (dict(cod_forma="3", cod_frecuencia=None), "CK_GD_COMPRA"),                          # N02 regalo con lugar
    (dict(cod_unidad=None), "CK_GD_UNIDAD"),                                             # N03 bien sin unidad
    (dict(cod_unidad="8"), "CK_GD_OTRA_UNIDAD"),                                         # N04 «Otra» sin especificar
    (dict(cod_frecuencia=None), "CK_GD_COMPRA"),                                         # N06 compra sin frecuencia
    (dict(tipo_item="SERVICIO"), "CK_GD_UNIDAD"),                                        # servicio con unidad
    (dict(equivalencia_g_cc=Decimal(500)), "CK_GD_EQUIVALENCIA"),                         # equivalencia en libra
    (dict(cod_forma="7"), "CK_GD_OTRA_FORMA"),                                           # forma «Otra» sin especificar
    (dict(cod_frecuencia="1"), "CK_GD_FRECUENCIA"),                                      # frecuencia «Nunca»
])
def test_reglas_del_capitulo_d(s, u, h, cambios, restriccion):
    with falla(ErrorNegocio, "ORA-02290") as e:
        s.registrar_gasto(u["jgomez"], h[2], 8, gasto(**cambios))


def test_n05_d1_no_admite_na():
    with pytest.raises(ValidationError):
        comida(tipo_gasto="NA")


def test_n07_catalogo_inexistente(s, u, h):
    with falla(ErrorNegocio, "ORA-02291"):
        s.registrar_gasto(u["jgomez"], h[2], 5, gasto(cod_lugar="99"))


def test_n09_dia_fuera_del_periodo(s, u, h):
    with falla(ErrorNegocio, "ORA-20001"):
        s.registrar_gasto(u["jgomez"], h[2], 15, gasto())


def test_n11_capitulo_c_bisemana(s, u, h):
    with falla(ErrorNegocio, "ORA-02290"):
        s.guardar_caracteristica(u["ccastro"], h[2], "02", CaracteristicaEntrada(
            cod_frecuencia="3", valor_ultima_compra=Decimal(1000)))


def test_d1_personal_solo_dias_1_a_7(s, u, h):
    with falla(ErrorNegocio, "ORA-02290"):
        s.registrar_comida(u["jgomez"], h[2], 9, comida(tipo_gasto="2"))


# ====================================================================== N: reglas de procedimientos y disparadores
def test_n13_captura_en_hogar_aprobado(s, u, h):
    with falla(Conflicto, "ORA-20010"):
        s.registrar_gasto(u["pruiz"], h[1], 6, gasto())


def test_n14_informante_no_asignado(s, u, h):
    with falla(NoAutorizado, "ORA-20060"):
        s.registrar_gasto(u["pruiz"], h[2], 5, gasto())


def test_informante_no_edita_ni_borra(s, u, h):
    with falla(NoAutorizado):
        s.actualizar_gasto(u["jgomez"], h[2], 5, 1, gasto())
    with falla(NoAutorizado):
        s.eliminar_gasto(u["jgomez"], h[2], 5, 1)


def test_dia_futuro(s, u):
    nuevo = s.crear_hogar(u["ccastro"], hogar_nuevo("ENPH-PRUEBA-0200", HOY.date())).id_hogar
    s.asignar(u["mlopez"], nuevo, u["jgomez"].id_usuario)
    # El día 1 es hoy y se admite; el día 2 es mañana y se rechaza.
    s.iniciar_captura(u["ccastro"], nuevo)
    s.registrar_gasto(u["jgomez"], nuevo, 1, gasto())
    with falla(ErrorNegocio, "ORA-20063"):
        s.registrar_gasto(u["jgomez"], nuevo, 2, gasto())


def test_iniciar_captura_exige_asignado_e_informante(s, u, h):
    with falla(ErrorNegocio, "ORA-20062"):
        s.iniciar_captura(u["ccastro"], h[3])
    with falla(Conflicto, "ORA-20061"):
        s.iniciar_captura(u["ccastro"], h[2])
    with falla(ErrorNegocio, "ORA-20064"):
        s.registrar_gasto(u["ccastro"], h[3], 1, gasto())


def test_n16_total_de_renglones_incorrecto(s, u, h):
    with falla(ErrorNegocio, "ORA-20065"):
        s.cerrar_jornada(u["jgomez"], h[2], 5, CierreJornada(total_renglones=7))
    assert s.cerrar_jornada(u["jgomez"], h[2], 5, CierreJornada(total_renglones=2)).completa


def test_n17_cerrar_con_jornadas_incompletas(s, u, h):
    with falla(ErrorNegocio, "ORA-20067"):
        s.cerrar_cuadernillo(u["ccastro"], h[2], CierreEntrada(gasto_evento_especial=False, cod_forma_pago="3"))


def test_n18_critica_solo_por_critico(s, u, hogar_cerrado):
    with falla(NoAutorizado):
        s.iniciar_revision(u["ccastro"], hogar_cerrado)


def test_n19_revision_concluida_es_inmutable(s, u, h):
    with falla(Conflicto, "ORA-20032"):
        s.registrar_hallazgo(u["acritico"], h[1], 1, HallazgoEntrada(capitulo="A", descripcion="Otro"))


def test_n20_verificado_no_vuelve_a_corregirse(s, u, h):
    with falla(Conflicto, "ORA-20045"):
        s.corregir_hallazgo(u["ccastro"], h[1], 1, 1, Correccion(respuesta="Otra vez"))


def test_capitulos_a_b_c_bloqueados_al_aprobar(s, u, h):
    with falla(Conflicto):
        s.guardar_caracteristica(u["ccastro"], h[1], "01", CaracteristicaEntrada(cod_frecuencia="2"))


# ====================================================================== F: cierre, crítica y aprobación
def test_flujo_completo(s, u, hogar_cerrado):
    hid, enc, sup, cri = hogar_cerrado, u["ccastro"], u["mlopez"], u["acritico"]
    assert s.revisar_caso(sup, hid)["puede_aprobar"]                           # F01 cierre: CERRADO

    rev = s.iniciar_revision(cri, hid).numero_revision
    with falla(Conflicto, "ORA-20074"):
        s.iniciar_revision(cri, hid)                                           # una revisión a la vez
    with falla(Conflicto, "ORA-20072"):                                        # revisión en curso
        s.decidir_supervisor(sup, hid, DecisionSupervisor(decision="APROBADO"))
    with falla(ErrorNegocio, "ORA-02290"):                                     # F02 hallazgo D sin día
        s.registrar_hallazgo(cri, hid, rev, HallazgoEntrada(capitulo="D", descripcion="Sin día"))
    hall = s.registrar_hallazgo(cri, hid, rev, HallazgoEntrada(capitulo="D", dia_encuesta=3,
                                                               descripcion="Valor dudoso")).numero_hallazgo
    s.concluir_revision(cri, hid, rev, Conclusion())
    assert s.revisiones(cri, hid)[0].estado == "OBSERVADA"

    with falla(Conflicto, "ORA-20078"):                                        # F03 saltar a VERIFICADO
        s.verificar_hallazgo(cri, hid, rev, hall, Verificacion(aceptada=True))
    with falla(Conflicto, "ORA-20071"):                                        # F04 aprobar con ABIERTO
        s.decidir_supervisor(sup, hid, DecisionSupervisor(decision="APROBADO"))
    with falla(ErrorNegocio, "ORA-02290"):                                     # F05 devolver sin motivo
        s.decidir_supervisor(sup, hid, DecisionSupervisor(decision="DEVUELTO"))
    assert s.decidir_supervisor(sup, hid, DecisionSupervisor(
        decision="DEVUELTO", observacion="Revisar día 3")).estado == "DEVUELTO"  # F06

    s.actualizar_gasto(enc, hid, 3, 1, gasto(valor_pagado=Decimal(2600)))   # CU-07: corrige el dato
    s.cerrar_jornada(enc, hid, 3, CierreJornada(total_renglones=1))
    s.corregir_hallazgo(enc, hid, rev, hall, Correccion(respuesta="Valor corregido"))
    s.verificar_hallazgo(cri, hid, rev, hall, Verificacion(aceptada=False, comentario="Falta soporte"))
    assert s.revisiones(cri, hid)[0].hallazgos[0].estado == "ABIERTO"          # rechazo: vuelve a ABIERTO
    s.corregir_hallazgo(enc, hid, rev, hall, Correccion(respuesta="Factura adjunta"))
    s.verificar_hallazgo(cri, hid, rev, hall, Verificacion(aceptada=True))
    s.cerrar_cuadernillo(enc, hid, CierreEntrada(gasto_evento_especial=True, cod_forma_pago="6",
                                                 otra_forma_pago="Transferencia"))
    assert s.decidir_supervisor(sup, hid, DecisionSupervisor(decision="APROBADO")).estado == "APROBADO"
    eventos = s.revisiones(sup, hid)[0].hallazgos[0].eventos
    assert [e.estado for e in eventos] == ["ABIERTO", "CORREGIDO", "ABIERTO", "CORREGIDO", "VERIFICADO"]
    with falla(Conflicto, "ORA-20069"):
        s.decidir_supervisor(sup, hid, DecisionSupervisor(decision="DEVUELTO", observacion="x"))


def test_cierre_exige_25_grupos(s, u, hogar_cerrado):
    s.decidir_supervisor(u["mlopez"], hogar_cerrado, DecisionSupervisor(decision="DEVUELTO", observacion="C"))
    s.eliminar_caracteristica(u["ccastro"], hogar_cerrado, "25")
    with falla(ErrorNegocio, "ORA-20068"):
        s.cerrar_cuadernillo(u["ccastro"], hogar_cerrado, CierreEntrada(gasto_evento_especial=False,
                                                                       cod_forma_pago="3"))


def test_forma_de_pago_otra_exige_detalle(s, u, h):
    with falla(ErrorNegocio, "ORA-02290"):
        s.cerrar_cuadernillo(u["ccastro"], h[2], CierreEntrada(gasto_evento_especial=False, cod_forma_pago="6"))


def test_transaccion_revierte_si_falla(s, u, h):
    """Si una operación falla a mitad de camino, nada queda escrito (ROLLBACK)."""
    antes = len(s.dia(u["jgomez"], h[2], 5)["gastos"])
    with pytest.raises(RuntimeError):
        with s.repo.transaccion() as r:
            r.registrar_gasto(h[2], 5, u["jgomez"].id_usuario, gasto())
            raise RuntimeError("falla simulada")
    assert len(s.dia(u["jgomez"], h[2], 5)["gastos"]) == antes


@pytest.mark.skipif(os.environ.get("ENPH_PRUEBAS_ORACLE") != "1", reason="solo contra Oracle")
def test_oracle_es_la_ultima_barrera(s, u, h):
    """Sin pasar por los servicios, Oracle rechaza igual: CHECK, disparador y procedimiento."""
    with falla(ErrorNegocio, "ORA-02290"):
        with s.repo.transaccion() as r:
            r.registrar_gasto(h[2], 8, u["jgomez"].id_usuario, gasto(tipo_gasto="2"))
    with falla(Conflicto, "ORA-20010"):
        with s.repo.transaccion() as r:
            r.actualizar_gasto(h[1], 6, 1, u["ccastro"].id_usuario, gasto())
    with falla(NoAutorizado, "ORA-20060"):
        with s.repo.transaccion() as r:
            r.registrar_gasto(h[2], 5, u["pruiz"].id_usuario, gasto())
    with falla(Conflicto, "ORA-20069"):  # un caso ya aprobado no vuelve a decidirse
        with s.repo.transaccion() as r:
            r.revisar_supervisor(h[1], u["mlopez"].id_usuario, "APROBADO", None)


def test_administracion_de_usuarios(s, u):
    from app.modelos import UsuarioNuevo
    nuevo = s.crear_usuario(u["mlopez"], UsuarioNuevo(nombre_usuario="lgomez", nombre_completo="Laura Gómez",
                                                      correo="lgomez@demo.enph.local", rol="CRITICO_DIGITADOR",
                                                      clave="clave-segura-1"))
    assert nuevo.rol == "CRITICO_DIGITADOR" and nuevo.estado == "ACTIVO"
    assert s.iniciar_sesion("lgomez", "clave-segura-1")[1].id_usuario == nuevo.id_usuario
    assert s.cambiar_estado_usuario(u["mlopez"], nuevo.id_usuario, "INACTIVO").estado == "INACTIVO"
    with falla(CredencialesInvalidas):
        s.iniciar_sesion("lgomez", "clave-segura-1")
    with falla(NoAutorizado):
        s.crear_usuario(u["ccastro"], UsuarioNuevo(nombre_usuario="otro", nombre_completo="Otro",
                                                   correo="otro@demo.enph.local", rol="INFORMANTE", clave="12345678"))
    with falla(ErrorNegocio, "ORA-00001"):
        s.crear_usuario(u["mlopez"], UsuarioNuevo(nombre_usuario="pruiz", nombre_completo="Repetido",
                                                  correo="nuevo@demo.enph.local", rol="INFORMANTE", clave="12345678"))
