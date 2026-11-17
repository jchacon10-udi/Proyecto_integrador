-- =====================================================================
-- ENPH - 09. Pruebas: CRUD de tablas básicas y reglas de negocio
-- Ejecutar como ENPH después de 08_datos_prueba.sql.
-- Cada prueba imprime PASA o FALLA. Al final se hace ROLLBACK: los datos
-- de prueba quedan como estaban y el script puede repetirse.
-- =====================================================================
SET DEFINE OFF
SET SERVEROUTPUT ON SIZE 1000000

DECLARE
  v_ok    NUMBER := 0;
  v_falla NUMBER := 0;
  v_h1 NUMBER; v_h2 NUMBER; v_ord NUMBER; v_rev NUMBER; v_hall NUMBER; v_n NUMBER;
  v_pruiz NUMBER; v_jgomez NUMBER; v_ccastro NUMBER; v_mlopez NUMBER; v_critico NUMBER;
  v_txt VARCHAR2(200);

  PROCEDURE resultado(p_id VARCHAR2, p_desc VARCHAR2, p_bien BOOLEAN, p_det VARCHAR2 DEFAULT NULL) IS
  BEGIN
    IF p_bien THEN
      v_ok := v_ok + 1;
      DBMS_OUTPUT.PUT_LINE('PASA  ' || RPAD(p_id, 5) || p_desc);
    ELSE
      v_falla := v_falla + 1;
      DBMS_OUTPUT.PUT_LINE('FALLA ' || RPAD(p_id, 5) || p_desc || ' -> ' || p_det);
    END IF;
  END;

  -- Ejecuta un bloque que DEBE fallar con el código indicado.
  PROCEDURE esperar_error(p_id VARCHAR2, p_desc VARCHAR2, p_bloque VARCHAR2, p_codigo NUMBER) IS
  BEGIN
    EXECUTE IMMEDIATE 'BEGIN ' || p_bloque || ' END;';
    resultado(p_id, p_desc, FALSE, 'no produjo error');
  EXCEPTION
    WHEN OTHERS THEN
      resultado(p_id, p_desc || ' [ORA' || SQLCODE || ']', SQLCODE = p_codigo, SQLERRM);
  END;

  FUNCTION id_usuario_de(p VARCHAR2) RETURN NUMBER IS v NUMBER;
  BEGIN SELECT ID_USUARIO INTO v FROM USUARIO WHERE NOMBRE_USUARIO = p; RETURN v; END;
BEGIN
  SAVEPOINT inicio_pruebas;
  SELECT ID_HOGAR INTO v_h1 FROM HOGAR WHERE CODIGO_OPERATIVO = 'ENPH-11001-0001';
  SELECT ID_HOGAR INTO v_h2 FROM HOGAR WHERE CODIGO_OPERATIVO = 'ENPH-68001-0002';
  v_pruiz := id_usuario_de('pruiz'); v_jgomez := id_usuario_de('jgomez');
  v_ccastro := id_usuario_de('ccastro'); v_mlopez := id_usuario_de('mlopez');
  v_critico := id_usuario_de('acritico');

  DBMS_OUTPUT.PUT_LINE('=== CRUD de tablas básicas ===');

  -- C01 Catálogo LUGAR_COMPRA
  INSERT INTO LUGAR_COMPRA VALUES ('99', 'Lugar de prueba');
  SELECT NOMBRE INTO v_txt FROM LUGAR_COMPRA WHERE COD_LUGAR = '99';
  UPDATE LUGAR_COMPRA SET NOMBRE = 'Lugar de prueba editado' WHERE COD_LUGAR = '99';
  SELECT NOMBRE INTO v_txt FROM LUGAR_COMPRA WHERE COD_LUGAR = '99';
  DELETE FROM LUGAR_COMPRA WHERE COD_LUGAR = '99';
  SELECT COUNT(*) INTO v_n FROM LUGAR_COMPRA WHERE COD_LUGAR = '99';
  resultado('C01', 'CRUD LUGAR_COMPRA (insertar, leer, actualizar, borrar)', v_txt = 'Lugar de prueba editado' AND v_n = 0);

  -- C02 USUARIO (ID por secuencia)
  INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH)
  VALUES (2, 'prueba', 'Usuario de prueba', 'prueba@demo.enph.local', 'x');
  SELECT ID_USUARIO INTO v_n FROM USUARIO WHERE NOMBRE_USUARIO = 'prueba';
  UPDATE USUARIO SET ESTADO = 'INACTIVO' WHERE ID_USUARIO = v_n;
  SELECT ESTADO INTO v_txt FROM USUARIO WHERE ID_USUARIO = v_n;
  DELETE FROM USUARIO WHERE ID_USUARIO = v_n;
  resultado('C02', 'CRUD USUARIO con ID de SEQ_USUARIO (' || v_n || ')', v_txt = 'INACTIVO' AND SQL%ROWCOUNT = 1);

  -- C03 HOGAR (capítulo A)
  INSERT INTO HOGAR (CODIGO_OPERATIVO, REGION, DEPARTAMENTO, MUNICIPIO, CLASE, DIRECCION,
                     TOTAL_HOGARES_VIVIENDA, HOGAR_NUMERO, TOTAL_PERSONAS, FECHA_INICIO)
  VALUES ('PRUEBA-0001', '2', '68', '68001', '1', 'Calle de prueba', 1, 1, 1, DATE '2026-12-01');
  UPDATE HOGAR SET TELEFONO = '3009999999' WHERE CODIGO_OPERATIVO = 'PRUEBA-0001';
  SELECT TELEFONO INTO v_txt FROM HOGAR WHERE CODIGO_OPERATIVO = 'PRUEBA-0001';
  DELETE FROM HOGAR WHERE CODIGO_OPERATIVO = 'PRUEBA-0001';
  resultado('C03', 'CRUD HOGAR', v_txt = '3009999999' AND SQL%ROWCOUNT = 1);

  -- C04 GASTO_DIARIO (capítulo D) en hogar EN_CAPTURA
  PR_REGISTRAR_GASTO(v_h2, 5, v_jgomez, 'Arroz', 'BIEN', 1, '5', NULL, NULL, '1', NULL, '6', 2500, '3', '1', v_ord);
  UPDATE GASTO_DIARIO SET CANTIDAD = 2, VALOR_PAGADO = 5000
   WHERE ID_HOGAR = v_h2 AND DIA_ENCUESTA = 5 AND NUMERO_ORDEN = v_ord;
  SELECT VALOR_PAGADO INTO v_n FROM GASTO_DIARIO WHERE ID_HOGAR = v_h2 AND DIA_ENCUESTA = 5 AND NUMERO_ORDEN = v_ord;
  DELETE FROM GASTO_DIARIO WHERE ID_HOGAR = v_h2 AND DIA_ENCUESTA = 5 AND NUMERO_ORDEN = v_ord;
  resultado('C04', 'CRUD GASTO_DIARIO (orden ' || v_ord || ' asignado por PR_REGISTRAR_GASTO)', v_n = 5000 AND SQL%ROWCOUNT = 1);

  -- C05 COMIDA_FUERA (apartado D1)
  PR_REGISTRAR_COMIDA(v_h2, 5, v_jgomez, 'Almuerzo ejecutivo', '2', 1, '1', NULL, '18', 12000, '3', '1', 'N', v_ord);
  UPDATE COMIDA_FUERA SET A_DOMICILIO = 'S' WHERE ID_HOGAR = v_h2 AND DIA_ENCUESTA = 5 AND NUMERO_ORDEN = v_ord;
  SELECT A_DOMICILIO INTO v_txt FROM COMIDA_FUERA WHERE ID_HOGAR = v_h2 AND DIA_ENCUESTA = 5 AND NUMERO_ORDEN = v_ord;
  DELETE FROM COMIDA_FUERA WHERE ID_HOGAR = v_h2 AND DIA_ENCUESTA = 5 AND NUMERO_ORDEN = v_ord;
  resultado('C05', 'CRUD COMIDA_FUERA', v_txt = 'S' AND SQL%ROWCOUNT = 1);

  -- C06 VISITA (capítulo B)
  INSERT INTO VISITA (ID_HOGAR, NUMERO_VISITA, FECHA_HORA_INICIO, COD_RESULTADO)
  VALUES (v_h2, 2, TO_DATE('2026-10-29 17:30','YYYY-MM-DD HH24:MI'), 'NH');
  UPDATE VISITA SET COD_RESULTADO = 'EI', FECHA_HORA_FIN = TO_DATE('2026-10-29 18:00','YYYY-MM-DD HH24:MI')
   WHERE ID_HOGAR = v_h2 AND NUMERO_VISITA = 2;
  SELECT COD_RESULTADO INTO v_txt FROM VISITA WHERE ID_HOGAR = v_h2 AND NUMERO_VISITA = 2;
  DELETE FROM VISITA WHERE ID_HOGAR = v_h2 AND NUMERO_VISITA = 2;
  resultado('C06', 'CRUD VISITA', v_txt = 'EI' AND SQL%ROWCOUNT = 1);

  -- C07 Funciones y vistas
  resultado('C07', 'FN_FECHA_DIA(h1, 6) = 2026-10-08', FN_FECHA_DIA(v_h1, 6) = DATE '2026-10-08');
  SELECT COUNT(*) INTO v_n FROM V_AVANCE_HOGAR WHERE ID_HOGAR = v_h1 AND ESTADO = 'APROBADO' AND DIAS_DECLARADOS = 14;
  resultado('C08', 'V_AVANCE_HOGAR: hogar 1 APROBADO con 14 días', v_n = 1);
  resultado('C09', 'FN_TOTAL_GASTO(h1, día 6) = 116.900', FN_TOTAL_GASTO(v_h1, 6) = 116900, TO_CHAR(FN_TOTAL_GASTO(v_h1, 6)));
  SELECT COUNT(*) INTO v_n FROM EVENTO_HALLAZGO WHERE ID_HOGAR = v_h1;
  resultado('C10', 'Historial del hallazgo con 3 eventos (ABIERTO, CORREGIDO, VERIFICADO)', v_n = 3, TO_CHAR(v_n));

  DBMS_OUTPUT.PUT_LINE('=== Reglas declarativas (CHECK, FK, UNIQUE) ===');
  esperar_error('N01', 'Gasto personal (2) en el día 8',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 8, ' || v_jgomez || ', ''Gaseosa'', ''BIEN'', 1, ''2'', NULL, NULL, ''1'', NULL, ''6'', 3000, ''2'', ''2'', o); END;', -2290);
  esperar_error('N02', 'Regalo con lugar de compra',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 3, ' || v_jgomez || ', ''Pan'', ''BIEN'', 1, ''8'', ''Pan'', NULL, ''3'', NULL, ''6'', 2000, NULL, ''NA'', o); END;', -2290);
  esperar_error('N03', 'BIEN sin unidad de medida',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 3, ' || v_jgomez || ', ''Queso'', ''BIEN'', 1, NULL, NULL, NULL, ''1'', NULL, ''6'', 9000, ''3'', ''1'', o); END;', -2290);
  esperar_error('N04', 'Unidad 8 (Otra) sin especificar',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 3, ' || v_jgomez || ', ''Panela'', ''BIEN'', 1, ''8'', NULL, NULL, ''1'', NULL, ''6'', 3000, ''3'', ''1'', o); END;', -2290);
  esperar_error('N05', 'D1 con tipo de gasto NA',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_COMIDA(' || v_h2 || ', 3, ' || v_jgomez || ', ''Arepa'', ''4'', 1, ''1'', NULL, ''13'', 2000, ''2'', ''NA'', ''N'', o); END;', -2290);
  esperar_error('N06', 'Compra sin frecuencia',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 3, ' || v_jgomez || ', ''Sal'', ''BIEN'', 1, ''5'', NULL, NULL, ''1'', NULL, ''6'', 1500, NULL, ''1'', o); END;', -2290);
  esperar_error('N07', 'Lugar de compra inexistente (FK)',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 3, ' || v_jgomez || ', ''Sal'', ''BIEN'', 1, ''5'', NULL, NULL, ''1'', NULL, ''98'', 1500, ''3'', ''1'', o); END;', -2291);
  esperar_error('N08', 'Jornada duplicada (PK hogar, día)',
    'INSERT INTO JORNADA_DIARIA (ID_HOGAR, DIA_ENCUESTA) VALUES (' || v_h2 || ', 1);', -1);
  esperar_error('N09', 'Día 15 fuera del período (CHECK)',
    'INSERT INTO JORNADA_DIARIA (ID_HOGAR, DIA_ENCUESTA) VALUES (' || v_h2 || ', 15);', -2290);
  esperar_error('N10', 'Borrar forma de adquisición en uso (FK)',
    'DELETE FROM FORMA_ADQUISICION WHERE COD_FORMA = ''1'';', -2292);
  esperar_error('N11', 'Capítulo C: valor de última compra con frecuencia semanal',
    'INSERT INTO CARACTERISTICA_GASTO VALUES (' || v_h2 || ', ''01'', ''3'', 5000, ''S'');', -2290);
  esperar_error('N12', 'Correo de usuario duplicado (UNIQUE)',
    'INSERT INTO USUARIO (ID_ROL, NOMBRE_USUARIO, NOMBRE_COMPLETO, CORREO, CLAVE_HASH) VALUES (1, ''otro'', ''Otro'', ''pruiz@demo.enph.local'', ''x'');', -1);

  DBMS_OUTPUT.PUT_LINE('=== Reglas de procedimientos y disparadores ===');
  esperar_error('N13', 'Captura en hogar APROBADO (trigger)',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h1 || ', 3, ' || v_pruiz || ', ''Pan'', ''BIEN'', 1, ''8'', ''Pan'', NULL, ''1'', NULL, ''6'', 2000, ''2'', ''1'', o); END;', -20010);
  esperar_error('N14', 'Captura por informante no asignado al hogar',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h1 || ', 3, ' || v_jgomez || ', ''Pan'', ''BIEN'', 1, ''8'', ''Pan'', NULL, ''1'', NULL, ''6'', 2000, ''2'', ''1'', o); END;', -20060);
  esperar_error('N15', 'Día 15 en procedimiento',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_GASTO(' || v_h2 || ', 15, ' || v_jgomez || ', ''Pan'', ''BIEN'', 1, ''8'', ''Pan'', NULL, ''1'', NULL, ''6'', 2000, ''2'', ''1'', o); END;', -20001);
  esperar_error('N16', 'Total de renglones declarado incorrecto',
    'PR_CERRAR_JORNADA(' || v_h2 || ', 5, ' || v_jgomez || ', 7);', -20065);
  esperar_error('N17', 'Cerrar cuadernillo con jornadas incompletas',
    'PR_CERRAR_CUADERNILLO(' || v_h2 || ', ' || v_ccastro || ', ''N'', ''3'', NULL);', -20067);
  esperar_error('N18', 'Revisión de crítica por un ENCUESTADOR (trigger)',
    'INSERT INTO REVISION_CRITICA (ID_HOGAR, NUMERO_REVISION, ID_CRITICO) VALUES (' || v_h1 || ', 9, ' || v_ccastro || ');', -20030);
  esperar_error('N19', 'Modificar una revisión concluida',
    'UPDATE REVISION_CRITICA SET RESULTADO = ''x'' WHERE ID_HOGAR = ' || v_h1 || ';', -20032);
  esperar_error('N20', 'Saltar de VERIFICADO a ABIERTO',
    'UPDATE HALLAZGO_CRITICA SET ESTADO = ''ABIERTO'' WHERE ID_HOGAR = ' || v_h1 || ';', -20044);
  esperar_error('N21', 'Eliminar un hallazgo',
    'DELETE FROM HALLAZGO_CRITICA WHERE ID_HOGAR = ' || v_h1 || ';', -20040);
  esperar_error('N22', 'Modificar el historial de eventos',
    'UPDATE EVENTO_HALLAZGO SET COMENTARIO = ''x'' WHERE ID_HOGAR = ' || v_h1 || ';', -20050);

  DBMS_OUTPUT.PUT_LINE('=== Flujo de cierre y aprobación sobre el hogar 2 ===');
  FOR g IN (SELECT COD_GRUPO FROM GRUPO_ALIMENTO) LOOP
    INSERT INTO CARACTERISTICA_GASTO (ID_HOGAR, COD_GRUPO, COD_FRECUENCIA) VALUES (v_h2, g.COD_GRUPO, '3');
  END LOOP;
  FOR d IN 5 .. 14 LOOP
    PR_CERRAR_JORNADA(v_h2, d, v_jgomez, FN_RENGLONES_DIA(v_h2, d));
  END LOOP;
  PR_CERRAR_CUADERNILLO(v_h2, v_ccastro, 'S', '6', 'Transferencia', NULL);
  SELECT COUNT(*) INTO v_n FROM HOGAR WHERE ID_HOGAR = v_h2 AND ESTADO = 'CERRADO';
  resultado('F01', 'Cierre con 14 jornadas y 25 grupos: hogar CERRADO', v_n = 1);
  PR_INICIAR_REVISION(v_h2, v_critico, v_rev);
  esperar_error('F02', 'Hallazgo del capítulo D sin día',
    'DECLARE o NUMBER; BEGIN PR_REGISTRAR_HALLAZGO(' || v_h2 || ', ' || v_rev || ', ' || v_critico || ', ''D'', NULL, ''Sin día'', o); END;', -2290);
  PR_REGISTRAR_HALLAZGO(v_h2, v_rev, v_critico, 'D1', 2, 'Empanadas: confirmar si fue gasto personal.', v_hall);
  esperar_error('F03', 'Saltar de ABIERTO a VERIFICADO',
    'PR_VERIFICAR_HALLAZGO(' || v_h2 || ', ' || v_rev || ', ' || v_hall || ', ' || v_critico || ', ''S'');', -20078);
  PR_CONCLUIR_REVISION(v_h2, v_rev, v_critico, 'Un hallazgo D1.');
  esperar_error('F04', 'Aprobar con un hallazgo ABIERTO',
    'PR_REVISAR_SUPERVISOR(' || v_h2 || ', ' || v_mlopez || ', ''APROBADO'');', -20071);
  esperar_error('F05', 'Devolver sin motivo (CHECK)',
    'PR_REVISAR_SUPERVISOR(' || v_h2 || ', ' || v_mlopez || ', ''DEVUELTO'', NULL);', -2290);
  PR_REVISAR_SUPERVISOR(v_h2, v_mlopez, 'DEVUELTO', 'Atender hallazgo D1.');
  SELECT COUNT(*) INTO v_n FROM HOGAR WHERE ID_HOGAR = v_h2 AND ESTADO = 'DEVUELTO';
  resultado('F06', 'Devolución con hallazgo abierto: hogar DEVUELTO', v_n = 1);

  ROLLBACK TO inicio_pruebas;
  DBMS_OUTPUT.PUT_LINE('=== Resultado: ' || v_ok || ' pasan, ' || v_falla || ' fallan (cambios revertidos) ===');
EXCEPTION
  WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('ERROR INESPERADO: ' || SQLERRM);
    DBMS_OUTPUT.PUT_LINE(DBMS_UTILITY.FORMAT_ERROR_BACKTRACE);
    ROLLBACK TO inicio_pruebas;
END;
/
