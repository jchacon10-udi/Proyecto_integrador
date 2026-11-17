-- =====================================================================
-- ENPH - 05. Procedimientos almacenados (Oracle 10g)
-- Implementan los casos de uso con sus reglas de negocio. No hacen COMMIT:
-- la aplicación (o el script de prueba) confirma o revierte la transacción.
-- =====================================================================
SET DEFINE OFF

-- Utilidad interna: exige que el usuario esté asignado al hogar con uno de los roles.
CREATE OR REPLACE PROCEDURE PR_EXIGIR_AUTORIZACION (
  p_id_usuario IN USUARIO.ID_USUARIO%TYPE,
  p_id_hogar   IN HOGAR.ID_HOGAR%TYPE,
  p_roles      IN VARCHAR2
) IS
BEGIN
  IF FN_USUARIO_AUTORIZADO(p_id_usuario, p_id_hogar, p_roles) = 'N' THEN
    RAISE_APPLICATION_ERROR(-20060, 'Usuario ' || p_id_usuario || ' sin asignación vigente al hogar '
                            || p_id_hogar || ' con rol ' || p_roles);
  END IF;
END;
/

-- Utilidad interna: agrega un evento al historial de un hallazgo (RN-13).
CREATE OR REPLACE PROCEDURE PR_REGISTRAR_EVENTO (
  p_id_hogar   IN NUMBER,
  p_num_rev    IN NUMBER,
  p_num_hall   IN NUMBER,
  p_estado     IN VARCHAR2,
  p_id_usuario IN NUMBER,
  p_comentario IN VARCHAR2
) IS
  v_num NUMBER;
BEGIN
  SELECT NVL(MAX(NUMERO_EVENTO), 0) + 1 INTO v_num FROM EVENTO_HALLAZGO
   WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev AND NUMERO_HALLAZGO = p_num_hall;
  INSERT INTO EVENTO_HALLAZGO (ID_HOGAR, NUMERO_REVISION, NUMERO_HALLAZGO, NUMERO_EVENTO,
                               ESTADO, FECHA_EVENTO, ID_USUARIO, COMENTARIO)
  VALUES (p_id_hogar, p_num_rev, p_num_hall, v_num, p_estado, SYSDATE, p_id_usuario, p_comentario);
END;
/

-- Utilidad interna: estado actual del hogar con bloqueo de fila (serializa cambios del caso).
CREATE OR REPLACE FUNCTION FN_BLOQUEAR_HOGAR (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE
) RETURN VARCHAR2
IS
  v_estado HOGAR.ESTADO%TYPE;
BEGIN
  SELECT ESTADO INTO v_estado FROM HOGAR WHERE ID_HOGAR = p_id_hogar FOR UPDATE;
  RETURN v_estado;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20002, 'No existe el hogar ' || p_id_hogar);
END;
/

-- RF-03. Asigna (o reactiva) un usuario a un hogar.
CREATE OR REPLACE PROCEDURE PR_ASIGNAR_USUARIO (
  p_id_usuario IN USUARIO.ID_USUARIO%TYPE,
  p_id_hogar   IN HOGAR.ID_HOGAR%TYPE
) IS
BEGIN
  UPDATE ASIGNACION_HOGAR SET ESTADO = 'VIGENTE', FECHA_ASIGNACION = SYSDATE
   WHERE ID_USUARIO = p_id_usuario AND ID_HOGAR = p_id_hogar;
  IF SQL%ROWCOUNT = 0 THEN
    INSERT INTO ASIGNACION_HOGAR (ID_USUARIO, ID_HOGAR) VALUES (p_id_usuario, p_id_hogar);
  END IF;
END;
/

-- RF-07. Abre el período de 14 días: crea las 14 jornadas y pasa el hogar a EN_CAPTURA.
CREATE OR REPLACE PROCEDURE PR_INICIAR_CAPTURA (
  p_id_hogar       IN HOGAR.ID_HOGAR%TYPE,
  p_id_encuestador IN USUARIO.ID_USUARIO%TYPE
) IS
  v_estado HOGAR.ESTADO%TYPE;
  v_n      NUMBER;
BEGIN
  v_estado := FN_BLOQUEAR_HOGAR(p_id_hogar);
  PR_EXIGIR_AUTORIZACION(p_id_encuestador, p_id_hogar, 'ENCUESTADOR');
  IF v_estado <> 'ASIGNADO' THEN
    RAISE_APPLICATION_ERROR(-20061, 'Solo se inicia la captura de un hogar ASIGNADO (actual: ' || v_estado || ')');
  END IF;
  SELECT COUNT(*) INTO v_n FROM ASIGNACION_HOGAR A JOIN USUARIO U ON U.ID_USUARIO = A.ID_USUARIO
   JOIN ROL R ON R.ID_ROL = U.ID_ROL
   WHERE A.ID_HOGAR = p_id_hogar AND A.ESTADO = 'VIGENTE' AND R.NOMBRE = 'INFORMANTE';
  IF v_n = 0 THEN
    RAISE_APPLICATION_ERROR(-20062, 'El hogar no tiene un INFORMANTE asignado');
  END IF;
  FOR d IN 1 .. 14 LOOP
    INSERT INTO JORNADA_DIARIA (ID_HOGAR, DIA_ENCUESTA) VALUES (p_id_hogar, d);
  END LOOP;
  UPDATE HOGAR SET ESTADO = 'EN_CAPTURA' WHERE ID_HOGAR = p_id_hogar;
END;
/

-- CU-05 / RF-08. Registra un renglón del capítulo D y devuelve su número de orden.
CREATE OR REPLACE PROCEDURE PR_REGISTRAR_GASTO (
  p_id_hogar       IN  NUMBER,
  p_dia            IN  NUMBER,
  p_id_usuario     IN  NUMBER,
  p_descripcion    IN  VARCHAR2,
  p_tipo_item      IN  VARCHAR2,
  p_cantidad       IN  NUMBER,
  p_cod_unidad     IN  VARCHAR2,
  p_otra_unidad    IN  VARCHAR2,
  p_equivalencia   IN  NUMBER,
  p_cod_forma      IN  VARCHAR2,
  p_otra_forma     IN  VARCHAR2,
  p_cod_lugar      IN  VARCHAR2,
  p_valor          IN  NUMBER,
  p_cod_frecuencia IN  VARCHAR2,
  p_tipo_gasto     IN  VARCHAR2,
  p_numero_orden   OUT NUMBER
) IS
  v_dia NUMBER;
BEGIN
  PR_EXIGIR_AUTORIZACION(p_id_usuario, p_id_hogar, 'INFORMANTE,ENCUESTADOR');
  IF FN_FECHA_DIA(p_id_hogar, p_dia) > TRUNC(SYSDATE) THEN
    RAISE_APPLICATION_ERROR(-20063, 'No se registran gastos de un día futuro');
  END IF;
  -- Bloquea la jornada para asignar el consecutivo sin colisiones.
  SELECT DIA_ENCUESTA INTO v_dia FROM JORNADA_DIARIA
   WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia FOR UPDATE;
  SELECT NVL(MAX(NUMERO_ORDEN), 0) + 1 INTO p_numero_orden FROM GASTO_DIARIO
   WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia;
  INSERT INTO GASTO_DIARIO (ID_HOGAR, DIA_ENCUESTA, NUMERO_ORDEN, DESCRIPCION, TIPO_ITEM, CANTIDAD,
         COD_UNIDAD, OTRA_UNIDAD, EQUIVALENCIA_G_CC, COD_FORMA, OTRA_FORMA, COD_LUGAR,
         VALOR_PAGADO, COD_FRECUENCIA, TIPO_GASTO, ID_USUARIO_REGISTRO)
  VALUES (p_id_hogar, p_dia, p_numero_orden, p_descripcion, p_tipo_item, p_cantidad,
         p_cod_unidad, p_otra_unidad, p_equivalencia, p_cod_forma, p_otra_forma, p_cod_lugar,
         p_valor, p_cod_frecuencia, p_tipo_gasto, p_id_usuario);
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20064, 'La jornada ' || p_dia || ' no existe: inicie la captura del hogar');
END;
/

-- CU-06 / RF-09. Registra un renglón del apartado D1 y devuelve su número de orden.
CREATE OR REPLACE PROCEDURE PR_REGISTRAR_COMIDA (
  p_id_hogar        IN  NUMBER,
  p_dia             IN  NUMBER,
  p_id_usuario      IN  NUMBER,
  p_descripcion     IN  VARCHAR2,
  p_cod_tipo_comida IN  VARCHAR2,
  p_cantidad        IN  NUMBER,
  p_cod_forma       IN  VARCHAR2,
  p_otra_forma      IN  VARCHAR2,
  p_cod_lugar       IN  VARCHAR2,
  p_valor           IN  NUMBER,
  p_cod_frecuencia  IN  VARCHAR2,
  p_tipo_gasto      IN  VARCHAR2,
  p_a_domicilio     IN  CHAR,
  p_numero_orden    OUT NUMBER
) IS
  v_dia NUMBER;
BEGIN
  PR_EXIGIR_AUTORIZACION(p_id_usuario, p_id_hogar, 'INFORMANTE,ENCUESTADOR');
  IF FN_FECHA_DIA(p_id_hogar, p_dia) > TRUNC(SYSDATE) THEN
    RAISE_APPLICATION_ERROR(-20063, 'No se registran gastos de un día futuro');
  END IF;
  SELECT DIA_ENCUESTA INTO v_dia FROM JORNADA_DIARIA
   WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia FOR UPDATE;
  SELECT NVL(MAX(NUMERO_ORDEN), 0) + 1 INTO p_numero_orden FROM COMIDA_FUERA
   WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia;
  INSERT INTO COMIDA_FUERA (ID_HOGAR, DIA_ENCUESTA, NUMERO_ORDEN, DESCRIPCION, COD_TIPO_COMIDA,
         CANTIDAD, COD_FORMA, OTRA_FORMA, COD_LUGAR, VALOR_PAGADO, COD_FRECUENCIA, TIPO_GASTO,
         A_DOMICILIO, ID_USUARIO_REGISTRO)
  VALUES (p_id_hogar, p_dia, p_numero_orden, p_descripcion, p_cod_tipo_comida,
         p_cantidad, p_cod_forma, p_otra_forma, p_cod_lugar, p_valor, p_cod_frecuencia, p_tipo_gasto,
         p_a_domicilio, p_id_usuario);
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20064, 'La jornada ' || p_dia || ' no existe: inicie la captura del hogar');
END;
/

-- Declara el total de renglones del día (control del formulario) y lo contrasta.
CREATE OR REPLACE PROCEDURE PR_CERRAR_JORNADA (
  p_id_hogar        IN NUMBER,
  p_dia             IN NUMBER,
  p_id_usuario      IN NUMBER,
  p_total_renglones IN NUMBER,
  p_observaciones   IN VARCHAR2 DEFAULT NULL
) IS
  v_estado     HOGAR.ESTADO%TYPE;
  v_registrados NUMBER;
BEGIN
  v_estado := FN_BLOQUEAR_HOGAR(p_id_hogar);
  IF v_estado NOT IN ('EN_CAPTURA', 'DEVUELTO') THEN
    RAISE_APPLICATION_ERROR(-20010, 'Captura cerrada: el hogar está en estado ' || v_estado);
  END IF;
  PR_EXIGIR_AUTORIZACION(p_id_usuario, p_id_hogar, 'INFORMANTE,ENCUESTADOR');
  v_registrados := FN_RENGLONES_DIA(p_id_hogar, p_dia);
  IF p_total_renglones <> v_registrados THEN
    RAISE_APPLICATION_ERROR(-20065, 'Total declarado (' || p_total_renglones ||
      ') distinto de los renglones registrados (' || v_registrados || ') en el día ' || p_dia);
  END IF;
  UPDATE JORNADA_DIARIA SET TOTAL_RENGLONES = p_total_renglones, OBSERVACIONES = p_observaciones
   WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia;
  IF SQL%ROWCOUNT = 0 THEN
    RAISE_APPLICATION_ERROR(-20064, 'La jornada ' || p_dia || ' no existe');
  END IF;
END;
/

-- CU-08 / RF-13. Cierre de captura (D2) por el encuestador.
CREATE OR REPLACE PROCEDURE PR_CERRAR_CUADERNILLO (
  p_id_hogar        IN NUMBER,
  p_id_encuestador  IN NUMBER,
  p_evento_especial IN CHAR,
  p_cod_forma_pago  IN VARCHAR2,
  p_otra_forma_pago IN VARCHAR2,
  p_observaciones   IN VARCHAR2 DEFAULT NULL
) IS
  v_estado HOGAR.ESTADO%TYPE;
  v_n      NUMBER;
BEGIN
  v_estado := FN_BLOQUEAR_HOGAR(p_id_hogar);
  PR_EXIGIR_AUTORIZACION(p_id_encuestador, p_id_hogar, 'ENCUESTADOR');
  IF v_estado NOT IN ('EN_CAPTURA', 'DEVUELTO') THEN
    RAISE_APPLICATION_ERROR(-20066, 'Solo se cierra un hogar EN_CAPTURA o DEVUELTO (actual: ' || v_estado || ')');
  END IF;
  v_n := FN_DIAS_COMPLETOS(p_id_hogar);
  IF v_n < 14 THEN
    RAISE_APPLICATION_ERROR(-20067, 'Faltan jornadas por completar: ' || v_n || ' de 14 cerradas y coincidentes');
  END IF;
  SELECT COUNT(*) INTO v_n FROM CARACTERISTICA_GASTO WHERE ID_HOGAR = p_id_hogar;
  IF v_n < 25 THEN
    RAISE_APPLICATION_ERROR(-20068, 'Capítulo C incompleto: ' || v_n || ' de 25 grupos');
  END IF;
  UPDATE CIERRE_CUADERNILLO
     SET GASTO_EVENTO_ESPECIAL = p_evento_especial, COD_FORMA_PAGO = p_cod_forma_pago,
         OTRA_FORMA_PAGO = p_otra_forma_pago, OBSERVACIONES = p_observaciones,
         ID_ENCUESTADOR = p_id_encuestador, FECHA_CIERRE = SYSDATE,
         ESTADO_REVISION = 'PENDIENTE', ID_SUPERVISOR = NULL, FECHA_REVISION = NULL
   WHERE ID_HOGAR = p_id_hogar;
  IF SQL%ROWCOUNT = 0 THEN
    INSERT INTO CIERRE_CUADERNILLO (ID_HOGAR, GASTO_EVENTO_ESPECIAL, COD_FORMA_PAGO, OTRA_FORMA_PAGO,
                                    OBSERVACIONES, ID_ENCUESTADOR)
    VALUES (p_id_hogar, p_evento_especial, p_cod_forma_pago, p_otra_forma_pago,
            p_observaciones, p_id_encuestador);
  END IF;
  UPDATE HOGAR SET ESTADO = 'CERRADO', COD_RESULTADO = 'EC' WHERE ID_HOGAR = p_id_hogar;
END;
/

-- CU-09 / RF-14. Aprobación o devolución por el supervisor (RN-09).
CREATE OR REPLACE PROCEDURE PR_REVISAR_SUPERVISOR (
  p_id_hogar      IN NUMBER,
  p_id_supervisor IN NUMBER,
  p_decision      IN VARCHAR2,
  p_observacion   IN VARCHAR2 DEFAULT NULL
) IS
  v_estado HOGAR.ESTADO%TYPE;
  v_n      NUMBER;
BEGIN
  v_estado := FN_BLOQUEAR_HOGAR(p_id_hogar);
  PR_EXIGIR_AUTORIZACION(p_id_supervisor, p_id_hogar, 'SUPERVISOR');
  IF v_estado <> 'CERRADO' THEN
    RAISE_APPLICATION_ERROR(-20069, 'Solo se revisa un hogar CERRADO (actual: ' || v_estado || ')');
  END IF;
  IF p_decision NOT IN ('APROBADO', 'DEVUELTO') THEN
    RAISE_APPLICATION_ERROR(-20070, 'Decisión inválida: use APROBADO o DEVUELTO');
  END IF;
  IF p_decision = 'APROBADO' THEN
    v_n := FN_HALLAZGOS_ABIERTOS(p_id_hogar);
    IF v_n > 0 THEN
      RAISE_APPLICATION_ERROR(-20071, 'No se aprueba: hay ' || v_n || ' hallazgos de crítica ABIERTO');
    END IF;
    SELECT COUNT(*) INTO v_n FROM REVISION_CRITICA WHERE ID_HOGAR = p_id_hogar AND ESTADO = 'EN_REVISION';
    IF v_n > 0 THEN
      RAISE_APPLICATION_ERROR(-20072, 'No se aprueba: hay una revisión de crítica en curso');
    END IF;
  END IF;
  UPDATE CIERRE_CUADERNILLO
     SET ESTADO_REVISION = p_decision, ID_SUPERVISOR = p_id_supervisor,
         FECHA_REVISION = SYSDATE, OBSERVACION_SUPERVISOR = p_observacion
   WHERE ID_HOGAR = p_id_hogar;
  UPDATE HOGAR SET ESTADO = p_decision WHERE ID_HOGAR = p_id_hogar;
END;
/

-- CU-12 / RF-16. Inicia una revisión de crítica sobre un hogar cerrado.
CREATE OR REPLACE PROCEDURE PR_INICIAR_REVISION (
  p_id_hogar   IN  NUMBER,
  p_id_critico IN  NUMBER,
  p_numero     OUT NUMBER
) IS
  v_estado HOGAR.ESTADO%TYPE;
  v_n      NUMBER;
BEGIN
  v_estado := FN_BLOQUEAR_HOGAR(p_id_hogar);
  PR_EXIGIR_AUTORIZACION(p_id_critico, p_id_hogar, 'CRITICO_DIGITADOR');
  IF v_estado <> 'CERRADO' THEN
    RAISE_APPLICATION_ERROR(-20073, 'La crítica se realiza sobre un hogar CERRADO (actual: ' || v_estado || ')');
  END IF;
  SELECT COUNT(*) INTO v_n FROM REVISION_CRITICA WHERE ID_HOGAR = p_id_hogar AND ESTADO = 'EN_REVISION';
  IF v_n > 0 THEN
    RAISE_APPLICATION_ERROR(-20074, 'Ya existe una revisión EN_REVISION para el hogar');
  END IF;
  SELECT NVL(MAX(NUMERO_REVISION), 0) + 1 INTO p_numero FROM REVISION_CRITICA WHERE ID_HOGAR = p_id_hogar;
  INSERT INTO REVISION_CRITICA (ID_HOGAR, NUMERO_REVISION, ID_CRITICO) VALUES (p_id_hogar, p_numero, p_id_critico);
END;
/

-- CU-13 / RF-17. Registra un hallazgo en una revisión en curso del mismo crítico.
CREATE OR REPLACE PROCEDURE PR_REGISTRAR_HALLAZGO (
  p_id_hogar    IN  NUMBER,
  p_num_rev     IN  NUMBER,
  p_id_critico  IN  NUMBER,
  p_capitulo    IN  VARCHAR2,
  p_dia         IN  NUMBER,
  p_descripcion IN  VARCHAR2,
  p_numero      OUT NUMBER
) IS
  v_autor REVISION_CRITICA.ID_CRITICO%TYPE;
BEGIN
  SELECT ID_CRITICO INTO v_autor FROM REVISION_CRITICA
   WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev FOR UPDATE;
  IF v_autor <> p_id_critico THEN
    RAISE_APPLICATION_ERROR(-20075, 'Solo el autor de la revisión registra hallazgos en ella');
  END IF;
  SELECT NVL(MAX(NUMERO_HALLAZGO), 0) + 1 INTO p_numero FROM HALLAZGO_CRITICA
   WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev;
  INSERT INTO HALLAZGO_CRITICA (ID_HOGAR, NUMERO_REVISION, NUMERO_HALLAZGO, CAPITULO, DIA_ENCUESTA, DESCRIPCION)
  VALUES (p_id_hogar, p_num_rev, p_numero, p_capitulo, p_dia, p_descripcion);
  PR_REGISTRAR_EVENTO(p_id_hogar, p_num_rev, p_numero, 'ABIERTO', p_id_critico, p_descripcion);
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20076, 'No existe la revisión ' || p_num_rev || ' del hogar ' || p_id_hogar);
END;
/

-- Concluye la revisión: OBSERVADA si tiene hallazgos, CONFORME si no (RN-13).
CREATE OR REPLACE PROCEDURE PR_CONCLUIR_REVISION (
  p_id_hogar   IN NUMBER,
  p_num_rev    IN NUMBER,
  p_id_critico IN NUMBER,
  p_resultado  IN VARCHAR2
) IS
  v_autor REVISION_CRITICA.ID_CRITICO%TYPE;
  v_n     NUMBER;
BEGIN
  SELECT ID_CRITICO INTO v_autor FROM REVISION_CRITICA
   WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev FOR UPDATE;
  IF v_autor <> p_id_critico THEN
    RAISE_APPLICATION_ERROR(-20075, 'Solo el autor de la revisión puede concluirla');
  END IF;
  SELECT COUNT(*) INTO v_n FROM HALLAZGO_CRITICA WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev;
  UPDATE REVISION_CRITICA
     SET ESTADO = CASE WHEN v_n > 0 THEN 'OBSERVADA' ELSE 'CONFORME' END,
         RESULTADO = NVL(p_resultado, 'Sin hallazgos')
   WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20076, 'No existe la revisión ' || p_num_rev || ' del hogar ' || p_id_hogar);
END;
/

-- CU-07. El responsable (encuestador o informante asignado) declara la corrección.
CREATE OR REPLACE PROCEDURE PR_CORREGIR_HALLAZGO (
  p_id_hogar       IN NUMBER,
  p_num_rev        IN NUMBER,
  p_num_hall       IN NUMBER,
  p_id_responsable IN NUMBER,
  p_respuesta      IN VARCHAR2
) IS
BEGIN
  PR_EXIGIR_AUTORIZACION(p_id_responsable, p_id_hogar, 'ENCUESTADOR,INFORMANTE');
  UPDATE HALLAZGO_CRITICA
     SET ESTADO = 'CORREGIDO', ID_RESPONSABLE = p_id_responsable,
         FECHA_CORRECCION = SYSDATE, RESPUESTA_CORRECCION = p_respuesta
   WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev AND NUMERO_HALLAZGO = p_num_hall;
  IF SQL%ROWCOUNT = 0 THEN
    RAISE_APPLICATION_ERROR(-20077, 'No existe el hallazgo indicado');
  END IF;
  PR_REGISTRAR_EVENTO(p_id_hogar, p_num_rev, p_num_hall, 'CORREGIDO', p_id_responsable, p_respuesta);
END;
/

-- CU-14 / RF-18. El crítico acepta (VERIFICADO) o rechaza (vuelve a ABIERTO) la corrección.
CREATE OR REPLACE PROCEDURE PR_VERIFICAR_HALLAZGO (
  p_id_hogar   IN NUMBER,
  p_num_rev    IN NUMBER,
  p_num_hall   IN NUMBER,
  p_id_critico IN NUMBER,
  p_aceptada   IN CHAR,
  p_comentario IN VARCHAR2 DEFAULT NULL
) IS
  v_nuevo HALLAZGO_CRITICA.ESTADO%TYPE;
BEGIN
  PR_EXIGIR_AUTORIZACION(p_id_critico, p_id_hogar, 'CRITICO_DIGITADOR');
  IF p_aceptada = 'S' THEN
    v_nuevo := 'VERIFICADO';
    UPDATE HALLAZGO_CRITICA SET ESTADO = v_nuevo, FECHA_VERIFICACION = SYSDATE
     WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev AND NUMERO_HALLAZGO = p_num_hall
       AND ESTADO = 'CORREGIDO';
  ELSE
    v_nuevo := 'ABIERTO';
    UPDATE HALLAZGO_CRITICA SET ESTADO = v_nuevo
     WHERE ID_HOGAR = p_id_hogar AND NUMERO_REVISION = p_num_rev AND NUMERO_HALLAZGO = p_num_hall
       AND ESTADO = 'CORREGIDO';
  END IF;
  IF SQL%ROWCOUNT = 0 THEN
    RAISE_APPLICATION_ERROR(-20078, 'Solo se verifica un hallazgo existente en estado CORREGIDO');
  END IF;
  PR_REGISTRAR_EVENTO(p_id_hogar, p_num_rev, p_num_hall, v_nuevo, p_id_critico, p_comentario);
END;
/
