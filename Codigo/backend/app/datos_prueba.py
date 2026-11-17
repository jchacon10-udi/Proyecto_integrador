"""Datos de prueba del modo en memoria: el mismo recorrido de 08_datos_prueba.sql.

Pasa por los servicios, así que cada paso cumple las reglas de negocio:
  Hogar 1: 14 días -> cierre -> crítica -> devolución -> corrección -> nuevo cierre
           -> verificación -> APROBADO. El día 6 es el ejemplo oficial del cuadernillo.
  Hogar 2: EN_CAPTURA con días 1 a 5 diligenciados.
  Hogar 3: ASIGNADO, sin iniciar.
Contraseña de todas las cuentas: enph-demo.
"""
from datetime import date, datetime
from decimal import Decimal

from .modelos import (CaracteristicaEntrada, CierreEntrada, CierreJornada, ComidaEntrada, Conclusion, Correccion,
                      DecisionSupervisor, GastoEntrada, HallazgoEntrada, HogarNuevo, ResumenEntrada, Verificacion,
                      VisitaEntrada)
from .repositorio.memoria import RepositorioMemoria
from .servicios import Servicios

USUARIOS = [  # (rol, usuario, nombre, hash de enph-demo igual al de 08_datos_prueba.sql)
    (1, "pruiz", "Paola Ruiz Salazar", "dad71b17800e94daf90120a145a459b0a781432295d15b17d50ad6725ad9b08f"),
    (2, "ccastro", "Carlos Castro Méndez", "176a86c7d740d85ee373020c2a7009685bc4f19a197c2f32634509eef8c6db32"),
    (3, "mlopez", "María López Torres", "f9e37a0a5a28f6ab17061055498f3fadd63374f568f080076f90f6ae28937b66"),
    (4, "acritico", "Andrés Rincón Díaz", "2a68feb4057f2b4d4aafae1460f87e3d211338d4458eaf646e9a9564c5d2a9f2"),
    (1, "jgomez", "Julián Gómez Pardo", "f9faa5f281046c7cbe1d23ae9aaf6ebe726f648cae6789942d9bf762808b9c57"),
]


def gasto(descripcion, cantidad, unidad, forma, lugar, valor, frecuencia, tipo, item="BIEN", otra_unidad=None,
          equivalencia=None):
    return GastoEntrada(descripcion=descripcion, tipo_item=item, cantidad=Decimal(str(cantidad)), cod_unidad=unidad,
                        otra_unidad=otra_unidad, equivalencia_g_cc=equivalencia, cod_forma=forma, cod_lugar=lugar,
                        valor_pagado=Decimal(valor), cod_frecuencia=frecuencia, tipo_gasto=tipo)


def comida(descripcion, tipo_comida, cantidad, lugar, valor, frecuencia, tipo, domicilio):
    return ComidaEntrada(descripcion=descripcion, cod_tipo_comida=tipo_comida, cantidad=Decimal(str(cantidad)),
                         cod_forma="1", cod_lugar=lugar, valor_pagado=Decimal(valor), cod_frecuencia=frecuencia,
                         tipo_gasto=tipo, a_domicilio=domicilio)


DIA_TIPICO = [gasto("Pan tajado integral", 1, "8", "1", "6", 4500, "2", "1", otra_unidad="Paquete",
                    equivalencia=Decimal(500)),
              gasto("Leche entera en bolsa", 1, "2", "1", "6", 3800, "2", "1")]

DIA_6 = [  # Ejemplo oficial del Cuadernillo 2 (capítulo D)
    gasto("Hígado de res", 2, "5", "1", "1", 14000, "3", "1"),
    gasto("Manzana grande", 1, "6", "1", "10", 4000, "4", "1"),
    gasto("Cilantro", 1, "8", "1", "10", 300, "3", "1", otra_unidad="Manojo"),
    gasto("Gaseosa", 2, "2", "3", None, 3500, None, "NA"),
    gasto("Huevos", 4, "8", "1", "6", 1200, "2", "1", otra_unidad="Huevo grande"),
    gasto("Pan blandito pequeño", 10, "8", "3", None, 2000, None, "NA", otra_unidad="Pan pequeño"),
    gasto("Pasaje en bus urbano", 2, None, "1", None, 3200, "2.1", "2", item="SERVICIO"),
    gasto("Gasolina corriente", 7, "8", "1", "16", 58000, "3", "2", otra_unidad="Galón", equivalencia=Decimal(3785)),
    gasto("Plátano verde mediano", 1, "8", "5", None, 8000, None, "1", otra_unidad="Racimo"),
]

COMIDAS_DIA_6 = [comida("Sándwich de pollo", "3", 0.5, "19", 6000, "5", "1", True),
                 comida("Ensalada de frutas", "1", 1, "19", 6500, "5", "1", False),
                 comida("Almuerzo corriente", "2", 1, "18", 10000, "9", "2", False)]


def hogar(codigo, region, depto, municipio, direccion, inicio, hogares=1, numero=1, personas=1, **otros):
    return HogarNuevo(codigo_operativo=codigo, region=region, departamento=depto, municipio=municipio, clase="1",
                      direccion=direccion, total_hogares_vivienda=hogares, hogar_numero=numero,
                      total_personas=personas, fecha_inicio=inicio, **otros)


def visita(inicio, fin, resultado, pendientes=None, proxima=None):
    f = lambda t: datetime.fromisoformat(t) if t else None
    return VisitaEntrada(fecha_hora_inicio=f(inicio), fecha_hora_fin=f(fin), cod_resultado=resultado,
                         pendientes=pendientes, proxima_visita=f(proxima))


def cargar(s: Servicios):
    r: RepositorioMemoria = s.repo
    with r.transaccion():
        ids = {u: r.crear_usuario(rol, u, nombre, f"{u}@demo.enph.local", f"pbkdf2_sha256$200000$enph-{u}${h}")
               for rol, u, nombre, h in USUARIOS}
    us = {n: r.usuario(i) for n, i in ids.items()}
    pruiz, ccastro, mlopez, critico, jgomez = (us[n] for n in ("pruiz", "ccastro", "mlopez", "acritico", "jgomez"))

    h1 = s.crear_hogar(ccastro, hogar("ENPH-11001-0001", "5", "11", "11001", "Calle 45 # 13-20 apto 301",
                                      date(2026, 10, 3), personas=4, sector="0042", seccion="03", manzana="017",
                                      segmento="2", ciclo="4", edificacion_numero="12", vivienda_numero="1",
                                      barrio_vereda="Chapinero", telefono="3000000001",
                                      responsable_nombre="Paola Ruiz Salazar", responsable_orden=2)).id_hogar
    h2 = s.crear_hogar(ccastro, hogar("ENPH-68001-0002", "2", "68", "68001", "Carrera 33 # 48-15", date(2026, 10, 27),
                                      hogares=2, personas=3, sector="0110", seccion="07", manzana="005",
                                      segmento="1", ciclo="4", edificacion_numero="3", vivienda_numero="2",
                                      barrio_vereda="Cabecera del Llano", telefono="3000000002",
                                      responsable_nombre="Julián Gómez Pardo", responsable_orden=1)).id_hogar
    s.crear_hogar(ccastro, hogar("ENPH-68001-0003", "2", "68", "68001", "Calle 56 # 30-12", date(2026, 11, 20),
                                 personas=2))
    for u in (pruiz, mlopez, critico):
        s.asignar(mlopez, h1, u.id_usuario)
    for u in (jgomez, mlopez, critico):
        s.asignar(mlopez, h2, u.id_usuario)

    # ---------------------------------------------------------------- hogar 1
    s.registrar_visita(ccastro, h1, visita("2026-10-03 09:00", "2026-10-03 10:10", "EI", "Capítulo D en curso",
                                           "2026-10-05 09:00"))
    s.registrar_visita(ccastro, h1, visita("2026-10-08 18:00", "2026-10-08 18:40", "EI", "Días 7 a 14",
                                           "2026-10-16 18:00"))
    s.registrar_visita(ccastro, h1, visita("2026-10-16 18:00", "2026-10-16 19:00", "EC"))
    for n in range(1, 26):
        if n % 5 == 0:  # compra mensual: aplican C3.1 y C3.2
            dto = CaracteristicaEntrada(cod_frecuencia="5", valor_ultima_compra=Decimal(n * 2000), comprara_14_dias=True)
        else:
            dto = CaracteristicaEntrada(cod_frecuencia="3" if n % 2 == 0 else "2.1")
        s.guardar_caracteristica(ccastro, h1, f"{n:02d}", dto)
    s.guardar_resumen(ccastro, h1, "98", ResumenEntrada(valor_total=Decimal(350000)))
    s.iniciar_captura(ccastro, h1)
    for d in range(1, 15):
        for g in (DIA_6 if d == 6 else DIA_TIPICO):
            s.registrar_gasto(pruiz, h1, d, g)
    for c in COMIDAS_DIA_6:
        s.registrar_comida(pruiz, h1, 6, c)
    for d in range(1, 15):
        s.cerrar_jornada(pruiz, h1, d, CierreJornada(total_renglones=12 if d == 6 else 2))
    cierre = CierreEntrada(gasto_evento_especial=False, cod_forma_pago="3", observaciones="Cuadernillo completo")
    s.cerrar_cuadernillo(ccastro, h1, cierre)

    rev = s.iniciar_revision(critico, h1).numero_revision
    hall = s.registrar_hallazgo(critico, h1, rev, HallazgoEntrada(
        capitulo="D", dia_encuesta=6,
        descripcion="Renglón 2 (manzana grande): el valor no coincide con la factura conservada por el hogar.")
    ).numero_hallazgo
    s.concluir_revision(critico, h1, rev, Conclusion(resultado="Un hallazgo en el capítulo D, día 6."))
    s.decidir_supervisor(mlopez, h1, DecisionSupervisor(decision="DEVUELTO",
                                                        observacion="Atender hallazgo de crítica del día 6."))
    s.actualizar_gasto(ccastro, h1, 6, 2, DIA_6[1].model_copy(update={"valor_pagado": Decimal(4200)}))
    s.corregir_hallazgo(ccastro, h1, rev, hall, Correccion(respuesta="Valor ajustado a $4.200 según factura."))
    s.cerrar_cuadernillo(ccastro, h1, cierre.model_copy(update={"observaciones": "Cierre tras corrección de crítica"}))
    s.verificar_hallazgo(critico, h1, rev, hall, Verificacion(aceptada=True,
                                                             comentario="Corrección verificada contra la factura."))
    s.decidir_supervisor(mlopez, h1, DecisionSupervisor(decision="APROBADO"))

    # ---------------------------------------------------------------- hogar 2
    s.registrar_visita(ccastro, h2, visita("2026-10-27 17:30", "2026-10-27 18:30", "EI", "Capítulo D",
                                           "2026-10-29 17:30"))
    s.iniciar_captura(ccastro, h2)
    for d in range(1, 6):
        for g in DIA_TIPICO:
            s.registrar_gasto(jgomez, h2, d, g)
    s.registrar_comida(jgomez, h2, 2, comida("Empanadas", "4", 3, "13", 4500, "2.1", "2", False))
    for d in range(1, 5):
        s.cerrar_jornada(jgomez, h2, d, CierreJornada(total_renglones=3 if d == 2 else 2))
