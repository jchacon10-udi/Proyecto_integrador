-- =====================================================================
-- ENPH - Instalador completo. Ejecutar conectado como ENPH desde esta carpeta:
--   sqlplus ENPH/<clave>@//localhost:1521/XEPDB1 @instalar.sql
-- Genera el registro instalacion.log (evidencia para el documento).
-- Para reinstalar desde cero, ejecutar antes @99_eliminar_objetos.sql
-- =====================================================================
SET ECHO ON
SET FEEDBACK ON
SET SERVEROUTPUT ON SIZE 1000000
SET DEFINE OFF
SET SQLBLANKLINES ON
SPOOL instalacion.log

@@01_tablas.sql
@@02_secuencias_triggers.sql
@@03_datos_catalogos.sql
@@04_funciones.sql
@@05_procedimientos.sql
@@06_vistas_reportes.sql
@@07_roles_privilegios.sql
@@08_datos_prueba.sql

SET ECHO OFF
SPOOL OFF
SPOOL pruebas.log
@@09_pruebas.sql
@@10_verificacion.sql
SPOOL OFF
