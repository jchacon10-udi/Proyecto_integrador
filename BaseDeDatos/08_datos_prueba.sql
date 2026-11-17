-- =====================================================================
-- ENPH - 08. Datos de prueba ficticios
-- Recorre el flujo completo usando los procedimientos almacenados:
--   Hogar 1: captura 14 días -> cierre -> crítica -> devolución -> corrección
--            -> nuevo cierre -> verificación -> APROBADO
--   Hogar 2: EN_CAPTURA con días 1-5 diligenciados
--   Hogar 3: ASIGNADO (aún sin iniciar)
-- El día 6 del hogar 1 reproduce el ejemplo oficial del Cuadernillo 2 (Paola).
-- Contraseña de todas las cuentas de demostración: enph-demo (hash PBKDF2).
-- =====================================================================
SET DEFINE OFF
SET SERVEROUTPUT ON

INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
VALUES (1, 'pruiz', 'Paola Ruiz Salazar', 'pruiz@demo.enph.local',
        'pbkdf2_sha256$200000$enph-pruiz$dad71b17800e94daf90120a145a459b0a781432295d15b17d50ad6725ad9b08f');
INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
VALUES (2, 'ccastro', 'Carlos Castro Méndez', 'ccastro@demo.enph.local',
        'pbkdf2_sha256$200000$enph-ccastro$176a86c7d740d85ee373020c2a7009685bc4f19a197c2f32634509eef8c6db32');
INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
VALUES (3, 'mlopez', 'María López Torres', 'mlopez@demo.enph.local',
        'pbkdf2_sha256$200000$enph-mlopez$f9e37a0a5a28f6ab17061055498f3fadd63374f568f080076f90f6ae28937b66');
INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
VALUES (4, 'acritico', 'Andrés Rincón Díaz', 'acritico@demo.enph.local',
        'pbkdf2_sha256$200000$enph-acritico$2a68feb4057f2b4d4aafae1460f87e3d211338d4458eaf646e9a9564c5d2a9f2');
INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
VALUES (1, 'jgomez', 'Julián Gómez Pardo', 'jgomez@demo.enph.local',
        'pbkdf2_sha256$200000$enph-jgomez$f9faa5f281046c7cbe1d23ae9aaf6ebe726f648cae6789942d9bf762808b9c57');

INSERT INTO HOGAR (CODIGO_OPERATIVO, REGION, DEPARTAMENTO, MUNICIPIO, CLASE, SECTOR, SECCION, MANZANA,
       SEGMENTO, CICLO, EDIFICACION_NUMERO, VIVIENDA_NUMERO, TOTAL_HOGARES_VIVIENDA, HOGAR_NUMERO,
       TOTAL_PERSONAS, BARRIO_VEREDA, DIRECCION, TELEFONO, RESPONSABLE_NOMBRE, RESPONSABLE_ORDEN, FECHA_INICIO)
VALUES ('ENPH-11001-0001', '5', '11', '11001', '1', '0042', '03', '017', '2', '4', '12', '1', 1, 1,
        4, 'Chapinero', 'Calle 45 # 13-20 apto 301', '3000000001', 'Paola Ruiz Salazar', 2, DATE '2026-10-03');
INSERT INTO HOGAR (CODIGO_OPERATIVO, REGION, DEPARTAMENTO, MUNICIPIO, CLASE, SECTOR, SECCION, MANZANA,
       SEGMENTO, CICLO, EDIFICACION_NUMERO, VIVIENDA_NUMERO, TOTAL_HOGARES_VIVIENDA, HOGAR_NUMERO,
       TOTAL_PERSONAS, BARRIO_VEREDA, DIRECCION, TELEFONO, RESPONSABLE_NOMBRE, RESPONSABLE_ORDEN, FECHA_INICIO)
VALUES ('ENPH-68001-0002', '2', '68', '68001', '1', '0110', '07', '005', '1', '4', '3', '2', 2, 1,
        3, 'Cabecera del Llano', 'Carrera 33 # 48-15', '3000000002', 'Julián Gómez Pardo', 1, DATE '2026-10-27');
INSERT INTO HOGAR (CODIGO_OPERATIVO, REGION, DEPARTAMENTO, MUNICIPIO, CLASE, DIRECCION,
       TOTAL_HOGARES_VIVIENDA, HOGAR_NUMERO, TOTAL_PERSONAS, FECHA_INICIO)
VALUES ('ENPH-68001-0003', '2', '68', '68001', '1', 'Calle 56 # 30-12', 1, 1, 2, DATE '2026-11-20');

DECLARE
  v_pruiz NUMBER; v_ccastro NUMBER; v_mlopez NUMBER; v_critico NUMBER; v_jgomez NUMBER;
  v_h1 NUMBER; v_h2 NUMBER; v_h3 NUMBER;
  v_ord NUMBER; v_rev NUMBER; v_hall NUMBER;

  FUNCTION id_usuario_de(p VARCHAR2) RETURN NUMBER IS v NUMBER;
  BEGIN SELECT ID_USUARIO INTO v FROM USUARIO WHERE NOMBRE_USUARIO = p; RETURN v; END;
  FUNCTION id_hogar_de(p VARCHAR2) RETURN NUMBER IS v NUMBER;
  BEGIN SELECT ID_HOGAR INTO v FROM HOGAR WHERE CODIGO_OPERATIVO = p; RETURN v; END;

  -- Día típico: pan y leche comprados en la tienda del barrio.
  PROCEDURE dia_tipico(p_h NUMBER, p_d NUMBER, p_u NUMBER) IS o NUMBER;
  BEGIN
    PR_REGISTRAR_GASTO(p_h, p_d, p_u, 'Pan tajado integral', 'BIEN', 1, '8', 'Paquete', 500,
                       '1', NULL, '6', 4500, '2', '1', o);
    PR_REGISTRAR_GASTO(p_h, p_d, p_u, 'Leche entera en bolsa', 'BIEN', 1, '2', NULL, NULL,
                       '1', NULL, '6', 3800, '2', '1', o);
  END;
BEGIN
  v_pruiz := id_usuario_de('pruiz'); v_ccastro := id_usuario_de('ccastro'); v_mlopez := id_usuario_de('mlopez');
  v_critico := id_usuario_de('acritico'); v_jgomez := id_usuario_de('jgomez');
  v_h1 := id_hogar_de('ENPH-11001-0001'); v_h2 := id_hogar_de('ENPH-68001-0002'); v_h3 := id_hogar_de('ENPH-68001-0003');

  -- Asignaciones (RF-03)
  FOR u IN (SELECT ID_USUARIO FROM USUARIO WHERE NOMBRE_USUARIO IN ('pruiz','ccastro','mlopez','acritico')) LOOP
    PR_ASIGNAR_USUARIO(u.ID_USUARIO, v_h1);
  END LOOP;
  FOR u IN (SELECT ID_USUARIO FROM USUARIO WHERE NOMBRE_USUARIO IN ('jgomez','ccastro','mlopez','acritico')) LOOP
    PR_ASIGNAR_USUARIO(u.ID_USUARIO, v_h2);
  END LOOP;
  PR_ASIGNAR_USUARIO(v_ccastro, v_h3);

  -- ================= HOGAR 1 =================
  INSERT INTO VISITA (ID_HOGAR, NUMERO_VISITA, FECHA_HORA_INICIO, FECHA_HORA_FIN, COD_RESULTADO, PENDIENTES, PROXIMA_VISITA)
  VALUES (v_h1, 1, TO_DATE('2026-10-03 09:00','YYYY-MM-DD HH24:MI'), TO_DATE('2026-10-03 10:10','YYYY-MM-DD HH24:MI'),
          'EI', 'Capítulo D en curso', TO_DATE('2026-10-05 09:00','YYYY-MM-DD HH24:MI'));
  INSERT INTO VISITA (ID_HOGAR, NUMERO_VISITA, FECHA_HORA_INICIO, FECHA_HORA_FIN, COD_RESULTADO, PENDIENTES, PROXIMA_VISITA)
  VALUES (v_h1, 2, TO_DATE('2026-10-08 18:00','YYYY-MM-DD HH24:MI'), TO_DATE('2026-10-08 18:40','YYYY-MM-DD HH24:MI'),
          'EI', 'Días 7 a 14', TO_DATE('2026-10-16 18:00','YYYY-MM-DD HH24:MI'));
  INSERT INTO VISITA (ID_HOGAR, NUMERO_VISITA, FECHA_HORA_INICIO, FECHA_HORA_FIN, COD_RESULTADO)
  VALUES (v_h1, 3, TO_DATE('2026-10-16 18:00','YYYY-MM-DD HH24:MI'), TO_DATE('2026-10-16 19:00','YYYY-MM-DD HH24:MI'), 'EC');

  -- Capítulo C: 25 grupos; cada quinto grupo es de compra mensual (aplica C3.1 y C3.2).
  FOR g IN (SELECT COD_GRUPO, TO_NUMBER(COD_GRUPO) N FROM GRUPO_ALIMENTO) LOOP
    IF MOD(g.N, 5) = 0 THEN
      INSERT INTO CARACTERISTICA_GASTO VALUES (v_h1, g.COD_GRUPO, '5', g.N * 2000, 'S');
    ELSE
      INSERT INTO CARACTERISTICA_GASTO (ID_HOGAR, COD_GRUPO, COD_FRECUENCIA)
      VALUES (v_h1, g.COD_GRUPO, CASE WHEN MOD(g.N, 2) = 0 THEN '3' ELSE '2.1' END);
    END IF;
  END LOOP;
  INSERT INTO RESUMEN_MERCADO VALUES (v_h1, '98', 350000);

  PR_INICIAR_CAPTURA(v_h1, v_ccastro);

  FOR d IN 1 .. 14 LOOP
    IF d <> 6 THEN
      dia_tipico(v_h1, d, v_pruiz);
    END IF;
  END LOOP;

  -- Día 6: ejemplo oficial del cuadernillo (capítulo D)
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Hígado de res', 'BIEN', 2, '5', NULL, NULL, '1', NULL, '1', 14000, '3', '1', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Manzana grande', 'BIEN', 1, '6', NULL, NULL, '1', NULL, '10', 4000, '4', '1', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Cilantro', 'BIEN', 1, '8', 'Manojo', NULL, '1', NULL, '10', 300, '3', '1', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Gaseosa', 'BIEN', 2, '2', NULL, NULL, '3', NULL, NULL, 3500, NULL, 'NA', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Huevos', 'BIEN', 4, '8', 'Huevo grande', NULL, '1', NULL, '6', 1200, '2', '1', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Pan blandito pequeño', 'BIEN', 10, '8', 'Pan pequeño', NULL, '3', NULL, NULL, 2000, NULL, 'NA', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Pasaje en bus urbano', 'SERVICIO', 2, NULL, NULL, NULL, '1', NULL, NULL, 3200, '2.1', '2', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Gasolina corriente', 'BIEN', 7, '8', 'Galón', 3785, '1', NULL, '16', 58000, '3', '2', v_ord);
  PR_REGISTRAR_GASTO(v_h1, 6, v_pruiz, 'Plátano verde mediano', 'BIEN', 1, '8', 'Racimo', NULL, '5', NULL, NULL, 8000, NULL, '1', v_ord);
  -- Día 6: apartado D1
  PR_REGISTRAR_COMIDA(v_h1, 6, v_pruiz, 'Sándwich de pollo', '3', 0.5, '1', NULL, '19', 6000, '5', '1', 'S', v_ord);
  PR_REGISTRAR_COMIDA(v_h1, 6, v_pruiz, 'Ensalada de frutas', '1', 1, '1', NULL, '19', 6500, '5', '1', 'N', v_ord);
  PR_REGISTRAR_COMIDA(v_h1, 6, v_pruiz, 'Almuerzo corriente', '2', 1, '1', NULL, '18', 10000, '9', '2', 'N', v_ord);

  FOR d IN 1 .. 14 LOOP
    PR_CERRAR_JORNADA(v_h1, d, v_pruiz, FN_RENGLONES_DIA(v_h1, d));
  END LOOP;

  PR_CERRAR_CUADERNILLO(v_h1, v_ccastro, 'N', '3', NULL, 'Cuadernillo completo');

  -- Crítica: un hallazgo sobre el día 6, renglón 2 del capítulo D
  PR_INICIAR_REVISION(v_h1, v_critico, v_rev);
  PR_REGISTRAR_HALLAZGO(v_h1, v_rev, v_critico, 'D', 6,
    'Renglón 2 (manzana grande): el valor no coincide con la factura conservada por el hogar.', v_hall);
  PR_CONCLUIR_REVISION(v_h1, v_rev, v_critico, 'Un hallazgo en el capítulo D, día 6.');

  -- Supervisor devuelve; el encuestador corrige el dato y declara la corrección.
  PR_REVISAR_SUPERVISOR(v_h1, v_mlopez, 'DEVUELTO', 'Atender hallazgo de crítica del día 6.');
  UPDATE GASTO_DIARIO SET VALOR_PAGADO = 4200, ID_USUARIO_REGISTRO = v_ccastro
   WHERE ID_HOGAR = v_h1 AND DIA_ENCUESTA = 6 AND NUMERO_ORDEN = 2;
  PR_CORREGIR_HALLAZGO(v_h1, v_rev, v_hall, v_ccastro, 'Valor ajustado a $4.200 según factura.');
  PR_CERRAR_CUADERNILLO(v_h1, v_ccastro, 'N', '3', NULL, 'Cierre tras corrección de crítica');
  PR_VERIFICAR_HALLAZGO(v_h1, v_rev, v_hall, v_critico, 'S', 'Corrección verificada contra la factura.');
  PR_REVISAR_SUPERVISOR(v_h1, v_mlopez, 'APROBADO', NULL);

  -- ================= HOGAR 2 =================
  INSERT INTO VISITA (ID_HOGAR, NUMERO_VISITA, FECHA_HORA_INICIO, FECHA_HORA_FIN, COD_RESULTADO, PENDIENTES, PROXIMA_VISITA)
  VALUES (v_h2, 1, TO_DATE('2026-10-27 17:30','YYYY-MM-DD HH24:MI'), TO_DATE('2026-10-27 18:30','YYYY-MM-DD HH24:MI'),
          'EI', 'Capítulo D', TO_DATE('2026-10-29 17:30','YYYY-MM-DD HH24:MI'));
  PR_INICIAR_CAPTURA(v_h2, v_ccastro);
  FOR d IN 1 .. 5 LOOP
    dia_tipico(v_h2, d, v_jgomez);
  END LOOP;
  PR_REGISTRAR_COMIDA(v_h2, 2, v_jgomez, 'Empanadas', '4', 3, '1', NULL, '13', 4500, '2.1', '2', 'N', v_ord);
  FOR d IN 1 .. 4 LOOP
    PR_CERRAR_JORNADA(v_h2, d, v_jgomez, FN_RENGLONES_DIA(v_h2, d));
  END LOOP;

  DBMS_OUTPUT.PUT_LINE('Datos de prueba cargados: hogares ' || v_h1 || ', ' || v_h2 || ', ' || v_h3);
END;
/

COMMIT;
