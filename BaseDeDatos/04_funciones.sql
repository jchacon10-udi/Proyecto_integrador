-- =====================================================================
-- ENPH - 04. Funciones (Oracle 10g)
-- Calculan los atributos derivados del MER y los indicadores de avance.
-- =====================================================================
SET DEFINE OFF

-- Fecha calendario de un día del período: FECHA_INICIO + día - 1.
CREATE OR REPLACE FUNCTION FN_FECHA_DIA (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE,
  p_dia      IN NUMBER
) RETURN DATE
IS
  v_inicio HOGAR.FECHA_INICIO%TYPE;
BEGIN
  IF p_dia NOT BETWEEN 1 AND 14 THEN
    RAISE_APPLICATION_ERROR(-20001, 'El día debe estar entre 1 y 14');
  END IF;
  SELECT FECHA_INICIO INTO v_inicio FROM HOGAR WHERE ID_HOGAR = p_id_hogar;
  RETURN v_inicio + p_dia - 1;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20002, 'No existe el hogar ' || p_id_hogar);
END;
/

-- Día del período (1-14) que corresponde a una fecha; NULL si está fuera.
CREATE OR REPLACE FUNCTION FN_DIA_DE_FECHA (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE,
  p_fecha    IN DATE
) RETURN NUMBER
IS
  v_dia NUMBER;
BEGIN
  SELECT TRUNC(p_fecha) - FECHA_INICIO + 1 INTO v_dia FROM HOGAR WHERE ID_HOGAR = p_id_hogar;
  IF v_dia BETWEEN 1 AND 14 THEN
    RETURN v_dia;
  END IF;
  RETURN NULL;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20002, 'No existe el hogar ' || p_id_hogar);
END;
/

-- Renglones registrados en un día (D + D1).
CREATE OR REPLACE FUNCTION FN_RENGLONES_DIA (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE,
  p_dia      IN NUMBER
) RETURN NUMBER
IS
  v_d  NUMBER;
  v_d1 NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_d  FROM GASTO_DIARIO WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia;
  SELECT COUNT(*) INTO v_d1 FROM COMIDA_FUERA WHERE ID_HOGAR = p_id_hogar AND DIA_ENCUESTA = p_dia;
  RETURN v_d + v_d1;
END;
/

-- Valor total (pagado o estimado) de un día, o de todo el período si p_dia es NULL.
CREATE OR REPLACE FUNCTION FN_TOTAL_GASTO (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE,
  p_dia      IN NUMBER DEFAULT NULL
) RETURN NUMBER
IS
  v_d  NUMBER;
  v_d1 NUMBER;
BEGIN
  SELECT NVL(SUM(VALOR_PAGADO), 0) INTO v_d FROM GASTO_DIARIO
   WHERE ID_HOGAR = p_id_hogar AND (p_dia IS NULL OR DIA_ENCUESTA = p_dia);
  SELECT NVL(SUM(VALOR_PAGADO), 0) INTO v_d1 FROM COMIDA_FUERA
   WHERE ID_HOGAR = p_id_hogar AND (p_dia IS NULL OR DIA_ENCUESTA = p_dia);
  RETURN v_d + v_d1;
END;
/

-- Días con captura declarada: total de renglones informado y coincidente con lo registrado.
CREATE OR REPLACE FUNCTION FN_DIAS_COMPLETOS (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE
) RETURN NUMBER
IS
  v_n NUMBER := 0;
BEGIN
  FOR j IN (SELECT DIA_ENCUESTA, TOTAL_RENGLONES FROM JORNADA_DIARIA
             WHERE ID_HOGAR = p_id_hogar AND TOTAL_RENGLONES IS NOT NULL) LOOP
    IF j.TOTAL_RENGLONES = FN_RENGLONES_DIA(p_id_hogar, j.DIA_ENCUESTA) THEN
      v_n := v_n + 1;
    END IF;
  END LOOP;
  RETURN v_n;
END;
/

-- Hallazgos de crítica en estado ABIERTO para el hogar (RN-09).
CREATE OR REPLACE FUNCTION FN_HALLAZGOS_ABIERTOS (
  p_id_hogar IN HOGAR.ID_HOGAR%TYPE
) RETURN NUMBER
IS
  v_n NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_n FROM HALLAZGO_CRITICA
   WHERE ID_HOGAR = p_id_hogar AND ESTADO = 'ABIERTO';
  RETURN v_n;
END;
/

-- 'S' si el usuario está asignado y vigente en el hogar, con alguno de los roles dados.
-- p_roles: lista separada por comas, p. ej. 'INFORMANTE,ENCUESTADOR'.
CREATE OR REPLACE FUNCTION FN_USUARIO_AUTORIZADO (
  p_id_usuario IN USUARIO.ID_USUARIO%TYPE,
  p_id_hogar   IN HOGAR.ID_HOGAR%TYPE,
  p_roles      IN VARCHAR2
) RETURN CHAR
IS
  v_n NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_n
    FROM ASIGNACION_HOGAR A
    JOIN USUARIO U ON U.ID_USUARIO = A.ID_USUARIO
    JOIN ROL R     ON R.ID_ROL = U.ID_ROL
   WHERE A.ID_USUARIO = p_id_usuario
     AND A.ID_HOGAR = p_id_hogar
     AND A.ESTADO = 'VIGENTE'
     AND U.ESTADO = 'ACTIVO'
     AND INSTR(',' || p_roles || ',', ',' || R.NOMBRE || ',') > 0;
  IF v_n > 0 THEN
    RETURN 'S';
  END IF;
  RETURN 'N';
END;
/
