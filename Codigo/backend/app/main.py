"""API HTTP del sistema ENPH (FastAPI). Traduce solicitudes a los servicios de casos de uso.

Modo de datos (variable ENPH_MODO):
  memoria  datos de prueba en memoria (por defecto; se pierden al reiniciar)
  oracle   esquema ENPH en Oracle (ver app/repositorio/oracle.py y config.py)
"""
from typing import Annotated

from fastapi import Depends, FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config
from .errores import CredencialesInvalidas, ErrorNegocio
from .modelos import (Asignacion, CaracteristicaEntrada, CierreEntrada, CierreJornada, ComidaEntrada, Conclusion,
                      Correccion, Credenciales, DecisionSupervisor, EstadoUsuario, GastoEntrada, HallazgoEntrada,
                      HogarActualizacion, HogarNuevo, ResumenEntrada, Usuario, UsuarioNuevo, Verificacion, VisitaEntrada)
from .servicios import Servicios


def crear_servicios(modo: str) -> Servicios:
    if modo == "memoria":
        from .datos_prueba import cargar
        from .repositorio.memoria import RepositorioMemoria
        servicios = Servicios(RepositorioMemoria())
        cargar(servicios)
        return servicios
    if modo == "oracle":
        from .repositorio.oracle import RepositorioOracle
        return Servicios(RepositorioOracle(config.oracle()))
    raise RuntimeError(f"ENPH_MODO desconocido: {modo}")


def create_app(modo: str | None = None, servicios: Servicios | None = None) -> FastAPI:
    modo = modo or config.modo()
    s = servicios or crear_servicios(modo)
    app = FastAPI(title="ENPH Cuadernillo 2 urbano", version="1.0.0")
    app.state.servicios = s
    app.add_middleware(CORSMiddleware, allow_origins=config.origenes(), allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])
    portador = HTTPBearer(auto_error=False)

    @app.exception_handler(ErrorNegocio)
    async def error_negocio(_, exc: ErrorNegocio):
        return JSONResponse(status_code=exc.estado_http, content={"detail": exc.mensaje, "codigo": exc.codigo})

    @app.exception_handler(RequestValidationError)
    async def error_validacion(_, exc: RequestValidationError):
        campos = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
        return JSONResponse(status_code=422, content={"detail": campos, "codigo": "VALIDACION"})

    def sesion(cred: Annotated[HTTPAuthorizationCredentials | None, Depends(portador)]) -> Usuario:
        if cred is None:
            raise CredencialesInvalidas("Inicie sesión")
        return s.usuario_de_token(cred.credentials)

    U = Annotated[Usuario, Depends(sesion)]

    # ------------------------------------------------------------ CU-01
    @app.get("/api/salud")
    def salud():
        return {"modo": modo, "estado": "ok"}

    @app.post("/api/sesion")
    def iniciar_sesion(dto: Credenciales):
        token, usuario = s.iniciar_sesion(dto.usuario, dto.clave)
        return {"token": token, "usuario": usuario}

    @app.get("/api/sesion")
    def sesion_actual(u: U):
        return {"usuario": u}

    @app.delete("/api/sesion", status_code=204)
    def cerrar_sesion(cred: Annotated[HTTPAuthorizationCredentials | None, Depends(portador)]):
        if cred:
            s.cerrar_sesion(cred.credentials)
        return Response(status_code=204)

    @app.get("/api/catalogos")
    def catalogos(u: U):
        return s.catalogos()

    @app.get("/api/usuarios")
    def usuarios(u: U):
        return s.usuarios(u)

    @app.post("/api/usuarios", status_code=201)
    def crear_usuario(dto: UsuarioNuevo, u: U):
        return s.crear_usuario(u, dto)

    @app.put("/api/usuarios/{id_usuario}/estado")
    def estado_usuario(id_usuario: int, dto: EstadoUsuario, u: U):
        return s.cambiar_estado_usuario(u, id_usuario, dto.estado)

    # ------------------------------------------------------------ hogares, CU-02, CU-10
    @app.get("/api/hogares")
    def hogares(u: U):
        return s.hogares(u)

    @app.post("/api/hogares", status_code=201)
    def crear_hogar(dto: HogarNuevo, u: U):
        return s.crear_hogar(u, dto)

    @app.get("/api/hogares/{id_hogar}")
    def hogar(id_hogar: int, u: U):
        return s.hogar(u, id_hogar)

    @app.put("/api/hogares/{id_hogar}")
    def actualizar_hogar(id_hogar: int, dto: HogarActualizacion, u: U):
        return s.actualizar_hogar(u, id_hogar, dto)

    @app.post("/api/hogares/{id_hogar}/asignaciones", status_code=204)
    def asignar(id_hogar: int, dto: Asignacion, u: U):
        s.asignar(u, id_hogar, dto.id_usuario)
        return Response(status_code=204)

    @app.post("/api/hogares/{id_hogar}/iniciar-captura")
    def iniciar_captura(id_hogar: int, u: U):
        return s.iniciar_captura(u, id_hogar)

    @app.get("/api/hogares/{id_hogar}/avance")
    def avance(id_hogar: int, u: U):
        return s.avance(u, id_hogar)

    # ------------------------------------------------------------ CU-03
    @app.get("/api/hogares/{id_hogar}/visitas")
    def visitas(id_hogar: int, u: U):
        return s.visitas(u, id_hogar)

    @app.post("/api/hogares/{id_hogar}/visitas", status_code=201)
    def registrar_visita(id_hogar: int, dto: VisitaEntrada, u: U):
        return s.registrar_visita(u, id_hogar, dto)

    @app.put("/api/hogares/{id_hogar}/visitas/{numero}")
    def actualizar_visita(id_hogar: int, numero: int, dto: VisitaEntrada, u: U):
        return s.actualizar_visita(u, id_hogar, numero, dto)

    # ------------------------------------------------------------ CU-04
    @app.get("/api/hogares/{id_hogar}/caracteristicas")
    def caracteristicas(id_hogar: int, u: U):
        return s.caracteristicas(u, id_hogar)

    @app.put("/api/hogares/{id_hogar}/caracteristicas/{cod_grupo}")
    def guardar_caracteristica(id_hogar: int, cod_grupo: str, dto: CaracteristicaEntrada, u: U):
        return s.guardar_caracteristica(u, id_hogar, cod_grupo, dto)

    @app.delete("/api/hogares/{id_hogar}/caracteristicas/{cod_grupo}", status_code=204)
    def eliminar_caracteristica(id_hogar: int, cod_grupo: str, u: U):
        s.eliminar_caracteristica(u, id_hogar, cod_grupo)
        return Response(status_code=204)

    @app.put("/api/hogares/{id_hogar}/resumen-mercado/{cod_mercado}")
    def guardar_resumen(id_hogar: int, cod_mercado: str, dto: ResumenEntrada, u: U):
        return s.guardar_resumen(u, id_hogar, cod_mercado, dto)

    @app.delete("/api/hogares/{id_hogar}/resumen-mercado/{cod_mercado}", status_code=204)
    def eliminar_resumen(id_hogar: int, cod_mercado: str, u: U):
        s.eliminar_resumen(u, id_hogar, cod_mercado)
        return Response(status_code=204)

    # ------------------------------------------------------------ CU-05, CU-06, CU-07 (renglones)
    @app.get("/api/hogares/{id_hogar}/dias/{dia}")
    def dia(id_hogar: int, dia: int, u: U):
        return s.dia(u, id_hogar, dia)

    @app.post("/api/hogares/{id_hogar}/dias/{dia}/gastos", status_code=201)
    def registrar_gasto(id_hogar: int, dia: int, dto: GastoEntrada, u: U):
        return s.registrar_gasto(u, id_hogar, dia, dto)

    @app.put("/api/hogares/{id_hogar}/dias/{dia}/gastos/{orden}")
    def actualizar_gasto(id_hogar: int, dia: int, orden: int, dto: GastoEntrada, u: U):
        return s.actualizar_gasto(u, id_hogar, dia, orden, dto)

    @app.delete("/api/hogares/{id_hogar}/dias/{dia}/gastos/{orden}", status_code=204)
    def eliminar_gasto(id_hogar: int, dia: int, orden: int, u: U):
        s.eliminar_gasto(u, id_hogar, dia, orden)
        return Response(status_code=204)

    @app.post("/api/hogares/{id_hogar}/dias/{dia}/comidas", status_code=201)
    def registrar_comida(id_hogar: int, dia: int, dto: ComidaEntrada, u: U):
        return s.registrar_comida(u, id_hogar, dia, dto)

    @app.put("/api/hogares/{id_hogar}/dias/{dia}/comidas/{orden}")
    def actualizar_comida(id_hogar: int, dia: int, orden: int, dto: ComidaEntrada, u: U):
        return s.actualizar_comida(u, id_hogar, dia, orden, dto)

    @app.delete("/api/hogares/{id_hogar}/dias/{dia}/comidas/{orden}", status_code=204)
    def eliminar_comida(id_hogar: int, dia: int, orden: int, u: U):
        s.eliminar_comida(u, id_hogar, dia, orden)
        return Response(status_code=204)

    @app.post("/api/hogares/{id_hogar}/dias/{dia}/cierre")
    def cerrar_jornada(id_hogar: int, dia: int, dto: CierreJornada, u: U):
        return s.cerrar_jornada(u, id_hogar, dia, dto)

    # ------------------------------------------------------------ CU-08, CU-09, CU-11
    @app.get("/api/hogares/{id_hogar}/cierre")
    def cierre(id_hogar: int, u: U):
        return s.cierre(u, id_hogar)

    @app.post("/api/hogares/{id_hogar}/cierre")
    def cerrar_cuadernillo(id_hogar: int, dto: CierreEntrada, u: U):
        return s.cerrar_cuadernillo(u, id_hogar, dto)

    @app.get("/api/hogares/{id_hogar}/revision-caso")
    def revisar_caso(id_hogar: int, u: U):
        return s.revisar_caso(u, id_hogar)

    @app.post("/api/hogares/{id_hogar}/decision")
    def decidir(id_hogar: int, dto: DecisionSupervisor, u: U):
        return s.decidir_supervisor(u, id_hogar, dto)

    # ------------------------------------------------------------ CU-12, CU-13, CU-14, CU-07 (hallazgos)
    @app.get("/api/hogares/{id_hogar}/revisiones")
    def revisiones(id_hogar: int, u: U):
        return s.revisiones(u, id_hogar)

    @app.post("/api/hogares/{id_hogar}/revisiones", status_code=201)
    def iniciar_revision(id_hogar: int, u: U):
        return s.iniciar_revision(u, id_hogar)

    @app.post("/api/hogares/{id_hogar}/revisiones/{numero}/hallazgos", status_code=201)
    def registrar_hallazgo(id_hogar: int, numero: int, dto: HallazgoEntrada, u: U):
        return s.registrar_hallazgo(u, id_hogar, numero, dto)

    @app.post("/api/hogares/{id_hogar}/revisiones/{numero}/conclusion")
    def concluir(id_hogar: int, numero: int, dto: Conclusion, u: U):
        return s.concluir_revision(u, id_hogar, numero, dto)

    @app.post("/api/hogares/{id_hogar}/revisiones/{numero}/hallazgos/{hallazgo}/correccion")
    def corregir(id_hogar: int, numero: int, hallazgo: int, dto: Correccion, u: U):
        return s.corregir_hallazgo(u, id_hogar, numero, hallazgo, dto)

    @app.post("/api/hogares/{id_hogar}/revisiones/{numero}/hallazgos/{hallazgo}/verificacion")
    def verificar(id_hogar: int, numero: int, hallazgo: int, dto: Verificacion, u: U):
        return s.verificar_hallazgo(u, id_hogar, numero, hallazgo, dto)

    # ------------------------------------------------------------ reportes
    @app.get("/api/reportes/{nombre}")
    def reporte(nombre: str, u: U):
        return s.reporte(u, nombre)

    return app
