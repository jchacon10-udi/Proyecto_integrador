"""CU-01. Contraseñas PBKDF2 (formato de USUARIO.CLAVE_HASH) y sesiones con token opaco."""
import hashlib
import hmac
import secrets
import time
from threading import RLock

from .errores import CredencialesInvalidas
from .modelos import Usuario

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 200_000
DURACION_SESION = 8 * 3600


def generar_hash(clave: str, sal: str | None = None, iteraciones: int = ITERACIONES) -> str:
    sal = sal or secrets.token_hex(8)
    derivada = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), iteraciones).hex()
    return f"{ALGORITMO}${iteraciones}${sal}${derivada}"


def verificar_clave(clave: str, clave_hash: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = clave_hash.split("$")
    except ValueError:
        return False
    if algoritmo != ALGORITMO:
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), int(iteraciones)).hex()
    return hmac.compare_digest(calculado, esperado)


class Sesiones:
    """Tokens en memoria del proceso; una sesión vence a las 8 horas."""

    def __init__(self, reloj=time.monotonic):
        self._reloj = reloj
        self._bloqueo = RLock()
        self._sesiones: dict[str, tuple[int, float]] = {}

    def abrir(self, usuario: Usuario) -> str:
        token = secrets.token_urlsafe(32)
        with self._bloqueo:
            ahora = self._reloj()
            self._sesiones = {t: v for t, v in self._sesiones.items() if v[1] > ahora}
            self._sesiones[token] = (usuario.id_usuario, ahora + DURACION_SESION)
        return token

    def usuario(self, token: str) -> int:
        with self._bloqueo:
            valor = self._sesiones.get(token)
            if not valor or valor[1] <= self._reloj():
                self._sesiones.pop(token, None)
                raise CredencialesInvalidas("Sesión inválida o vencida")
            return valor[0]

    def cerrar(self, token: str):
        with self._bloqueo:
            self._sesiones.pop(token, None)
