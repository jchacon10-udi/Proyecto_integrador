"""Reglas del Cuadernillo 2 que dependen solo de los datos del registro.

Son las mismas restricciones CHECK de 01_tablas.sql (el nombre de cada una va
en el mensaje). Validarlas aquí permite responder con un mensaje claro antes de
llegar a la base de datos; Oracle las vuelve a garantizar.
"""
from datetime import date, timedelta

from .errores import ErrorNegocio
from .modelos import CaracteristicaEntrada, CierreEntrada, ComidaEntrada, GastoEntrada, HallazgoEntrada, VisitaEntrada

COMPRA = "1"
OTRA_FORMA = "7"
OTRA_UNIDAD = "8"
NUNCA = "1"
OTRA_FORMA_PAGO = "6"
FRECUENCIAS_MAYORES_A_BISEMANA = {"5", "6", "7", "9"}
DIAS = 14
DIAS_GASTO_PERSONAL = 7
GRUPOS_CAPITULO_C = 25

ESTADOS_CAPTURA_ABIERTA = {"EN_CAPTURA", "DEVUELTO"}


def fecha_dia(fecha_inicio: date, dia: int) -> date:
    """FN_FECHA_DIA: fecha calendario del día del período (atributo derivado)."""
    validar_dia(dia)
    return fecha_inicio + timedelta(days=dia - 1)


def validar_dia(dia: int):
    if not 1 <= dia <= DIAS:
        raise ErrorNegocio("El día debe estar entre 1 y 14", "ORA-20001")


def _exigir(condicion: bool, mensaje: str, restriccion: str):
    if not condicion:
        raise ErrorNegocio(f"{mensaje} ({restriccion})", "ORA-02290")


def _forma_y_compra(dto, prefijo: str):
    _exigir((dto.cod_forma == OTRA_FORMA) == (dto.otra_forma is not None),
            "La forma «Otra» exige especificarla, y solo ella", f"CK_{prefijo}_OTRA_FORMA")
    if dto.cod_forma == COMPRA:
        _exigir(dto.cod_frecuencia is not None, "Una compra exige la frecuencia de compra", f"CK_{prefijo}_COMPRA")
    else:
        _exigir(dto.cod_lugar is None and dto.cod_frecuencia is None,
                "Lugar y frecuencia solo aplican cuando la forma de adquisición es Compra", f"CK_{prefijo}_COMPRA")
    _exigir(dto.cod_frecuencia != NUNCA, "La frecuencia «Nunca» no aplica a un gasto registrado", f"CK_{prefijo}_FRECUENCIA")


def validar_gasto(dto: GastoEntrada, dia: int):
    """CHECK de GASTO_DIARIO (capítulo D)."""
    validar_dia(dia)
    if dto.tipo_item == "BIEN":
        _exigir(dto.cod_unidad is not None, "Un BIEN exige unidad de medida", "CK_GD_UNIDAD")
    else:
        _exigir(dto.cod_unidad is None and dto.equivalencia_g_cc is None,
                "Un SERVICIO no lleva unidad ni equivalencia", "CK_GD_UNIDAD")
    _exigir((dto.cod_unidad == OTRA_UNIDAD) == (dto.otra_unidad is not None),
            "La unidad «Otra» exige especificarla, y solo ella", "CK_GD_OTRA_UNIDAD")
    if dto.equivalencia_g_cc is not None:
        _exigir(dto.cod_unidad == OTRA_UNIDAD and dto.equivalencia_g_cc > 0,
                "La equivalencia en gramos o cc solo aplica a unidades no tradicionales (Otra)", "CK_GD_EQUIVALENCIA")
    _forma_y_compra(dto, "GD")
    _exigir(dto.tipo_gasto != "2" or dia <= DIAS_GASTO_PERSONAL,
            "El gasto personal del responsable solo se registra en los días 1 a 7", "CK_GD_PERSONAL_7")


def validar_comida(dto: ComidaEntrada, dia: int):
    """CHECK de COMIDA_FUERA (apartado D1)."""
    validar_dia(dia)
    _forma_y_compra(dto, "CF")
    _exigir(dto.tipo_gasto != "2" or dia <= DIAS_GASTO_PERSONAL,
            "El gasto personal del responsable solo se registra en los días 1 a 7", "CK_CF_PERSONAL_7")


def validar_caracteristica(dto: CaracteristicaEntrada):
    """CK_CG_BISEMANA: C3.1 y C3.2 solo para frecuencias mayores a la bisemana."""
    if dto.cod_frecuencia not in FRECUENCIAS_MAYORES_A_BISEMANA:
        _exigir(dto.valor_ultima_compra is None and dto.comprara_14_dias is None,
                "El valor de la última compra y la compra en 14 días solo aplican a frecuencias "
                "mensual, bimestral, trimestral o esporádica", "CK_CG_BISEMANA")


def validar_visita(dto: VisitaEntrada):
    _exigir(dto.fecha_hora_fin is None or dto.fecha_hora_fin > dto.fecha_hora_inicio,
            "La hora de fin debe ser posterior a la de inicio", "CK_VISITA_FIN")
    _exigir(dto.proxima_visita is None or dto.proxima_visita > dto.fecha_hora_inicio,
            "La próxima visita debe ser posterior a esta", "CK_VISITA_PROX")


def validar_hogar(total_hogares_vivienda: int, hogar_numero: int):
    _exigir(1 <= hogar_numero <= total_hogares_vivienda,
            "El número de hogar no puede superar el total de hogares de la vivienda", "CK_HOGAR_NUMERO")


def validar_cierre(dto: CierreEntrada):
    _exigir((dto.cod_forma_pago == OTRA_FORMA_PAGO) == (dto.otra_forma_pago is not None),
            "La forma de pago «Otra» exige especificarla, y solo ella", "CK_CC_OTRA_PAGO")


def validar_hallazgo(dto: HallazgoEntrada):
    _exigir((dto.capitulo in ("D", "D1")) == (dto.dia_encuesta is not None),
            "Un hallazgo de los capítulos D o D1 exige el día; los demás capítulos no lo llevan", "CK_HC_DIA")
