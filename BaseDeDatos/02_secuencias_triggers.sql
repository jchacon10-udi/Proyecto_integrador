-- =====================================================================
-- ENPH - 02. Secuencias y disparadores (Oracle 10g)
-- Ejecutar como el dueño del esquema después de 01_tablas.sql.
-- Códigos de error de negocio: -20001 a -20099 (ver 01_Diseno).
-- =====================================================================
SET DEFINE OFF

-- ---------------------------------------------------------------------
-- Claves sustitutas: solo USUARIO y HOGAR. Las demás tablas usan claves
-- naturales (catálogos) o claves compuestas de entidades débiles.
-- ---------------------------------------------------------------------
CREATE SEQUENCE SEQ_USUARIO START WITH 100 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_HOGAR   START WITH 1000 INCREMENT BY 1 NOCACHE NOCYCLE;

CREATE OR REPLACE TRIGGER TRG_USUARIO_ID
BEFORE INSERT ON USUARIO
FOR EACH ROW
WHEN (NEW.ID_USUARIO IS NULL)
BEGIN
  SELECT SEQ_USUARIO.NEXTVAL INTO :NEW.ID_USUARIO FROM DUAL;
END;
/

CREATE OR REPLACE TRIGGER TRG_HOGAR_ID
BEFORE INSERT ON HOGAR
FOR EACH ROW
WHEN (NEW.ID_HOGAR IS NULL)
BEGIN
  SELECT SEQ_HOGAR.NEXTVAL INTO :NEW.ID_HOGAR FROM DUAL;
END;
/

-- ---------------------------------------------------------------------
-- Captura D y D1: solo con el caso abierto (EN_CAPTURA o DEVUELTO).
-- ---------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_GD_CAPTURA_ABIERTA
BEFORE INSERT OR UPDATE OR DELETE ON GASTO_DIARIO
FOR EACH ROW
DECLARE
  v_estado HOGAR.ESTADO%TYPE;
  v_hogar  HOGAR.ID_HOGAR%TYPE;
BEGIN
  IF DELETING THEN
    v_hogar := :OLD.ID_HOGAR;
  ELSE
    v_hogar := :NEW.ID_HOGAR;
  END IF;
  SELECT ESTADO INTO v_estado FROM HOGAR WHERE ID_HOGAR = v_hogar;
  IF v_estado NOT IN ('EN_CAPTURA', 'DEVUELTO') THEN
    RAISE_APPLICATION_ERROR(-20010, 'Captura cerrada: el hogar está en estado ' || v_estado);
  END IF;
END;
/

CREATE OR REPLACE TRIGGER TRG_CF_CAPTURA_ABIERTA
BEFORE INSERT OR UPDATE OR DELETE ON COMIDA_FUERA
FOR EACH ROW
DECLARE
  v_estado HOGAR.ESTADO%TYPE;
  v_hogar  HOGAR.ID_HOGAR%TYPE;
BEGIN
  IF DELETING THEN
    v_hogar := :OLD.ID_HOGAR;
  ELSE
    v_hogar := :NEW.ID_HOGAR;
  END IF;
  SELECT ESTADO INTO v_estado FROM HOGAR WHERE ID_HOGAR = v_hogar;
  IF v_estado NOT IN ('EN_CAPTURA', 'DEVUELTO') THEN
    RAISE_APPLICATION_ERROR(-20010, 'Captura cerrada: el hogar está en estado ' || v_estado);
  END IF;
END;
/

-- Auditoría: FECHA_REGISTRO refleja la última modificación del renglón.
CREATE OR REPLACE TRIGGER TRG_GD_AUDITORIA
BEFORE UPDATE ON GASTO_DIARIO
FOR EACH ROW
BEGIN
  :NEW.FECHA_REGISTRO := SYSDATE;
END;
/

CREATE OR REPLACE TRIGGER TRG_CF_AUDITORIA
BEFORE UPDATE ON COMIDA_FUERA
FOR EACH ROW
BEGIN
  :NEW.FECHA_REGISTRO := SYSDATE;
END;
/

-- ---------------------------------------------------------------------
-- Cierre: solo un SUPERVISOR decide y solo un ENCUESTADOR cierra.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_CC_ROLES
BEFORE INSERT OR UPDATE ON CIERRE_CUADERNILLO
FOR EACH ROW
DECLARE
  v_n NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_n FROM USUARIO U JOIN ROL R ON R.ID_ROL = U.ID_ROL
   WHERE U.ID_USUARIO = :NEW.ID_ENCUESTADOR AND R.NOMBRE = 'ENCUESTADOR';
  IF v_n = 0 THEN
    RAISE_APPLICATION_ERROR(-20020, 'El cierre debe registrarlo un ENCUESTADOR');
  END IF;
  IF :NEW.ID_SUPERVISOR IS NOT NULL THEN
    SELECT COUNT(*) INTO v_n FROM USUARIO U JOIN ROL R ON R.ID_ROL = U.ID_ROL
     WHERE U.ID_USUARIO = :NEW.ID_SUPERVISOR AND R.NOMBRE = 'SUPERVISOR';
    IF v_n = 0 THEN
      RAISE_APPLICATION_ERROR(-20021, 'La revisión del cierre corresponde a un SUPERVISOR');
    END IF;
  END IF;
END;
/

-- ---------------------------------------------------------------------
-- Crítica (RN-11, RN-13)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_RC_ROL_CRITICO
BEFORE INSERT OR UPDATE OF ID_CRITICO ON REVISION_CRITICA
FOR EACH ROW
DECLARE
  v_n NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_n FROM USUARIO U JOIN ROL R ON R.ID_ROL = U.ID_ROL
   WHERE U.ID_USUARIO = :NEW.ID_CRITICO AND R.NOMBRE = 'CRITICO_DIGITADOR';
  IF v_n = 0 THEN
    RAISE_APPLICATION_ERROR(-20030, 'La revisión de crítica la realiza un CRITICO_DIGITADOR');
  END IF;
END;
/

CREATE OR REPLACE TRIGGER TRG_RC_INMUTABLE
BEFORE UPDATE OR DELETE ON REVISION_CRITICA
FOR EACH ROW
BEGIN
  IF DELETING THEN
    RAISE_APPLICATION_ERROR(-20031, 'Las revisiones de crítica no se eliminan');
  END IF;
  IF :OLD.ESTADO <> 'EN_REVISION' THEN
    RAISE_APPLICATION_ERROR(-20032, 'Revisión concluida: es inmutable; inicie una nueva revisión');
  END IF;
  IF :NEW.ID_CRITICO <> :OLD.ID_CRITICO OR :NEW.FECHA_REVISION <> :OLD.FECHA_REVISION THEN
    RAISE_APPLICATION_ERROR(-20033, 'No se modifica el autor ni la fecha de la revisión');
  END IF;
END;
/

CREATE OR REPLACE TRIGGER TRG_HC_TRANSICION
BEFORE INSERT OR UPDATE OR DELETE ON HALLAZGO_CRITICA
FOR EACH ROW
DECLARE
  v_estado_rev REVISION_CRITICA.ESTADO%TYPE;
BEGIN
  IF DELETING THEN
    RAISE_APPLICATION_ERROR(-20040, 'Los hallazgos no se eliminan; se conserva su historial');
  END IF;
  IF INSERTING THEN
    IF :NEW.ESTADO <> 'ABIERTO' THEN
      RAISE_APPLICATION_ERROR(-20041, 'Todo hallazgo inicia en estado ABIERTO');
    END IF;
    SELECT ESTADO INTO v_estado_rev FROM REVISION_CRITICA
     WHERE ID_HOGAR = :NEW.ID_HOGAR AND NUMERO_REVISION = :NEW.NUMERO_REVISION;
    IF v_estado_rev <> 'EN_REVISION' THEN
      RAISE_APPLICATION_ERROR(-20042, 'Solo se registran hallazgos en una revisión EN_REVISION');
    END IF;
  ELSE
    IF :NEW.CAPITULO <> :OLD.CAPITULO OR :NEW.DESCRIPCION <> :OLD.DESCRIPCION
       OR NVL(:NEW.DIA_ENCUESTA, 0) <> NVL(:OLD.DIA_ENCUESTA, 0)
       OR :NEW.FECHA_REGISTRO <> :OLD.FECHA_REGISTRO THEN
      RAISE_APPLICATION_ERROR(-20043, 'El hallazgo original no se sobrescribe');
    END IF;
    IF :OLD.ESTADO = 'VERIFICADO' THEN
      RAISE_APPLICATION_ERROR(-20044, 'Hallazgo VERIFICADO: es inmutable');
    END IF;
    IF :NEW.ESTADO <> :OLD.ESTADO AND NOT (
         (:OLD.ESTADO = 'ABIERTO'   AND :NEW.ESTADO = 'CORREGIDO') OR
         (:OLD.ESTADO = 'CORREGIDO' AND :NEW.ESTADO = 'VERIFICADO') OR
         (:OLD.ESTADO = 'CORREGIDO' AND :NEW.ESTADO = 'ABIERTO')) THEN
      RAISE_APPLICATION_ERROR(-20045, 'Transición no permitida: ' || :OLD.ESTADO || ' -> ' || :NEW.ESTADO);
    END IF;
  END IF;
END;
/

CREATE OR REPLACE TRIGGER TRG_EH_INMUTABLE
BEFORE UPDATE OR DELETE ON EVENTO_HALLAZGO
FOR EACH ROW
BEGIN
  RAISE_APPLICATION_ERROR(-20050, 'El historial de eventos no se modifica ni se elimina');
END;
/
