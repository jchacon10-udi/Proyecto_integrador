-- =====================================================================
-- ENPH - Diagnóstico previo a la instalación (Oracle 10g o superior).
-- Ejecutar conectado con el usuario donde se instalará el esquema.
-- No crea ni modifica nada. Guarda el resultado en diagnostico.log.
-- =====================================================================
SET LINESIZE 150
SET PAGESIZE 100
COLUMN BANNER FORMAT A80
COLUMN PARAMETER FORMAT A30
COLUMN VALUE FORMAT A40
COLUMN PRIVILEGE FORMAT A30
COLUMN TABLESPACE_NAME FORMAT A20
SPOOL diagnostico.log

PROMPT === D01. Versión del motor
SELECT BANNER FROM V$VERSION;

PROMPT === D02. Usuario conectado y esquema
SELECT USER AS USUARIO, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') AS ESQUEMA FROM DUAL;

PROMPT === D03. Juego de caracteres de la base
SELECT PARAMETER, VALUE FROM NLS_DATABASE_PARAMETERS
 WHERE PARAMETER IN ('NLS_CHARACTERSET', 'NLS_NCHAR_CHARACTERSET');

PROMPT === D04. Privilegios (se requieren CREATE TABLE, VIEW, SEQUENCE, TRIGGER, PROCEDURE; CREATE ROLE es opcional)
SELECT PRIVILEGE FROM SESSION_PRIVS
 WHERE PRIVILEGE IN ('CREATE SESSION', 'CREATE TABLE', 'CREATE VIEW', 'CREATE SEQUENCE', 'CREATE TRIGGER',
                     'CREATE PROCEDURE', 'CREATE ROLE', 'CREATE USER', 'UNLIMITED TABLESPACE')
 ORDER BY PRIVILEGE;

PROMPT === D05. Cuota en tablespaces (-1 = ilimitada)
SELECT TABLESPACE_NAME, MAX_BYTES FROM USER_TS_QUOTAS;
SELECT DEFAULT_TABLESPACE FROM USER_USERS;

PROMPT === D06. Objetos que ya existen en el esquema (si hay del ENPH, ejecutar antes 99_eliminar_objetos.sql)
SELECT OBJECT_TYPE, COUNT(*) AS TOTAL FROM USER_OBJECTS GROUP BY OBJECT_TYPE ORDER BY OBJECT_TYPE;

SPOOL OFF
