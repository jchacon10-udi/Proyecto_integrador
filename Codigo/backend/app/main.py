"""Adaptador HTTP. Toda escritura es exclusivamente en memoria DEMO."""
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from .auth import AuthService
from .domain import Session, GastoInput, Gasto, ConflictError
from .repository import MemoryRepository
from .services import CapturaService

class LoginInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    usuario: str=Field(min_length=1,max_length=40)
    password: str=Field(min_length=1,max_length=200)

def create_app(mode: str="demo") -> FastAPI:
    if mode!="demo":
        raise RuntimeError("Oracle bloqueado: faltan metadatos, adaptador compatible y autorización. Sin fallback demo.")
    app=FastAPI(title="ENPH DEMO — CU-05, sin Oracle",version="0.1.0")
    app.add_middleware(CORSMiddleware,allow_origins=["http://127.0.0.1:5173","http://localhost:5173"],allow_methods=["GET","POST","PUT","DELETE"],allow_headers=["Authorization","Content-Type"])
    auth=AuthService();repository=MemoryRepository();service=CapturaService(repository)
    bearer=HTTPBearer(auto_error=False)
    app.state.repository=repository

    def session(credentials: Annotated[HTTPAuthorizationCredentials | None,Depends(bearer)]):
        if credentials is None:
            raise HTTPException(401,"Sesión demo requerida",headers={"WWW-Authenticate":"Bearer"})
        try:return auth.resolve(credentials.credentials)
        except PermissionError:
            raise HTTPException(401,"Sesión inválida o expirada",headers={"WWW-Authenticate":"Bearer"})

    CurrentSession=Annotated[Session,Depends(session)]

    @app.exception_handler(ConflictError)
    async def conflict(request,exc):return JSONResponse(status_code=409,content={"detail":str(exc)})

    @app.exception_handler(PermissionError)
    async def forbidden(request,exc):return JSONResponse(status_code=403,content={"detail":"Operación no autorizada para este perfil/hogar"})

    @app.exception_handler(ValueError)
    async def invalid(request,exc):return JSONResponse(status_code=422,content={"detail":str(exc)})

    @app.exception_handler(KeyError)
    async def missing(request,exc):return JSONResponse(status_code=404,content={"detail":"Registro no disponible"})

    @app.get("/api/health")
    def health():return {"mode":"demo","oracle_connected":False,"vertical":"CU-05"}

    @app.post("/api/demo/login")
    def login(dto: LoginInput):
        try:return {"token":auth.login(dto.usuario,dto.password),"expires_in":1200,"mode":"demo"}
        except PermissionError:raise HTTPException(401,"Credenciales demo inválidas")

    @app.get("/api/context")
    def context(s: CurrentSession):
        return {"mode":"demo","rol":s.rol,"usuario_id":s.usuario_id,"hogares":sorted(s.hogares),"can_capture":s.rol=="Informante del hogar","jornadas":[{"id":j.id,"dia":j.dia,"hogar_id":j.hogar_id,"fecha":j.fecha.isoformat()} for j in repository.jornadas.values() if j.hogar_id in s.hogares],"unidades":repository.unidades,"formas":repository.formas,"lugares":repository.lugares,"frecuencias":repository.frecuencias}

    @app.get("/api/hogares/{hogar_id}/jornadas/{jornada_id}/gastos",response_model=list[Gasto])
    def list_gastos(hogar_id:int,jornada_id:int,s:CurrentSession):return service.list(s,hogar_id,jornada_id)

    @app.post("/api/hogares/{hogar_id}/jornadas/{jornada_id}/gastos",response_model=Gasto,status_code=201)
    def create_gasto(hogar_id:int,jornada_id:int,dto:GastoInput,s:CurrentSession):return service.create(s,hogar_id,jornada_id,dto)

    @app.put("/api/gastos/{gasto_id}",response_model=Gasto)
    def update_gasto(gasto_id:int,dto:GastoInput,s:CurrentSession):return service.update(s,gasto_id,dto)

    @app.delete("/api/gastos/{gasto_id}",status_code=204)
    def delete_gasto(gasto_id:int,s:CurrentSession):
        service.delete(s,gasto_id)
        return Response(status_code=204)

    return app
