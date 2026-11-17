"""Casos de uso CU-01 a CU-14: autorización, estados del caso y reglas entre tablas.

Cada método abre una transacción del repositorio, comprueba rol y asignación,
valida el estado del hogar y las reglas, y escribe. Los códigos ORA- de los
errores son los mismos que lanzan los procedimientos y disparadores de Oracle.
"""
from decimal import Decimal

from .errores import Conflicto, CredencialesInvalidas, ErrorNegocio, NoAutorizado, NoEncontrado
from .modelos import (Avance, Caracteristica, CaracteristicaEntrada, CierreEntrada, CierreJornada, ComidaEntrada,
                      Conclusion, Correccion, DecisionSupervisor, GastoEntrada, HallazgoEntrada, Hogar,
                      HogarActualizacion, HogarNuevo, Jornada, ResumenEntrada, Usuario, UsuarioNuevo, Verificacion,
                      VisitaEntrada)
from .reglas import (DIAS, ESTADOS_CAPTURA_ABIERTA, GRUPOS_CAPITULO_C, fecha_dia, validar_caracteristica,
                     validar_cierre, validar_comida, validar_dia, validar_gasto, validar_hallazgo, validar_hogar,
                     validar_visita)
from .repositorio.base import Repositorio, buscar_hallazgo
from .seguridad import Sesiones, generar_hash, verificar_clave

INFORMANTE, ENCUESTADOR, SUPERVISOR, CRITICO = "INFORMANTE", "ENCUESTADOR", "SUPERVISOR", "CRITICO_DIGITADOR"
REPORTES = {"gasto_por_forma": {SUPERVISOR}, "gasto_por_lugar": {SUPERVISOR}, "comidas_por_tipo": {SUPERVISOR},
            "carga_encuestador": {SUPERVISOR}, "hallazgos": {SUPERVISOR, CRITICO}}


class Servicios:
    def __init__(self, repositorio: Repositorio, sesiones: Sesiones | None = None):
        self.repo = repositorio
        self.sesiones = sesiones or Sesiones()

    # ================================================================ utilidades
    @staticmethod
    def _exigir_rol(u: Usuario, *roles: str):
        if u.rol not in roles:
            raise NoAutorizado(f"La operación corresponde a: {', '.join(roles)}")

    @staticmethod
    def _hogar(r: Repositorio, id_hogar: int) -> Hogar:
        h = r.hogar(id_hogar)
        if h is None:
            raise NoEncontrado(f"No existe el hogar {id_hogar}", "ORA-20002")
        return h

    def _autorizar(self, r: Repositorio, u: Usuario, id_hogar: int, *roles: str) -> Hogar:
        """PR_EXIGIR_AUTORIZACION: rol permitido y asignación VIGENTE al hogar."""
        h = self._hogar(r, id_hogar)
        self._exigir_rol(u, *roles)
        if id_hogar not in r.hogares_asignados(u.id_usuario):
            raise NoAutorizado(f"Sin asignación vigente al hogar {h.codigo_operativo}", "ORA-20060")
        return h

    def _ver(self, r: Repositorio, u: Usuario, id_hogar: int) -> Hogar:
        """Lectura: el supervisor ve todos los hogares; los demás, solo los asignados."""
        if u.rol == SUPERVISOR:
            return self._hogar(r, id_hogar)
        return self._autorizar(r, u, id_hogar, u.rol)

    @staticmethod
    def _captura_abierta(h: Hogar):
        """TRG_GD_CAPTURA_ABIERTA: D y D1 solo cambian con el caso EN_CAPTURA o DEVUELTO."""
        if h.estado not in ESTADOS_CAPTURA_ABIERTA:
            raise Conflicto(f"Captura cerrada: el hogar está en estado {h.estado}", "ORA-20010")

    @staticmethod
    def _editable(h: Hogar):
        """Capítulos A, B y C: no se modifican con el caso cerrado o aprobado."""
        if h.estado in ("CERRADO", "APROBADO"):
            raise Conflicto(f"El hogar está {h.estado}: no admite cambios")

    @staticmethod
    def _catalogo(r: Repositorio, nombre: str, codigo: str | None, etiqueta: str):
        if codigo is not None and codigo not in {c["codigo"] for c in r.catalogos()[nombre]}:
            raise ErrorNegocio(f"{etiqueta} «{codigo}» no existe en el catálogo", "ORA-02291")

    @staticmethod
    def _jornada(r: Repositorio, id_hogar: int, dia: int):
        validar_dia(dia)
        if dia not in r.jornadas(id_hogar):
            raise ErrorNegocio(f"La jornada {dia} no existe: inicie la captura del hogar", "ORA-20064")

    def _renglones(self, r: Repositorio, id_hogar: int, dia: int) -> int:
        """FN_RENGLONES_DIA: renglones D + D1 del día."""
        return len(r.gastos(id_hogar, dia)) + len(r.comidas(id_hogar, dia))

    def _jornadas(self, r: Repositorio, h: Hogar) -> list[Jornada]:
        hoy = r.hoy()
        gastos, comidas = r.gastos(h.id_hogar), r.comidas(h.id_hogar)
        salida = []
        for dia, (total, obs) in r.jornadas(h.id_hogar).items():
            d = [g for g in gastos if g.dia_encuesta == dia]
            d1 = [c for c in comidas if c.dia_encuesta == dia]
            fecha = fecha_dia(h.fecha_inicio, dia)
            salida.append(Jornada(dia_encuesta=dia, fecha=fecha, total_renglones=total, observaciones=obs,
                                  renglones_d=len(d), renglones_d1=len(d1),
                                  valor_total=sum((x.valor_pagado for x in d + d1), Decimal(0)),
                                  completa=total is not None and total == len(d) + len(d1), futura=fecha > hoy))
        return salida

    def _avance(self, r: Repositorio, h: Hogar) -> Avance:
        """V_AVANCE_HOGAR."""
        jornadas = self._jornadas(r, h)
        return Avance(id_hogar=h.id_hogar, codigo_operativo=h.codigo_operativo, direccion=h.direccion,
                      estado=h.estado, fecha_inicio=h.fecha_inicio, fecha_fin=h.fecha_fin,
                      dias_completos=sum(j.completa for j in jornadas),
                      renglones_d=sum(j.renglones_d for j in jornadas),
                      renglones_d1=sum(j.renglones_d1 for j in jornadas),
                      grupos_capitulo_c=len(r.caracteristicas(h.id_hogar)),
                      valor_total=sum((j.valor_total for j in jornadas), Decimal(0)),
                      hallazgos_abiertos=self._abiertos(r, h.id_hogar))

    @staticmethod
    def _abiertos(r: Repositorio, id_hogar: int) -> int:
        """FN_HALLAZGOS_ABIERTOS."""
        return sum(1 for rev in r.revisiones(id_hogar) for x in rev.hallazgos if x.estado == "ABIERTO")

    # ================================================================ CU-01 autenticarse
    def iniciar_sesion(self, nombre_usuario: str, clave: str) -> tuple[str, Usuario]:
        with self.repo.transaccion() as r:
            fila = r.usuario_por_nombre(nombre_usuario)
        if fila is None or fila[0].estado != "ACTIVO" or not verificar_clave(clave, fila[1]):
            raise CredencialesInvalidas("Usuario o contraseña incorrectos")
        return self.sesiones.abrir(fila[0]), fila[0]

    def usuario_de_token(self, token: str) -> Usuario:
        id_usuario = self.sesiones.usuario(token)
        with self.repo.transaccion() as r:
            u = r.usuario(id_usuario)
        if u is None or u.estado != "ACTIVO":
            raise CredencialesInvalidas("Usuario inactivo")
        return u

    def cerrar_sesion(self, token: str):
        self.sesiones.cerrar(token)

    def crear_usuario(self, u: Usuario, dto: UsuarioNuevo) -> Usuario:
        """Alta de usuarios por el supervisor; la contraseña se guarda como hash PBKDF2."""
        self._exigir_rol(u, SUPERVISOR)
        with self.repo.transaccion() as r:
            id_rol = next(int(c["codigo"]) for c in r.catalogos()["rol"] if c["nombre"] == dto.rol)
            nuevo = r.crear_usuario(id_rol, dto.nombre_usuario, dto.nombre_completo, dto.correo, generar_hash(dto.clave))
            return r.usuario(nuevo)

    def cambiar_estado_usuario(self, u: Usuario, id_usuario: int, estado: str) -> Usuario:
        self._exigir_rol(u, SUPERVISOR)
        if id_usuario == u.id_usuario:
            raise ErrorNegocio("No puede desactivar su propio usuario")
        with self.repo.transaccion() as r:
            if r.usuario(id_usuario) is None:
                raise NoEncontrado(f"No existe el usuario {id_usuario}")
            r.cambiar_estado_usuario(id_usuario, estado)
            return r.usuario(id_usuario)

    def catalogos(self) -> dict:
        with self.repo.transaccion() as r:
            return r.catalogos()

    def usuarios(self, u: Usuario) -> list[Usuario]:
        self._exigir_rol(u, SUPERVISOR)
        with self.repo.transaccion() as r:
            return r.usuarios()

    # ================================================================ CU-10 avance y lista de hogares
    def hogares(self, u: Usuario) -> list[Avance]:
        with self.repo.transaccion() as r:
            ids = None if u.rol == SUPERVISOR else r.hogares_asignados(u.id_usuario)
            return [self._avance(r, h) for h in r.hogares(ids)]

    def avance(self, u: Usuario, id_hogar: int) -> dict:
        with self.repo.transaccion() as r:
            h = self._ver(r, u, id_hogar)
            return {"avance": self._avance(r, h), "jornadas": self._jornadas(r, h)}

    # ================================================================ CU-02 identificación (capítulo A)
    def hogar(self, u: Usuario, id_hogar: int) -> dict:
        with self.repo.transaccion() as r:
            h = self._ver(r, u, id_hogar)
            return {"hogar": h, "asignaciones": [{"usuario": a, "estado": e} for a, e in r.asignaciones(id_hogar)]}

    def crear_hogar(self, u: Usuario, dto: HogarNuevo) -> Hogar:
        self._exigir_rol(u, ENCUESTADOR)
        validar_hogar(dto.total_hogares_vivienda, dto.hogar_numero)
        with self.repo.transaccion() as r:
            id_hogar = r.crear_hogar(dto)
            r.asignar(u.id_usuario, id_hogar)
            return r.hogar(id_hogar)

    def actualizar_hogar(self, u: Usuario, id_hogar: int, dto: HogarActualizacion) -> Hogar:
        validar_hogar(dto.total_hogares_vivienda, dto.hogar_numero)
        with self.repo.transaccion() as r:
            self._editable(self._autorizar(r, u, id_hogar, ENCUESTADOR))
            r.actualizar_hogar(id_hogar, dto)
            return r.hogar(id_hogar)

    def asignar(self, u: Usuario, id_hogar: int, id_usuario: int):
        """RF-03: el supervisor asigna usuarios a los hogares."""
        self._exigir_rol(u, SUPERVISOR)
        with self.repo.transaccion() as r:
            self._hogar(r, id_hogar)
            destino = r.usuario(id_usuario)
            if destino is None or destino.estado != "ACTIVO":
                raise NoEncontrado(f"No existe un usuario activo {id_usuario}")
            r.asignar(id_usuario, id_hogar)

    def iniciar_captura(self, u: Usuario, id_hogar: int) -> Hogar:
        """RF-07: abre el período de 14 días."""
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, ENCUESTADOR)
            if h.estado != "ASIGNADO":
                raise Conflicto(f"Solo se inicia la captura de un hogar ASIGNADO (actual: {h.estado})", "ORA-20061")
            if not any(a.rol == INFORMANTE and e == "VIGENTE" for a, e in r.asignaciones(id_hogar)):
                raise ErrorNegocio("El hogar no tiene un INFORMANTE asignado", "ORA-20062")
            r.iniciar_captura(id_hogar, u.id_usuario)
            return r.hogar(id_hogar)

    # ================================================================ CU-03 visitas (capítulo B)
    def visitas(self, u: Usuario, id_hogar: int):
        with self.repo.transaccion() as r:
            self._ver(r, u, id_hogar)
            return r.visitas(id_hogar)

    def registrar_visita(self, u: Usuario, id_hogar: int, dto: VisitaEntrada):
        validar_visita(dto)
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, ENCUESTADOR)
            if h.estado == "APROBADO":
                raise Conflicto("El hogar está APROBADO: no admite más visitas")
            self._catalogo(r, "resultado_entrevista", dto.cod_resultado, "El resultado")
            numero = max((v.numero_visita for v in r.visitas(id_hogar)), default=0) + 1
            if numero > DIAS:
                raise ErrorNegocio("Se admiten como máximo 14 visitas por hogar (CK_VISITA_NUM)", "ORA-02290")
            r.crear_visita(id_hogar, numero, dto)
            return r.visitas(id_hogar)[-1]

    def actualizar_visita(self, u: Usuario, id_hogar: int, numero: int, dto: VisitaEntrada):
        validar_visita(dto)
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, ENCUESTADOR)
            if h.estado == "APROBADO":
                raise Conflicto("El hogar está APROBADO: no admite cambios")
            self._catalogo(r, "resultado_entrevista", dto.cod_resultado, "El resultado")
            r.actualizar_visita(id_hogar, numero, dto)
            return next(v for v in r.visitas(id_hogar) if v.numero_visita == numero)

    # ================================================================ CU-04 características (capítulo C)
    def caracteristicas(self, u: Usuario, id_hogar: int) -> dict:
        with self.repo.transaccion() as r:
            self._ver(r, u, id_hogar)
            actuales = {c.cod_grupo: c for c in r.caracteristicas(id_hogar)}
            grupos = [{"cod_grupo": g["codigo"], "grupo": g["nombre"], "registro": actuales.get(g["codigo"])}
                      for g in r.catalogos()["grupo_alimento"]]
            return {"grupos": grupos, "resumen_mercado": r.resumen_mercado(id_hogar)}

    def guardar_caracteristica(self, u: Usuario, id_hogar: int, cod_grupo: str,
                               dto: CaracteristicaEntrada) -> Caracteristica:
        validar_caracteristica(dto)
        with self.repo.transaccion() as r:
            self._editable(self._autorizar(r, u, id_hogar, ENCUESTADOR))
            self._catalogo(r, "grupo_alimento", cod_grupo, "El grupo")
            self._catalogo(r, "frecuencia_compra", dto.cod_frecuencia, "La frecuencia")
            r.guardar_caracteristica(id_hogar, cod_grupo, dto)
            return next(c for c in r.caracteristicas(id_hogar) if c.cod_grupo == cod_grupo)

    def eliminar_caracteristica(self, u: Usuario, id_hogar: int, cod_grupo: str):
        with self.repo.transaccion() as r:
            self._editable(self._autorizar(r, u, id_hogar, ENCUESTADOR))
            r.eliminar_caracteristica(id_hogar, cod_grupo)

    def guardar_resumen(self, u: Usuario, id_hogar: int, cod_mercado: str, dto: ResumenEntrada):
        with self.repo.transaccion() as r:
            self._editable(self._autorizar(r, u, id_hogar, ENCUESTADOR))
            self._catalogo(r, "tipo_mercado", cod_mercado, "El tipo de mercado")
            r.guardar_resumen(id_hogar, cod_mercado, dto.valor_total)
            return r.resumen_mercado(id_hogar)

    def eliminar_resumen(self, u: Usuario, id_hogar: int, cod_mercado: str):
        with self.repo.transaccion() as r:
            self._editable(self._autorizar(r, u, id_hogar, ENCUESTADOR))
            r.eliminar_resumen(id_hogar, cod_mercado)

    # ================================================================ CU-05 y CU-06 captura diaria
    def dia(self, u: Usuario, id_hogar: int, dia: int) -> dict:
        with self.repo.transaccion() as r:
            h = self._ver(r, u, id_hogar)
            self._jornada(r, id_hogar, dia)
            jornada = next(j for j in self._jornadas(r, h) if j.dia_encuesta == dia)
            return {"jornada": jornada, "gastos": r.gastos(id_hogar, dia), "comidas": r.comidas(id_hogar, dia)}

    def _validar_captura(self, r: Repositorio, u: Usuario, id_hogar: int, dia: int, *roles: str) -> Hogar:
        # Mismo orden de comprobación que PR_REGISTRAR_GASTO y TRG_GD_CAPTURA_ABIERTA.
        h = self._autorizar(r, u, id_hogar, *roles)
        self._jornada(r, id_hogar, dia)
        if fecha_dia(h.fecha_inicio, dia) > r.hoy():
            raise ErrorNegocio("No se registran gastos de un día futuro", "ORA-20063")
        self._captura_abierta(h)
        return h

    def _catalogos_renglon(self, r: Repositorio, dto):
        self._catalogo(r, "forma_adquisicion", dto.cod_forma, "La forma de adquisición")
        self._catalogo(r, "lugar_compra", dto.cod_lugar, "El lugar de compra")
        self._catalogo(r, "frecuencia_compra", dto.cod_frecuencia, "La frecuencia")

    def registrar_gasto(self, u: Usuario, id_hogar: int, dia: int, dto: GastoEntrada):
        validar_gasto(dto, dia)
        with self.repo.transaccion() as r:
            self._validar_captura(r, u, id_hogar, dia, INFORMANTE, ENCUESTADOR)
            self._catalogo(r, "unidad_medida", dto.cod_unidad, "La unidad")
            self._catalogos_renglon(r, dto)
            orden = r.registrar_gasto(id_hogar, dia, u.id_usuario, dto)
            return next(g for g in r.gastos(id_hogar, dia) if g.numero_orden == orden)

    def actualizar_gasto(self, u: Usuario, id_hogar: int, dia: int, orden: int, dto: GastoEntrada):
        """CU-07: el encuestador corrige un renglón; queda registrado como autor de la corrección."""
        validar_gasto(dto, dia)
        with self.repo.transaccion() as r:
            self._validar_captura(r, u, id_hogar, dia, ENCUESTADOR)
            self._catalogo(r, "unidad_medida", dto.cod_unidad, "La unidad")
            self._catalogos_renglon(r, dto)
            r.actualizar_gasto(id_hogar, dia, orden, u.id_usuario, dto)
            return next(g for g in r.gastos(id_hogar, dia) if g.numero_orden == orden)

    def eliminar_gasto(self, u: Usuario, id_hogar: int, dia: int, orden: int):
        with self.repo.transaccion() as r:
            self._validar_captura(r, u, id_hogar, dia, ENCUESTADOR)
            r.eliminar_gasto(id_hogar, dia, orden)

    def registrar_comida(self, u: Usuario, id_hogar: int, dia: int, dto: ComidaEntrada):
        validar_comida(dto, dia)
        with self.repo.transaccion() as r:
            self._validar_captura(r, u, id_hogar, dia, INFORMANTE, ENCUESTADOR)
            self._catalogo(r, "tipo_comida", dto.cod_tipo_comida, "El tipo de comida")
            self._catalogos_renglon(r, dto)
            orden = r.registrar_comida(id_hogar, dia, u.id_usuario, dto)
            return next(c for c in r.comidas(id_hogar, dia) if c.numero_orden == orden)

    def actualizar_comida(self, u: Usuario, id_hogar: int, dia: int, orden: int, dto: ComidaEntrada):
        validar_comida(dto, dia)
        with self.repo.transaccion() as r:
            self._validar_captura(r, u, id_hogar, dia, ENCUESTADOR)
            self._catalogo(r, "tipo_comida", dto.cod_tipo_comida, "El tipo de comida")
            self._catalogos_renglon(r, dto)
            r.actualizar_comida(id_hogar, dia, orden, u.id_usuario, dto)
            return next(c for c in r.comidas(id_hogar, dia) if c.numero_orden == orden)

    def eliminar_comida(self, u: Usuario, id_hogar: int, dia: int, orden: int):
        with self.repo.transaccion() as r:
            self._validar_captura(r, u, id_hogar, dia, ENCUESTADOR)
            r.eliminar_comida(id_hogar, dia, orden)

    def cerrar_jornada(self, u: Usuario, id_hogar: int, dia: int, dto: CierreJornada) -> Jornada:
        """Control del formulario: el total declarado debe coincidir con lo registrado."""
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, INFORMANTE, ENCUESTADOR)
            self._captura_abierta(h)
            self._jornada(r, id_hogar, dia)
            registrados = self._renglones(r, id_hogar, dia)
            if dto.total_renglones != registrados:
                raise ErrorNegocio(f"Total declarado ({dto.total_renglones}) distinto de los renglones registrados "
                                   f"({registrados}) en el día {dia}", "ORA-20065")
            r.cerrar_jornada(id_hogar, dia, u.id_usuario, dto.total_renglones, dto.observaciones)
            return next(j for j in self._jornadas(r, h) if j.dia_encuesta == dia)

    # ================================================================ CU-08 cierre (D2)
    def cierre(self, u: Usuario, id_hogar: int):
        with self.repo.transaccion() as r:
            self._ver(r, u, id_hogar)
            return r.cierre(id_hogar)

    def cerrar_cuadernillo(self, u: Usuario, id_hogar: int, dto: CierreEntrada) -> Hogar:
        validar_cierre(dto)
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, ENCUESTADOR)
            if h.estado not in ESTADOS_CAPTURA_ABIERTA:
                raise Conflicto(f"Solo se cierra un hogar EN_CAPTURA o DEVUELTO (actual: {h.estado})", "ORA-20066")
            completos = sum(j.completa for j in self._jornadas(r, h))
            if completos < DIAS:
                raise ErrorNegocio(f"Faltan jornadas por completar: {completos} de 14 cerradas y coincidentes",
                                   "ORA-20067")
            grupos = len(r.caracteristicas(id_hogar))
            if grupos < GRUPOS_CAPITULO_C:
                raise ErrorNegocio(f"Capítulo C incompleto: {grupos} de 25 grupos", "ORA-20068")
            self._catalogo(r, "forma_pago", dto.cod_forma_pago, "La forma de pago")
            r.cerrar_cuadernillo(id_hogar, u.id_usuario, dto)
            return r.hogar(id_hogar)

    # ================================================================ CU-11 y CU-09 supervisor
    def revisar_caso(self, u: Usuario, id_hogar: int) -> dict:
        """CU-11: integridad del caso antes de aprobar o devolver."""
        with self.repo.transaccion() as r:
            h = self._ver(r, u, id_hogar)
            avance = self._avance(r, h)
            revisiones = r.revisiones(id_hogar)
            en_curso = any(x.estado == "EN_REVISION" for x in revisiones)
            verificaciones = [
                {"control": "Hogar cerrado por el encuestador", "cumple": h.estado == "CERRADO"},
                {"control": "14 jornadas completas", "cumple": avance.dias_completos == DIAS},
                {"control": "25 grupos del capítulo C", "cumple": avance.grupos_capitulo_c == GRUPOS_CAPITULO_C},
                {"control": "Sin hallazgos de crítica ABIERTO", "cumple": avance.hallazgos_abiertos == 0},
                {"control": "Sin revisión de crítica en curso", "cumple": not en_curso},
            ]
            return {"hogar": h, "avance": avance, "cierre": r.cierre(id_hogar), "revisiones": revisiones,
                    "verificaciones": verificaciones, "puede_aprobar": all(v["cumple"] for v in verificaciones)}

    def decidir_supervisor(self, u: Usuario, id_hogar: int, dto: DecisionSupervisor) -> Hogar:
        if dto.decision == "DEVUELTO" and not dto.observacion:
            raise ErrorNegocio("Devolver un caso exige el motivo (CK_CC_DEVUELTO)", "ORA-02290")
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, SUPERVISOR)
            if h.estado != "CERRADO":
                raise Conflicto(f"Solo se revisa un hogar CERRADO (actual: {h.estado})", "ORA-20069")
            if dto.decision == "APROBADO":
                abiertos = self._abiertos(r, id_hogar)
                if abiertos:
                    raise Conflicto(f"No se aprueba: hay {abiertos} hallazgos de crítica ABIERTO", "ORA-20071")
                if any(x.estado == "EN_REVISION" for x in r.revisiones(id_hogar)):
                    raise Conflicto("No se aprueba: hay una revisión de crítica en curso", "ORA-20072")
            r.revisar_supervisor(id_hogar, u.id_usuario, dto.decision, dto.observacion)
            return r.hogar(id_hogar)

    # ================================================================ CU-12 a CU-14 crítica, CU-07 corrección
    def revisiones(self, u: Usuario, id_hogar: int):
        with self.repo.transaccion() as r:
            self._ver(r, u, id_hogar)
            return r.revisiones(id_hogar)

    def iniciar_revision(self, u: Usuario, id_hogar: int):
        with self.repo.transaccion() as r:
            h = self._autorizar(r, u, id_hogar, CRITICO)
            if h.estado != "CERRADO":
                raise Conflicto(f"La crítica se realiza sobre un hogar CERRADO (actual: {h.estado})", "ORA-20073")
            if any(x.estado == "EN_REVISION" for x in r.revisiones(id_hogar)):
                raise Conflicto("Ya existe una revisión EN_REVISION para el hogar", "ORA-20074")
            numero = r.iniciar_revision(id_hogar, u.id_usuario)
            return next(x for x in r.revisiones(id_hogar) if x.numero_revision == numero)

    def _revision_propia(self, r: Repositorio, u: Usuario, id_hogar: int, numero: int):
        self._autorizar(r, u, id_hogar, CRITICO)
        rev = next((x for x in r.revisiones(id_hogar) if x.numero_revision == numero), None)
        if rev is None:
            raise NoEncontrado(f"No existe la revisión {numero} del hogar", "ORA-20076")
        if rev.id_critico != u.id_usuario:
            raise NoAutorizado("Solo el autor de la revisión puede modificarla", "ORA-20075")
        if rev.estado != "EN_REVISION":
            raise Conflicto("Revisión concluida: es inmutable; inicie una nueva revisión", "ORA-20032")
        return rev

    def registrar_hallazgo(self, u: Usuario, id_hogar: int, numero: int, dto: HallazgoEntrada):
        validar_hallazgo(dto)
        with self.repo.transaccion() as r:
            self._revision_propia(r, u, id_hogar, numero)
            if dto.dia_encuesta is not None and dto.dia_encuesta not in r.jornadas(id_hogar):
                raise ErrorNegocio(f"El día {dto.dia_encuesta} no tiene jornada en este hogar (FK_HC_JORNADA)",
                                   "ORA-02291")
            n = r.registrar_hallazgo(id_hogar, numero, u.id_usuario, dto)
            return buscar_hallazgo(r.revisiones(id_hogar), numero, n)[1]

    def concluir_revision(self, u: Usuario, id_hogar: int, numero: int, dto: Conclusion):
        with self.repo.transaccion() as r:
            self._revision_propia(r, u, id_hogar, numero)
            r.concluir_revision(id_hogar, numero, u.id_usuario, dto.resultado)
            return next(x for x in r.revisiones(id_hogar) if x.numero_revision == numero)

    def _hallazgo(self, r: Repositorio, id_hogar: int, numero: int, hallazgo: int):
        encontrado = buscar_hallazgo(r.revisiones(id_hogar), numero, hallazgo)
        if encontrado is None:
            raise NoEncontrado("No existe el hallazgo indicado", "ORA-20077")
        return encontrado[1]

    def corregir_hallazgo(self, u: Usuario, id_hogar: int, numero: int, hallazgo: int, dto: Correccion):
        """CU-07: el responsable asignado declara la corrección; el crítico la verifica después."""
        with self.repo.transaccion() as r:
            self._autorizar(r, u, id_hogar, ENCUESTADOR, INFORMANTE)
            h = self._hallazgo(r, id_hogar, numero, hallazgo)
            if h.estado != "ABIERTO":
                raise Conflicto(f"Transición no permitida: {h.estado} -> CORREGIDO", "ORA-20045")
            r.corregir_hallazgo(id_hogar, numero, hallazgo, u.id_usuario, dto.respuesta)
            return self._hallazgo(r, id_hogar, numero, hallazgo)

    def verificar_hallazgo(self, u: Usuario, id_hogar: int, numero: int, hallazgo: int, dto: Verificacion):
        with self.repo.transaccion() as r:
            self._autorizar(r, u, id_hogar, CRITICO)
            if self._hallazgo(r, id_hogar, numero, hallazgo).estado != "CORREGIDO":
                raise Conflicto("Solo se verifica un hallazgo existente en estado CORREGIDO", "ORA-20078")
            r.verificar_hallazgo(id_hogar, numero, hallazgo, u.id_usuario, dto.aceptada, dto.comentario)
            return self._hallazgo(r, id_hogar, numero, hallazgo)

    # ================================================================ reportes
    def reporte(self, u: Usuario, nombre: str) -> list[dict]:
        if nombre not in REPORTES:
            raise NoEncontrado(f"No existe el reporte {nombre}")
        self._exigir_rol(u, *sorted(REPORTES[nombre]))
        with self.repo.transaccion() as r:
            return r.reporte(nombre)
