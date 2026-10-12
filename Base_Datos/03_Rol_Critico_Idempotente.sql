-- PROPUESTA. Ejecutar sólo tras validar ROL y sus triggers; requiere autorización.
-- Usa el ID automático REAL del esquema. No cambia IDs ni nombres existentes.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE N NUMBER;
BEGIN
 SELECT COUNT(*) INTO N FROM ROL WHERE NOMBRE='Crítico-digitador';
 IF N>1 THEN RAISE_APPLICATION_ERROR(-20020,'Rol duplicado: revisar datos'); END IF;
 IF N=0 THEN
  SELECT COUNT(*) INTO N FROM ROL
  WHERE REGEXP_REPLACE(REPLACE(LOWER(TRIM(NOMBRE)),'í','i'),
        '[[:space:]‐‑‒–—-]','')='criticodigitador';
  IF N>0 THEN RAISE_APPLICATION_ERROR(-20021,'Existe variante del nombre: reconciliar sin duplicar'); END IF;
  INSERT INTO ROL(NOMBRE) VALUES('Crítico-digitador');
 END IF;
END;
/
SELECT ID_ROL,NOMBRE FROM ROL WHERE NOMBRE='Crítico-digitador';
-- Sin COMMIT automático: revisar resultado y confirmar manualmente o ROLLBACK.
-- Si no existe trigger/estrategia automática, preparar INSERT con ID suministrado
-- por el mecanismo real; NO asumir MAX(ID)+1 ni alterar secuencias existentes.
