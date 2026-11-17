-- =====================================================================
-- ENPH - 03. Datos de catálogos (códigos oficiales del Cuadernillo 2 urbano)
-- Fuente: DANE, ENPH 2016-2017, Cuadernillo 2 urbano, pestaña final y cap. C.
-- =====================================================================
SET DEFINE OFF

INSERT INTO ROL VALUES (1, 'INFORMANTE', 'Registra los capítulos D y D1 de su hogar.');
INSERT INTO ROL VALUES (2, 'ENCUESTADOR', 'Gestiona A, B, C y D2, acompaña la captura y cierra el cuadernillo.');
INSERT INTO ROL VALUES (3, 'SUPERVISOR', 'Revisa casos cerrados y los aprueba o devuelve.');
INSERT INTO ROL VALUES (4, 'CRITICO_DIGITADOR', 'Coteja los datos, registra hallazgos y verifica subsanaciones.');

INSERT INTO RESULTADO_ENTREVISTA VALUES ('EC', 'Encuesta completa');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('NH', 'Nadie en el hogar');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('R',  'Rechazo');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('V',  'Vacante');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('EI', 'Encuesta incompleta');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('AT', 'Ausente temporal');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('OC', 'Ocupado');
INSERT INTO RESULTADO_ENTREVISTA VALUES ('O',  'Otro motivo');

INSERT INTO GRUPO_ALIMENTO VALUES ('01', 'Pan, arepas, bollos y almojábanas');
INSERT INTO GRUPO_ALIMENTO VALUES ('02', 'Galletas de sal y de dulce');
INSERT INTO GRUPO_ALIMENTO VALUES ('03', 'Arroz, pastas alimenticias, avena, maíz, harinas y otros cereales');
INSERT INTO GRUPO_ALIMENTO VALUES ('04', 'Carne de res, cerdo, hueso y vísceras');
INSERT INTO GRUPO_ALIMENTO VALUES ('05', 'Pollo, otras aves y menudencias');
INSERT INTO GRUPO_ALIMENTO VALUES ('06', 'Salchichas, jamón, mortadela, salchichón y otras carnes frías preparadas');
INSERT INTO GRUPO_ALIMENTO VALUES ('07', 'Pescado de río, mar y otros productos marinos');
INSERT INTO GRUPO_ALIMENTO VALUES ('08', 'Leche (animal y vegetal)');
INSERT INTO GRUPO_ALIMENTO VALUES ('09', 'Queso (animal y vegetal)');
INSERT INTO GRUPO_ALIMENTO VALUES ('10', 'Otros derivados de la leche: yogur, kumis, etc.');
INSERT INTO GRUPO_ALIMENTO VALUES ('11', 'Huevos');
INSERT INTO GRUPO_ALIMENTO VALUES ('12', 'Aceites y grasas');
INSERT INTO GRUPO_ALIMENTO VALUES ('13', 'Frutas');
INSERT INTO GRUPO_ALIMENTO VALUES ('14', 'Verduras y hortalizas');
INSERT INTO GRUPO_ALIMENTO VALUES ('15', 'Granos secos: fríjol, lenteja, garbanzo, etc.');
INSERT INTO GRUPO_ALIMENTO VALUES ('16', 'Enlatados y encurtidos');
INSERT INTO GRUPO_ALIMENTO VALUES ('17', 'Plátano, yuca, arracacha, ñame, papa y otros tubérculos');
INSERT INTO GRUPO_ALIMENTO VALUES ('18', 'Azúcar, panela y otros endulzantes');
INSERT INTO GRUPO_ALIMENTO VALUES ('19', 'Mermeladas, arequipe, bocadillos, dulces, helados, chocolatinas, etc.');
INSERT INTO GRUPO_ALIMENTO VALUES ('20', 'Salsas, mayonesa, mostaza, vinagre, etc.');
INSERT INTO GRUPO_ALIMENTO VALUES ('21', 'Sal y condimentos');
INSERT INTO GRUPO_ALIMENTO VALUES ('22', 'Café, chocolate, otras bebidas con cacao, té y aromáticas');
INSERT INTO GRUPO_ALIMENTO VALUES ('23', 'Papas fritas, chitos, maicitos, patacones, maní, etc.');
INSERT INTO GRUPO_ALIMENTO VALUES ('24', 'Agua, gaseosas, refrescos, jugos y otras bebidas no alcohólicas');
INSERT INTO GRUPO_ALIMENTO VALUES ('25', 'Alimentos y bebidas preparados fuera del hogar');

INSERT INTO FRECUENCIA_COMPRA VALUES ('1',   'Nunca');
INSERT INTO FRECUENCIA_COMPRA VALUES ('2',   'Diario');
INSERT INTO FRECUENCIA_COMPRA VALUES ('2.1', 'Varias veces por semana');
INSERT INTO FRECUENCIA_COMPRA VALUES ('3',   'Semanal');
INSERT INTO FRECUENCIA_COMPRA VALUES ('4',   'Quincenal');
INSERT INTO FRECUENCIA_COMPRA VALUES ('5',   'Mensual');
INSERT INTO FRECUENCIA_COMPRA VALUES ('6',   'Bimestral');
INSERT INTO FRECUENCIA_COMPRA VALUES ('7',   'Trimestral');
INSERT INTO FRECUENCIA_COMPRA VALUES ('9',   'Esporádica');

INSERT INTO TIPO_MERCADO VALUES ('95', 'Carnes, huevos, leche y sus derivados');
INSERT INTO TIPO_MERCADO VALUES ('96', 'Frutas y verduras');
INSERT INTO TIPO_MERCADO VALUES ('97', 'Granos, harinas, cereales, azúcar y abarrotes en general');
INSERT INTO TIPO_MERCADO VALUES ('98', 'Mercado único (carnes, frutas, verduras y granos)');

INSERT INTO UNIDAD_MEDIDA VALUES ('1', 'Centímetros cúbicos');
INSERT INTO UNIDAD_MEDIDA VALUES ('2', 'Litro');
INSERT INTO UNIDAD_MEDIDA VALUES ('3', 'Gramos');
INSERT INTO UNIDAD_MEDIDA VALUES ('4', 'Onzas');
INSERT INTO UNIDAD_MEDIDA VALUES ('5', 'Libra');
INSERT INTO UNIDAD_MEDIDA VALUES ('6', 'Kilo');
INSERT INTO UNIDAD_MEDIDA VALUES ('7', 'Arroba');
INSERT INTO UNIDAD_MEDIDA VALUES ('8', 'Otra');

INSERT INTO FORMA_ADQUISICION VALUES ('1', 'Compra');
INSERT INTO FORMA_ADQUISICION VALUES ('2', 'Recibido como pago por trabajo');
INSERT INTO FORMA_ADQUISICION VALUES ('3', 'Regalo o donación');
INSERT INTO FORMA_ADQUISICION VALUES ('4', 'Intercambio o trueque');
INSERT INTO FORMA_ADQUISICION VALUES ('5', 'Traído de la finca o producido por el hogar');
INSERT INTO FORMA_ADQUISICION VALUES ('6', 'Tomado de un negocio del hogar');
INSERT INTO FORMA_ADQUISICION VALUES ('7', 'Otra');

INSERT INTO LUGAR_COMPRA VALUES ('1',  'Almacenes, supermercados de cadena, tiendas por departamento o hipermercados');
INSERT INTO LUGAR_COMPRA VALUES ('4',  'Supermercados de cajas de compensación, cooperativas, fondos de empleados y comisariatos');
INSERT INTO LUGAR_COMPRA VALUES ('6',  'Supermercado de barrio, tiendas de barrio, cigarrerías, salsamentarias y delicatessen');
INSERT INTO LUGAR_COMPRA VALUES ('7',  'Misceláneas de barrio y cacharrerías');
INSERT INTO LUGAR_COMPRA VALUES ('10', 'Plazas de mercado, galerías, mercados móviles, centrales mayoristas y graneros');
INSERT INTO LUGAR_COMPRA VALUES ('13', 'Vendedores ambulantes');
INSERT INTO LUGAR_COMPRA VALUES ('14', 'Sanandresitos, bodegas y fábricas');
INSERT INTO LUGAR_COMPRA VALUES ('16', 'Establecimiento especializado en la venta del artículo o la prestación del servicio');
INSERT INTO LUGAR_COMPRA VALUES ('17', 'Farmacias y droguerías');
INSERT INTO LUGAR_COMPRA VALUES ('18', 'Restaurantes');
INSERT INTO LUGAR_COMPRA VALUES ('19', 'Cafeterías y establecimientos de comidas rápidas');
INSERT INTO LUGAR_COMPRA VALUES ('20', 'Persona particular');
INSERT INTO LUGAR_COMPRA VALUES ('21', 'Ferias especializadas');
INSERT INTO LUGAR_COMPRA VALUES ('22', 'A través de internet');
INSERT INTO LUGAR_COMPRA VALUES ('23', 'Televentas y ventas por catálogo');
INSERT INTO LUGAR_COMPRA VALUES ('24', 'Otro');
INSERT INTO LUGAR_COMPRA VALUES ('25', 'Plazoleta de comidas');

INSERT INTO TIPO_COMIDA VALUES ('1', 'Desayuno');
INSERT INTO TIPO_COMIDA VALUES ('2', 'Almuerzo');
INSERT INTO TIPO_COMIDA VALUES ('3', 'Cena');
INSERT INTO TIPO_COMIDA VALUES ('4', 'Onces, medias nueves, snacks');

INSERT INTO FORMA_PAGO VALUES ('1', 'Tarjeta débito');
INSERT INTO FORMA_PAGO VALUES ('2', 'Tarjeta de crédito');
INSERT INTO FORMA_PAGO VALUES ('3', 'Efectivo');
INSERT INTO FORMA_PAGO VALUES ('4', 'Fiado');
INSERT INTO FORMA_PAGO VALUES ('5', 'Bonos');
INSERT INTO FORMA_PAGO VALUES ('6', 'Otra');

COMMIT;
