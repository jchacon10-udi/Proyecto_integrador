"""Configuración por variables de entorno (archivo .env opcional en backend/).

ENPH_MODO              memoria (por defecto) u oracle
ENPH_ORIGENES          orígenes permitidos para el navegador, separados por comas
ORACLE_DSN             host:puerto/servicio o alias TNS (p. ej. orcl)
ORACLE_USUARIO         usuario de conexión (ENPH_APP en producción)
ORACLE_CLAVE           contraseña; nunca se guarda en el repositorio
ORACLE_ESQUEMA         dueño de los objetos (ENPH); se usa como prefijo
ORACLE_CLIENTE         carpeta de Oracle Instant Client: activa el modo thick,
                       obligatorio para Oracle 10g (el modo thin exige 12.1 o superior)
"""
import os
from dataclasses import dataclass
from pathlib import Path


def _cargar_env():
    archivo = Path(__file__).resolve().parent.parent / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.strip() and not linea.lstrip().startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()


@dataclass(frozen=True)
class ConfigOracle:
    dsn: str
    usuario: str
    clave: str
    esquema: str = "ENPH"
    cliente: str | None = None


def modo() -> str:
    return os.environ.get("ENPH_MODO", "memoria")


def origenes() -> list[str]:
    return os.environ.get("ENPH_ORIGENES", "http://127.0.0.1:5173,http://localhost:5173").split(",")


def oracle() -> ConfigOracle:
    faltan = [v for v in ("ORACLE_DSN", "ORACLE_USUARIO", "ORACLE_CLAVE") if not os.environ.get(v)]
    if faltan:
        raise RuntimeError(f"Modo oracle: faltan las variables {', '.join(faltan)}")
    return ConfigOracle(dsn=os.environ["ORACLE_DSN"], usuario=os.environ["ORACLE_USUARIO"],
                        clave=os.environ["ORACLE_CLAVE"], esquema=os.environ.get("ORACLE_ESQUEMA", "ENPH"),
                        cliente=os.environ.get("ORACLE_CLIENTE") or None)
