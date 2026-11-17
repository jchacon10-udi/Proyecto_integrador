-- =====================================================================
-- ENPH - Cuadernillo 2 urbano. Script generado desde herramientas/modelo.py
-- Compatible con Oracle 10g (sin IDENTITY, sin columnas virtuales).
-- NO editar a mano: modificar modelo.py y regenerar.
-- =====================================================================
-- 99. Elimina los objetos del esquema ENPH para reinstalar desde cero.
-- ATENCION: borra tablas y datos del esquema actual. Usar solo en laboratorio.
BEGIN
  FOR r IN (SELECT object_name, object_type FROM user_objects
            WHERE object_type IN ('VIEW','PROCEDURE','FUNCTION','PACKAGE','SEQUENCE')) LOOP
    IF r.object_name LIKE 'V\_%' ESCAPE '\' OR r.object_name LIKE 'FN\_%' ESCAPE '\'
       OR r.object_name LIKE 'PR\_%' ESCAPE '\' OR r.object_name LIKE 'PKG\_%' ESCAPE '\'
       OR r.object_name LIKE 'SEQ\_%' ESCAPE '\' THEN
      EXECUTE IMMEDIATE 'DROP ' || r.object_type || ' ' || r.object_name;
    END IF;
  END LOOP;
  FOR r IN (SELECT table_name FROM user_tables WHERE table_name IN ('EVENTO_HALLAZGO','HALLAZGO_CRITICA','REVISION_CRITICA','CIERRE_CUADERNILLO','COMIDA_FUERA','GASTO_DIARIO','JORNADA_DIARIA','RESUMEN_MERCADO','CARACTERISTICA_GASTO','FORMA_PAGO','TIPO_COMIDA','LUGAR_COMPRA','FORMA_ADQUISICION','UNIDAD_MEDIDA','TIPO_MERCADO','FRECUENCIA_COMPRA','GRUPO_ALIMENTO','VISITA','ASIGNACION_HOGAR','HOGAR','RESULTADO_ENTREVISTA','USUARIO','ROL')) LOOP
    EXECUTE IMMEDIATE 'DROP TABLE ' || r.table_name || ' CASCADE CONSTRAINTS';
  END LOOP;
END;
/
