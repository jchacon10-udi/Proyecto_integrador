-- =====================================================================
-- ENPH - 00. Creación del esquema y de los usuarios de base de datos
-- Ejecutar UNA VEZ conectado como SYSTEM (o un usuario con privilegio DBA).
-- Si el servidor de la universidad ya entrega un esquema, omitir este script
-- y ejecutar instalar.sql directamente en ese esquema.
-- Las contraseñas se piden al ejecutar el script y no se guardan en él.
-- =====================================================================
SET DEFINE ON
SET VERIFY OFF
ACCEPT clave_enph        CHAR PROMPT 'Clave para ENPH (dueño del esquema): ' HIDE
ACCEPT clave_app         CHAR PROMPT 'Clave para ENPH_APP (aplicación): ' HIDE
ACCEPT clave_informante  CHAR PROMPT 'Clave para ENPH_INFORMANTE: ' HIDE
ACCEPT clave_encuestador CHAR PROMPT 'Clave para ENPH_ENCUESTADOR: ' HIDE
ACCEPT clave_supervisor  CHAR PROMPT 'Clave para ENPH_SUPERVISOR: ' HIDE
ACCEPT clave_critico     CHAR PROMPT 'Clave para ENPH_CRITICO: ' HIDE

-- Dueño de las tablas, vistas y programas
CREATE USER ENPH IDENTIFIED BY "&clave_enph"
  DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP
  QUOTA UNLIMITED ON USERS;
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE SEQUENCE,
      CREATE TRIGGER, CREATE PROCEDURE, CREATE ROLE TO ENPH;

-- Usuario con el que se conecta la aplicación FastAPI
CREATE USER ENPH_APP IDENTIFIED BY "&clave_app"
  DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP;
GRANT CREATE SESSION, CREATE SYNONYM TO ENPH_APP;

-- Un usuario de base de datos por actor, para demostrar los roles
CREATE USER ENPH_INFORMANTE  IDENTIFIED BY "&clave_informante"  DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP;
CREATE USER ENPH_ENCUESTADOR IDENTIFIED BY "&clave_encuestador" DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP;
CREATE USER ENPH_SUPERVISOR  IDENTIFIED BY "&clave_supervisor"  DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP;
CREATE USER ENPH_CRITICO     IDENTIFIED BY "&clave_critico"     DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP;
GRANT CREATE SESSION TO ENPH_INFORMANTE, ENPH_ENCUESTADOR, ENPH_SUPERVISOR, ENPH_CRITICO;

UNDEFINE clave_enph clave_app clave_informante clave_encuestador clave_supervisor clave_critico
SET DEFINE OFF
